import numpy as np

from dace import nodes

import daceml.onnx as donnx
from daceml.pytorch import DaceModule
from daceml import transformation

import torch
import torch.nn as nn
import torch.nn.functional as F

from daceml.transformation.input_to_constant import forward_memlet_tree_with_nested

import dace


@dace.program
def relu(x):
    return dace.elementwise(lambda a: max(a, dace.float32(0)), x)


N, inp, fc1, fc2, out = (dace.symbol(s)
                         for s in ('N', 'inp', 'fc1', 'fc2', 'out'))

C, H, W = (dace.symbol(s) for s in 'CHW')

H_conv1 = H - 4
W_conv1 = W - 4
H_pool1 = H_conv1 / 2
W_pool1 = W_conv1 / 2
H_conv2 = H_pool1 - 4
W_conv2 = W_pool1 - 4
H_pool2 = H_conv2 / 2
W_pool2 = W_conv2 / 2
C_before_fc1 = 16 * H_pool2 * W_pool2

Wout = dace.symbol('Wout')
Hout = dace.symbol('Hout')
Cout = dace.symbol('Cout')
sx = dace.symbol('sx')
sy = dace.symbol('sy')
kx = dace.symbol('kx')
ky = dace.symbol('ky')

@dace.program
def lenet5_parametric(input: dace.float32[N, C, H, W],
                      conv1: dace.float32[Cout, C, ky,
                                          kx], conv1bias: dace.float32[Cout],
                      conv2: dace.float32[16, 6, 5,
                                          5], conv2bias: dace.float32[16],
                      fc1w: dace.float32[C_before_fc1,
                                         120], fc1b: dace.float32[120],
                      fc2w: dace.float32[120, 84], fc2b: dace.float32[84],
                      fc3w: dace.float32[84, 10], fc3b: dace.float32[10]):
    oconv1 = np.ndarray([N, Cout, Hout, Wout], dtype=np.float32)

    donnx.ONNXConv(X=input, W=conv1, B=conv1bias, Y=oconv1, strides=[sx, sy])
    return oconv1


sdfg = lenet5_parametric.to_sdfg()
donnx.default_implementation = 'pure'
sdfg.expand_library_nodes()
sdfg.save('conv-param.sdfg')