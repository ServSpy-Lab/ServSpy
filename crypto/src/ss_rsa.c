/*
 * ss_rsa.c - RSA-OAEP (SHA-256) key management and encryption.
 */
#include "ss_rsa.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <openssl/bio.h>
#include <openssl/err.h>
#include <openssl/evp.h>
#include <openssl/pem.h>
#include <openssl/rsa.h>

struct ss_rsa_key {
    EVP_PKEY *pkey;
};

ss_err_t ss_rsa_keygen(int bits, ss_rsa_key_t **out_key) {
    if (out_key == NULL) {
        return SS_ERR_INVALID_ARG;
    }
    if (bits < (int)SS_RSA_MIN_BITS || bits > (int)SS_RSA_MAX_BITS) {
        return SS_ERR_INVALID_ARG;
    }
    EVP_PKEY_CTX *ctx = EVP_PKEY_CTX_new_id(EVP_PKEY_RSA, NULL);
    if (ctx == NULL) {
        return SS_ERR_OPENSSL;
    }
    if (EVP_PKEY_keygen_init(ctx) <= 0 ||
        EVP_PKEY_CTX_set_rsa_keygen_bits(ctx, bits) <= 0) {
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

    ss_rsa_key_t *key = (ss_rsa_key_t *)calloc(1, sizeof(*key));
    if (key == NULL) {
        EVP_PKEY_free(pkey);
        return SS_ERR_NOMEM;
    }
    key->pkey = pkey;
    *out_key = key;
    return SS_OK;
}

static ss_err_t read_pem_key(const char *path, const char *passphrase, int want_private,
                             ss_rsa_key_t **out_key) {
    if (path == NULL || out_key == NULL) {
        return SS_ERR_INVALID_ARG;
    }
    BIO *bio = BIO_new_file(path, "rb");
    if (bio == NULL) {
        return SS_ERR_IO;
    }
    EVP_PKEY *pkey = NULL;
    if (want_private) {
        pkey = PEM_read_bio_PrivateKey(bio, NULL, NULL, (void *)passphrase);
    } else {
        pkey = PEM_read_bio_PUBKEY(bio, NULL, NULL, NULL);
    }
    BIO_free(bio);
    if (pkey == NULL) {
        /* Covers malformed PEM, wrong type, and wrong passphrase. */
        return SS_ERR_PARSE;
    }
    if (EVP_PKEY_base_id(pkey) != EVP_PKEY_RSA) {
        EVP_PKEY_free(pkey);
        return SS_ERR_UNSUPPORTED;
    }
    ss_rsa_key_t *key = (ss_rsa_key_t *)calloc(1, sizeof(*key));
    if (key == NULL) {
        EVP_PKEY_free(pkey);
        return SS_ERR_NOMEM;
    }
    key->pkey = pkey;
    *out_key = key;
    return SS_OK;
}

ss_err_t ss_rsa_read_pub(const char *path, ss_rsa_key_t **out_key) {
    return read_pem_key(path, NULL, 0, out_key);
}

ss_err_t ss_rsa_read_priv(const char *path, const char *passphrase, ss_rsa_key_t **out_key) {
    return read_pem_key(path, passphrase, 1, out_key);
}

ss_err_t ss_rsa_write_pub(const ss_rsa_key_t *key, const char *path) {
    if (key == NULL || key->pkey == NULL || path == NULL) {
        return SS_ERR_INVALID_ARG;
    }
    BIO *bio = BIO_new_file(path, "wb");
    if (bio == NULL) {
        return SS_ERR_IO;
    }
    int rc = PEM_write_bio_PUBKEY(bio, key->pkey);
    BIO_free(bio);
    return rc == 1 ? SS_OK : SS_ERR_OPENSSL;
}

ss_err_t ss_rsa_write_priv(const ss_rsa_key_t *key, const char *path,
                           const char *passphrase) {
    if (key == NULL || key->pkey == NULL || path == NULL) {
        return SS_ERR_INVALID_ARG;
    }
    BIO *bio = BIO_new_file(path, "wb");
    if (bio == NULL) {
        return SS_ERR_IO;
    }
    const EVP_CIPHER *cipher = passphrase != NULL ? EVP_aes_256_cbc() : NULL;
    int rc = PEM_write_bio_PKCS8PrivateKey(bio, key->pkey, cipher, NULL, 0, NULL,
                                           (void *)passphrase);
    BIO_free(bio);
    return rc == 1 ? SS_OK : SS_ERR_OPENSSL;
}

size_t ss_rsa_ciphertext_len(const ss_rsa_key_t *key) {
    if (key == NULL || key->pkey == NULL) {
        return 0;
    }
    return (size_t)EVP_PKEY_size(key->pkey);
}

size_t ss_rsa_max_plaintext_len(const ss_rsa_key_t *key) {
    size_t k = ss_rsa_ciphertext_len(key);
    if (k == 0) {
        return 0;
    }
    size_t hlen = (size_t)EVP_MD_size(EVP_sha256());
    /* OAEP: k - 2*hLen - 2 */
    return k > 2 * hlen + 2 ? k - 2 * hlen - 2 : 0;
}

ss_err_t ss_rsa_encrypt(const ss_rsa_key_t *key, const uint8_t *in, size_t in_len,
                        uint8_t *out, size_t *out_len) {
    if (key == NULL || key->pkey == NULL || in == NULL || in_len == 0 || out_len == NULL) {
        return SS_ERR_INVALID_ARG;
    }
    if (in_len > ss_rsa_max_plaintext_len(key)) {
        return SS_ERR_INVALID_ARG;
    }
    EVP_PKEY_CTX *ctx = EVP_PKEY_CTX_new(key->pkey, NULL);
    if (ctx == NULL) {
        return SS_ERR_OPENSSL;
    }
    if (EVP_PKEY_encrypt_init(ctx) <= 0 ||
        EVP_PKEY_CTX_set_rsa_padding(ctx, RSA_PKCS1_OAEP_PADDING) <= 0 ||
        EVP_PKEY_CTX_set_rsa_oaep_md(ctx, EVP_sha256()) <= 0) {
        EVP_PKEY_CTX_free(ctx);
        return SS_ERR_OPENSSL;
    }
    size_t need = 0;
    if (EVP_PKEY_encrypt(ctx, NULL, &need, in, in_len) <= 0) {
        EVP_PKEY_CTX_free(ctx);
        return SS_ERR_OPENSSL;
    }
    if (out == NULL) {
        *out_len = need;
        EVP_PKEY_CTX_free(ctx);
        return SS_OK;
    }
    if (*out_len < need) {
        *out_len = need;
        EVP_PKEY_CTX_free(ctx);
        return SS_ERR_BUFFER_TOO_SMALL;
    }
    size_t actual = need;
    if (EVP_PKEY_encrypt(ctx, out, &actual, in, in_len) <= 0) {
        EVP_PKEY_CTX_free(ctx);
        return SS_ERR_OPENSSL;
    }
    *out_len = actual;
    EVP_PKEY_CTX_free(ctx);
    return SS_OK;
}

ss_err_t ss_rsa_decrypt(const ss_rsa_key_t *key, const uint8_t *in, size_t in_len,
                        uint8_t *out, size_t *out_len) {
    if (key == NULL || key->pkey == NULL || in == NULL || in_len == 0 || out_len == NULL) {
        return SS_ERR_INVALID_ARG;
    }
    EVP_PKEY_CTX *ctx = EVP_PKEY_CTX_new(key->pkey, NULL);
    if (ctx == NULL) {
        return SS_ERR_OPENSSL;
    }
    if (EVP_PKEY_decrypt_init(ctx) <= 0 ||
        EVP_PKEY_CTX_set_rsa_padding(ctx, RSA_PKCS1_OAEP_PADDING) <= 0 ||
        EVP_PKEY_CTX_set_rsa_oaep_md(ctx, EVP_sha256()) <= 0) {
        EVP_PKEY_CTX_free(ctx);
        return SS_ERR_OPENSSL;
    }
    size_t need = 0;
    if (EVP_PKEY_decrypt(ctx, NULL, &need, in, in_len) <= 0) {
        EVP_PKEY_CTX_free(ctx);
        return SS_ERR_DECRYPT;
    }
    if (out == NULL) {
        *out_len = need;
        EVP_PKEY_CTX_free(ctx);
        return SS_OK;
    }
    if (*out_len < need) {
        *out_len = need;
        EVP_PKEY_CTX_free(ctx);
        return SS_ERR_BUFFER_TOO_SMALL;
    }
    size_t actual = need;
    if (EVP_PKEY_decrypt(ctx, out, &actual, in, in_len) <= 0) {
        EVP_PKEY_CTX_free(ctx);
        return SS_ERR_DECRYPT;
    }
    *out_len = actual;
    EVP_PKEY_CTX_free(ctx);
    return SS_OK;
}

void ss_rsa_key_free(ss_rsa_key_t *key) {
    if (key == NULL) {
        return;
    }
    EVP_PKEY_free(key->pkey);
    free(key);
}
