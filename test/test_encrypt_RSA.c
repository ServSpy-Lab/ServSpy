#include <stdio.h>
#include <string.h>
#include <openssl/evp.h>
#include "../src/include/encrypt_RSA.h"

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

    printf("Enter message to encrypt (max 245 characters for 2048-bit RSA): ");
    scanf("%244s", msg); // 限制输入长度为244字符，为安全起见

    // 检查消息长度
    if (strlen((char *)msg) > 245)
    {
        printf("Error: Message too long! Maximum length for 2048-bit RSA is 245 characters.\n");
        printf("Your message length: %lu characters\n", strlen((char *)msg));
        EVP_PKEY_free(key);
        return 1;
    }

    printf("Original msg: %s\n", msg);
    printf("Message length: %lu characters\n", strlen((char *)msg));

    size_t encrypted_msg_length = 0;
    encrypted_msg = RSA_pub_encrypt(key, msg, &encrypted_msg_length);

    if (encrypted_msg)
    {
        printf("RSA message encrypted successfully.\n");
        printf("Encrypted msg length: %ld bytes\n", encrypted_msg_length);
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
        printf("Decrypted msg length: %ld bytes\n", decrypted_msg_length);
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