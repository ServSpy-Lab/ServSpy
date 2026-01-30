#ifndef ENCRYPT_RSA_H
#define ENCRYPT_RSA_H

#include <stdio.h>
#include <openssl/evp.h>
#include <openssl/rsa.h>
#include <openssl/err.h>
#include <openssl/pem.h>
#include <openssl/evp.h>

EVP_PKEY *RSA_generate_keys(EVP_PKEY *rtrn_key);

int RSA_write(EVP_PKEY *RSA_key, const char *pubkey_file, const char *privkey_file);

EVP_PKEY *RSA_read(const char *pubkey_file, const char *privkey_file);

unsigned char *RSA_pub_encrypt(EVP_PKEY *RSA_key, const unsigned char *msg, size_t *encrypted_msg_length);

unsigned char *RSA_priv_decrypt(EVP_PKEY *RSA_key, const unsigned char *encrypted_msg, 
                                size_t encrypted_msg_length, size_t *decrypted_msg_length);

#endif /* ENCRYPT_RSA_H */





