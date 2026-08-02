/*
 * ss_rsa.h - RSA-OAEP public-key encryption.
 *
 * Key generation, PEM persistence and encrypt/decrypt using RSA with
 * OAEP padding and SHA-256 (RFC 8017). The OAEP hash is fixed to
 * SHA-256; interoperating peers must use the same parameters.
 *
 * The key handle is an opaque struct; allocate/free with
 * ss_rsa_keygen / ss_rsa_read_* / ss_rsa_key_free.
 */
#ifndef SS_RSA_H
#define SS_RSA_H

#include "ss_crypto.h"

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct ss_rsa_key ss_rsa_key_t;

/* Recommended minimum key size; ss_rsa_keygen accepts 2048..16384. */
#define SS_RSA_MIN_BITS 2048u
#define SS_RSA_MAX_BITS 16384u

/*
 * Generate an RSA key pair of `bits` (2048, 3072 or 4096 recommended).
 * On success *out_key receives a new handle (free with ss_rsa_key_free).
 */
SS_CRYPTO_API ss_err_t ss_rsa_keygen(int bits, ss_rsa_key_t **out_key);

/*
 * Read a public / private key from a PEM file.
 * passphrase: required only for encrypted private keys, else NULL.
 * A wrong passphrase is reported as SS_ERR_PARSE (OpenSSL does not
 * reliably distinguish it from a malformed file).
 * The returned handle carries whatever key material was loaded; a
 * public-key-only handle can be used for encryption, and a private-key
 * handle for decryption (it also contains the public key).
 */
SS_CRYPTO_API ss_err_t ss_rsa_read_pub(const char *path, ss_rsa_key_t **out_key);
SS_CRYPTO_API ss_err_t ss_rsa_read_priv(const char *path, const char *passphrase,
                                        ss_rsa_key_t **out_key);

/*
 * Write the public key (SubjectPublicKeyInfo) / private key (PKCS#8)
 * to a PEM file. When passphrase is non-NULL the private key is
 * encrypted with AES-256-CBC. The output file is overwritten.
 */
SS_CRYPTO_API ss_err_t ss_rsa_write_pub(const ss_rsa_key_t *key, const char *path);
SS_CRYPTO_API ss_err_t ss_rsa_write_priv(const ss_rsa_key_t *key, const char *path,
                                         const char *passphrase);

/*
 * RSA-OAEP (SHA-256) encrypt/decrypt. Binary-safe: operates on
 * in_len bytes, including embedded NUL bytes.
 *
 * Query pattern: pass out == NULL to obtain the required buffer size
 * in *out_len, then call again with a buffer of that size.
 * Encrypting more than ss_rsa_max_plaintext_len() bytes returns
 * SS_ERR_INVALID_ARG.
 */
SS_CRYPTO_API ss_err_t ss_rsa_encrypt(const ss_rsa_key_t *key,
                                      const uint8_t *in, size_t in_len,
                                      uint8_t *out, size_t *out_len);
SS_CRYPTO_API ss_err_t ss_rsa_decrypt(const ss_rsa_key_t *key,
                                      const uint8_t *in, size_t in_len,
                                      uint8_t *out, size_t *out_len);

/* Size of the ciphertext for this key (== RSA modulus size in bytes). */
SS_CRYPTO_API size_t ss_rsa_ciphertext_len(const ss_rsa_key_t *key);

/* Maximum plaintext length for OAEP-SHA256 with this key. */
SS_CRYPTO_API size_t ss_rsa_max_plaintext_len(const ss_rsa_key_t *key);

SS_CRYPTO_API void ss_rsa_key_free(ss_rsa_key_t *key);

#ifdef __cplusplus
}
#endif

#endif /* SS_RSA_H */
