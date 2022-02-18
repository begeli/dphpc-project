import numpy as np
import dace as dc


N, H, SM = (dc.symbol(s, dc.int64) for s in ('N', 'H', 'SM'))

# Numerically-stable version of softmax
@dc.program
def softmax(x: dc.float32[N, H, SM, SM]):
    # tmp_max = np.max(x, axis=-1, keepdims=True)
    tmp_max = np.maximum.reduce(x, axis=-1, keepdims=True, initial=-9999)
    tmp_out = np.exp(x - tmp_max)
    # tmp_sum = np.sum(tmp_out, axis=-1, keepdims=True)
    tmp_sum = np.add.reduce(tmp_out, axis=-1, keepdims=True)
    return tmp_out / tmp_sum


# Numerically-stable version of softmax
@dc.program
def softmax_gpu(x: dc.float32[N, H, SM, SM], out: dc.float32[N, H, SM, SM]):
    # tmp_max = np.max(x, axis=-1, keepdims=True)
    tmp_max = np.maximum.reduce(x, axis=-1, keepdims=True, initial=-9999)
    tmp_out = np.exp(x - tmp_max)
    # tmp_sum = np.sum(tmp_out, axis=-1, keepdims=True)
    tmp_sum = np.add.reduce(tmp_out, axis=-1, keepdims=True)
    out[:] = tmp_out / tmp_sum

sdfg = softmax.to_sdfg()

sdfg.expand_library_nodes()
sdfg.save("softmax.sdfg")