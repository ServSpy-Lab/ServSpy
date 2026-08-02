# ss_crypto - ServSpy C/OpenSSL cryptography module.
#
# Usable both standalone (cmake -S crypto -B build) and as a subdirectory
# of a larger project (add_subdirectory(crypto)).

if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
  cmake_minimum_required(VERSION 3.16)
  project(ss_crypto VERSION 1.0.0 LANGUAGES C)
endif()

include(GNUInstallDirs)
include(CMakePackageConfigHelpers)
include(CTest) # defines BUILD_TESTING

enable_testing()

option(SS_CRYPTO_BUILD_TESTS "Build the ss_crypto test suite" ON)

find_package(OpenSSL REQUIRED)

set(SS_CRYPTO_SOURCES
  src/ss_crypto.c
  src/ss_rsa.c
  src/ss_ecdh.c
)

add_library(ss_crypto ${SS_CRYPTO_SOURCES})
add_library(ss_crypto::ss_crypto ALIAS ss_crypto)

target_include_directories(ss_crypto PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
)
target_link_libraries(ss_crypto PUBLIC OpenSSL::Crypto)

set_target_properties(ss_crypto PROPERTIES
  C_STANDARD 11
  C_STANDARD_REQUIRED ON
  C_EXTENSIONS OFF
  C_VISIBILITY_PRESET hidden
  VERSION ${PROJECT_VERSION}
  SOVERSION ${PROJECT_VERSION_MAJOR}
  POSITION_INDEPENDENT_CODE ON
)

if(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(ss_crypto PRIVATE -Wall -Wextra)
endif()

# ---- Install & export -----------------------------------------------------
install(TARGETS ss_crypto
  EXPORT ss_cryptoTargets
  ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
  LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
  RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)
install(DIRECTORY include/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})

install(EXPORT ss_cryptoTargets
  FILE ss_cryptoTargets.cmake
  NAMESPACE ss_crypto::
  DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/ss_crypto
)

configure_package_config_file(
  ${CMAKE_CURRENT_SOURCE_DIR}/cmake/ss_cryptoConfig.cmake.in
  ${CMAKE_CURRENT_BINARY_DIR}/ss_cryptoConfig.cmake
  INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/ss_crypto
)
write_basic_package_version_file(
  ${CMAKE_CURRENT_BINARY_DIR}/ss_cryptoConfigVersion.cmake
  VERSION ${PROJECT_VERSION}
  COMPATIBILITY SameMajorVersion
)
install(FILES
  ${CMAKE_CURRENT_BINARY_DIR}/ss_cryptoConfig.cmake
  ${CMAKE_CURRENT_BINARY_DIR}/ss_cryptoConfigVersion.cmake
  DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/ss_crypto
)

# pkg-config file
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/ss_crypto.pc.in
               ${CMAKE_CURRENT_BINARY_DIR}/ss_crypto.pc @ONLY)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/ss_crypto.pc
        DESTINATION ${CMAKE_INSTALL_LIBDIR}/pkgconfig)

# ---- Tests -----------------------------------------------------------------
if(SS_CRYPTO_BUILD_TESTS AND BUILD_TESTING)
  add_subdirectory(tests)
endif()
