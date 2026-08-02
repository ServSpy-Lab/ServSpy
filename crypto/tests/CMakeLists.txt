# Test executables for ss_crypto.

foreach(test_name IN ITEMS test_hkdf test_rsa test_ecdh)
  add_executable(${test_name} ${test_name}.c)
  target_link_libraries(${test_name} PRIVATE ss_crypto)
  target_compile_options(${test_name} PRIVATE -Wall -Wextra)
  add_test(NAME ${test_name} COMMAND ${test_name})
endforeach()

# Memory/UB sanity under ASan+UBSan when the compiler supports it.
if(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
  include(CheckCCompilerFlag)
  check_c_compiler_flag("-fsanitize=address,undefined" SS_CRYPTO_HAS_SANITIZERS)
  if(SS_CRYPTO_HAS_SANITIZERS)
    foreach(test_name IN ITEMS test_hkdf test_rsa test_ecdh)
      target_compile_options(${test_name} PRIVATE -fsanitize=address,undefined -fno-omit-frame-pointer)
      target_link_options(${test_name} PRIVATE -fsanitize=address,undefined)
    endforeach()
  endif()
endif()
