import ast
from collections import defaultdict, namedtuple

import astunparse
from dace.sdfg.graph import MultiConnectorEdge
import dace
from dace.sdfg.nodes import *
from dace.subsets import Range
# from dace.sdfg import Scope

from dace.symbolic import pystr_to_symbolic
from dace import subsets
from dace.libraries.blas import MatMul, Transpose
import sympy
import sys
from typing import Any, DefaultDict, Dict, List, Union
import sympy as sp
import numpy as np
from sympy.solvers import solve
from sympy.parsing.sympy_parser import parse_expr
from sympy import oo, symbols, Poly
import json
from datetime import datetime
import time
import copy
from typing import Optional
import concurrent.futures
import dace.symbolic as ds
import networkx as nx
from ordered_set import OrderedSet
from soap.utils import * # global_parameters, extract_access, get_access_from_memlet, d2sp
from warnings import warn

LULESH_DEBUG = True

pathToMatlab = 'C:\\gk_pliki\\uczelnia\\doktorat\\performance_modelling\\repo\\DAAPCe\\daapce\\matlab'



def strip_range_name_from_ranges(iters_, ranges_, sep = "_"):
    ranges = copy.deepcopy(ranges_)
    iters = copy.deepcopy(iters_)
    if isinstance(ranges, list):
        ranges = {str(rng[0]) : (rng[1], rng[2], 0) for rng in ranges}
    if iters:
        if isinstance(iters, dict):
            newIters = {}
            for i, range in iters.items():
                   # oldIterVar = range[0].free_symbols.pop()
                    iterRange = str(range[1].free_symbols.pop())
                    newIterVar = str(i).replace(sep + iterRange, '')
                    newIters[newIterVar] = range
            iters = newIters
        else:
            # check if we are operating on state ranges (e.g., [i, 1, N]) or memlet ranges (e.g., [i, i, 1])
            if iters[0][0] == iters[0][1]:
                for i, range in enumerate(iters):
                    oldIterVar = range[0].free_symbols.pop()                    
                    iterRange = str(ranges[str(oldIterVar)][1].free_symbols.pop())
                    newIterVar = sp.sympify(str(oldIterVar).replace(sep + iterRange, ''))
                    iters[i] = [range[0].subs(oldIterVar, newIterVar), 
                                    range[1].subs(oldIterVar, newIterVar), 
                                    range[2]]
            else:
                for i, range in enumerate(iters):
                    oldIterVar = range[0].free_symbols.pop()
                    iterRange = str(ranges[str(oldIterVar)][1].free_symbols.pop())
                    newIterVar = sp.sympify(str(oldIterVar).replace(sep + iterRange, ''))
                    iters[i] = [range[0].subs(oldIterVar, newIterVar), 
                                    range[1], range[2]]
        a = 1
        return iters
    


class SOAP_statement:

    def __init__(self):
        self.variables = []
        self.ranges = defaultdict(list)
        self.daceRanges = {}
        self.reductionRanges = []
        self.phis = {}
        self.output_accesses = {}
        self.Q = []
        self.name = ""
        self.numExecutions = sp.sympify(1)
        self.appended_versions = False
        self.SSAed = False
        self.parent_subgraph = []
        self.subgraph = set()
        self.in_transients = set()
        self.out_transients = set()

    
    def get_phis(self):
        flat_phis = {}
        for arrName, baseAccesses in self.phis.items():
            for baseAccess, offsets in baseAccess.items():
                flat_phis[arrName + '[' + baseAccess + ']'] = offsets

        return flat_phis



    def solve(self, solver, params: global_parameters):
        if "data_2;__tmp4_1;__tmp2_1;data_1" in self.name:
            a = 1
        self.update_ranges()        
        self.calculate_dominator_size_2()  
        self.calculate_H_size()
        self.count_V()      
        
        self.reductionRanges = [red_dim[0] for sublist in [arr[3] 
                                for arr in self.output_accesses.values()] 
                                for red_dim in sublist]

        if not self.Dom_size or self.Dom_size == 0 or not self.Dom_size.free_symbols:
            self.rhoOpts = oo
            self.Q = self.V / self.rhoOpts
            if 'J' in str(self.rhoOpts):
                a  = 1
            return


        # if the input size is of the same order as the output size, 
        # then the computational intensity is constant
        if sum(sp.degree_list(sp.LT(self.Dom_size))) == sum(sp.degree_list(sp.LT(self.H_size))):            
            self.rhoOpts = sp.LT(self.H_size) / sp.LT(self.Dom_size)
            if not self.rhoOpts.is_number:
                self.rhoOpts = 1
            self.rhoOpts = sp.sympify(self.rhoOpts)
            self.Q = self.V / self.rhoOpts
            if 'J' in str(self.rhoOpts):
                a  = 1
            return
        if len(self.Dom_size.free_symbols) != len(self.H_size.free_symbols):
            # we have a scenario like the dominator is `i`, but the computation size is `i*k`,
            # so we have a constant I/O for some free parameter (in this case `k`). What it means
            # is that rho = k
            rho = sp.LT(self.H_size) / sp.LT(self.Dom_size)
            # now we need to resolve the range of that free iteration variable
            all_ranges = [[item[0], [item[1], item[2]]] for sublist in list(self.ranges.values()) for item in sublist] 
            rangesDict = dict(all_ranges)
            rhoRanges = [(d2sp(it), d2sp(r[0]), d2sp(r[1])) for (it, r) in rangesDict.items() if d2sp(it) in rho.free_symbols]
            for rng in rhoRanges:
                rho = rho / rng[0]
                rho = sp.Sum(rho, rng).doit()

            self.rhoOpts = rho
            if 'tmp_index' in str(rho):
                a = 1
            self.Q = self.V / self.rhoOpts
            if 'J' in str(self.rhoOpts):
                a  = 1
            return
                
        # TODO: CONTROVERSIAL!        
        # self.Dom_size = sp.sympify(str(self.Dom_size).replace('_', ''))
        if ("**" in str(self.Dom_size)):
            a = 1
        self.H_size = np.prod(list(self.Dom_size.free_symbols))     
          
        input = str(self.Dom_size).replace('_', 'x').replace('**', '^')
        output = str(self.H_size).replace('_', 'x').replace('**', '^')
        print("input: " + input + ",   output: " + output)
        if '-' in input:
            a = 1
            
        if solver.debug_no_solve:
            self.rhoOpts = 1
        else:
            self.parse_solution(solver.Command(input + ";" + output),  params)
        if self.rhoOpts == 0:
            self.rhoOpts = oo
        if 'J' in str(self.rhoOpts) or 'I' in str(self.rhoOpts):
            a = 1
        self.Q = self.V / self.rhoOpts

        if params.chosen_par_setup == "memory_independent":
            X = sp.symbols('X')
            p = sp.symbols('p')
            loc_domain_size = sp.prod(self.varsOpt[0])
            X_opt = solve(self.V - (p * loc_domain_size), X)[0]
            # absolutely horrible hack, but sp.sympify assumptions are broken
            if str(X_opt)[0] == "-":
                X_opt = X_opt * (-1)
            self.outer_tile = [tile_size.subs(X, X_opt) for tile_size in self.varsOpt[0]]
            self.Q = X_opt


    def parse_solution(self, input : str,  params : global_parameters):
        data = input
        data = data.replace('Inf', 'oo')
        data = data.replace('^', '**')
        data = data.replace('S', 'Ss')    
        data = json.loads(data)    
        if data['rhoOpts'][0] == '-1' or data['rhoOpts'][0] == '-2':
            print('Matlab server error')
            print('Error description: ' + str(data['varsOpt'][0]))
            print('Parameters: ' + str(data['Xopts'][0]) + ", " + str(data['variables'][0])) 
            print('Error code: ' + str(data['rhoOpts'][0]))
            quit()
        self.variables = sp.symbols(data["variables"], positive = True)
        try:
            self.rhoOpts = [sp.sympify(expr) for expr in data['rhoOpts']][0]
            self.varsOpt = [sp.sympify(expr) for expr in data['varsOpt']]
            self.varsOpt = np.reshape(self.varsOpt, (len(self.varsOpt)//len(self.variables), len(self.variables)))
            self.Xopts = [sp.sympify(expr) for expr in data['Xopts']]
            self.inner_tile = [sp.sympify(expr) for expr in data['inner_tile']]
            self.outer_tile = [sp.sympify(expr) for expr in data['outer_tile']]
            self.xpart_dims = copy.deepcopy(self.outer_tile)
            
            self.create_schedule(params)            
        except:
            a = 1
            
        if "j" in str(self.rhoOpts):
            a = 1
            
    
    def create_schedule(self,  params : global_parameters):
        # Get the streaming dimension. If we do have reduction ranges, we pick
        # the direction of the largest tile dimension in it.
        # If we don't have any reduction, we pick just the largest tile dimension among all dimensions
        Ss = sp.symbols('Ss')
        X = sp.symbols('X')
        p = sp.symbols('p')
        streaming = sp.symbols('streaming')
        if not self.reductionRanges:
            self.stream_dim = self.variables[np.argmax([t.subs(Ss, 100) for t in self.inner_tile])]
        else:
            # filtered_tile sets to 1 all tile dimenstions that are not in self.reductionRanges
            filtered_tile = [v if str(k) in [str(r) for r in self.reductionRanges] else sp.sympify(1) for k,v in zip(self.variables, self.inner_tile)]
            self.stream_dim = self.variables[np.argmax([t.subs(Ss, 100) for t in filtered_tile])]
           
        # calculate the outer tile (the parallel local domain) as a function of S, P, and total iteration domain
        loc_domain_size = sp.prod(self.variables).subs(self.stream_dim, X)
        loc_domain_size = loc_domain_size.subs(zip(self.variables, self.outer_tile))
        a = solve(self.V - (p * loc_domain_size), X)
        warnings.warn('RESULT OF SOLVE:\b' + str(a))
        X_size = a[0]
        self.outer_tile[self.variables.index(self.stream_dim)] = X_size
        
        # we EXPLICITLY fix the inner_tile dimension in the streaming dimension to "streaming"
        self.inner_tile[self.variables.index(self.stream_dim)] = streaming


    def init_decomposition(self, subs_list,  params : global_parameters):
        dimensions = {str(d[0]) : d[2] - d[1] + 1 for d in list(self.ranges.values())[0]}
        self.dimensions_ordered = [sp.sympify(str(dimensions[str(i)])).subs(subs_list) for i in self.variables]
        stream_dim_number = self.variables.index(self.stream_dim)
        self.param_vals = [(sp.symbols(p), val) for (p, val) in subs_list]            
        Ss = sp.symbols('Ss')
        X = sp.symbols('X')
        p = sp.symbols('p')
        comm_world = [x[1] for x in self.param_vals if x[0] == p][0]
        S_val = [x[1] for x in self.param_vals if x[0] == Ss][0]
        
        loc_domain_found = False
        
        # xpart_dims is the size of the local domain as a function of X
        xpart_dims = copy.deepcopy(self.varsOpt[0])
        # xpart_opt_dims is the size of the local domain as a function of S
        xpart_opt_dims = copy.deepcopy(self.xpart_dims)
        while(not loc_domain_found):
            loc_domain_found = True
            loc_domain_dims = [sp.floor(dim) for dim in xpart_opt_dims]
            if params.chosen_par_setup == "memory_dependent":
                loc_domain_vol = sp.prod(self.variables).subs(self.stream_dim, X)
                loc_domain_vol = loc_domain_vol.subs(zip(self.variables, loc_domain_dims))
                a = solve(self.V - (p * loc_domain_vol), X)
                warnings.warn('272 RESULT OF SOLVE: \b' + str(a))
                X_size = a[0]
                loc_domain_dims[self.variables.index(self.stream_dim)] = X_size
            else:
                loc_domain_vol = sp.prod(loc_domain_dims).subs(Ss, X)
                try:
                    a = solve(self.V - (p * loc_domain_vol), X)
                    warnings.warn('279 RESULT OF SOLVE: \b' + str(a))
                    X_size = a[0]
                except:
                    loc_domain_dims = [dim for dim in xpart_opt_dims]
                    loc_domain_vol = sp.prod(loc_domain_dims).subs(Ss, X)
                    a = solve(self.V - (p * loc_domain_vol), X)
                    warnings.warn('285 RESULT OF SOLVE: \b' + str(a))
                    X_size = a[0]
                loc_domain_dims = [dim.subs(Ss, X_size) for dim in loc_domain_dims]
                
            self.loc_domain_dims = [sp.ceiling(dim.subs(self.param_vals)) for dim in loc_domain_dims]        
            for dim_num, (loc_dim, glob_dim) in enumerate(zip(self.loc_domain_dims, self.dimensions_ordered)):
                if loc_dim > glob_dim:
                    xpart_dims[dim_num] = self.dimensions_ordered[dim_num]
                    xpart_opt_dims[dim_num] = self.dimensions_ordered[dim_num]
                    
                    # we do not need to reevaluate it for memory dependent bound, 
                    # as there is only one degree of freedom (in the streaming dimension).
                    if params.chosen_par_setup == "memory_independent":                        
                        loc_domain_found = False
        
        self.p_grid = [sp.ceiling((v / t).subs(self.param_vals))  for v,t in zip(self.dimensions_ordered, self.loc_domain_dims) ]
        
        if (sp.prod(self.p_grid) > comm_world):
            if params.chosen_par_setup == "memory_dependent":
                if self.p_grid[stream_dim_number] == 1:
                    print("\n\nERROR!!!\nMemory-dependent bound. For S={}, the minimum number of ranks is p_min={}. \
                        \nHowever, only {} ranks are given\n\n".format(S_val, sp.prod(self.p_grid), comm_world))
                    return {}
                else:
                    self.p_grid[stream_dim_number] -= 1
            else:
                # gradually increase X
                correct_decomp = False
                X_val = X_size.subs(self.param_vals)    
                while (not correct_decomp):
                    X_val *= 1.02
                    self.loc_domain_dims = [sp.ceiling(var.subs(X, X_val)) for var in xpart_dims]
                    self.p_grid = [sp.ceiling((v / t).subs(self.param_vals))  for v,t in zip(self.dimensions_ordered, self.loc_domain_dims) ]        
                    if (sp.prod(self.p_grid) <= comm_world):
                        correct_decomp = True
            
        if (sp.prod(self.p_grid) < comm_world):
            print("\n\nWarning!!!\nUsing {} out of {} processors\n\n".format(sp.prod(self.p_grid), comm_world))
            
        else:
            print("\nUsing all {} processors.\n".format(comm_world) )
        
        
    def get_data_decomposition(self, pp):
        # p_pos is an N -> N^d mapping, translating a global rank to a cooridnate rank in 
        # the d-dimensional iteration space  (p  -> [p_x, p_y, p_z, ....])
        if (sp.prod(self.p_grid) <= pp):
            print("\n\nDecomposition uses only {} processors. Given rank {} will be idle!\n\n".format(sp.prod(self.p_grid), pp))
            return {}
        
        div = lambda x,y: (x-x%y)/y
        p_pos = []
        for dim_num, dim_size in enumerate(self.p_grid):
            p_dim = div(pp, sp.prod(self.p_grid[dim_num+1 :]))
            p_pos.append(p_dim)
            pp -= p_dim * sp.prod(self.p_grid[dim_num+1 :])
            
        iter_ranges = {str(var) : 
            (p_pos[i]* self.loc_domain_dims[i], min((p_pos[i] + 1)* self.loc_domain_dims[i], dim_size))  
            for i, (var, dim_size) in enumerate(zip(self.variables, self.dimensions_ordered))}
        
        
        par_distribution = {}
        for arr, accesses in self.phis.items():
            for access, pars in accesses.items():
                rngs = {}
                for it in access.split('*'):
                    rngs[it] = iter_ranges[it]
            par_distribution[arr] = rngs
                            
        return par_distribution    
    
        
    def update_ranges(self):
        # converting ranges from "Range" type to list type
        for Sname, Sranges in self.daceRanges.items(): 
            for daceVar in Sranges:
                daceRange = Sranges[daceVar]
                if isinstance(daceRange, Range):
                    daceRange = daceRange[0]
                Sranges[daceVar] = daceRange
                

            iterVars = [dace.symbol(k) for k in list(Sranges.keys())]
            iterVarsStr = [str(x) for x in iterVars]
            while Sranges:
                daceRangesTmp = copy.deepcopy(Sranges)
                for daceVar in daceRangesTmp:
                    iterVar = dace.symbol(daceVar)
                    daceRange = Sranges[daceVar]
                    rangeVars = np.sum(list(daceRange)[:2]).free_symbols
                    rangeVarsStr = [str(x) for x in rangeVars]
                    if set(iterVarsStr).intersection(set(rangeVarsStr)):
                        continue
                    iterStep = daceRange[2]
                    if iterStep == 1 or iterStep == 0:
                        iterStart = daceRange[0]
                        iterEnd = daceRange[1]
                    elif iterStep == -1:
                        iterStart = daceRange[1]
                        iterEnd = daceRange[2]
                    else:
                        exit("incorrect step in iteration range!")

                    self.ranges[Sname].append((iterVar, iterStart, iterEnd))
                    iterVarsStr.remove(daceVar)
                    del Sranges[daceVar]


    def calculate_H_size(self):
        # SDG subgraph may span different scopes with different ranges
        # (e.g., containing one tasklet from a 3D iteration space and and 
        # another one from a 2D iteration space). In such cases, we take the 
        # single scope with maximal dimension.
        max_dom_size = 0
        max_rngs_state = []
        for st, rngs in self.ranges.items():
            if len(rngs) > max_dom_size:
                max_dom_size = len(rngs)
                max_rngs = rngs
        for st, rngs in self.ranges.items():
            if len(rngs) == max_dom_size:
                max_rngs_state.append(rngs)

        # if we entered this branch, instead of taking one maximal scope, we would
        # add their sizes (e.g., instead of a single I*J*K, we would have I*J*K + I*J)
        if len(max_rngs_state) < 3:
            self.H_size = sum(
               sp.prod(v[0] for v in Sranges) for 
               Sranges in self.ranges.values()
            )
        else:
            for st, rngs in self.ranges.items():
                if len(rngs) > max_dom_size:
                    max_dom_size = len(rngs)
                    max_rngs = rngs
            self.H_size = sp.prod(v[0] for v in max_rngs)        

        simplify_H_size = True
        if simplify_H_size:
            # Keep only highest degree terms in the Vh
            # e.g., for Vh = IJ + IK + Kj - I - j - K, we keep only IJ + IK + KJ
            H_Pol = sp.Poly(self.H_size)
            H_vars = H_Pol.gens
            maxDeg = sum(sp.degree_list(sp.LT(self.H_size)))
            simp_H = sp.sympify(0)
            for k, c in zip(H_Pol.monoms(), H_Pol.coeffs()):
                if sum(k) >= maxDeg:
                    monom = c * sp.prod(x**k1 for x, k1 in zip(H_vars,k))
                    simp_H += monom
            self.H_size = d2sp(simp_H)
            
        if '**' in str(self.H_size):
            a = 1


    def simplify_dom_size(self):
        # another simplification term. Keep only highest degree terms in the denominator
        # e.g., for Dom = IJ + IK + Kj - I - j - K, we keep only IJ + IK + KJ
        DomPol = sp.Poly(self.Dom_size)
        Dom_sizears = DomPol.gens
        # NEW_VER
        maxDeg = min(sum(sp.degree_list(sp.LT(self.Dom_size))),3)
        simpDom = sp.sympify(0)
        for k, c in zip(DomPol.monoms(), DomPol.coeffs()):
            if sum(k) >= maxDeg - 1:
                # we filter out the negative terms (e.g., -i -j)
                if c > 0:
                    monom = c * sp.prod(x**k1 for x, k1 in zip(Dom_sizears,k))
                    simpDom += monom
        self.Dom_size = d2sp(simpDom)


    def calculate_dominator_size_2(self, strip_array_versions : bool = False):
        if 'data_2;__tmp4_1;__tmp2_1;data_1' in self.name:
            a = 1
        if strip_array_versions:
            # remove the version numbers from array names
            stripped_phis = {}
            for arr_name, base_accesses in self.phis.items():
                strip_name = '_'.join(arr_name.split('_')[:-1])
                stripped_phis[strip_name] = base_accesses

            stripped_outputs = {}
            for arr_name, base_accesses in self.output_accesses.items():
                strip_name = '_'.join(arr_name.split('_')[:-1])
                stripped_outputs[strip_name] = base_accesses
        else:
            stripped_phis = self.phis
            stripped_outputs = self.output_accesses
            
        self.Dom_size = sp.simplify(0)          

        # iterate over input accesses 
        for array_name, array_accesses in stripped_phis.items():    
            # iterate over different base accesses to the same array 
            for base_access, access_params in array_accesses.items():                
                dim = len(next(iter(access_params.offsets)))
                                
                vars = sp.sympify(base_access.split('*'))
                t = []                 
                access_size = sp.simplify(1)            
                        
                # iterate over different offsets in the same base access. Creating access offset set t
                for offset in access_params.offsets:
                    for i in range(dim):
                        if len(t) <= i:
                            t.append(set())                                
                        t[i].add(offset[i])
                                
                # check if we need to add the SSA dimension
                SSAing = False
                
                if array_name in self.output_arrays.keys() and \
                        eq_accesses(base_access, self.output_arrays[array_name][0]):
                    # We only checked so far that the current array is updated SOMEWHERE in our SDFG scope.
                    # Now we need to check if THIS statement updates it:
                    if array_name in stripped_outputs.keys() and \
                            eq_accesses(base_access, stripped_outputs[array_name][0]):        
                        SSAing = True            
                                                                
                    for i in range(dim):
                        # check if this output array is transient
                        if self.output_arrays[array_name][1] == []:
                            # if so, at least it should be in the output accesses, properly unrolled
                            t[i].add(self.output_accesses[array_name][1][i])
                        else:
                            t[i].add(self.output_arrays[array_name][1][i])  #stripped_outputs[array_name][1][i])
                                        
                    # assert len(access_params.ssa_dim) < 2
                    if len(access_params.ssa_dim) >= 2:
                        a = 1
                    t.append({0, 1})
                    dim += 1    
                    # if ssa_dim is empty, then every element is updated only once (not a parametric number of times).
                    # Then, we don't add additional parametric dimension.
                    if len(access_params.ssa_dim) == 1:
                        vars.append(sp.sympify(str(access_params.ssa_dim[0][0])))
                        base_access += "*" + str(access_params.ssa_dim[0][0])
                    elif SSAing:
                        ssa_dim = sp.sympify("temp")
                        vars.append(ssa_dim)
                        base_access += "*" + str(ssa_dim)
                    if not (len(access_params.ssa_dim) > 0 or SSAing):
                        dim -= 1
                                        
                    
                        
                for i in range(dim):
                    access_size *= (vars[i] - len(t[i]) + 1)
                    # accessSize *= (vars[i] - len(t[i] - set({0})))
                access_size = 2*sp.sympify(base_access) - access_size
                
                if SSAing:                    
                    access_size -= sp.sympify(base_access)
                    
                self.Dom_size += sp.simplify(access_size)

        if len(self.Dom_size.free_symbols) > 0:
            self.simplify_dom_size()
                
        self.Dom_size = d2sp(self.Dom_size)





    def count_V(self):
        if "hz_guard_1;ex_guard_1" in self.name:
            a = 1

        self.V = 0    
        
        # TODO: experimental. Instead of summing the sizes for each of the scopes,
        # we take only the largest one
        max_V = 0
        for Sname, Sranges in self.ranges.items():  
            #Sranges = StripRangeNameFromRanges(Sranges_, Sranges_)  
            Visize = sp.prod(srange[0] for srange in Sranges)
            # reorder the loops so that dependent ranges are inntermost
            dependentSymbols = [str(x) for x in Visize.free_symbols]
            ordered_ranges = []
            unordered_ranges = copy.deepcopy(Sranges)
            while unordered_ranges:
                for loop in unordered_ranges:
                    if not (any([str(x) in dependentSymbols for x in loop[2].free_symbols])) and \
                            not (any([str(x) in dependentSymbols for x in loop[1].free_symbols])):
                        ordered_ranges.append(loop)
                        if str(loop[0]) in dependentSymbols:
                            dependentSymbols.remove(str(loop[0]))
                        unordered_ranges.remove(loop)
            
            Sranges = ordered_ranges

            # check if the dominator set is degenerated
            if Visize == sp.prod(self.Dom_size.free_symbols):
                degeneratedDom = True
            else:
                degeneratedDom = False

            Vsize = 1
            self.W = 1
            for loop in reversed(Sranges):
                self.W = sp.Sum(self.W, loop).doit()
                if str(loop[0]) in [str(x) for x in list(Visize.free_symbols)]:
                    Vsize = sp.Sum(Vsize, loop).doit()
                else:
                    if degeneratedDom:                    
                        a = 1
                        Vsize = sp.Sum(Vsize, loop).doit()
            
            if str(max_V) == 'dace_m_0*dace_n_0 + dace_m_0*(dace_n_0**2/2 - dace_n_0/2)':
                a = 1
            if compare_Q(Vsize, max_V):
                self.V = d2sp(Vsize)
                max_V = Vsize
            #self.V += d2sp(Vsize)

        if "j" in str(self.V):
            a = 1


    def concatenate_sdg_statements(self, pred, in_S):  
        if "fc2_1" in in_S.name:
            a = 1
        
        # merge ranges of two statements            
        for in_state, in_ranges in in_S.ranges.items():
            if in_state in self.ranges.keys():
                for in_rng in in_ranges:
                    if all(in_rng[0] != rng[0] for rng in self.ranges[in_state]):
                        self.ranges[in_state].append(in_rng)
            else:
                self.ranges[in_state] = in_ranges
      
        if "stateFOR115_map" in self.ranges.keys():
            vars = [x for (x, y, z) in self.ranges["stateFOR115_map"]]
            if len(vars) != len(set(vars)):
                a = 1
        self.name = ';'.join(list(OrderedSet(self.name.split(';')).union(OrderedSet(in_S.name.split(';')))))
        self.subgraph = self.subgraph.union(in_S.subgraph)
        self.output_arrays = {**self.output_arrays, **in_S.output_arrays}
        if all(nm in self.name for nm in ["fc2_1", "__tmp8_1"]):
            a = 1
            
        if not self.has_correct_ranges():
            a = 1
                
        if pred:
            ## OLD: joining only on a single designated array pred
            # concatenation_array = strip(pred)
            # NEW: joining on all in_S arrays
            for concatenation_array in in_S.output_accesses.keys():    
                if concatenation_array in self.phis.keys():                    
                    self.match_iter_vars(in_S, concatenation_array, True)

                    
        # matching iteration variables also on input reuse
        for concatenation_array in in_S.phis.keys():    
            if concatenation_array in self.phis.keys():
                self.match_iter_vars(in_S, concatenation_array, False)
                    
    
                    
        for array, phi in in_S.phis.items():
            if array in self.phis:
                for baseAccess in phi.keys():
                    #check for an equivalent existing access (e.g. i*j and j*i)
                    equiv_base_access = [other for other in self.phis[array].keys() if sp.sympify(baseAccess) == sp.sympify(other)]
                                              
                    if baseAccess in self.phis[array].keys():
                        self.phis[array][baseAccess].offsets |= copy.deepcopy(phi[baseAccess].offsets)
                    elif equiv_base_access:
                        self.phis[array][equiv_base_access[0]].offsets |= copy.deepcopy(phi[baseAccess].offsets)
                    else:
                        self.phis[array][baseAccess] = copy.deepcopy(phi[baseAccess])
            else:
                self.phis[array] = copy.deepcopy(phi)

        for array, access in in_S.output_accesses.items():
            # TODO: check this condition
            #if array not in self.phis:
                self.output_accesses[array] = copy.deepcopy(access)
                
        if "data_2;__tmp4_1;__tmp2_1;data_1" in self.name:
            a = 1


    def add_edge_to_statement(self, memlet : dace.Memlet, ssa_dim,  params : global_parameters):
        if memlet.subset is None or memlet.is_empty():
            return

        # all iteration variables known to this statement
        itervars = set(map(dace.symbol, [v.keys() for v in self.daceRanges.values()][0]))
        (arrayName, baseAccess, offsets) =  get_access_from_memlet(memlet, itervars)
        if arrayName not in self.phis.keys():
            self.phis[arrayName] = defaultdict(set)
        # check if the access is SOAP: that is, if the same array is accessed by 
        # DIFFERENT baseAccess, we need to check if they overlap

        if len(self.phis[arrayName]) > 0:
            existingPhi = list(self.phis[arrayName])[0].split('*')
            baseAccessVec = baseAccess.split('*')
            if params.allInjective:
                warn('Assuming that the access ' + arrayName + str(existingPhi) \
                    + " never overlaps with "  + arrayName + str(baseAccessVec) + "\n")
            else:
                warn('Assuming that the access ' + arrayName + str(existingPhi) \
                    +" perfectly overlaps with "  + arrayName + str(baseAccessVec) + "], "\
                    +"thus, the latter one does not generate any additional inputs.\n")
                return
    
        soap_array = SOAPArray(memlet.data)
        memlet.soap_array = soap_array
        memlet.soap_array.baseAccess = baseAccess
    

        # check for an equivalent existing access (e.g. i*j and j*i)
        equiv_base_access = [other for other in self.phis[arrayName].keys() if sp.sympify(baseAccess) == sp.sympify(other)]
        if equiv_base_access:
            baseAccess = equiv_base_access[0]

        if baseAccess not in self.phis[arrayName].keys():
            # self.phis[arrayName][baseAccess] = set()
            access_params = namedtuple('params', ['ssa_dim', 'offsets'])
            self.phis[arrayName][baseAccess] = access_params
            self.phis[arrayName][baseAccess].offsets = set()
        
        self.phis[arrayName][baseAccess].offsets.add(tuple(offsets))
        # will this work?
        self.phis[arrayName][baseAccess].ssa_dim = ssa_dim



    def add_output_edge_to_statement(self, memlet : dace.Memlet, ssa_dim):
        # all iteration variables known to this statement
        itervars = set(map(dace.symbol, [v.keys() for v in self.daceRanges.values()][0]))
        (arrayName, baseAccess, offsets) =  get_access_from_memlet(memlet, itervars)
        
        # self.SSAed = memlet.soap_array.SSAed
        self.output_accesses[arrayName] = (baseAccess,tuple(offsets), memlet.wcr is not None, ssa_dim)


    def match_iter_vars(self, in_S, concatenation_array : str, out_join : bool):
        """"
        here we can also resolve matching iteration variables. E.g., 
        if self.phis[concatenation_array] == A[tmp_for_3] and in_S.output_accessses == A[tmp_for_4],
        then we know that tmp_for_3 == tmp_for_4. 
        BUT! Their ranges also must match, e.g., temp[i] and temp[j],
        if i in range(N) and j in range(i, N) SHOULD NOT be merged
        """        
        if out_join:
            join_base_accesses = [in_S.output_accesses[concatenation_array][0]]
        else:             
            join_base_accesses = list(in_S.phis[concatenation_array].keys())
                
        iters_to_merge = []
        for join_access in join_base_accesses:
            for base_access in self.phis[concatenation_array].keys():
                if eq_accesses(base_access, join_access):    
                    # it doesn't make sense to merge identical accesses (e.g., A[i] -> A[i])
                    # it makes sense only for non-trivial merges, e.g., A[tmp_1] -> A[tmp_2]
                    if base_access != join_access:                                            
                        iters_to_merge = dict(zip(base_access.split('*'), join_access.split('*')))                            
                
            if iters_to_merge:
                #   rng_dict = rng_global2dict(self.ranges)
                for scope, ranges in self.ranges.items():    
                    rng_dict = rng_list2dict(ranges)                        
                    for i, rng in enumerate(ranges):
                        if str(rng[0]) in iters_to_merge.keys():
                            new_it = dace.symbol(iters_to_merge[str(rng[0])])
                            # check if iteration variable (new_it) is present in our scope to swap it
                            if new_it not in rng_dict.keys():
                            #     # and if it is, the ranges must match
                            #     if rng_dict[new_it][0].free_symbols == rng[1].free_symbols \
                            #             and rng_dict[new_it][1].free_symbols == rng[2].free_symbols:
                            #         ranges[i] = (dace.symbol(iters_to_merge[str(rng[0])]), rng[1], rng[2])
                            # else:
                                ranges[i] = (dace.symbol(iters_to_merge[str(rng[0])]), rng[1], rng[2])
                
                if not out_join:
                    # merge input reuse access variables
                    self.phis[concatenation_array][join_access] = self.phis[concatenation_array][base_access]
                    del self.phis[concatenation_array][base_access]
                                
            if out_join:
                # TODO: experimental            
                del self.phis[concatenation_array]
                
    
    def print_schedule(self):
        print("Kernel:              " + self.name)
        print("Iteration variables: " + str(self.variables))
        print("Inner tile:          " + str(self.inner_tile))
        print("Outer tile:          " + str(self.outer_tile))
        print("Streaming direction: " + str(self.stream_dim))
        print("Comp. intensity:     " + str(self.rhoOpts))
                
            
                
                     



# TODO:
# below is the work in progress for proper depth counting

    #    # do the same to update numExecutions
    #    # dependentSymbols = [str(x) for x in self.numExecutions.free_symbols]
    #     ordered_iteration_ranges = []
    #     dependentSymbols = [str(var[0]) for var in self.ranges
    #                                 if str(var[0]) in [str(x) for x in sp.sympify(self.numExecutions).free_symbols]]
    #     unordered_ranges = [rng for rng in self.ranges if str(rng[0]) in dependentSymbols]
    #     while unordered_ranges:
    #         for loop in unordered_ranges:
    #             if not (any([str(x) in dependentSymbols for x in loop[2].free_symbols])) and \
    #                     not (any([str(x) in dependentSymbols for x in loop[1].free_symbols])):
    #                 ordered_iteration_ranges.append(loop)
    #                 if str(loop[0]) in dependentSymbols:
    #                     dependentSymbols.remove(str(loop[0]))
    #                 unordered_ranges.remove(loop)
        
    #     # # we fist calculate number of executions which are iteration-variable-dependent
    #     # if "i" in str(self.numExecutions):
    #     #     a = 1
    #     #     # i = dace.symbol("i")
    #     #     # N = dace.symbol("N")
    #     #     # if "j" in str(self.numExecutions):
    #     #     #     j = dace.symbol("j")
    #     #     #     self.numExecutions = self.numExecutions.subs([[i, N], [j, N]])/6
    #     #     # else:
    #     #     #     self.numExecutions = self.numExecutions.subs(i, N)/2
    #     # dependentExec = sp.sympify(1)
    #     # for loop in reversed(ordered_iteration_ranges):
    #     #     dependentExec = sp.Sum(dependentExec, loop).doit()

    #     # # and finally we multiply by the independent part. To get the independent part, we substitute iteration
    #     # # variables with 1
    #     # subsList = []
    #     # dependentSymbols = [(var[0]) for var in self.ranges
    #     #                             if str(var[0]) in [str(x) for x in sp.sympify(self.numExecutions).free_symbols]]
    #     # for depVar in dependentSymbols:
    #     #     subsList.append([depVar, 1])
    #     # independentExec = self.numExecutions.subs(subsList)

    #     # for loop in reversed(ordered_iteration_ranges):
    #     #     independentExec = sp.Sum(independentExec, loop).doit()

    #     # self.numExecutions = dependentExec * independentExec
      

    def count_D(self):
        self.D = sp.sympify(1)
        for redRange in self.reductionRanges:
            redVar = redRange[0]
            thisD = sp.log(sp.Sum(1, redRange)).doit()            
            self.D += thisD
        
        
        cur_ranges = next(iter(self.ranges.values()))
        cur_ranges_dict = {str(x[0]) : (x[1], x[2], 1) for x in cur_ranges}

        while (True):
            dependentVars = [var[0] for var in cur_ranges
                                    if str(var[0]) in [str(x) for x in self.D.free_symbols]]
            if not dependentVars:
                break
            for var in dependentVars:
                varRange = [rng for rng in cur_ranges if rng[0] == var][0]
                dfdx = sp.diff(self.D, var)
                if dfdx.free_symbols:
                    subsList = []
                    for symbol in dfdx.free_symbols:
                        subsList.append([symbol, 10 if symbol == var else 1000])
                    dfdx = dfdx.subs(subsList)
                if dfdx > 0:
                    self.D = self.D.subs(var, varRange[2])
                else:
                    self.D = self.D.subs(var, varRange[1])              

        if self.name == "T83":
            a = 1

        # while (any(str(x) in self.SOAPranges for x in self.numExecutions.free_symbols)):                
        #     x = [x for x in self.numExecutions.free_symbols if str(x) in self.SOAPranges][0]
        #     cur_range = self.SOAPranges[str(x)]
        #     self.numExecutions = sp.Sum(self.numExecutions, (x, cur_range[0], cur_range[1])).doit()
        
        # reductionRange may be dynamic (dependent on outer iteration variables)
        # if so, use self.ranges to resolve it

        # self.ranges is a dict of ranges indexed by the state name (to encompass SDG statements
        # spanning multiple states). However, counting D is only relevant for atomic (single-tasklet)
        # statements, so we can just take the first element of the dictionary
        if len(self.ranges) > 1:
            raise Exception("Counting statement depth on the composite subgraph statement")
        
        d = 1
        for cur_depth in reversed(self.numExecutions):
            x = sp.sympify(str(cur_depth[0]))
            d = sp.Sum(d, (x, 1, cur_depth[1])).doit()
        #     dependent_iter_vars = [x for x in cur_depth.free_symbols if str(x) in cur_ranges_dict.keys()]
        #     if len(dependent_iter_vars) == 0:
        #         x = sp.sympify('aux_iter_var')
        #         relevant_range = (0, cur_depth-1)
        #     else:
        #         x = dependent_iter_vars[0]
        #         relevant_range = cur_ranges_dict[str(x)]
        #     d = sp.Sum(d, (x, relevant_range[0], relevant_range[1])).doit()
        # d /= sp.simplify(self.numExecutions[0])
        if ('-' in str(d)):
            a = 1

        self.D *= d  

        
        if "i" in str(self.D):
            a = 1
                


    def max_rho(self):
        solverTimeout = 15
        inputs = self.Dom_size
        outputs = sp.prod(inputs.free_symbols)

        vars = list(inputs.free_symbols.union(outputs.free_symbols))
        self.variables = vars
        u = sp.symbols(['u{}'.format(i) for i in range(len(vars))])
        A, X, M = sp.symbols('A, X, M', positive = True)
        ineqconstr = [a * b for a, b in zip(u, np.array(list(vars)) - 1)]

        # form the Lagrangian from the KKT multipliers
        L = outputs - A * (inputs - X) - sum(ineqconstr)
        grad = [L.diff(x) for x in vars + [A]]
        sys = grad + ineqconstr
        varss = vars + [A] + u
      #  print("\nsys:\n" + str(sys))
      #  print("\nvarss:\n" + str(varss))
      #  print("\nsolve(sys,vars):\n")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(solve, sys, varss)
            try:
                sol = future.result(timeout = solverTimeout)
            except:
                a = 1
           # print(return_value)

        # sol = solve(sys, varss)

        Xoptstmp = []
        rhoOptstmp = []
        varsOpttmp = []
        Xopts = []
        rhoOpts = []
        varsOpt = []
        maxRho = sp.sympify(0)
        if self.name == 'comp_iout':
            a = 1
        for i in range(len(sol)):
            varOpt = sol[i][:len(vars)]
            rho = (outputs / (X - M)).subs(tuple(zip(vars, varOpt)))
            # Xopt = solve(sp.diff(rho, X), X)
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(solve, sp.diff(rho, X), X)
                try:
                    Xopt = future.result(timeout = solverTimeout)
                    a = 1
                except:
                    Xopt = []
                    a = 1
            if not Xopt:
                curRho = sp.limit(rho, X, oo)
                Xopt = oo
            else:
                if len(Xopt) > 1:
                    # TODO: again, something fishy... We have suspiciously many solutions to optimal rho.
                    oneGoodRho = False
                    for XoptSol in Xopt:
                        if M in XoptSol.free_symbols:
                            curRho = sp.simplify(rho.subs(X, XoptSol[0]))
                            if not oneGoodRho:
                                oneGoodRho = True
                            else:
                                # now it means that more than one solution contains M
                                sys.exit("Too many solutions in dRho == 0")
                    if not oneGoodRho:
                        sys.exit("Many solutions, but none with M in dRho == 0")
                else:
                    curRho = sp.simplify(rho.subs(X, Xopt[0]))
                
            
            # TODO: Do we want only the best solution, or all of them?
            if curRho.subs(M,1000) > maxRho.subs(M,1000):
                maxRho = curRho
                rhoOpts = maxRho
                varsOpt = varOpt
                Xopts = Xopt

        self.rhoOpts = rhoOpts
        self.varsOpt = varsOpt
        self.Xopts = Xopts
        if not rhoOpts:
            a = 1 
        return [rhoOpts, varsOpt, Xopts]
    
    
    def swap_iter_vars(self, swaplist, inv_swaplist, solver):
        # used for a loop swap transformation, e.g., interchanging i<->j
        
        # swap inputs (phis)
        temp_phis = defaultdict(set)
        for arr, base_accesses in self.phis.items():
            temp_phis[arr] = defaultdict(set)
            for base_access in base_accesses:
                new_base = swap_in_string(base_access, swaplist, inv_swaplist)                
                temp_phis[arr][new_base] = copy.deepcopy(self.phis[arr][base_access])            
        self.phis = temp_phis
            
        # swap outputs
        for arr, access in self.output_accesses.items():
            self.output_accesses[arr] = (swap_in_string(access[0], swaplist, inv_swaplist),
                                         access[1], access[2], access[3])
            
        # swap ranges
        for st, rngs in self.ranges.items():
            new_rngs = []
            for rng in rngs:
                new_rngs += [(dace.symbol(swap_in_string(str(rng[0]), swaplist, inv_swaplist)),
                                          rng[1], rng[2])]
            self.ranges[st] = new_rngs
        
        # recalculate
        self.solve(solver)

    # --------------------------------------------
    # ---------- various helper functions --------
    # --------------------------------------------
    
    def has_correct_ranges(self) -> bool:
        for state, rngs in self.ranges.items():
            vars = [x for (x, y, z) in rngs]
            if len(vars) != len(set(vars)):
                return False
            
        return True

class SOAPArray:
    def __init__(self, arrName):
        self.arrName = arrName
        self.version = 0
        self.SSAed = False


# ------------------------------------
# W/D result container
# ------------------------------------

class WDresult:
    W = sp.sympify(0)
    D_manual = sp.sympify(0)
    D_auto = sp.sympify(0)
    avpar_manual = sp.sympify(0)
    avpar_auto = sp.sympify(0)
    Wstr = ""
    D_manual_str = ""
    D_auto_str = ""
    avpar_manual_str = ""
    avpar_auto_str = ""
    def __init__(self):
        self.W = sp.sympify(0)
        self.D_manual = sp.sympify(0)
        self.D_auto = sp.sympify(0)
        self.avpar_manual = sp.sympify(0)
        self.avpar_auto = sp.sympify(0)
        self.Wstr = ""
        self.D_manual_str = ""
        self.D_auto_str = ""
        self.avpar_manual_str = ""
        self.avpar_auto_str = ""