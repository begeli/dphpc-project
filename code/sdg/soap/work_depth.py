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
    
workCosts = defaultdict(int)
depthCosts = defaultdict(int)
# workCosts["<class 'dace.sdfg.nodes.MapExit'>"] = 1
# depthCosts["<class 'dace.sdfg.nodes.MapExit'>"] = 1
# workCosts["<class 'dace.sdfg.nodes.MapEntry'>"] = 1
# depthCosts["<class 'dace.sdfg.nodes.MapEntry'>"] = 1
# workCosts["wcr"] = 1
# depthCosts["wcr"] = 1








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
            


def DAGifySDFG(sdfg: dace.SDFG):
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
            if out_edges[0].data.condition_sympy() != (sympy.Not(
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


    # print('\n'.join(
    #     sorted([
    #         f"{s.sparent.label} -> {s.label}" for s in sdfg.nodes()
    #         if s.sparent is not None
    #     ])))
    # print('Toplevel:', next(s.label for s in sdfg.nodes() if s.sparent is None))



class LeafAnalysis:
    variables = []
    ranges = []
    daceRanges = {}
    phis = defaultdict(lambda : defaultdict(list))
    outputAccess = []
    # TODO: how to do it better?
    DomV = sp.simplify(0)
    W = sp.simplify(0)
    D = sp.simplify(0)
    V = []
    Q = []
    rhoOpts = []
    varsOpt = []
    Xopts = []
    name = ""

    def __init__(self):
        self.variables = []
        self.ranges = []
        self.daceRanges = {}
        self.phis = {}
        self.Q = []
        self.name = ""


    def UpdateRanges(self):            
        #  # parse scope ranges. Now this state ranges are duplicated, indexed by str and symbol:
        # SOAPranges = {}
        # for k,v in self.daceRanges.items():
        #     if isinstance(k, str):
        #         if isinstance(v, Range):
        #             SOAPranges[k] = v[0]
        #         else:
        #             SOAPranges[k] = v
        # self.daceRanges = SOAPranges

        iterVars = [dace.symbol(k) for k in list(self.daceRanges.keys())]
        iterVarsStr = [str(x) for x in iterVars]
        while self.daceRanges:
            daceRangesTmp = copy.deepcopy(self.daceRanges)
            for daceVar in daceRangesTmp:
                iterVar = dace.symbol(daceVar)
                daceRange = self.daceRanges[daceVar]
                rangeVars = np.sum(list(daceRange)[:2]).free_symbols
                rangeVarsStr = [str(x) for x in rangeVars]
                if set(iterVarsStr).intersection(set(rangeVarsStr)):
                    continue
                iterStep = daceRange[2]
                if iterStep == 1:
                    iterStart = daceRange[0]
                    iterEnd = daceRange[1]
                elif iterStep == -1:
                    iterStart = daceRange[1]
                    iterEnd = daceRange[2]
                else:
                    exit("incorrect step in iteration range!")

                self.ranges.append((iterVar, iterStart, iterEnd))
                iterVarsStr.remove(daceVar)
                del self.daceRanges[daceVar]

                    

    def CountV(self):
        self.V = 1
        for loop in reversed(self.ranges):
            self.V = sp.Sum(self.V, loop).doit()




iprint = lambda *args: print(*args)

# Do not use O(x) or Order(x) in sympy, it's not working as intended
bigo = sympy.Function('bigo')
sdfg_path = 'dace/samples/polybench/.dacecache/k2mm/program.sdfg'



def AnalyzeWorkDepth(sdfg: dace.SDFG, 
                ranges: Dict[str, Range] = None) -> [int, int]:
    # Get spanning forest
    rootNodes = []
    for node in sdfg.nodes():
        node.counted = False
        if not sdfg.in_edges(node):
            rootNodes.append(node)
        # check if we have some fixed costs defined for this class of nodes
        if not hasattr(node, 'W'):
            if str(type(node)) in workCosts.keys():
                node.W = workCosts[str(type(node))]
                node.D = depthCosts[str(type(node))]
            else:
                node.W = 0
                node.D = 0
        
    # now count depth of a scope as max and work of a scope as sum
    curWork = 0
    maxDepth = sp.sympify(0)
    if sdfg.name == "jacobi1d":
        a = 1
    for root in rootNodes:
        [W,D] = CalculateWorkDepth(sdfg, root, ranges)
         # determine which depth is longer
        symsMaxD = list(maxDepth.free_symbols)
        symsD = list(D.free_symbols)
        if maxDepth == 0 or \
                maxDepth.subs(list(zip(symsMaxD, [10000]*len(symsMaxD)))) < \
                D.subs(list(zip(symsD, [10000]*len(symsD)))):
            maxDepth = D
        # maxDepth = max(maxDepth, D)
    for node in sdfg.nodes():
        curWork += node.W
        #curWork += W
    
    sdfg.W = curWork
    sdfg.D = maxDepth
    return [curWork, maxDepth]


def CalculateWorkDepth(state: dace.SDFGState,
                    node: dace.SDFGState, 
                    ranges: Dict[str, Range]) -> [int, int]:
    # check if we are a leaf:
    # first check is state coming from DafigySDFG which adds sparents and schilren for unrolled loops
    if hasattr(node, 'sparent') and (not hasattr(node, 'schildren') or not node.schildren):
        return [node.W, node.D]
    if not state.out_edges(node):
        return [node.W, node.D]
    
    if state.name == "state_7":
        a = 1
    if node.label == "state_7":
        a = 1
    curWork = 0
    maxDepth = sp.sympify(0)

    if hasattr(node, 'sparent') and hasattr(node, 'schildren'):
        children = [child for child in node.schildren if child.counted == False]
    else:
        children = [e.dst for e in state.out_edges(node) if e.dst.counted == False]

    for e in children:
        [W,D] = CalculateWorkDepth(state, e, ranges)
  #      if node.counted:
  #          continue
  #      if not node.counted: 
            #if isinstance(node, (dace.nodes.Tasklet, dace.nodes.LibraryNode)):
        W += node.W
        D += node.D
        node.counted = True
                            
        # determine which depth is longer
        symsMaxD = list(maxDepth.free_symbols)
        D = sp.sympify(D)
        symsD = list(D.free_symbols)    
        if maxDepth == 0 or \
                maxDepth.subs(list(zip(symsMaxD, [10000]*len(symsMaxD)))) < \
                D.subs(list(zip(symsD, [10000]*len(symsD)))):
                
            maxDepth = D
        # maxDepth = max(maxDepth.subs(symsMaxD, [10000]*len(symsMaxD)),
        #                D.subs(symsD, [10000]*len(symsD)))
        curWork += W
    return [curWork, maxDepth]


def Analyze_sdfg(sdfg: dace.SDFG, statements: List[LeafAnalysis], 
            ranges: Dict[str, Range] = None)  -> [int, int]:
    work = 0
    depth  = 0
    ranges = ranges or {}
    for state in sdfg.nodes():
        in_ranges = copy.copy(ranges)
        state.SOAPranges = {k:v[0] for k, v in state.ranges.items() if isinstance(k, str)}
        in_ranges.update(state.SOAPranges)
        Analyze_scope(state, statements, in_ranges, None)   

    # fold the loops
    cycles = list(sdfg.find_cycles())
    loops = []
    for cycle in cycles:
        # cycle has repeating vertices! WTF?
        loops.append(SDFGloop(list(set(cycle)), sdfg))
    
    for loop in loops:
        loop.allLoops = loops
    
    for loop in loops:
        loop.PropagateParents()

    for loop in loops:
        loop.EvaluateLoop()
  
    for loop in loops:
        loop.RemoveInnerNodes()

    if sdfg.label == "computecol_57_8":
        a = 1
    [work, depth] = AnalyzeWorkDepth(sdfg, ranges)             
    return [work, depth] 


def Analyze_scope(state: dace.SDFGState, 
                  statements: List[LeafAnalysis], 
                  ranges: Dict[str, Range],
                  scope: Optional[dace.nodes.EntryNode])-> [int, int]:

    # propagate recursively
    snodes = state.scope_children()[scope]
    work = 0
    depth = 0

    if hasattr(scope, 'range'):
        in_ranges_dict = {var:rng for var,rng in list(zip(scope.params, scope.range.ranges))}        
    else:
        in_ranges_dict = {}

    for node in snodes:
        if isinstance(node, (dace.nodes.Tasklet, dace.nodes.LibraryNode)):
            # Analyze_node(node, state, statements, in_ranges_dict)
            Analyze_node(node, state, statements, ranges)
        elif isinstance(node, dace.nodes.EntryNode):
            # ranges.update(node.range.ranges)
            scope_range = copy.copy(ranges)
            scope_range.update({k: v for k, v in zip(node.params, node.range.ranges)})      
            Analyze_scope(state, statements, scope_range, node)
        elif isinstance(node, dace.nodes.NestedSDFG):
            #[work, depth] += 
            Analyze_sdfg(node.sdfg, statements, copy.copy(ranges))
            node.W = node.sdfg.W
            node.D = node.sdfg.D
        elif isinstance(node, dace.nodes.ExitNode):
             # update ranges for map exits, as some WCR edges are parameter-dependent            
            node.ranges = {}
            mapentry = node
            while state.entry_node(mapentry):
                mapentry = state.entry_node(mapentry)
                for pname, rng in zip(mapentry.params, mapentry.range):
                    node.ranges[pname] = rng


    if isinstance(scope, dace.nodes.EntryNode):
        return [0,0]

    if state.label == "computecol_57_8":
        a = 1
    [work, depth] = AnalyzeWorkDepth(state, ranges)
    return [state.W, state.D]


def Analyze_node(node, 
            state: dace.nodes, 
            statements: List[LeafAnalysis],
            ranges: Dict[str, Range]):
    
    S = LeafAnalysis()
    mapentry = node
    while state.entry_node(mapentry):
        mapentry = state.entry_node(mapentry)
        for pname, rng in zip(mapentry.params, mapentry.range):
            S.daceRanges[pname] = rng

    node.ranges = S.daceRanges
    node.SOAPranges = S.daceRanges

    S.UpdateRanges()
    # TODO : how to do it? Right now it's just the size of subcomputation, but it does not count operations per tasklet
    S.CountV()
    node.W = S.V
#    node.W = sp.simplify(S.V / state.executions)
    if 'i' in str(node.W):
        a = 1
    node.D = 1
    statements.append(S)





#-------------------------------------
#------------Work-depth analysis -----
#-------------------------------------

def WD_sdfg(sdfg: dace.SDFG, params)  -> [int, int]:
    for state in sdfg.nodes():
        WD_scope(state, None, params) 
        if not hasattr(state, 'W'):
            if str(type(state)) in workCosts.keys():
                state.W = workCosts[str(type(state))]
                state.D = depthCosts[str(type(state))]
            else:
                state.W = sp.sympify(0)
                state.D = sp.sympify(0)   


    DAGifySDFG(sdfg)
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
    DAGifySDFG(sdfg)

    if sdfg.label == "IF90":
        a = 1
    [work, depth] = AnalyzeWorkDepth(sdfg, sdfg.SOAPranges) 
    if "numElem" not in str(depth):
        a = 1
    return [work, depth] 


def WD_scope(state: dace.SDFGState, 
                  scope: Optional[dace.nodes.EntryNode], params) -> [int, int]:
    
    snodes = state.scope_children()[scope]    
    for node in snodes:
        if isinstance(node, (dace.nodes.Tasklet, dace.nodes.LibraryNode)):
            WD_node(node, state, params)
        elif isinstance(node, dace.nodes.EntryNode):            
            WD_scope(state, node, params)
        elif isinstance(node, dace.nodes.NestedSDFG):
            WD_sdfg(node.sdfg, params)
            node.W = node.sdfg.W
            node.D = node.sdfg.D

    [work, depth] = AnalyzeWorkDepth(state, state.SOAPranges)
    return [work, depth]


def WD_node(node, state: dace.nodes, params):
    if not state.out_edges(node) or not state.in_edges(node):
        node.W = sp.sympify(0)
        node.D = sp.sympify(0)
        return        

    ranges = node.SOAPranges
    if any(ker in node.name for ker in ['tasklet788', 'T176']):
        a = 1
    S = SOAPStatement()    
    S.name = node.label
    S.tasklet = node
    S.daceRanges[S.name] = ranges
    S.stateName = state.label
    S.inEdges = state.in_edges(node)
    S.outEdges = state.out_edges(node)

    for e in state.out_edges(node):
        AddOutputEdgeToStatement(e.data, S)    
        

    for e in state.in_edges(node):
        # check if this is an in-edge without any data 
        if e.data.subset is None or \
                    len(e.data.subset.ranges) == 0 or \
                    len(e.data.subset.ranges[0][0].free_symbols) == 0:
            continue
        AddEdgeToStatement(e.data, S, params)
           
    # TODO: this is fishy....
    if not S.outputAccesses:
        return
    if not any(S.daceRanges.values()):
        return
    S.UpdateRanges()        
    S.CalculateDominatorSize()        
    S.numExecutions = state.SOAPexecutions 
    S.CountV()
    S.CountD()

    if not S.DomV or S.DomV == 0 or not S.DomV.free_symbols:# \
                #or (len(S.DomV.free_symbols) != len(S.VhSize.free_symbols)):
        S.rhoOpts = oo
        return
    
    node.W = S.W
    node.D = S.D 
    if "-N + main__n" in str(node.D):
        a = 1

    return 












def ComparePolybenchWD(sdfg,
            statements: list, final_analysis : dict, 
            final_analysisSym : dict,
            exp : str, 
            oldPolybench : bool = True):    
    W = sum([s.W for s in statements])    
    D = sdfg.D 
    if params.allParamsEqual:
        # potentialParams = ['n']                
        potentialParams = ['n', 'm', 'w', 'h', 'N', 'M', 'W', 'H']  
        N = dace.symbol('N')
        tsteps = dace.symbol('t')
        subsList = []
        for symbol in W.free_symbols:
            if any([(param in str(symbol)) for param in potentialParams]) \
                    and 'step' not in str(symbol):
                subsList.append([symbol, N])
            if 'step' in str(symbol):
                subsList.append([symbol, tsteps])
        W = W.subs(subsList)

        subsList = []
        for symbol in D.free_symbols:
            if any([(param in str(symbol)) for param in potentialParams]) \
                    and 'step' not in str(symbol):
                subsList.append([symbol, N])
            if 'step' in str(symbol):
                subsList.append([symbol, tsteps])
        D = D.subs(subsList)  
        
        if params.superDuperMadadakaSimplification:          
            W = sp.LT(W)
            D = sp.LT(D)

    avPar = W/D               
        
    strW = str(sp.simplify(W)).replace('Ss', 'S').replace("**", "^").replace("*", "").replace("Nt", "N \\cdot t").replace("log", "\log")
    strD = str(sp.simplify(D)).replace('Ss', 'S').replace("**", "^").replace("Abs","").replace("*", "").replace("Nt", "N \\cdot t").replace("log", "\log")          
    strAvPar = str(sp.simplify(avPar)).replace('Ss', 'S').replace("**", "^").replace("Abs","").replace("*", "").replace("Nt", "N \\cdot t").replace("log", "\log")
    
    solver.sendall(("simplify;"+strW).encode())    
    strW = solver.recv(2048).decode()

    solver.sendall(("simplify;"+strD).encode())    
    strD = fromSolver.recv(2048).decode()

    toSolver.sendall(("simplify;"+strAvPar).encode())    
    strAvPar = fromSolver.recv(2048).decode()
    final_analysis[exp] = [strW, strD, strAvPar]
    
    if exp in final_analysisSym.keys():
        WDres = final_analysisSym[exp]
    else:
        WDres = WDresult()

    if oldPolybench:
        WDres.W = W.subs([[N, 1000],[tsteps, 10]])
        WDres.D_manual = D.subs([[N, 1000],[tsteps, 10]])
        WDres.avpar_manual = WDres.W / WDres.D_manual
        WDres.Wstr = strW
        WDres.D_manual_str = strD
        WDres.avpar_manual_str = strAvPar
    else:
        WDres.W = W.subs([[N, 1000],[tsteps, 10]])
        WDres.D_auto = D.subs([[N, 1000],[tsteps, 10]])
        WDres.avpar_auto = WDres.W / WDres.D_manual
        WDres.Wstr = strW
        WDres.D_auto_str = strD
        WDres.avpar_auto_str = strAvPar
    final_analysisSym[exp] = WDres

