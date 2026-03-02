#include "include/encrypt_RSA.h"

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
    const char *rt_err = NULL;
    FILE *fp = NULL;
    if ((fp = fopen(pubkey_file, "wb")) == NULL)
    {
        rt_err = "Failed to open public key file for writing.";
        goto err;
    }
    PEM_write_PUBKEY(fp, RSA_key);
    fclose(fp);
    if ((fp = fopen(privkey_file, "wb")) == NULL)
    {
        rt_err = "Failed to open private key file for writing.";
        goto err;
    }
    PEM_write_PrivateKey(fp, RSA_key, NULL, NULL, 0, NULL, NULL);
    fclose(fp);
    return 0;
err:
    printf("[ERROR]: %s\n", rt_err);
    fclose(fp);
    return -1;
}

EVP_PKEY *RSA_read(const char *pubkey_file, const char *privkey_file)
{
    const char *rt_err = NULL;
    FILE *fp = NULL;
    EVP_PKEY *RSA_key = NULL;
    if ((fp = fopen(pubkey_file, "rb")) == NULL)
    {
        printf("Failed to open public key file for reading.\n");
        goto err;
    }
    RSA_key = PEM_read_PUBKEY(fp, NULL, NULL, NULL);
    fclose(fp);
    if (!RSA_key)
    {
        printf("Failed to read public key from file.\n");
        goto err;
    }
    if ((fp = fopen(privkey_file, "rb")) == NULL)
    {
        printf("Failed to open private key file for reading.\n");
        goto err;
    }
    RSA_key = PEM_read_PrivateKey(fp, NULL, NULL, NULL);
    fclose(fp);
    if (!RSA_key)
    {
        printf("Failed to read private key from file.\n");
        goto err;
    }
    return RSA_key;
err:
    if (fp) fclose(fp);
    printf("[ERROR]: %s\n", rt_err);
    return NULL;
}

unsigned char *RSA_pub_encrypt(EVP_PKEY *RSA_key, const unsigned char *msg, size_t *encrypted_msg_length)
{
    const char *rt_err = NULL;
    EVP_PKEY_CTX *ctx = NULL;
    unsigned char *encrypted_msg = NULL;
    size_t outlen;

    ctx = EVP_PKEY_CTX_new(RSA_key, NULL);
    if (!ctx)
    {
        rt_err = "Failed to create EVP_PKEY_CTX.";
        goto err;
    }

    if (EVP_PKEY_encrypt_init(ctx) <= 0)
    {
        rt_err = "Failed to initialize EVP_PKEY_CTX for encryption.";
        goto err;
    }
    if (EVP_PKEY_encrypt(ctx, NULL, &outlen, msg, strlen((const char *)msg)) <= 0)
    {
        rt_err = "Failed to get encrypted message length.";
        goto err;
    }
    encrypted_msg = (unsigned char *)malloc(outlen);
    if (!encrypted_msg)
    {
        rt_err = "Failed to allocate memory for encrypted message.";
        goto err;
    }
    if (EVP_PKEY_encrypt(ctx, encrypted_msg, &outlen, msg, strlen((const char *)msg)) <= 0)
    {
        rt_err = "Failed to encrypt message.";
        goto err;
    }

    *encrypted_msg_length = outlen;
    EVP_PKEY_CTX_free(ctx);

    return encrypted_msg;

err:
    printf("[ERROR]: %s\n", rt_err);
    if(ctx) EVP_PKEY_CTX_free(ctx);
    if(encrypted_msg) free(encrypted_msg);
    return NULL;
}

unsigned char *RSA_priv_decrypt(EVP_PKEY *RSA_key, const unsigned char *encrypted_msg, size_t encrypted_msg_length, size_t *decrypted_msg_length)
{
    const char *rt_err = NULL;
    EVP_PKEY_CTX *ctx = NULL;
    unsigned char *decrypted_msg = NULL;
    size_t outlen;
    ctx = EVP_PKEY_CTX_new(RSA_key, NULL);
    if (!ctx)
    {
        rt_err = "Failed to create EVP_PKEY_CTX.";
        goto err;
    }
    if (EVP_PKEY_decrypt_init(ctx) <= 0)
    {
        rt_err = "Failed to initialize EVP_PKEY_CTX for decryption.";
        goto err;
    }
    if (EVP_PKEY_decrypt(ctx, NULL, &outlen, encrypted_msg, encrypted_msg_length) <= 0)
    {
        rt_err = "Failed to get decrypted message length.";
        goto err;
    }
    decrypted_msg = (unsigned char *)malloc(outlen);
    if (!decrypted_msg)
    {
        rt_err = "Failed to allocate memory for decrypted message.";
        goto err;
    }
    if (EVP_PKEY_decrypt(ctx, decrypted_msg, &outlen, encrypted_msg, encrypted_msg_length) <= 0)
    {
        rt_err = "Failed to decrypt message.";
        goto err;
    }
    *decrypted_msg_length = outlen;
    EVP_PKEY_CTX_free(ctx);
    return decrypted_msg;

err:
    printf("[ERROR]: %s\n", rt_err);
    if(ctx) EVP_PKEY_CTX_free(ctx);
    if(decrypted_msg) free(decrypted_msg);
    return NULL;
}
