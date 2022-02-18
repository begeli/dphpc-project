cmake_minimum_required(VERSION 3.17)
project(tc)

if (NOT UNIX)
    message(FATAL_ERROR "Unsupported OS")
endif ()

# PYBIND11 START
find_package(PythonInterp REQUIRED)
include_directories(${PYTHON_INCLUDE_DIRS})
add_subdirectory(pybind11)
# PYBIND11 END

# MPI stuff begin
find_package(MPI REQUIRED)
include_directories(${MPI_INCLUDE_PATH})
SET(CMAKE_C_COMPILER mpicc)
SET(CMAKE_CXX_COMPILER mpicxx)
# MPI stuff end

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wall -Wextra -Wpedantic")

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -Wpedantic")

set(CMAKE_POSITION_INDEPENDENT_CODE ON)

list(APPEND CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/cmake)

include(address-sanitizer)
include(undefined-sanitizer)
include(clang-tidy)

find_package(GTest)

if (NOT GTEST_FOUND)
    message(STATUS "Adding GTest as external project")
    include(googletest)
endif ()

add_custom_target(lint)

add_subdirectory(src)
add_subdirectory(test)