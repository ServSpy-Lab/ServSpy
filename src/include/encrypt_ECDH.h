#define EC_name NID_X9_62_prime256v1

#ifndef ENCRYPT_ECDH_H
#define ENCRYPT_ECDH_H

#include <openssl/evp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <openssl/ec.h>
#include <openssl/obj_mac.h>
#include <openssl/bn.h>
#include <openssl/rand.h>
#include <openssl/aes.h>

BIGNUM* generate_private_key();

EC_POINT* generate_public_key(const BIGNUM* priv_key);

EC_POINT* compute_shared_secret(const BIGNUM* priv_key, const EC_POINT* pub_key);

unsigned char* derive_key_from_shared_secret(const EC_POINT* shared_secret, size_t* key_len);

unsigned char* encrypt_ecdh(const unsigned char* plaintext, size_t plaintext_len, 
                           const EC_POINT* shared_secret, size_t* ciphertext_len);

unsigned char* decrypt_ecdh(const unsigned char* ciphertext, size_t ciphertext_len, 
                           const EC_POINT* shared_secret, size_t* plaintext_len);

#endif /* ENCRYPT_ECDH_H */