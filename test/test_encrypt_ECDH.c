#include "../src/include/encrypt_ECDH.h"
#include <stdio.h>
#include <string.h>

int main()
{
    printf("=== ECDH Encrypt Decrypt Test ===\n");

    printf("Generate A side private key...\n");
    BIGNUM *private_key_A = generate_private_key();
    if (!private_key_A)
    {
        printf("Failed to generate private key A\n");
        return 1;
    }

    EC_POINT *public_key_A = generate_public_key(private_key_A);
    if (!public_key_A)
    {
        printf("Failed to generate public key A\n");
        BN_free(private_key_A);
        return 1;
    }
    printf("Successfully generate A side private key and public key\n");

    printf("Generate B side private key...\n");
    BIGNUM *private_key_B = generate_private_key();
    if (!private_key_B)
    {
        printf("Failed to generate private key B\n");
        BN_free(private_key_A);
        EC_POINT_free(public_key_A);
        return 1;
    }

    EC_POINT *public_key_B = generate_public_key(private_key_B);
    if (!public_key_B)
    {
        printf("Failed to generate public key B\n");
        BN_free(private_key_A);
        BN_free(private_key_B);
        EC_POINT_free(public_key_A);
        return 1;
    }
    printf("Successfully generate B side private key and public key\n");

    printf("Compute shared secret...\n");
    EC_POINT *shared_secret_A = compute_shared_secret(private_key_A, public_key_B);
    EC_POINT *shared_secret_B = compute_shared_secret(private_key_B, public_key_A);

    if (!shared_secret_A || !shared_secret_B)
    {
        printf("Failed to compute shared secret\n");
    }
    else
    {
        printf("Successfully compute shared secret\n");

        printf("Test key derivation...\n");
        size_t key_len_A, key_len_B;
        unsigned char *key_A = derive_key_from_shared_secret(shared_secret_A, &key_len_A);
        unsigned char *key_B = derive_key_from_shared_secret(shared_secret_B, &key_len_B);

        if (key_A && key_B && key_len_A == key_len_B &&
            memcmp(key_A, key_B, key_len_A) == 0)
        {
            printf("Successfully derive keys from shared secret, keys match\n");

            printf("Test encrypt decrypt function...\n");
            const char *test_message = "Hello! This is a test message.";
            size_t message_len = strlen(test_message) + 1;

            printf("Original message: %s\n", test_message);

            size_t ciphertext_len;
            unsigned char *ciphertext = encrypt_ecdh((const unsigned char *)test_message,
                                                     message_len, shared_secret_A, &ciphertext_len);

            if (ciphertext)
            {
                printf("Successfully encrypt message, ciphertext length: %zu bytes\n", ciphertext_len);

                size_t decrypted_len;
                unsigned char *decrypted = decrypt_ecdh(ciphertext, ciphertext_len,
                                                        shared_secret_B, &decrypted_len);

                if (decrypted && decrypted_len == message_len &&
                    memcmp(decrypted, test_message, message_len) == 0)
                {
                    printf("Successfully decrypt message: %s\n", (char *)decrypted);
                    printf("Encrypt decrypt test passed!\n");
                    free(decrypted);
                }
                else
                {
                    printf("Failed to decrypt message\n");
                }

                free(ciphertext);
            }
            else
            {
                printf("Failed to encrypt message\n");
            }

            free(key_A);
            free(key_B);
        }
        else
        {
            printf("Failed to derive keys from shared secret or keys do not match\n");
            if (key_A)
                free(key_A);
            if (key_B)
                free(key_B);
        }
    }

    printf("Clean up resources...\n");
    if (shared_secret_A)
        EC_POINT_free(shared_secret_A);
    if (shared_secret_B)
        EC_POINT_free(shared_secret_B);
    EC_POINT_free(public_key_A);
    EC_POINT_free(public_key_B);
    BN_free(private_key_A);
    BN_free(private_key_B);

    printf("=== Test completed ===\n");
    return 0;
}
