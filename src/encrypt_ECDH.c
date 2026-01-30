#include "include/encrypt_ECDH.h"

BIGNUM* generate_private_key(){
    const char *rt_err = NULL;
    EC_GROUP* group = EC_GROUP_new_by_curve_name(EC_name);
    if(!group){
        rt_err = "Failed to create EC_GROUP";
        goto err;
    }
    BIGNUM* priv_key = BN_new();
    const BIGNUM* order = EC_GROUP_get0_order(group);
    if(!order){
        rt_err = "Failed to create order";
        goto err;
    }
    BN_rand_range(priv_key, order);
    if(!priv_key){
        rt_err = "Failed to create priv_key";
        goto err;
    }
    EC_GROUP_free(group);
    return priv_key;

err:
    if(group) EC_GROUP_free(group);
    printf("[ERROR]: %s\n", rt_err);
    return NULL;
}

EC_POINT* generate_public_key(const BIGNUM* priv_key){
    const char *rt_err = NULL;
    EC_GROUP* group = EC_GROUP_new_by_curve_name(EC_name);
    if(!group){
        rt_err = "Failed to create EC_GROUP";
        goto err;
    }
    EC_POINT* pub_key = EC_POINT_new(group);
    EC_POINT_mul(group, pub_key, priv_key, NULL, NULL, NULL);
    if(!pub_key){
        rt_err = "Failed to create pub_key";
        goto err;
    }
    EC_GROUP_free(group);
    return pub_key;

err:
    if(group) EC_GROUP_free(group);
    printf("[ERROR]: %s\n", rt_err);
    return NULL;
}

EC_POINT* compute_shared_secret(const BIGNUM* priv_key, const EC_POINT* pub_key){
    const char *rt_err = NULL;
    EC_GROUP* group = EC_GROUP_new_by_curve_name(EC_name);
    if(!group){
        rt_err = "Failed to create EC_GROUP";
        goto err;
    }
    EC_POINT* shared_secret = EC_POINT_new(group);
    EC_POINT_mul(group, shared_secret, NULL, pub_key, priv_key, NULL);
    if(!shared_secret){
        rt_err = "Failed to create shared_secret";
        goto err;
    }
    EC_GROUP_free(group);
    return shared_secret;

err:
    if(group) EC_GROUP_free(group);
    printf("[ERROR]: %s\n", rt_err);
    return NULL;
}

unsigned char* derive_key_from_shared_secret(const EC_POINT* shared_secret, size_t* key_len){
    const char *rt_err = NULL;
    EC_GROUP* group = EC_GROUP_new_by_curve_name(EC_name);
    if(!group){
        rt_err = "Failed to create EC_GROUP";
        goto err;
    }
    
    BIGNUM* x = BN_new();
    if(!x){
        rt_err = "Failed to create BIGNUM for x coordinate";
        goto err;
    }
    
    if(!EC_POINT_get_affine_coordinates(group, shared_secret, x, NULL, NULL)){
        rt_err = "Failed to get affine coordinates";
        goto err;
    }
    
    int bn_size = BN_num_bytes(x);
    unsigned char* key_material = (unsigned char*)malloc(bn_size);
    if(!key_material){
        rt_err = "Failed to allocate memory for key material";
        goto err;
    }
    
    BN_bn2bin(x, key_material);
    
    EVP_MD_CTX* mdctx = EVP_MD_CTX_new();
    if(!mdctx){
        rt_err = "Failed to create message digest context";
        goto err;
    }
    
    unsigned char* derived_key = (unsigned char*)malloc(EVP_MAX_MD_SIZE);
    if(!derived_key){
        rt_err = "Failed to allocate memory for derived key";
        goto err;
    }
    
    unsigned int digest_len;
    if(!EVP_DigestInit_ex(mdctx, EVP_sha256(), NULL) ||
       !EVP_DigestUpdate(mdctx, key_material, bn_size) ||
       !EVP_DigestFinal_ex(mdctx, derived_key, &digest_len)){
        rt_err = "Failed to derive key";
        goto err;
    }
    
    *key_len = digest_len;
    
    EVP_MD_CTX_free(mdctx);
    BN_free(x);
    EC_GROUP_free(group);
    free(key_material);
    
    return derived_key;

err:
    if(group) EC_GROUP_free(group);
    if(x) BN_free(x);
    printf("[ERROR]: %s\n", rt_err);
    return NULL;
}

// ... existing code ...

unsigned char* encrypt_ecdh(const unsigned char* plaintext, size_t plaintext_len, 
                           const EC_POINT* shared_secret, size_t* ciphertext_len){
    const char *rt_err = NULL;
    EVP_CIPHER_CTX* ctx = NULL;
    unsigned char* ciphertext = NULL;
    
    if(!plaintext || plaintext_len == 0 || !shared_secret || !ciphertext_len){
        rt_err = "Invalid input parameters";
        goto err;
    }
    
    if(plaintext_len > SIZE_MAX - 28){
        rt_err = "Plaintext too large";
        goto err;
    }
    
    size_t key_len;
    unsigned char* key = derive_key_from_shared_secret(shared_secret, &key_len);
    if(!key){
        rt_err = "Failed to derive key from shared secret";
        goto err;
    }
    
    unsigned char iv[12]; 
    if(!RAND_bytes(iv, sizeof(iv))){
        rt_err = "Failed to generate IV";
        goto err;
    }
    
    size_t total_len = sizeof(iv) + plaintext_len + 16;
    ciphertext = (unsigned char*)malloc(total_len);
    if(!ciphertext){
        rt_err = "Failed to allocate memory for ciphertext";
        goto err;
    }
    
    memcpy(ciphertext, iv, sizeof(iv));
    
    ctx = EVP_CIPHER_CTX_new();
    if(!ctx){
        rt_err = "Failed to create cipher context";
        goto err;
    }
    
    if(!EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), NULL, key, iv)){
        rt_err = "Failed to initialize encryption";
        goto err;
    }
    
    int len;
    int ciphertext_part_len;
    
    if(!EVP_EncryptUpdate(ctx, ciphertext + sizeof(iv), &len, plaintext, plaintext_len)){
        rt_err = "Failed to encrypt data";
        goto err;
    }
    ciphertext_part_len = len;
    
    if(!EVP_EncryptFinal_ex(ctx, ciphertext + sizeof(iv) + len, &len)){
        rt_err = "Failed to finalize encryption";
        goto err;
    }
    ciphertext_part_len += len;
    
    if(!EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, 16, ciphertext + sizeof(iv) + ciphertext_part_len)){
        rt_err = "Failed to get authentication tag";
        goto err;
    }
    
    *ciphertext_len = sizeof(iv) + ciphertext_part_len + 16;
    
    EVP_CIPHER_CTX_free(ctx);
    free(key);
    
    return ciphertext;

err:
    if(ctx) EVP_CIPHER_CTX_free(ctx);
    if(key) free(key);
    if(ciphertext) free(ciphertext);
    printf("[ERROR]: %s\n", rt_err);
    return NULL;
}

unsigned char* decrypt_ecdh(const unsigned char* ciphertext, size_t ciphertext_len, 
                           const EC_POINT* shared_secret, size_t* plaintext_len){
    const char *rt_err = NULL;
    EVP_CIPHER_CTX* ctx = NULL;
    unsigned char* plaintext = NULL;
    
    if(!ciphertext || !shared_secret || !plaintext_len){
        rt_err = "Invalid input parameters";
        goto err;
    }
    
    if(ciphertext_len < 28){
        rt_err = "Ciphertext too short";
        goto err;
    }
    
    size_t key_len;
    unsigned char* key = derive_key_from_shared_secret(shared_secret, &key_len);
    if(!key){
        rt_err = "Failed to derive key from shared secret";
        goto err;
    }
    
    unsigned char iv[12];
    memcpy(iv, ciphertext, sizeof(iv));
    
    size_t data_len = ciphertext_len - sizeof(iv) - 16;
    if(data_len > SIZE_MAX - 1){ 
        rt_err = "Ciphertext too large";
        goto err;
    }
    
    plaintext = (unsigned char*)malloc(data_len + 1); 
    if(!plaintext){
        rt_err = "Failed to allocate memory for plaintext";
        goto err;
    }
    
    ctx = EVP_CIPHER_CTX_new();
    if(!ctx){
        rt_err = "Failed to create cipher context";
        goto err;
    }
    
    if(!EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(), NULL, key, iv)){
        rt_err = "Failed to initialize decryption";
        goto err;
    }
    
    int len;
    int plaintext_part_len;
    
    if(!EVP_DecryptUpdate(ctx, plaintext, &len, ciphertext + sizeof(iv), data_len)){
        rt_err = "Failed to decrypt data";
        goto err;
    }
    plaintext_part_len = len;
    
    if(!EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG, 16, (void*)(ciphertext + sizeof(iv) + data_len))){
        rt_err = "Failed to set authentication tag";
        goto err;
    }
    
    if(!EVP_DecryptFinal_ex(ctx, plaintext + len, &len)){
        rt_err = "Authentication failed or decryption error";
        goto err;
    }
    plaintext_part_len += len;
    
    *plaintext_len = plaintext_part_len;
    
    EVP_CIPHER_CTX_free(ctx);
    free(key);
    
    return plaintext;

err:
    if(ctx) EVP_CIPHER_CTX_free(ctx);
    if(key) free(key);
    if(plaintext) free(plaintext);
    printf("[ERROR]: %s\n", rt_err);
    return NULL;
}