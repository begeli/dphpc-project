
import dace as dc
import numpy as np
N = dc.symbol('N', dtype=dc.int64)
@dc.program
def kernel(I: dc.float64[N,N,N,N], A: dc.float64[N, N], B: dc.float64[N, N], C: dc.float64[N, N], D: dc.float64[N, N]): 
    outTemp0 = np.einsum('ijkl,pi->jklp', I, A)
    outTemp1 = np.einsum('jklp,qj->klpq', outTemp0, B)
    outTemp2 = np.einsum('klpq,rk->lpqr', outTemp1, C)
    outTemp3 = np.einsum('lpqr,sl->pqrs', outTemp2, D)
    return outTemp3
