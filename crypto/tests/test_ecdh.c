/* ECDH + AES-256-GCM seal/open test suite. */
#include "ss_ecdh.h"
#include "ss_rsa.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "test_util.h"

#define PRIV_A_FILE "test_ecdh_a_priv.pem"
#define PASSPHRASE "ecdh passphrase"
#define SALT "test salt"
#define INFO "test info"
#define AAD "authenticated but not encrypted"

static const uint8_t kPayload[] = {
    0x00, 0x01, 0x02, 0xde, 0xad, 0xbe, 0xef, 0x00, 0xff, 0xfe,
};


static void run_tests(void) {
    ss_ecdh_keypair_t *a = NULL;
    ss_ecdh_keypair_t *b = NULL;
    CHECK_ERR(ss_ecdh_keypair_generate(SS_ECDH_CURVE_P256, &a), SS_OK);
    CHECK_ERR(ss_ecdh_keypair_generate(SS_ECDH_CURVE_P256, &b), SS_OK);
    CHECK(a != NULL && b != NULL);

    char *pem_a = NULL, *pem_b = NULL;
    CHECK_ERR(ss_ecdh_pub_to_pem(a, &pem_a), SS_OK);
    CHECK_ERR(ss_ecdh_pub_to_pem(b, &pem_b), SS_OK);
    CHECK(pem_a != NULL && strstr(pem_a, "PUBLIC KEY") != NULL);

    ss_ecdh_pubkey_t *pub_a = NULL, *pub_b = NULL;
    CHECK_ERR(ss_ecdh_pub_from_pem(pem_a, &pub_a), SS_OK);
    CHECK_ERR(ss_ecdh_pub_from_pem(pem_b, &pub_b), SS_OK);

    uint8_t key_a[32], key_b[32];
    CHECK_ERR(ss_ecdh_derive_key(a, pub_b, (const uint8_t *)SALT, strlen(SALT),
                                 (const uint8_t *)INFO, strlen(INFO), key_a,
                                 sizeof(key_a)), SS_OK);
    CHECK_ERR(ss_ecdh_derive_key(b, pub_a, (const uint8_t *)SALT, strlen(SALT),
                                 (const uint8_t *)INFO, strlen(INFO), key_b,
                                 sizeof(key_b)), SS_OK);
    CHECK(memcmp(key_a, key_b, sizeof(key_a)) == 0);

    uint8_t *sealed = NULL;
    size_t sealed_len = 0;
    CHECK_ERR(ss_ecdh_seal(a, pub_b, (const uint8_t *)AAD, strlen(AAD), kPayload,
                           sizeof(kPayload), &sealed, &sealed_len), SS_OK);
    CHECK(sealed_len == sizeof(kPayload) + SS_ECDH_SEAL_OVERHEAD);

    uint8_t *opened = NULL;
    size_t opened_len = 0;
    CHECK_ERR(ss_ecdh_open(b, pub_a, (const uint8_t *)AAD, strlen(AAD), sealed,
                           sealed_len, &opened, &opened_len), SS_OK);
    CHECK(opened_len == sizeof(kPayload));
    CHECK(memcmp(opened, kPayload, sizeof(kPayload)) == 0);
    free(opened);
    free(sealed);

    /* Empty plaintext (AAD-only) */
    CHECK_ERR(ss_ecdh_seal(a, pub_b, NULL, 0, NULL, 0, &sealed, &sealed_len), SS_OK);
    CHECK(sealed_len == SS_ECDH_SEAL_OVERHEAD);
    CHECK_ERR(ss_ecdh_open(b, pub_a, NULL, 0, sealed, sealed_len, &opened, &opened_len),
              SS_OK);
    CHECK(opened_len == 0);
    free(opened);
    free(sealed);

    /* Tampering: ciphertext bit flip */
    uint8_t *sealed2 = NULL;
    size_t sealed2_len = 0;
    CHECK_ERR(ss_ecdh_seal(a, pub_b, NULL, 0, kPayload, sizeof(kPayload), &sealed2,
                           &sealed2_len), SS_OK);
    sealed2[SS_ECDH_SEAL_OVERHEAD] ^= 0x01;
    CHECK_ERR(ss_ecdh_open(b, pub_a, NULL, 0, sealed2, sealed2_len, &opened, &opened_len),
              SS_ERR_AUTH_FAILED);
    CHECK(opened == NULL);
    free(sealed2);

    /* Tampering: AAD bit flip */
    uint8_t *aad_sealed = NULL;
    size_t aad_sealed_len = 0;
    CHECK_ERR(ss_ecdh_seal(a, pub_b, (const uint8_t *)AAD, strlen(AAD), kPayload,
                           sizeof(kPayload), &aad_sealed, &aad_sealed_len), SS_OK);
    uint8_t bad_aad[] = "authenticated but NOT encrypted";
    CHECK_ERR(ss_ecdh_open(b, pub_a, bad_aad, sizeof(bad_aad) - 1, aad_sealed,
                           aad_sealed_len, &opened, &opened_len), SS_ERR_AUTH_FAILED);
    CHECK(opened == NULL);
    free(aad_sealed);

    /* Third-party with a different key pair fails to open */
    ss_ecdh_keypair_t *c = NULL;
    CHECK_ERR(ss_ecdh_keypair_generate(SS_ECDH_CURVE_P256, &c), SS_OK);
    char *pem_c = NULL;
    CHECK_ERR(ss_ecdh_pub_to_pem(c, &pem_c), SS_OK);
    ss_ecdh_pubkey_t *pub_c = NULL;
    CHECK_ERR(ss_ecdh_pub_from_pem(pem_c, &pub_c), SS_OK);
    sealed2 = NULL;
    sealed2_len = 0;
    CHECK_ERR(ss_ecdh_seal(a, pub_b, NULL, 0, kPayload, sizeof(kPayload), &sealed2,
                           &sealed2_len), SS_OK);
    CHECK_ERR(ss_ecdh_open(c, pub_a, NULL, 0, sealed2, sealed2_len, &opened, &opened_len),
              SS_ERR_AUTH_FAILED);
    CHECK(opened == NULL);
    free(sealed2);
    /* Error: input too short */
    uint8_t tiny[10] = {0};
    CHECK_ERR(ss_ecdh_open(a, pub_b, NULL, 0, tiny, sizeof(tiny), &opened, &opened_len),
              SS_ERR_INVALID_ARG);
    CHECK(opened == NULL);

    /* Unsupported curve name. */
    ss_ecdh_keypair_t *bad = NULL;
    CHECK_ERR(ss_ecdh_keypair_generate("secp256k1", &bad), SS_ERR_UNSUPPORTED);
    CHECK(bad == NULL);

    /* A non-EC public key is rejected. */
    ss_rsa_key_t *rsa = NULL;
    CHECK_ERR(ss_rsa_keygen(2048, &rsa), SS_OK);
    CHECK_ERR(ss_rsa_write_pub(rsa, "test_rsa_for_ecdh.pem"), SS_OK);
    FILE *fp = fopen("test_rsa_for_ecdh.pem", "rb");
    CHECK(fp != NULL);
    char rsa_pem[4096];
    size_t got = fread(rsa_pem, 1, sizeof(rsa_pem) - 1, fp);
    fclose(fp);
    rsa_pem[got] = '\0';
    ss_ecdh_pubkey_t *not_ec = NULL;
    CHECK_ERR(ss_ecdh_pub_from_pem(rsa_pem, &not_ec), SS_ERR_UNSUPPORTED);
    CHECK(not_ec == NULL);
    remove("test_rsa_for_ecdh.pem");
    ss_rsa_key_free(rsa);

    /* Private key persistence with passphrase. */
    CHECK_ERR(ss_ecdh_keypair_write_priv(a, PRIV_A_FILE, PASSPHRASE), SS_OK);
    ss_ecdh_keypair_t *a_loaded = NULL;
    CHECK_ERR(ss_ecdh_keypair_read_priv(PRIV_A_FILE, "wrong", &a_loaded), SS_ERR_PARSE);
    CHECK(a_loaded == NULL);
    CHECK_ERR(ss_ecdh_keypair_read_priv(PRIV_A_FILE, PASSPHRASE, &a_loaded), SS_OK);
    CHECK(a_loaded != NULL);

    uint8_t key_a_loaded[32];
    CHECK_ERR(ss_ecdh_derive_key(a_loaded, pub_b, (const uint8_t *)SALT, strlen(SALT),
                                 (const uint8_t *)INFO, strlen(INFO), key_a_loaded,
                                 sizeof(key_a_loaded)), SS_OK);
    CHECK(memcmp(key_a_loaded, key_a, sizeof(key_a)) == 0);

    remove(PRIV_A_FILE);
    ss_ecdh_keypair_free(a_loaded);
    free(pem_c);
    ss_ecdh_pubkey_free(pub_c);
    ss_ecdh_keypair_free(c);

    /* P-384 roundtrip */
    ss_ecdh_keypair_t *a384 = NULL, *b384 = NULL;
    CHECK_ERR(ss_ecdh_keypair_generate(SS_ECDH_CURVE_P384, &a384), SS_OK);
    CHECK_ERR(ss_ecdh_keypair_generate(SS_ECDH_CURVE_P384, &b384), SS_OK);
    char *pem_a384 = NULL;
    char *pem_b384 = NULL;
    CHECK_ERR(ss_ecdh_pub_to_pem(a384, &pem_a384), SS_OK);
    CHECK_ERR(ss_ecdh_pub_to_pem(b384, &pem_b384), SS_OK);
    ss_ecdh_pubkey_t *pub_b384 = NULL;
    CHECK_ERR(ss_ecdh_pub_from_pem(pem_b, &pub_b384), SS_OK); /* P-256 parses, fails later */
    ss_ecdh_pubkey_t *pub_a384 = NULL;
    CHECK_ERR(ss_ecdh_pub_from_pem(pem_a384, &pub_a384), SS_OK);
    ss_ecdh_pubkey_t *pub_b384_real = NULL;
    CHECK_ERR(ss_ecdh_pub_from_pem(pem_b384, &pub_b384_real), SS_OK);

    uint8_t *s384 = NULL;
    size_t s384_len = 0;
    uint8_t *cross_curve = NULL;
    size_t cross_curve_len = 0;
    CHECK_ERR(ss_ecdh_seal(a384, pub_b384, NULL, 0, kPayload, sizeof(kPayload),
                           &cross_curve, &cross_curve_len), SS_ERR_OPENSSL);
    CHECK(cross_curve == NULL);

    CHECK_ERR(ss_ecdh_seal(a384, pub_b384_real, NULL, 0, kPayload, sizeof(kPayload),
                           &s384, &s384_len), SS_OK);
    CHECK_ERR(ss_ecdh_open(b384, pub_a384, NULL, 0, s384, s384_len, &opened,
                           &opened_len), SS_OK);
    CHECK(memcmp(opened, kPayload, sizeof(kPayload)) == 0);
    free(opened);
    opened = NULL;
    free(s384);
    ss_ecdh_pubkey_free(pub_b384_real);
    free(pem_b384);

    /* P-521 roundtrip */
    ss_ecdh_keypair_t *a521 = NULL, *b521 = NULL;
    CHECK_ERR(ss_ecdh_keypair_generate(SS_ECDH_CURVE_P521, &a521), SS_OK);
    CHECK_ERR(ss_ecdh_keypair_generate(SS_ECDH_CURVE_P521, &b521), SS_OK);
    char *pem_b521 = NULL;
    CHECK_ERR(ss_ecdh_pub_to_pem(b521, &pem_b521), SS_OK);
    ss_ecdh_pubkey_t *pub_b521 = NULL;
    CHECK_ERR(ss_ecdh_pub_from_pem(pem_b521, &pub_b521), SS_OK);

    char *pem_a521 = NULL;
    CHECK_ERR(ss_ecdh_pub_to_pem(a521, &pem_a521), SS_OK);
    ss_ecdh_pubkey_t *pub_a521 = NULL;
    CHECK_ERR(ss_ecdh_pub_from_pem(pem_a521, &pub_a521), SS_OK);

    uint8_t *s521 = NULL;
    size_t s521_len = 0;
    CHECK_ERR(ss_ecdh_seal(a521, pub_b521, NULL, 0, kPayload, sizeof(kPayload),
                           &s521, &s521_len), SS_OK);
    CHECK_ERR(ss_ecdh_open(b521, pub_a521, NULL, 0, s521, s521_len, &opened, &opened_len),
              SS_OK);
    CHECK(memcmp(opened, kPayload, sizeof(kPayload)) == 0);
    free(opened);
    free(s521);

    free(pem_a521);
    ss_ecdh_pubkey_free(pub_a521);
    ss_ecdh_keypair_free(b521);
    ss_ecdh_keypair_free(a521);
    free(pem_b521);
    ss_ecdh_pubkey_free(pub_b521);

    free(pem_a384);
    ss_ecdh_pubkey_free(pub_a384);
    ss_ecdh_pubkey_free(pub_b384);
    ss_ecdh_keypair_free(b384);
    ss_ecdh_keypair_free(a384);


    free(pem_a);
    free(pem_b);
    ss_ecdh_pubkey_free(pub_a);
    ss_ecdh_pubkey_free(pub_b);
    ss_ecdh_keypair_free(b);
    ss_ecdh_keypair_free(a);
}

TEST_MAIN("test_ecdh")