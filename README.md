# Near-Optimal Parallel Tensor Contractions 
We present a near communication optimal tensor contraction framework for parallel systems. 
Previous frameworks primarily focus on computational optimizations. 
Our contribution is to make use of a graph based analytical approach to perform I/O optimal contractions. 
Our framework is capable of performing general tensor contractions, meaning that it can perform contractions with arbitrary number of tensors with arbitrary modes and dimensions.


## Results
Our framework was tested against state of the art tensor contraction framework, Cyclops Tensor Framework (CTF). We used matrix-matrix multiplication (MMM) and matricized tensor times Khatri-Rao product (MTTKRP) as our baseline operations. 
* For MMM our framework transferred up to x4 lower bytes compared to CTF. 
* For MTTKRP our framework transferred up to x6 lower bytes compared to CTF

## Project Setup
Currently only importing into CLion is confirmed to work.
Running CMake directly (passing the desired C and C++ compiler flags explicitly) should probably also work.

The cyclops tester code is contained inside `code/cyclopstest`. It can also be opened in CLion and compiling via 
`cmake . && make` works (while inside `code/cyclopstest`).

## For CLion
Open the outer folder in CLion as a project. Setup any Profile under `Build, Execution, Deployment` > `CMake`, passing the desired Compiler Flags (such as target architecture) as CMake options.

For now the C and C++ compiler flags are: `-DCMAKE_BUILD_TYPE=Release -DCMAKE_C_FLAGS="-std=c11 -O2 -g -march=[YOUR MACHINE ARCHITECTURE] -mprefer-vector-width=512 -ffast-math" -DCMAKE_CXX_FLAGS="-std=c++20 -O2 -g -march=[YOUR MACHINE ARCHITECTURE] -mprefer-vector-width=512 -ffast-math"`.

## Testing
### Using GoogleTest 
The `test` folder contains all tests.
Tests are compiled in C++ using the `GoogleTest` library. They test the GJK and BVH code, which was written and compiled in C.

To build the tests, uncomment lines 12 and 13 in `src/CMakeLists.txt` (and remove references to pybind `main.cpp`).

The tests can also be run from CLion conveniently, like unit tests in Java with JUnit.
(Note: you will have to build the `gjk` target, before building and running the `tester` target).

## Python Binding
Thanks to *PyBind* our code can be imported into python and used as a drop-in replacement for `numpy.einsum()`.
See line 317 in the top-level `handle_mpi.py` file to see an example usage.

The file `main.py` can be run to test our code as well. It accepts several command line parameters, such as einsum, number of processors, dimension and location of the schedule file.

## MPI
Note that this project works only with MPICH, *not* with OpenMPI (truncated message errors).

## Contributors 
* Mihai Zorca
* Daniel Trujillo
* Berke Egeli
