C/OpenSSL Crypto Module
========================

The ``crypto`` directory contains ServSpy's standalone C/OpenSSL
cryptography library. The library is independent from the Python runtime
and can be built either as part of the repository or as a separate CMake
project.

The module provides:

- RSA-OAEP encryption and decryption with SHA-256.
- ECDH key agreement on P-256, P-384, and P-521.
- HKDF-SHA256 session-key derivation.
- AES-256-GCM authenticated encryption for ECDH sessions.
- PEM key persistence and structured error reporting.

The public headers are located in ``crypto/include``:

- ``ss_crypto.h`` - common errors, OpenSSL diagnostics, and HKDF.
- ``ss_rsa.h`` - RSA key and encryption APIs.
- ``ss_ecdh.h`` - ECDH key agreement and seal/open APIs.

Build
=====

The module requires OpenSSL 1.1.1 or newer and CMake 3.16 or newer.
On Debian or Ubuntu, install the build dependencies with:

.. code-block:: bash

    sudo apt-get update
    sudo apt-get install -y build-essential cmake libssl-dev

Build it from the repository root:

.. code-block:: bash

    cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
    cmake --build build --parallel
    ctest --test-dir build --output-on-failure

The module can also be built independently:

.. code-block:: bash

    cmake -S crypto -B crypto-build -DCMAKE_BUILD_TYPE=Release
    cmake --build crypto-build --parallel
    ctest --test-dir crypto-build --output-on-failure

CMake install rules export the ``ss_crypto`` library, its public headers,
and a CMake package configuration. A pkg-config template is also provided
as ``crypto/ss_crypto.pc.in``.

Common API
==========

All public functions return ``ss_err_t``. ``SS_OK`` indicates success.
Use ``ss_err_string`` to convert an error code to readable text and
``ss_crypto_openssl_errors`` to retrieve the pending OpenSSL error queue.

.. code-block:: c

    #include "ss_crypto.h"

    ss_err_t error = ss_crypto_hkdf_sha256(
        ikm, ikm_len,
        salt, salt_len,
        info, info_len,
        session_key, 32);

    if (error != SS_OK) {
        fprintf(stderr, "crypto error: %s\n", ss_err_string(error));
    }

The library uses caller-provided output buffers for fixed-size results.
Functions that return allocated buffers document that the caller must
release them with ``free``. Opaque key handles must be released with their
corresponding ``*_free`` function.

RSA API
=======

RSA keys are generated with ``ss_rsa_keygen``. The implementation uses
RSA-OAEP with SHA-256 for encryption and decryption. Key sizes from 2048 to
16384 bits are accepted; 2048, 3072, or 4096 bits are recommended.

.. code-block:: c

    ss_rsa_key_t *key = NULL;
    ss_err_t error = ss_rsa_keygen(3072, &key);
    if (error != SS_OK) {
        return error;
    }

    size_t ciphertext_len = 0;
    error = ss_rsa_encrypt(key, plaintext, plaintext_len,
                           NULL, &ciphertext_len);
    if (error == SS_OK) {
        uint8_t *ciphertext = malloc(ciphertext_len);
        error = ss_rsa_encrypt(key, plaintext, plaintext_len,
                               ciphertext, &ciphertext_len);
        free(ciphertext);
    }

    ss_rsa_key_free(key);

The first encryption call with ``out == NULL`` queries the required output
size. RSA encryption is binary-safe and accepts an explicit input length.
The maximum plaintext size is returned by ``ss_rsa_max_plaintext_len``.

Public and private keys can be stored as PEM files:

.. code-block:: c

    ss_rsa_write_pub(key, "server-public.pem");
    ss_rsa_write_priv(key, "server-private.pem", "passphrase");

    ss_rsa_read_pub("server-public.pem", &public_key);
    ss_rsa_read_priv("server-private.pem", "passphrase", &private_key);

ECDH API
========

ECDH key pairs are created with ``ss_ecdh_keypair_generate``. The supported
curve names are:

- ``SS_ECDH_CURVE_P256``
- ``SS_ECDH_CURVE_P384``
- ``SS_ECDH_CURVE_P521``

Public keys are exchanged as PEM SubjectPublicKeyInfo strings. Parsed peer
keys are checked before use.

.. code-block:: c

    ss_ecdh_keypair_t *local = NULL;
    ss_ecdh_pubkey_t *peer = NULL;
    char *public_pem = NULL;

    ss_ecdh_keypair_generate(SS_ECDH_CURVE_P256, &local);
    ss_ecdh_pub_to_pem(local, &public_pem);
    ss_ecdh_pub_from_pem(peer_pem, &peer);

    uint8_t session_key[32];
    ss_ecdh_derive_key(local, peer,
                       salt, salt_len,
                       info, info_len,
                       session_key, sizeof(session_key));

    free(public_pem);
    ss_ecdh_pubkey_free(peer);
    ss_ecdh_keypair_free(local);

The higher-level ``ss_ecdh_seal`` and ``ss_ecdh_open`` APIs are recommended
for application payloads. They derive an AES-256-GCM key with HKDF-SHA256,
include a random salt and IV, and authenticate optional AAD.

The ``ss_ecdh_seal`` output format is:

.. code-block:: text

    salt(16 bytes) | iv(12 bytes) | ciphertext(N bytes) | tag(16 bytes)

The fixed overhead is ``SS_ECDH_SEAL_OVERHEAD`` (44 bytes). Empty plaintext
is allowed. A failed tag check returns ``SS_ERR_AUTH_FAILED`` and no
plaintext is returned.

Security Notes
==============

ECDH provides key agreement, but it does not authenticate public-key
ownership by itself. Public keys must be exchanged over an authenticated
channel or verified with an external signature/certificate mechanism.

Private key files may be protected with a passphrase. Applications should
restrict their file permissions and avoid logging passphrases, private keys,
or plaintext session keys.

Error Handling
==============

The main error codes are:

- ``SS_ERR_INVALID_ARG`` - invalid pointer or length.
- ``SS_ERR_NOMEM`` - allocation failure.
- ``SS_ERR_OPENSSL`` - OpenSSL operation failure.
- ``SS_ERR_IO`` - file operation failure.
- ``SS_ERR_PARSE`` - malformed PEM/DER input or wrong private-key passphrase.
- ``SS_ERR_BUFFER_TOO_SMALL`` - caller output buffer is insufficient.
- ``SS_ERR_AUTH_FAILED`` - AES-GCM authentication failed.
- ``SS_ERR_UNSUPPORTED`` - unsupported curve or key type.
- ``SS_ERR_DECRYPT`` - RSA decryption failed.

For detailed OpenSSL diagnostics:

.. code-block:: c

    char details[4096];
    ss_crypto_openssl_errors(details, sizeof(details));
    fprintf(stderr, "%s\n", details);
