# Copyright 2021 ETH Zurich and the NPBench authors. All rights reserved.

import numpy as np
import dace as dc

import ast
from typing import Dict, Set, Optional

import astunparse
from dace import registry, nodes as nd, SDFGState, SDFG, dtypes, data as dt
from dace.sdfg.utils import node_path_graph
from dace.transformation.transformation import Transformation, PatternNode

def find_str_not_in_set(existing: Set[str], target_str: Optional[str]) -> str:
    """ Try to find a new str that is not in the set.
        :param existing: the existing strs.
        :param target_str: (optional) a target_str that should be used as a base for the new str.
        :return: a new str that is not in `existing`.
    """
    base_name = target_str or "temp"

    if base_name not in existing:
        return base_name

    i = 0
    while (base_name + "_" + str(i)) in existing:
        i += 1
    return base_name + "_" + str(i)


class Renamer(ast.NodeTransformer):
    def __init__(self, repldict: Dict[str, str]):
        self.repldict = repldict

    def visit_Name(self, node):
        if node.id in self.repldict:
            node.id = self.repldict[node.id]
        return self.generic_visit(node)


class Inliner(ast.NodeTransformer):
    def __init__(self, target_id, target_ast):
        self.target_id = target_id
        self.target_ast = target_ast

    def visit_Name(self, node):
        if node.id == self.target_id:
            return ast.copy_location(self.target_ast, node)
        else:
            return self.generic_visit(node)


@registry.autoregister_params(singlestate=True)
class TaskletFusion(Transformation):
    """ Fuse a constant pad into a convolution.
    """

    tsk1 = PatternNode(nd.Tasklet)
    data = PatternNode(nd.AccessNode)
    tsk2 = PatternNode(nd.Tasklet)

    @classmethod
    def expressions(cls):
        return [
            node_path_graph(cls.tsk1, cls.data, cls.tsk2),
            node_path_graph(cls.tsk1, cls.tsk2)
        ]

    def can_be_applied(self, graph: SDFGState, candidate: Dict[PatternNode,
                                                               int],
                       expr_index: int, sdfg: SDFG, strict: bool) -> bool:
        tsk1: nd.Tasklet = self.tsk1(sdfg)
        data: nd.AccessNode = self.data(sdfg) if self.expr_index == 0 else None
        tsk2: nd.Tasklet = self.tsk2(sdfg)

        if tsk1.language is not dtypes.Language.Python or tsk2.language is not dtypes.Language.Python:
            return False

        if data is not None and data.desc(sdfg).total_size != 1:
            return False

        # tsk1 is not used anywhere else
        if graph.out_degree(tsk1) != 1 or (data is not None
                                           and graph.out_degree(data) != 1):
            return False

        # tsk2 should have one out connector only
        if graph.out_degree(tsk2) != 1:
            return False

        # try to parse the tasklet
        try:
            if len(tsk1.code.code) != 1 or len(tsk2.code.code) != 1:
                return False
            if len(tsk1.code.code[0].targets) != 1:
                return False
        except:
            return False
        return True

    def apply(self, sdfg: SDFG) -> nd.Tasklet:
        state: SDFGState = sdfg.node(self.state_id)
        tsk1: nd.Tasklet = self.tsk1(sdfg)
        data: nd.AccessNode = self.data(sdfg) if self.expr_index == 0 else None
        tsk2: nd.Tasklet = self.tsk2(sdfg)

        tsk2_in_edge = state.out_edges(data if data is not None else tsk1)[0]

        # remove the connector from tsk2
        inputs = {
            k: v
            for k, v in tsk2.in_connectors.items()
            if k != tsk2_in_edge.dst_conn
        }

        # copy tsk1's in connectors
        repldict = {}
        for in_edge in state.in_edges(tsk1):
            old_value = in_edge.dst_conn
            # check if there's a conflict
            if in_edge.dst_conn in inputs:
                # conflicts are ok if the memlets are the same
                tsk2edge = list(
                    state.in_edges_by_connector(tsk2, in_edge.dst_conn))[0]
                if (in_edge.data != tsk2edge.data
                        or in_edge.data.data != tsk2edge.data.data):
                    in_edge.dst_conn = find_str_not_in_set(
                        set(inputs), in_edge.dst_conn)
                    repldict[old_value] = in_edge.dst_conn

            inputs[in_edge.dst_conn] = tsk1.in_connectors[old_value]

        assigned_value = tsk1.code.code[0].value
        if repldict:
            assigned_value = Renamer(repldict).visit(assigned_value)
        new_code = Inliner(tsk2_in_edge.dst_conn,
                           assigned_value).visit(tsk2.code.code[0])
        new_code_str = astunparse.unparse(new_code)

        new_tasklet = state.add_tasklet(tsk1.label + "_fused_" + tsk2.label,
                                        inputs, tsk2.out_connectors,
                                        new_code_str)

        for in_edge in state.in_edges(tsk1):
            state.add_edge(in_edge.src, in_edge.src_conn, new_tasklet,
                           in_edge.dst_conn, in_edge.data)

        for in_edge in state.in_edges(tsk2):
            # only connect if there is no edge connected to that connector yet
            if len(
                    list(
                        state.in_edges_by_connector(new_tasklet,
                                                    in_edge.dst_conn))) == 0:
                state.add_edge(in_edge.src, in_edge.src_conn, new_tasklet,
                               in_edge.dst_conn, in_edge.data)
            else:
                state.remove_memlet_path(in_edge)

        for out_edge in state.out_edges(tsk2):
            state.add_edge(new_tasklet, out_edge.src_conn, out_edge.dst,
                           out_edge.dst_conn, out_edge.data)

        state.remove_node(tsk1)
        if data is not None:
            state.remove_node(data)
        state.remove_node(tsk2)


N = dc.symbol('N', dtype=dc.int64)

# @dc.program
def kernel(A: dc.float64[N,N,N,N], B: dc.float64[N, N],
            C: dc.float64[N, N],  B2: dc.float64[N, N],
            C2: dc.float64[N, N]): 
#     outTemp = np.einsum('ijkl,pi->jklp', A, B)
#     outTemp2 = np.einsum('jklp,qj->klpq', outTemp, C)    
#     outTemp3 = np.einsum('klpq,rk->lpqr', outTemp2, B2)
#     outTemp4 = np.einsum('lpqr,sl->pqrs', outTemp3, C2)
#     return outTemp4
    dim = 20
    S = 10
    A = np.random.rand(dim, dim, dim)
    B = np.random.rand(dim, dim)
    C = np.einsum('ikl,kj->ij', A, B)

    C2 = np.zeros(dim, dim)
    for i in range(N):
        for k in range(N):
            for j in range(N):
                for l in range(N):
                    C2[i,j] += A[i,k,l] * B[k,j]
                    
                    
    tile_size = S/2
    for i in range(N):
        for j in range(N):    
            # tile S/2 elements of B[0:S/2, j]                    
            for k in range(0,N, tile_size):
                tmpB = B[k : k+tile_size, j]
                for kk in range(k, k+tile_size):
                    # stream through l
                    for l in range(N):
                        # single load of A[i,kk,l] -> S/2 new computed values of C[i,j]
                        # tmpB is cached
                        C[i,j] += A[i,kk,l] * tmpB[kk - k]
                    
    # .einsum('pi,qj,ijkl,rk,sl->pqrs', )
 
def kernel_prep():
    dim = 30
    I = np.random.rand(dim, dim, dim, dim)
    A = np.random.rand(dim, dim)
    B = np.random.rand(dim, dim)
    C = np.random.rand(dim, dim)
    D = np.random.rand(dim, dim)
    import opt_einsum as oe
    einsum_string = 'pi,qj,ijkl,rk,sl->pqrs'
    arrays = ["A", "B", "I", "C", "D"]
    path_info = oe.contract_path(einsum_string, A, B, I, C, D)
    dp_string = """
import dace as dc
import numpy as np
N = dc.symbol('N', dtype=dc.int64)
@dc.program
def kernel(I: dc.float64[N,N,N,N], A: dc.float64[N, N], B: dc.float64[N, N], C: dc.float64[N, N], D: dc.float64[N, N]): 
"""
    counter = 0
    for c in path_info[1].contraction_list:  
        first, second = c[0]
        dp_string += f"    outTemp{counter} = np.einsum('{c[2]}', {arrays[c[0][0]]}, {arrays[c[0][1]]})\n"    
        # outTemp = np.einsum(c[2], arrays[c[0][0]], arrays[c[0][1]])
        if first > second:
            arrays.pop(first)
            arrays.pop(second)
        else:
            arrays.pop(second)
            arrays.pop(first)
        arrays.append(f'outTemp{counter}')
        counter += 1
    counter -= 1
    dp_string += f"    return outTemp{counter}\n"
    print(dp_string)
    return dp_string
 
# @dc.program   
# def kernel(I: dc.float64[N,N,N,N], C: dc.float64[N, N], O: dc.float64[N,N,N,N]): 

    
#     outTemp = np.einsum('ijkl,pi->jklp', I, C)
#     outTemp2 = np.einsum('jklp,qj->klpq', outTemp, C)    
#     outTemp3 = np.einsum('klpq,rk->lpqr', outTemp2, C)
#     outTemp4 = np.einsum('lpqr,sl->pqrs', outTemp3, C)
#     return outTemp4
    
@dc.program
def kernel(I: dc.float64[N,N,N,N], C: dc.float64[N, N], O: dc.float64[N,N,N,N]): 
    # for k in dc.map[0:N]:
    #     for j in dc.map[0:N]:
    #         for i in dc.map[0:N]:
    #             temp[j,i] += B[k,j] * A[i,k]
                
    # for j in dc.map[0:N]:
    #     for j in dc.map[0:N]:
    #         for i in dc.map[0:N]:
    #             temp[j,i] += B[k,j] * A[i,k]
                
   return np.einsum('pi,qj,ijkl,rk,sl->pqrs', C, C, I, C ,ConnectionAbortedError)

# f = open('myprogram.py', 'w')
# dp_string = kernel_prep()
# f.write(dp_string)
# f.close()
# from myprogram import kernel as dprog
# # dprog = eval(dp_string)
# sdfg = dprog.to_sdfg()
sdfg = kernel.to_sdfg()

sdfg.expand_library_nodes()
sdfg.apply_transformations_repeated(TaskletFusion)
# for state in sdfg.nodes():
#     for n in state.nodes():
#         if isinstance(n, nd.AccessNode) and sdfg.arrays[n.data].shape == (1,):
#             in_edge = state.in_edges(n)[0]
#             out_edge = state.out_edges(n)[0]
#             state.remove_edge(in_edge)
#             state.remove_edge(out_edge)
#             state.remove_node(n)
#             state.add_edge(in_edge.src, in_edge.src_conn, out_edge.dst, out_edge.dst_conn, in_edge.data)
#             # state.add_edge(in_edge.src, in_edge.src_conn, out_edge.dst, out_edge.dst_conn, dc.Memlet())
sdfg.save("tensors.sdfg")
