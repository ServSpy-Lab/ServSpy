/* RSA-OAEP test suite. */
#include "ss_rsa.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "test_util.h"

#define PUB_FILE "test_rsa_pub.pem"
#define PRIV_FILE "test_rsa_priv.pem"
#define PRIV_FILE_PW "test_rsa_priv_enc.pem"
#define PASSPHRASE "correct horse battery staple"

static void run_tests(void) {
    ss_rsa_key_t *key = NULL;
    CHECK_ERR(ss_rsa_keygen(2048, &key), SS_OK);
    CHECK(key != NULL);

    /* Key size invariants: 2048-bit RSA -> 256-byte ciphertext. */
    CHECK(ss_rsa_ciphertext_len(key) == 256);
    CHECK(ss_rsa_max_plaintext_len(key) == 256 - 2 * 32 - 2);

    /* Binary roundtrip, including embedded NULs and high bytes. */
    uint8_t msg[100];
    for (size_t i = 0; i < sizeof(msg); i++) {
        msg[i] = (uint8_t)(i * 7 + 1); /* includes 0x00 at i=73 */
    }
    size_t ct_len = 0;
    CHECK_ERR(ss_rsa_encrypt(key, msg, sizeof(msg), NULL, &ct_len), SS_OK);
    CHECK(ct_len == 256);

    uint8_t *ct = (uint8_t *)malloc(ct_len);
    CHECK(ct != NULL);
    CHECK_ERR(ss_rsa_encrypt(key, msg, sizeof(msg), ct, &ct_len), SS_OK);

    size_t pt_len = 0;
    CHECK_ERR(ss_rsa_decrypt(key, ct, ct_len, NULL, &pt_len), SS_OK);
    CHECK(pt_len >= sizeof(msg));
    uint8_t *pt = (uint8_t *)malloc(pt_len);
    CHECK(pt != NULL);
    CHECK_ERR(ss_rsa_decrypt(key, ct, ct_len, pt, &pt_len), SS_OK);
    CHECK(pt_len == sizeof(msg));
    CHECK(memcmp(pt, msg, sizeof(msg)) == 0);
    free(pt);
    free(ct);

    /* Oversized plaintext is rejected up front. */
    size_t dummy = 0;
    CHECK_ERR(ss_rsa_encrypt(key, msg, ss_rsa_max_plaintext_len(key) + 1, NULL, &dummy),
              SS_ERR_INVALID_ARG);

    /* PEM persistence, plaintext private key. */
    CHECK_ERR(ss_rsa_write_pub(key, PUB_FILE), SS_OK);
    CHECK_ERR(ss_rsa_write_priv(key, PRIV_FILE, NULL), SS_OK);

    ss_rsa_key_t *pub_only = NULL;
    CHECK_ERR(ss_rsa_read_pub(PUB_FILE, &pub_only), SS_OK);
    CHECK(pub_only != NULL);

    ss_rsa_key_t *priv_loaded = NULL;
    CHECK_ERR(ss_rsa_read_priv(PRIV_FILE, NULL, &priv_loaded), SS_OK);
    CHECK(priv_loaded != NULL);

    /* Public-key-only handle encrypts; decryption without the private
     * half fails. */
    size_t ct2_len = 0;
    CHECK_ERR(ss_rsa_encrypt(pub_only, msg, 16, NULL, &ct2_len), SS_OK);
    uint8_t *ct2 = (uint8_t *)malloc(ct2_len);
    CHECK(ct2 != NULL);
    CHECK_ERR(ss_rsa_encrypt(pub_only, msg, 16, ct2, &ct2_len), SS_OK);
    uint8_t *pt2 = (uint8_t *)malloc(ct2_len);
    CHECK(pt2 != NULL);
    size_t pt2_len = ct2_len;
    CHECK_ERR(ss_rsa_decrypt(pub_only, ct2, ct2_len, pt2, &pt2_len), SS_ERR_DECRYPT);

    /* The loaded key can decrypt what the public key encrypted. */
    pt2_len = ct2_len;
    CHECK_ERR(ss_rsa_decrypt(priv_loaded, ct2, ct2_len, pt2, &pt2_len), SS_OK);
    CHECK(pt2_len == 16 && memcmp(pt2, msg, 16) == 0);
    free(pt2);
    free(ct2);

    /* Passphrase-protected private key. */
    CHECK_ERR(ss_rsa_write_priv(key, PRIV_FILE_PW, PASSPHRASE), SS_OK);
    ss_rsa_key_t *pw_bad = NULL;
    CHECK_ERR(ss_rsa_read_priv(PRIV_FILE_PW, "wrong", &pw_bad), SS_ERR_PARSE);
    CHECK(pw_bad == NULL);
    ss_rsa_key_t *pw_ok = NULL;
    CHECK_ERR(ss_rsa_read_priv(PRIV_FILE_PW, PASSPHRASE, &pw_ok), SS_OK);
    CHECK(pw_ok != NULL);

    /* Missing file -> I/O error; bad content -> parse error. */
    ss_rsa_key_t *missing = NULL;
    CHECK_ERR(ss_rsa_read_pub("/nonexistent/pub.pem", &missing), SS_ERR_IO);
    CHECK(missing == NULL);

    /* Buffer-too-small path. */
    size_t small = 10;
    uint8_t small_buf[10];
    CHECK_ERR(ss_rsa_encrypt(key, msg, 16, small_buf, &small), SS_ERR_BUFFER_TOO_SMALL);
    CHECK(small == 256);
    ss_rsa_key_free(pw_ok);
    ss_rsa_key_free(pw_bad);
    ss_rsa_key_free(priv_loaded);
    ss_rsa_key_free(pub_only);
    ss_rsa_key_free(key);

    remove(PUB_FILE);
    remove(PRIV_FILE);
    remove(PRIV_FILE_PW);
}

TEST_MAIN("test_rsa")
