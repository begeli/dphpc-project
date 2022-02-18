set(TEST_SOURCES
        # add your *.cpp files here
        Tester.cpp
        TestPTC.cpp
        )
#add_subdirectory(backward-cpp-master)

add_executable(tester ${TEST_SOURCES})  # ${BACKWARD_ENABLE}
#add_backward(tester)

target_link_libraries(tester PUBLIC
    gjk_core
    GTest::GTest)
