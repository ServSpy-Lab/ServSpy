/*
 * ss_ecdh.c - ECDH key agreement (EVP high-level API), HKDF-SHA256
 * session key derivation, and AES-256-GCM seal/open bound to the
 * key pair.
 */
#include "ss_ecdh.h"

#include <limits.h>
#include <stdlib.h>
#include <string.h>

#include <openssl/bio.h>
#include <openssl/err.h>
#include <openssl/evp.h>
#include <openssl/obj_mac.h>
#include <openssl/pem.h>
#include <openssl/rand.h>
#include <openssl/x509.h>

#define SS_ECDH_SALT_LEN 16u
#define SS_ECDH_IV_LEN 12u
#define SS_ECDH_TAG_LEN 16u
#define SS_ECDH_KEY_LEN 32u /* AES-256 */

struct ss_ecdh_keypair {
    EVP_PKEY *pkey;
};

struct ss_ecdh_pubkey {
    EVP_PKEY *pkey;
};

static int curve_nid(const char *curve) {
    if (curve == NULL || strcmp(curve, SS_ECDH_CURVE_P256) == 0) {
        return NID_X9_62_prime256v1;
    }
    if (strcmp(curve, SS_ECDH_CURVE_P384) == 0) {
        return NID_secp384r1;
    }
    if (strcmp(curve, SS_ECDH_CURVE_P521) == 0) {
        return NID_secp521r1;
    }
    return 0;
}

ss_err_t ss_ecdh_keypair_generate(const char *curve, ss_ecdh_keypair_t **out_kp) {
    if (out_kp == NULL) {
        return SS_ERR_INVALID_ARG;
    }
    int nid = curve_nid(curve);
    if (nid == 0) {
        return SS_ERR_UNSUPPORTED;
    }
    EVP_PKEY_CTX *ctx = EVP_PKEY_CTX_new_id(EVP_PKEY_EC, NULL);
    if (ctx == NULL) {
        return SS_ERR_OPENSSL;
    }
    if (EVP_PKEY_keygen_init(ctx) <= 0 ||
        EVP_PKEY_CTX_set_ec_paramgen_curve_nid(ctx, nid) <= 0) {
        EVP_PKEY_CTX_free(ctx);
        return SS_ERR_OPENSSL;
    }
    EVP_PKEY *pkey = NULL;
    if (EVP_PKEY_keygen(ctx, &pkey) <= 0 || pkey == NULL) {
        EVP_PKEY_free(pkey);
        EVP_PKEY_CTX_free(ctx);
        return SS_ERR_OPENSSL;
    }
    EVP_PKEY_CTX_free(ctx);

    ss_ecdh_keypair_t *kp = (ss_ecdh_keypair_t *)calloc(1, sizeof(*kp));
    if (kp == NULL) {
        EVP_PKEY_free(pkey);
        return SS_ERR_NOMEM;
    }
    kp->pkey = pkey;
    *out_kp = kp;
    return SS_OK;
}

ss_err_t ss_ecdh_pub_to_pem(const ss_ecdh_keypair_t *kp, char **out_pem) {
    if (kp == NULL || kp->pkey == NULL || out_pem == NULL) {
        return SS_ERR_INVALID_ARG;
    }
    BIO *bio = BIO_new(BIO_s_mem());
    if (bio == NULL) {
        return SS_ERR_NOMEM;
    }
    if (PEM_write_bio_PUBKEY(bio, kp->pkey) <= 0) {
        BIO_free(bio);
        return SS_ERR_OPENSSL;
    }
    char *data = NULL;
    long n = BIO_get_mem_data(bio, &data);
    if (n <= 0) {
        BIO_free(bio);
        return SS_ERR_OPENSSL;
    }
    char *out = (char *)malloc((size_t)n + 1);
    if (out == NULL) {
        BIO_free(bio);
        return SS_ERR_NOMEM;
    }
    memcpy(out, data, (size_t)n);
    out[n] = '\0';
    BIO_free(bio);
    *out_pem = out;
    return SS_OK;
}

ss_err_t ss_ecdh_pub_from_pem(const char *pem, ss_ecdh_pubkey_t **out_pub) {
    if (pem == NULL || out_pub == NULL) {
        return SS_ERR_INVALID_ARG;
    }
    BIO *bio = BIO_new_mem_buf(pem, -1);
    if (bio == NULL) {
        return SS_ERR_NOMEM;
    }
    EVP_PKEY *pkey = PEM_read_bio_PUBKEY(bio, NULL, NULL, NULL);
    BIO_free(bio);
    if (pkey == NULL) {
        return SS_ERR_PARSE;
    }
    if (EVP_PKEY_base_id(pkey) != EVP_PKEY_EC) {
        EVP_PKEY_free(pkey);
        return SS_ERR_UNSUPPORTED;
    }
    /* Reject points that are not on the curve (invalid-curve defense). */
    EVP_PKEY_CTX *chk = EVP_PKEY_CTX_new(pkey, NULL);
    if (chk == NULL) {
        EVP_PKEY_free(pkey);
        return SS_ERR_OPENSSL;
    }
    int rc = EVP_PKEY_public_check(chk);
    EVP_PKEY_CTX_free(chk);
    if (rc != 1) {
        EVP_PKEY_free(pkey);
        return SS_ERR_PARSE;
    }

    ss_ecdh_pubkey_t *pub = (ss_ecdh_pubkey_t *)calloc(1, sizeof(*pub));
    if (pub == NULL) {
        EVP_PKEY_free(pkey);
        return SS_ERR_NOMEM;
    }
    pub->pkey = pkey;
    *out_pub = pub;
    return SS_OK;
}

static ss_err_t read_private_key(const char *path, const char *passphrase,
                                 ss_ecdh_keypair_t **out_kp) {
    if (path == NULL || out_kp == NULL) {
        return SS_ERR_INVALID_ARG;
    }
    BIO *bio = BIO_new_file(path, "rb");
    if (bio == NULL) {
        return SS_ERR_IO;
    }
    EVP_PKEY *pkey = PEM_read_bio_PrivateKey(bio, NULL, NULL, (void *)passphrase);
    BIO_free(bio);
    if (pkey == NULL) {
        return SS_ERR_PARSE; /* covers malformed PEM and wrong passphrase */
    }
    if (EVP_PKEY_base_id(pkey) != EVP_PKEY_EC) {
        EVP_PKEY_free(pkey);
        return SS_ERR_UNSUPPORTED;
    }
    ss_ecdh_keypair_t *kp = (ss_ecdh_keypair_t *)calloc(1, sizeof(*kp));
    if (kp == NULL) {
        EVP_PKEY_free(pkey);
        return SS_ERR_NOMEM;
    }
    kp->pkey = pkey;
    *out_kp = kp;
    return SS_OK;
}

ss_err_t ss_ecdh_keypair_write_priv(const ss_ecdh_keypair_t *kp, const char *path,
                                    const char *passphrase) {
    if (kp == NULL || kp->pkey == NULL || path == NULL) {
        return SS_ERR_INVALID_ARG;
    }
    BIO *bio = BIO_new_file(path, "wb");
    if (bio == NULL) {
        return SS_ERR_IO;
    }
    const EVP_CIPHER *cipher = passphrase != NULL ? EVP_aes_256_cbc() : NULL;
    int rc = PEM_write_bio_PKCS8PrivateKey(bio, kp->pkey, cipher, NULL, 0, NULL,
                                           (void *)passphrase);
    BIO_free(bio);
    return rc == 1 ? SS_OK : SS_ERR_OPENSSL;
}

ss_err_t ss_ecdh_keypair_read_priv(const char *path, const char *passphrase,
                                   ss_ecdh_keypair_t **out_kp) {
    return read_private_key(path, passphrase, out_kp);
}

/*
 * Compute the raw ECDH shared secret (malloc'd, caller frees).
 */
static ss_err_t derive_shared_secret(EVP_PKEY *self, EVP_PKEY *peer,
                                     uint8_t **out_secret, size_t *out_len) {
    EVP_PKEY_CTX *ctx = EVP_PKEY_CTX_new(self, NULL);
    if (ctx == NULL) {
        return SS_ERR_OPENSSL;
    }
    if (EVP_PKEY_derive_init(ctx) <= 0 || EVP_PKEY_derive_set_peer(ctx, peer) <= 0) {
        EVP_PKEY_CTX_free(ctx);
        return SS_ERR_OPENSSL;
    }
    size_t secret_len = 0;
    if (EVP_PKEY_derive(ctx, NULL, &secret_len) <= 0 || secret_len == 0) {
        EVP_PKEY_CTX_free(ctx);
        return SS_ERR_OPENSSL;
    }
    uint8_t *secret = (uint8_t *)malloc(secret_len);
    if (secret == NULL) {
        EVP_PKEY_CTX_free(ctx);
        return SS_ERR_NOMEM;
    }
    if (EVP_PKEY_derive(ctx, secret, &secret_len) <= 0) {
        OPENSSL_cleanse(secret, secret_len);
        free(secret);
        EVP_PKEY_CTX_free(ctx);
        return SS_ERR_OPENSSL;
    }
    EVP_PKEY_CTX_free(ctx);
    *out_secret = secret;
    *out_len = secret_len;
    return SS_OK;
}

/*
 * HKDF info binding: DER encodings of both public keys, byte-sorted so
 * that the two peers construct identical info regardless of call order.
 */
static ss_err_t build_key_binding_info(EVP_PKEY *a, EVP_PKEY *b,
                                       uint8_t **out_info, size_t *out_len) {
    uint8_t *der_a = NULL;
    uint8_t *der_b = NULL;
    int len_a = i2d_PUBKEY(a, &der_a);
    int len_b = i2d_PUBKEY(b, &der_b);
    if (len_a <= 0 || len_b <= 0) {
        OPENSSL_free(der_a);
        OPENSSL_free(der_b);
        return SS_ERR_OPENSSL;
    }
    const uint8_t *first;
    const uint8_t *second;
    size_t first_len, second_len;
    if ((size_t)len_a < (size_t)len_b ||
        ((size_t)len_a == (size_t)len_b && memcmp(der_a, der_b, (size_t)len_a) < 0)) {
        first = der_a;
        first_len = (size_t)len_a;
        second = der_b;
        second_len = (size_t)len_b;
    } else {
        first = der_b;
        first_len = (size_t)len_b;
        second = der_a;
        second_len = (size_t)len_a;
    }
    uint8_t *info = (uint8_t *)malloc(first_len + second_len);
    if (info == NULL) {
        OPENSSL_free(der_a);
        OPENSSL_free(der_b);
        return SS_ERR_NOMEM;
    }
    memcpy(info, first, first_len);
    memcpy(info + first_len, second, second_len);
    OPENSSL_free(der_a);
    OPENSSL_free(der_b);
    *out_info = info;
    *out_len = first_len + second_len;
    return SS_OK;
}

ss_err_t ss_ecdh_derive_key(const ss_ecdh_keypair_t *self, const ss_ecdh_pubkey_t *peer,
                            const uint8_t *salt, size_t salt_len,
                            const uint8_t *info, size_t info_len,
                            uint8_t *out_key, size_t out_key_len) {
    if (self == NULL || self->pkey == NULL || peer == NULL || peer->pkey == NULL ||
        out_key == NULL) {
        return SS_ERR_INVALID_ARG;
    }
    if (out_key_len == 0 || out_key_len > SS_CRYPTO_HKDF_SHA256_MAX_OUT) {
        return SS_ERR_INVALID_ARG;
    }
    if ((salt_len > 0 && salt == NULL) || (info_len > 0 && info == NULL)) {
        return SS_ERR_INVALID_ARG;
    }
    uint8_t *secret = NULL;
    size_t secret_len = 0;
    ss_err_t err = derive_shared_secret(self->pkey, peer->pkey, &secret, &secret_len);
    if (err != SS_OK) {
        return err;
    }
    err = ss_crypto_hkdf_sha256(secret, secret_len, salt, salt_len, info, info_len,
                                out_key, out_key_len);
    OPENSSL_cleanse(secret, secret_len);
    free(secret);
    return err;
}

/*
 * GCM's output length fits in int for inputs below INT_MAX - 16.
 */
static int gcm_len_ok(size_t len) {
    return len <= (size_t)(INT_MAX - 16);
}

ss_err_t ss_ecdh_seal(const ss_ecdh_keypair_t *self, const ss_ecdh_pubkey_t *peer,
                      const uint8_t *aad, size_t aad_len,
                      const uint8_t *plain, size_t plain_len,
                      uint8_t **out_buf, size_t *out_len) {
    if (self == NULL || self->pkey == NULL || peer == NULL || peer->pkey == NULL ||
        out_buf == NULL || out_len == NULL) {
        return SS_ERR_INVALID_ARG;
    }
    if ((plain_len > 0 && plain == NULL) || (aad_len > 0 && aad == NULL)) {
        return SS_ERR_INVALID_ARG;
    }
    if (plain_len > SIZE_MAX - SS_ECDH_SEAL_OVERHEAD || !gcm_len_ok(plain_len) ||
        !gcm_len_ok(aad_len)) {
        return SS_ERR_INVALID_ARG;
    }

    uint8_t *secret = NULL;
    uint8_t *info = NULL;
    uint8_t *key = NULL;
    uint8_t *buf = NULL;
    EVP_CIPHER_CTX *ctx = NULL;
    size_t secret_len = 0, info_len = 0;
    ss_err_t err;

    err = derive_shared_secret(self->pkey, peer->pkey, &secret, &secret_len);
    if (err != SS_OK) {
        return err;
    }
    err = build_key_binding_info(self->pkey, peer->pkey, &info, &info_len);
    if (err != SS_OK) {
        goto out;
    }
    uint8_t salt[SS_ECDH_SALT_LEN];
    uint8_t iv[SS_ECDH_IV_LEN];
    if (RAND_bytes(salt, sizeof(salt)) != 1 || RAND_bytes(iv, sizeof(iv)) != 1) {
        err = SS_ERR_OPENSSL;
        goto out;
    }
    key = (uint8_t *)malloc(SS_ECDH_KEY_LEN);
    if (key == NULL) {
        err = SS_ERR_NOMEM;
        goto out;
    }
    err = ss_crypto_hkdf_sha256(secret, secret_len, salt, sizeof(salt), info, info_len,
                                key, SS_ECDH_KEY_LEN);
    if (err != SS_OK) {
        goto out;
    }

    size_t total = SS_ECDH_SEAL_OVERHEAD + plain_len;
    buf = (uint8_t *)malloc(total);
    if (buf == NULL) {
        err = SS_ERR_NOMEM;
        goto out;
    }
    memcpy(buf, salt, sizeof(salt));
    memcpy(buf + SS_ECDH_SALT_LEN, iv, sizeof(iv));

    ctx = EVP_CIPHER_CTX_new();
    if (ctx == NULL) {
        err = SS_ERR_NOMEM;
        goto out;
    }
    int len = 0, outlen = 0;
    if (!EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), NULL, key, iv)) {
        err = SS_ERR_OPENSSL;
        goto out;
    }
    if (aad_len > 0 && !EVP_EncryptUpdate(ctx, NULL, &len, aad, (int)aad_len)) {
        err = SS_ERR_OPENSSL;
        goto out;
    }
    if (plain_len > 0 &&
        !EVP_EncryptUpdate(ctx, buf + SS_ECDH_SALT_LEN + SS_ECDH_IV_LEN, &len,
                           plain, (int)plain_len)) {
        err = SS_ERR_OPENSSL;
        goto out;
    }
    outlen = len;
    if (!EVP_EncryptFinal_ex(ctx, buf + SS_ECDH_SALT_LEN + SS_ECDH_IV_LEN + outlen,
                             &len)) {
        err = SS_ERR_OPENSSL;
        goto out;
    }
    outlen += len;
    if (outlen != (int)plain_len ||
        !EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, SS_ECDH_TAG_LEN,
                             buf + SS_ECDH_SALT_LEN + SS_ECDH_IV_LEN + outlen)) {
        err = SS_ERR_OPENSSL;
        goto out;
    }
    *out_buf = buf;
    *out_len = SS_ECDH_SALT_LEN + SS_ECDH_IV_LEN + (size_t)outlen + SS_ECDH_TAG_LEN;
    buf = NULL;
    err = SS_OK;

out:
    if (ctx != NULL) {
        EVP_CIPHER_CTX_free(ctx);
    }
    if (buf != NULL) {
        free(buf);
    }
    if (key != NULL) {
        OPENSSL_cleanse(key, SS_ECDH_KEY_LEN);
        free(key);
    }
    if (info != NULL) {
        free(info);
    }
    if (secret != NULL) {
        OPENSSL_cleanse(secret, secret_len);
        free(secret);
    }
    return err;
}

ss_err_t ss_ecdh_open(const ss_ecdh_keypair_t *self, const ss_ecdh_pubkey_t *peer,
                      const uint8_t *aad, size_t aad_len,
                      const uint8_t *in_buf, size_t in_len,
                      uint8_t **out_plain, size_t *out_len) {
    if (self == NULL || self->pkey == NULL || peer == NULL || peer->pkey == NULL ||
        in_buf == NULL || out_plain == NULL || out_len == NULL) {
        return SS_ERR_INVALID_ARG;
    }
    *out_plain = NULL;
    *out_len = 0;
    if (aad_len > 0 && aad == NULL) {
        return SS_ERR_INVALID_ARG;
    }
    if (in_len < SS_ECDH_SEAL_OVERHEAD) {
        return SS_ERR_INVALID_ARG;
    }
    size_t ct_len = in_len - SS_ECDH_SEAL_OVERHEAD;
    if (!gcm_len_ok(ct_len) || !gcm_len_ok(aad_len)) {
        return SS_ERR_INVALID_ARG;
    }
    const uint8_t *salt = in_buf;
    const uint8_t *iv = in_buf + SS_ECDH_SALT_LEN;
    const uint8_t *ct = in_buf + SS_ECDH_SALT_LEN + SS_ECDH_IV_LEN;
    const uint8_t *tag = ct + ct_len;

    uint8_t *secret = NULL;
    uint8_t *info = NULL;
    uint8_t *key = NULL;
    uint8_t *plain = NULL;
    EVP_CIPHER_CTX *ctx = NULL;
    size_t secret_len = 0, info_len = 0;
    ss_err_t err;

    err = derive_shared_secret(self->pkey, peer->pkey, &secret, &secret_len);
    if (err != SS_OK) {
        return err;
    }
    err = build_key_binding_info(self->pkey, peer->pkey, &info, &info_len);
    if (err != SS_OK) {
        goto out;
    }
    key = (uint8_t *)malloc(SS_ECDH_KEY_LEN);
    if (key == NULL) {
        err = SS_ERR_NOMEM;
        goto out;
    }
    err = ss_crypto_hkdf_sha256(secret, secret_len, salt, SS_ECDH_SALT_LEN, info,
                                info_len, key, SS_ECDH_KEY_LEN);
    if (err != SS_OK) {
        goto out;
    }

    plain = (uint8_t *)malloc(ct_len > 0 ? ct_len : 1);
    if (plain == NULL) {
        err = SS_ERR_NOMEM;
        goto out;
    }
    ctx = EVP_CIPHER_CTX_new();
    if (ctx == NULL) {
        err = SS_ERR_NOMEM;
        goto out;
    }
    int len = 0, outlen = 0;
    if (!EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(), NULL, key, iv)) {
        err = SS_ERR_OPENSSL;
        goto out;
    }
    if (aad_len > 0 && !EVP_DecryptUpdate(ctx, NULL, &len, aad, (int)aad_len)) {
        err = SS_ERR_OPENSSL;
        goto out;
    }
    if (!EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG, SS_ECDH_TAG_LEN,
                             (void *)tag)) {
        err = SS_ERR_OPENSSL;
        goto out;
    }
    if (ct_len > 0 &&
        !EVP_DecryptUpdate(ctx, plain, &len, ct, (int)ct_len)) {
        err = SS_ERR_OPENSSL;
        goto out;
    }
    outlen = len;
    if (!EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG, SS_ECDH_TAG_LEN,
                             (void *)tag)) {
        err = SS_ERR_OPENSSL;
        goto out;
    }
    if (!EVP_DecryptFinal_ex(ctx, plain + outlen, &len)) {
        err = SS_ERR_AUTH_FAILED; /* tampered data or wrong peer key */
        goto out;
    }
    outlen += len;
    *out_plain = plain;
    *out_len = (size_t)outlen;
    plain = NULL;
    err = SS_OK;

out:
    if (ctx != NULL) {
        EVP_CIPHER_CTX_free(ctx);
    }
    if (plain != NULL) {
        free(plain);
    }
    if (key != NULL) {
        OPENSSL_cleanse(key, SS_ECDH_KEY_LEN);
        free(key);
    }
    if (info != NULL) {
        free(info);
    }
    if (secret != NULL) {
        OPENSSL_cleanse(secret, secret_len);
        free(secret);
    }
    return err;
}

void ss_ecdh_keypair_free(ss_ecdh_keypair_t *kp) {
    if (kp == NULL) {
        return;
    }
    EVP_PKEY_free(kp->pkey);
    free(kp);
}

void ss_ecdh_pubkey_free(ss_ecdh_pubkey_t *pub) {
    if (pub == NULL) {
        return;
    }
    EVP_PKEY_free(pub->pkey);
    free(pub);
}
