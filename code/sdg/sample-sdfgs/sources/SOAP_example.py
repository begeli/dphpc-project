# Copyright 2019-2020 ETH Zurich and the DaCe authors. All rights reserved.
import dace
import polybench
from absl import app, flags

N = dace.symbol('N')
tsteps = dace.symbol('tsteps')

#datatypes = [dace.float64, dace.int32, dace.float32]
datatype = dace.float64

# Dataset sizes
sizes = [{
    tsteps: 20,
    N: 30
}, {
    tsteps: 40,
    N: 120
}, {
    tsteps: 100,
    N: 400
}, {
    tsteps: 500,
    N: 2000
}, {
    tsteps: 1000,
    N: 4000
}]
args = [([N], datatype), ([N], datatype)]  #, N, tsteps]


@dace.program(datatype[N, N], datatype[N, N], datatype[N, N],
            datatype[N, N, N], datatype[N, N, N], datatype[1])  #, dace.int32, dace.int32)
def SOAP_example(A, B, C, D, E, sum): 
    
    @dace.map
    def compD(i: _[0:N], j: _[0:N], k: _[0:N]):
        in_a << A[i, k]
        in_b << B[k, j]
        out >> D[i, j,k]
        out =  in_a * in_b

    @dace.map
    def compE(i: _[0:N], j: _[0:N], k: _[0:N]):
        in_c << C[i, k]
        in_b << B[k, j]
        out >> E[i, j,k]
        out =  in_c * in_b

    @dace.map
    def sum(i: _[1:N-1], j: _[1:N-1], k: _[1:N-1]):
        in_d1 << D[i-1,j, k]
        in_d2 << D[i,j, k]
        in_d3 << D[i+1,j, k]
        
        in_e1 << E[i-1,j, k]
        in_e2 << E[i,j, k]
        in_e3 << E[i+1,j, k]

        out >> sum(1, lambda x, y: x + y)
        out =  in_d1 + in_d2 + in_d3 + in_e1 + in_e2 + in_e3


def init_array(A, B, C):  #, N, tsteps):
    n = N.get()
    for i in range(n):
        A[i] = datatype(i + 2) / n
        B[i] = datatype(i + 3) / n
        C[i] = datatype(i + 3) / n


if __name__ == '__main__':
    polybench.main(sizes, args, [(0, 'A')], init_array, SOAP_example)
