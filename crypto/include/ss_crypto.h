/*
 * ss_crypto.h - ServSpy crypto module, common public interface.
 *
 * A self-contained C/OpenSSL cryptography library providing:
 *   - RSA-OAEP key generation, PEM persistence, encrypt/decrypt
 *   - ECDH key agreement with HKDF-SHA256 session key derivation
 *   - AES-256-GCM authenticated encryption (seal/open) bound to an
 *     ECDH key pair, with implicit key confirmation of the peer
 *
 * Design rules:
 *   - Every function returns an ss_err_t; SS_OK (0) means success.
 *   - No global mutable state; the library is thread-safe as long as
 *     each handle is used by one thread at a time.
 *   - Output buffers supplied by the caller are never overrun; the
 *     "query length" pattern (out == NULL) returns the required size
 *     in *out_len.
 *   - Buffers returned via **out (PEM strings, seal/open results) are
 *     allocated with malloc(3) and MUST be released with free(3).
 *
 * Requires OpenSSL >= 1.1.1. Uses only the EVP high-level API.
 */
#ifndef SS_CRYPTO_H
#define SS_CRYPTO_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define SS_CRYPTO_VERSION_MAJOR 1
#define SS_CRYPTO_VERSION_MINOR 0
#define SS_CRYPTO_VERSION_PATCH 0
#define SS_CRYPTO_VERSION_STRING "1.0.0"

/* DLL export/import for Windows shared builds; no-op elsewhere. */
#if defined(_WIN32)
#  if defined(SS_CRYPTO_SHARED)
#    define SS_CRYPTO_API __declspec(dllexport)
#  elif defined(SS_CRYPTO_USE_SHARED)
#    define SS_CRYPTO_API __declspec(dllimport)
#  else
#    define SS_CRYPTO_API
#  endif
#else
#  define SS_CRYPTO_API __attribute__((visibility("default")))
#endif

/* Maximum HKDF-SHA256 output: 255 * 32 bytes (RFC 5869). */
#define SS_CRYPTO_HKDF_SHA256_MAX_OUT 8160u

typedef enum {
    SS_OK = 0,               /* success */
    SS_ERR_INVALID_ARG,      /* NULL argument, illegal length, bad combination */
    SS_ERR_NOMEM,            /* memory allocation failed */
    SS_ERR_OPENSSL,          /* underlying OpenSSL operation failed; see
                                ss_crypto_openssl_errors() for detail */
    SS_ERR_IO,               /* file could not be opened/read/written */
    SS_ERR_PARSE,            /* PEM/DER input could not be parsed */
    SS_ERR_BUFFER_TOO_SMALL, /* caller-supplied output buffer too small */
    SS_ERR_AUTH_FAILED,      /* AEAD tag verification failed */
    SS_ERR_UNSUPPORTED,      /* unsupported algorithm or parameter */
    SS_ERR_DECRYPT,          /* decryption failed for a non-authentication
                                reason (e.g. malformed RSA padding) */
} ss_err_t;

/* Human-readable description of an error code. Never returns NULL. */
SS_CRYPTO_API const char *ss_err_string(ss_err_t err);

/*
 * Formats the pending OpenSSL error queue into buf (always NUL-terminated,
 * truncated to buf_len). Each call consumes the queue; "no error" is written
 * when the queue is empty. buf may be NULL with buf_len 0 to no-op.
 */
SS_CRYPTO_API void ss_crypto_openssl_errors(char *buf, size_t buf_len);

/*
 * HKDF (RFC 5869) with SHA-256: Extract-and-Expand.
 *   ikm      - input key material (for ECDH: the raw shared secret)
 *   salt     - optional salt; may be NULL/0 (HKDF zero-pads per RFC)
 *   info     - optional context binding; may be NULL/0
 *   out      - output buffer of out_len bytes; out_len <= SS_CRYPTO_HKDF_SHA256_MAX_OUT
 */
SS_CRYPTO_API ss_err_t ss_crypto_hkdf_sha256(
    const uint8_t *ikm, size_t ikm_len,
    const uint8_t *salt, size_t salt_len,
    const uint8_t *info, size_t info_len,
    uint8_t *out, size_t out_len);

#ifdef __cplusplus
}
#endif

#endif /* SS_CRYPTO_H */
