/* HKDF-SHA256 tests: RFC 5869 Appendix A test vectors. */
#include "ss_crypto.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "test_util.h"

/* Hex string -> bytes; returns byte count or -1 on error. */
static int hex2bin(const char *hex, uint8_t *out, size_t out_cap) {
    size_t n = strlen(hex);
    if (n % 2 != 0 || n / 2 > out_cap) {
        return -1;
    }
    for (size_t i = 0; i < n / 2; i++) {
        unsigned int byte;
        if (sscanf(hex + 2 * i, "%2x", &byte) != 1) {
            return -1;
        }
        out[i] = (uint8_t)byte;
    }
    return (int)(n / 2);
}

static void check_rfc5869_case(const char *ikm_hex, const char *salt_hex,
                               const char *info_hex, size_t out_len,
                               const char *okm_hex) {
    uint8_t ikm[128], salt[128], info[128], okm[255 * 32];
    int ikm_n = hex2bin(ikm_hex, ikm, sizeof(ikm));
    int salt_n = salt_hex ? hex2bin(salt_hex, salt, sizeof(salt)) : 0;
    int info_n = info_hex ? hex2bin(info_hex, info, sizeof(info)) : 0;
    int okm_n = okm_hex ? hex2bin(okm_hex, okm, sizeof(okm)) : -1;
    CHECK(ikm_n > 0);
    CHECK(okm_n >= 0 && (size_t)okm_n == out_len);

    uint8_t out[255 * 32];
    ss_err_t err = ss_crypto_hkdf_sha256(
        ikm, (size_t)ikm_n, salt_n > 0 ? salt : NULL, (size_t)salt_n,
        info_n > 0 ? info : NULL, (size_t)info_n, out, out_len);
    CHECK_ERR(err, SS_OK);
    CHECK(memcmp(out, okm, out_len) == 0);
}

static void run_tests(void) {
    /* RFC 5869 A.1: basic test case with SHA-256. */
    check_rfc5869_case(
        "0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b",          /* IKM 22B */
        "000102030405060708090a0b0c",                            /* salt 13B */
        "f0f1f2f3f4f5f6f7f8f9",                                  /* info 10B */
        42,
        "3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865");

    /* RFC 5869 A.2: longer inputs/outputs. */
    check_rfc5869_case(
        "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
        "202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f"
        "404142434445464748494a4b4c4d4e4f",
        "606162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f"
        "808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9f"
        "a0a1a2a3a4a5a6a7a8a9aaabacadaeaf",
        "b0b1b2b3b4b5b6b7b8b9babbbcbdbebfc0c1c2c3c4c5c6c7c8c9cacbcccdcecf"
        "d0d1d2d3d4d5d6d7d8d9dadbdcdddedfe0e1e2e3e4e5e6e7e8e9eaebecedeeef"
        "f0f1f2f3f4f5f6f7f8f9fafbfcfdfeff",
        82,
        "b11e398dc80327a1c8e7f78c596a49344f012eda2d4efad8a050cc4c19afa97c"
        "59045a99cac7827271cb41c65e590e09da3275600c2f09b8367793a9aca3db71"
        "cc30c58179ec3e87c14c01d5c1f3434f1d87");

    /* RFC 5869 A.3: zero-length salt and info. */
    check_rfc5869_case(
        "0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b",
        NULL, NULL, 42,
        "8da4e775a563c18f715f802a063c5a31b8a11f5c5ee1879ec3454e5f3c738d2d"
        "9d201395faa4b61a96c8");

    /* Argument validation. */
    uint8_t out[32];
    uint8_t ikm[8] = {1, 2, 3, 4, 5, 6, 7, 8};
    CHECK_ERR(ss_crypto_hkdf_sha256(NULL, 8, NULL, 0, NULL, 0, out, 32),
              SS_ERR_INVALID_ARG); /* NULL ikm */
    CHECK_ERR(ss_crypto_hkdf_sha256(ikm, 0, NULL, 0, NULL, 0, out, 32),
              SS_ERR_INVALID_ARG); /* empty ikm */
    CHECK_ERR(ss_crypto_hkdf_sha256(ikm, 8, NULL, 0, NULL, 0, NULL, 32),
              SS_ERR_INVALID_ARG); /* NULL out */
    CHECK_ERR(ss_crypto_hkdf_sha256(ikm, 8, NULL, 0, NULL, 0, out, 0),
              SS_ERR_INVALID_ARG); /* zero length */
    CHECK_ERR(ss_crypto_hkdf_sha256(ikm, 8, NULL, 0, NULL, 0, out,
                                    SS_CRYPTO_HKDF_SHA256_MAX_OUT + 1),
              SS_ERR_INVALID_ARG); /* too long */
}

TEST_MAIN("test_hkdf")
