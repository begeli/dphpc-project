import ast
from collections import defaultdict

import astunparse
from dace.sdfg.sdfg import InterstateEdge
import dace
from dace.sdfg.nodes import *
from dace.subsets import Range
# from dace.sdfg import Scope

from dace.symbolic import pystr_to_symbolic
from dace.libraries.blas import MatMul, Transpose
import sympy
import sys
from typing import Any, DefaultDict, Dict, List, Union
import sympy as sp
import numpy as np
from sympy.solvers import solve
from sympy.parsing.sympy_parser import parse_expr
from sympy import oo, symbols
import json
import os
from datetime import datetime
import time
import copy
from typing import Optional
from dace.sdfg.propagation import propagate_memlets_sdfg
import networkx as nx



class SDFGloop:
    cycle = []
    loopGuard = []
    loopRanges = {}
    uncutloopRanges = {}
    evaluatedInnerLoops = []
    allInnerNodes = set()
    parentLoop = []
    evaluated = False
    SDFG = []
    W = sp.sympify(0)
    D = sp.sympify(0)

    def __init__(self, cycle, SDFG, loopsDict):
        self.cycle = cycle
        self.allInnerNodes = set(cycle)
        self.SDFG = SDFG
        cycleRanges = cycle[0].SOAPranges
        thisLoopGuard = []
        for v in cycle:
            if len(v.SOAPranges) < len(cycleRanges):
                cycleRanges = v.SOAPranges
            if getattr(v, 'is_loop_guard', False) and v.sparent not in cycle:
                if thisLoopGuard:
                    # multiple loop guards with the same ranges inside one cycle?
                    a = 1
                thisLoopGuard = v
        
        if thisLoopGuard.label in loopsDict.keys():
            a = 1
        loopsDict[thisLoopGuard.label] = self
        self.loopsDict = loopsDict
        self.loopGuard = thisLoopGuard
        self.loopRanges = cycleRanges
        self.uncutloopRanges = cycleRanges
        self.evaluated = False

        
    def PropagateParents(self):
        for v in self.cycle:
            if getattr(v, 'is_loop_guard', False) and v != self.loopGuard:
                # this means that we have found a loop inside our loop                
                loop = self.loopsDict[v.name]
                # check for cyclic loop depenency
                if self.parentLoop == loop:
                    a = 1
                loop.parentLoop = self
                tmp = { k : loop.loopRanges[k] for k in set(loop.loopRanges) - set(self.uncutloopRanges) }
                if len(tmp) > 1:
                    a = 1
                loop.loopRanges = { k : loop.loopRanges[k] for k in set(loop.loopRanges) - set(self.uncutloopRanges) }
                


    def EvaluateLoop(self):
        #  Check if there are some non-evaluated inner loops
        for v in self.cycle:
            if getattr(v, 'is_loop_guard', False) and \
                    v != self.loopGuard and v not in self.evaluatedInnerLoops:
                # this means that we have found more loop guards which were not evaluated yet               
                loop = self.loopsDict[v.name]
                if not loop.evaluated:
                    loop.EvaluateLoop()                    
                    self.allInnerNodes |= loop.allInnerNodes
                self.evaluatedInnerLoops.append(v)

                if v not in self.evaluatedInnerLoops:
                    # sth is wrong. We could not find the loop for the inner loop guard
                    a = 1

        # evaluate the cost of the loop. If some vertex in the loop
        # is actually a loop guard of a nested loop itself, we have to get
        # its "relative" number of executions
        # loopW = 0
        # loopD = 0
        # for v in self.cycle:
        #     # check if v is the guard of the inner loop
        #     if getattr(v, 'is_loop_guard', False) and v != self.loopGuard:
        #         loopW += v.W / (v.executions - 1)
        #         loopD += v.D / (v.executions - 1)
        #     else:
        #         loopW += v.W
        #         loopD += v.D

        loopW = sp.sympify(sum(v.W for v in self.cycle))
        loopD = sp.sympify(sum(v.D for v in self.cycle))
        self.loopGuard.W = loopW
        self.loopGuard.D = loopD






        # for v in self.cycle:
        #     #if getattr(v, 'is_loop_guard', False):
        #     depVars = list(loopW.free_symbols - set([dace.symbol(constant) for constant in sdfg.constants.keys()]))
        #     if len(depVars) > 1:
        #         a = 1
        #     if len(self.loopRanges) > 1:
        #         a = 1
        
        self.evaluated = True

    def RemoveInnerNodes(self):
        # if self.parentLoop:
        #     # our parent will clean after us
        #     return
        
        for node in self.allInnerNodes:
            try:
                if node != self.loopGuard:
                    self.SDFG.remove_node(node)
            except:
                a = 1

    def remove_backedge(self):
        inEdges = self.SDFG.in_edges(self.loopGuard)
        for e in inEdges:
            if e.src in self.allInnerNodes:
                self.SDFG.remove_edge(e)




def add_loop_name_to_arrays(state: dace.SDFGState, loop_name : str):
    for node in nx.topological_sort(state.nx):    
        if isinstance(node, (dace.nodes.Tasklet, dace.nodes.LibraryNode)):
            S = node.soap_statement 
            if S:                
                # add loop name to all arrays in outputs and phis
                updated_outputs = {}                                         
                for arr_name, base_accesses in S.outputAccesses.items():
                    updated_name = arr_name + '_' + loop_name
                    updated_outputs[updated_name] = base_accesses
                S.outputAccesses = updated_outputs

                updated_phis = {}
                for arr_name, base_accesses in S.phis.items():
                    updated_name = arr_name + '_' + loop_name
                    updated_phis[updated_name] = base_accesses
                S.phis = updated_phis

              
        elif isinstance(node, dace.nodes.NestedSDFG):
            a = 1




def DAGify_and_resolve_loops_SDFG(sdfg: dace.SDFG):
    DAGify_SDFG_step(sdfg)
    # fold the loops
    cycles = list(sdfg.find_cycles())
    loops = []
    loopsDict = {}
    for cycle in cycles:
        # cycle has repeating vertices! WTF?
        loops.append(SDFGloop(list(set(cycle)), sdfg, loopsDict))    
    
    for loop in loops:
        loop.PropagateParents()

    # for loop in loops:
    #     for state in loop.allInnerNodes:
    #         add_loop_name_to_arrays(state, loop.loopGuard.label)
  
    for loop in loops:
        loop.remove_backedge()

    # update the children after removing the loops
    DAGify_SDFG_step(sdfg)



def DAGify_and_evaluate_SDFG(sdfg: dace.SDFG):
    DAGify_SDFG_step(sdfg)
    # fold the loops
    cycles = list(sdfg.find_cycles())
    loops = []
    loopsDict = {}
    for cycle in cycles:
        # cycle has repeating vertices! WTF?
        loops.append(SDFGloop(list(set(cycle)), sdfg, loopsDict))    
    
    for loop in loops:
        loop.PropagateParents()

    for loop in loops:
        loop.EvaluateLoop()
  
    for loop in loops:
        loop.RemoveInnerNodes()

    # update the children after removing the loops
    DAGify_SDFG_step(sdfg)


def DAGify_SDFG_step(sdfg: dace.SDFG):
    idom = nx.immediate_dominators(sdfg.nx, sdfg.start_state)

    # Get loops
    for state in sdfg:
        state.loopexit = None
    for cycle in sdfg.find_cycles():
        for v in cycle:
            if v.loopexit is not None:
                continue

            # Natural loops = one edge leads back to loop, another leads out
            in_edges = sdfg.in_edges(v)
            out_edges = sdfg.out_edges(v)

            # A for-loop guard has two or more incoming edges (1 increment and
            # n init, all identical), and exactly two outgoing edges (loop and
            # exit loop).
            if len(in_edges) < 2 or len(out_edges) != 2:
                continue

            # All incoming guard edges must set exactly one variable and it must
            # be the same for all of them.
            itvar = None
            for iedge in in_edges:
                if len(iedge.data.assignments) == 1:
                    if itvar is None:
                        itvar = list(iedge.data.assignments.keys())[0]
                    elif itvar not in iedge.data.assignments:
                        itvar = None
                        break
                else:
                    itvar = None
                    break
            if itvar is None:
                continue

            # The outgoing edges must be negations of one another.
            if out_edges[0].data.condition_sympy() != (sp.Not(
                    out_edges[1].data.condition_sympy())):
                continue

            # Make sure the last state of the loop (i.e. the state leading back
            # to the guard via 'increment' edge) is part of this cycle. If not,
            # we're looking at the guard for a nested cycle, which we ignore for
            # this cycle.

            increment_edge = in_edges[0]
            if pystr_to_symbolic(itvar) in pystr_to_symbolic(
                    in_edges[1].data.assignments[itvar]).free_symbols:
                increment_edge = in_edges[1]
            if increment_edge.src not in cycle:
                continue

            loop_state = None
            exit_state = None
            out_edges = sdfg.out_edges(v)
            if out_edges[0].dst in cycle and out_edges[1].dst not in cycle:
                loop_state = out_edges[0].dst
                exit_state = out_edges[1].dst
            elif out_edges[1].dst in cycle and out_edges[0].dst not in cycle:
                loop_state = out_edges[1].dst
                exit_state = out_edges[0].dst
            if loop_state is None or exit_state is None:
                continue
        #    print('Found loop', v)
            v.loopexit = exit_state

    for state in sdfg.nodes():        
        state.sparent = None
        state.schildren = []

    for state in sdfg.nodes():        
        curdom = idom[state]
        if curdom == state:
            state.sparent = None
            state.sparent_onemore = False
            continue

        # while curdom != idom[curdom]:
        #     if sdfg.out_degree(curdom) > 1:
        #         break
        #     curdom = idom[curdom]

        state.sparent_onemore = False
        if sdfg.out_degree(curdom) == 2 and curdom.loopexit is not None:
            p = state
            while p != curdom and p != curdom.loopexit:
                p = idom[p]
            if p == curdom.loopexit:
                # Dominated by loop exit: do one more step up
                state.sparent_onemore = True

        state.sparent = curdom
        if not hasattr(curdom, "schildren"):
            curdom.schildren = []
        curdom.schildren.append(state)

    for state in sdfg.nodes():
        if state.sparent_onemore and state.sparent is not None:
            state.sparent = state.sparent.sparent
            if state.sparent.sparent:
                if not hasattr(state.sparent.sparent, "schildren"):
                    state.sparent.sparent.schildren = []
                state.sparent.sparent.schildren.append(state)
