# Top-level build for ServSpy. C sources live in the self-contained
# crypto/ module; the Python package is managed by uv/pytest instead.
cmake_minimum_required(VERSION 3.16)
project(servspy VERSION 0.1.0 LANGUAGES C)

include(CTest)
enable_testing()
add_subdirectory(crypto)
