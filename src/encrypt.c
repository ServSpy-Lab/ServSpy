#include <openssl/evp.h>
#include <openssl/rsa.h>
#include <openssl/err.h>
#include <openssl/pem.h>
#include <stdio.h>
#include "include/encrypt.h"

EVP_PKEY *RSA_generate_keys(EVP_PKEY *rtrn_key)
{
    const char *rt_err = NULL;
    EVP_PKEY_CTX *ctx = NULL;
    EVP_PKEY *pkey = NULL;
    ctx = EVP_PKEY_CTX_new_id(EVP_PKEY_RSA, NULL);
    if (!ctx)
    {
        rt_err = "EVP_PKEY_CTX_new_id failed";
        goto err;
    }
    if (EVP_PKEY_keygen_init(ctx) <= 0)
    {
        rt_err = "EVP_PKEY_keygen_init failed";
        goto err;
    }
    if (EVP_PKEY_CTX_set_rsa_keygen_bits(ctx, 2048) <= 0)
    {
        rt_err = "EVP_PKEY_CTX_set_rsa_keygen_bits failed";
        goto err;
    }
    if (EVP_PKEY_keygen(ctx, &pkey) <= 0)
    {
        rt_err = "EVP_PKEY_keygen failed";
        goto err;
    }
    else if (pkey)
    {
        rtrn_key = pkey;
        EVP_PKEY_CTX_free(ctx);
        return rtrn_key;
    }

err:
    if (ctx)
        EVP_PKEY_CTX_free(ctx);
    if (pkey)
        return pkey;
    printf("[ERROR]: %s\n", rt_err);
    return NULL;
}
int RSA_write(EVP_PKEY *RSA_key, const char *pubkey_file, const char *privkey_file)
{
    FILE *fp = NULL;
    if ((fp = fopen(pubkey_file, "wb")) == NULL)
    {
        printf("Failed to open public key file for writing.\n");
        return -1;
    }
    PEM_write_PUBKEY(fp, RSA_key);
    fclose(fp);
    if ((fp = fopen(privkey_file, "wb")) == NULL)
    {
        printf("Failed to open private key file for writing.\n");
        return -1;
    }
    PEM_write_PrivateKey(fp, RSA_key, NULL, NULL, 0, NULL, NULL);
    fclose(fp);
    return 0;
}
EVP_PKEY *RSA_read(const char *pubkey_file, const char *privkey_file)
{
    FILE *fp = NULL;
    EVP_PKEY *RSA_key = NULL;
    if ((fp = fopen(pubkey_file, "rb")) == NULL)
    {
        printf("Failed to open public key file for reading.\n");
        return NULL;
    }
    RSA_key = PEM_read_PUBKEY(fp, NULL, NULL, NULL);
    fclose(fp);
    if (!RSA_key)
    {
        printf("Failed to read public key from file.\n");
        return NULL;
    }
    if ((fp = fopen(privkey_file, "rb")) == NULL)
    {
        printf("Failed to open private key file for reading.\n");
        return NULL;
    }
    RSA_key = PEM_read_PrivateKey(fp, NULL, NULL, NULL);
    fclose(fp);
    if (!RSA_key)
    {
        printf("Failed to read private key from file.\n");
        return NULL;
    }
    return RSA_key;
}
unsigned char *RSA_pub_encrypt(EVP_PKEY *RSA_key, const unsigned char *msg, size_t *encrypted_msg_length)
{
    EVP_PKEY_CTX *ctx = NULL;
    unsigned char *encrypted_msg = NULL;
    size_t outlen;

    ctx = EVP_PKEY_CTX_new(RSA_key, NULL);
    if (!ctx)
    {
        printf("Failed to create EVP_PKEY_CTX.\n");
        return NULL;
    }

    if (EVP_PKEY_encrypt_init(ctx) <= 0)
    {
        printf("Failed to initialize EVP_PKEY_CTX for encryption.\n");
        EVP_PKEY_CTX_free(ctx);
        return NULL;
    }
    if (EVP_PKEY_encrypt(ctx, NULL, &outlen, msg, strlen((const char *)msg)) <= 0)
    {
        printf("Failed to get encrypted message length.\n");
        EVP_PKEY_CTX_free(ctx);
        return NULL;
    }
    encrypted_msg = (unsigned char *)malloc(outlen);
    if (!encrypted_msg)
    {
        printf("Failed to allocate memory for encrypted message.\n");
        EVP_PKEY_CTX_free(ctx);
        return NULL;
    }
    if (EVP_PKEY_encrypt(ctx, encrypted_msg, &outlen, msg, strlen((const char *)msg)) <= 0)
    {
        printf("Failed to encrypt message.\n");
        free(encrypted_msg);
        EVP_PKEY_CTX_free(ctx);
        return NULL;
    }

    *encrypted_msg_length = outlen;
    EVP_PKEY_CTX_free(ctx);

    return encrypted_msg;
}
unsigned char *RSA_priv_decrypt(EVP_PKEY *RSA_key, const unsigned char *encrypted_msg, size_t encrypted_msg_length, size_t *decrypted_msg_length)
{
    EVP_PKEY_CTX *ctx = NULL;
    unsigned char *decrypted_msg = NULL;
    size_t outlen;
    ctx = EVP_PKEY_CTX_new(RSA_key, NULL);
    if (!ctx)
    {
        printf("Failed to create EVP_PKEY_CTX.\n");
        return NULL;
    }
    if (EVP_PKEY_decrypt_init(ctx) <= 0)
    {
        printf("Failed to initialize EVP_PKEY_CTX for decryption.\n");
        EVP_PKEY_CTX_free(ctx);
        return NULL;
    }
    if (EVP_PKEY_decrypt(ctx, NULL, &outlen, encrypted_msg, encrypted_msg_length) <= 0)
    {
        printf("Failed to get decrypted message length.\n");
        EVP_PKEY_CTX_free(ctx);
        return NULL;
    }
    decrypted_msg = (unsigned char *)malloc(outlen);
    if (!decrypted_msg)
    {
        printf("Failed to allocate memory for decrypted message.\n");
        EVP_PKEY_CTX_free(ctx);
        return NULL;
    }
    if (EVP_PKEY_decrypt(ctx, decrypted_msg, &outlen, encrypted_msg, encrypted_msg_length) <= 0)
    {
        printf("Failed to decrypt message.\n");
        free(decrypted_msg);
        EVP_PKEY_CTX_free(ctx);
        return NULL;
    }
    *decrypted_msg_length = outlen;
    EVP_PKEY_CTX_free(ctx);
    return decrypted_msg;
}
int main()
{
    EVP_PKEY *key = NULL;
    key = RSA_generate_keys(key);
    if (key)
    {
        printf("RSA key pair generated successfully.\n");
    }
    else
    {
        printf("Failed to generate RSA key pair.\n");
    }

    if (RSA_write(key, "pubkey.pem", "privkey.pem") != 0)
    {
        printf("Failed to write RSA key pair to files.\n");
    }
    else
    {
        printf("RSA key pair written to files successfully.\n");
    }

    EVP_PKEY_free(key);
    key = RSA_read("pubkey.pem", "privkey.pem");
    if (key)
    {
        printf("RSA key pair read from files successfully.\n");
    }
    else
    {
        printf("Failed to read RSA key pair from files.\n");
    }
    unsigned char msg[2048];
    unsigned char *encrypted_msg = NULL;
    unsigned char *decrypted_msg = NULL;

    printf("Enter message to encrypt: ");
    scanf("%2048s", msg);

    printf("Original msg: %s\n", msg);

    size_t encrypted_msg_length = 0;
    encrypted_msg = RSA_pub_encrypt(key, msg, &encrypted_msg_length);

    if (encrypted_msg)
    {
        printf("RSA message encrypted successfully.\n");
        printf("Encrypted msg length: %ld\n", encrypted_msg_length);
        printf("Encrypted msg (hex): ");
        for (size_t i = 0; i < encrypted_msg_length; i++)
        {
            printf("%02x", encrypted_msg[i]);
        }
        printf("\n");
    }
    else
    {
        printf("Failed to encrypt RSA message.\n");
    }

    size_t decrypted_msg_length = 0;
    decrypted_msg = RSA_priv_decrypt(key, encrypted_msg, encrypted_msg_length, &decrypted_msg_length);

    if (decrypted_msg)
    {
        printf("RSA message decrypted successfully.\n");
        decrypted_msg[decrypted_msg_length] = '\0';
        printf("Decrypted msg: %s\n", decrypted_msg);
        printf("Decrypted msg length: %ld\n", decrypted_msg_length);
        free(decrypted_msg);
    }
    else if (decrypted_msg_length == 0)
    {
        printf("Decrypted msg is empty.\n");
    }
    else
    {
        printf("Failed to decrypt RSA message.\n");
    }
    if (encrypted_msg)
    {
        free(encrypted_msg);
    }

    EVP_PKEY_free(key);
    return 0;
}
