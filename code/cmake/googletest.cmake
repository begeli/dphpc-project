include(ExternalProject)
find_package(Git REQUIRED)
find_package(Threads REQUIRED)

# Get googletest
ExternalProject_Add(
    googletest
    PREFIX "vendor/gtm"
    GIT_REPOSITORY "https://github.com/google/googletest.git"
    GIT_TAG release-1.8.0
    TIMEOUT 10
    CONFIGURE_COMMAND ""
    BUILD_COMMAND ""
    INSTALL_COMMAND ""
    UPDATE_COMMAND ""
)

# Build gtest
ExternalProject_Add(
    gtest_src
    PREFIX "vendor/gtm"
    SOURCE_DIR "vendor/gtm/src/googletest/googletest"
    INSTALL_DIR "vendor/gtm/gtest"
    CMAKE_ARGS
        -DCMAKE_INSTALL_PREFIX=${CMAKE_BINARY_DIR}/vendor/gtm/gtest
        -DCMAKE_C_COMPILER=${CMAKE_C_COMPILER}
        -DCMAKE_CXX_COMPILER=${CMAKE_CXX_COMPILER}
        -DCMAKE_CXX_FLAGS=${CMAKE_CXX_FLAGS}
        -DCMAKE_BUILD_TYPE:STRING=${CMAKE_BUILD_TYPE}
    DOWNLOAD_COMMAND ""
    UPDATE_COMMAND ""
)

# Prepare gtest
ExternalProject_Get_Property(gtest_src install_dir)
set(GTEST_INCLUDE_DIR ${install_dir}/include)
set(GTEST_LIBRARY_PATH ${install_dir}/lib/libgtest.a)
set(GTEST_MAIN_LIBRARY_PATH ${install_dir}/lib/libgtest_main.a)
file(MAKE_DIRECTORY ${GTEST_INCLUDE_DIR})
add_library(GTest::GTest STATIC IMPORTED)
set_property(TARGET GTest::GTest PROPERTY IMPORTED_LOCATION ${GTEST_LIBRARY_PATH})
set_property(TARGET GTest::GTest APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES ${GTEST_INCLUDE_DIR})
set_property(TARGET GTest::GTest APPEND PROPERTY INTERFACE_LINK_LIBRARIES Threads::Threads)

# Dependencies
add_dependencies(gtest_src googletest)
add_dependencies(GTest::GTest gtest_src)
