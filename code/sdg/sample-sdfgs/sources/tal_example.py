import dace

N = dace.symbol('N')

@dace.program
def example(A: dace.float64[N, N]):
    #for k in range(N):
    for k in dace.map[0:N]:  # TODO: wrong result using dace.map, why?
        for i in range(0, N):
            # A[i, k] = 1 + 2 * A[i, k]
            with dace.tasklet:
                A_in << A[i, k]
                A_out >> A[i, k]
                A_out = 1 + 2 * A_in
        for j in range(1, N):
            # A[j, k] = 2 * A[j, k]
            with dace.tasklet:
                A_in << A[j, k]
                A_out >> A[j, k]
                A_out = 2 * A_in

sdfg = example.to_sdfg()
sdfg.save("tal_example.sdfg")



@dace.program
def example(A: dace.float64[N, N]):
    for k in dace.map[0:N]: 
        with dace.tasklet:
            A_in << A[0, k]
            A_out >> A[0, k]
            A_out = 1 + 2 * A_in
        for i in dace.map[1:N]: 
            with dace.tasklet:
                A_in << A[i, k]
                A_out >> A[i, k]
                A_out = 2*(1 + 2 * A_in)       
