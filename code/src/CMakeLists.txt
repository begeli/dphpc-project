add_subdirectory(include)
add_subdirectory(mpi)

add_library(gjk_core STATIC ${ASL_SOURCES})
target_include_directories(gjk_core PUBLIC ${CMAKE_SOURCE_DIR})

add_clang_tidy_target(lint_gjk_core ${ASL_SOURCES})
add_dependencies(lint lint_gjk_core)

pybind11_add_module(pybind_gjk main.cpp)
target_link_libraries(pybind_gjk PUBLIC gjk_core)
#add_executable(gjk main.cpp)
#target_link_libraries(gjk PUBLIC gjk_core)