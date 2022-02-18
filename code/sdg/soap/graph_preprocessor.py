# from collections import defaultdict
# from dace.sdfg.nodes import *
# from dace.subsets import Range
# import sympy as sp
# from typing import Optional
# import copy
# from dace.sdfg.graph import MultiConnectorEdge
# import dace
# from dace.sdfg.nodes import *
# from dace.subsets import Range
# from dace import subsets
# import re
# from soap.utils import *
# import networkx as nx
# from soap.analysis_classes import SOAPArray



# class graph_preprocessor:
#     def __init__(self):
#         self.readWriteArrays = []
#         self.reducedArrays = []
#         self.readWriteOutputs = {}
#         self.counter = 0
#         self.iterVarDict = {}
#         self.taskletStatistics = defaultdict(lambda: defaultdict(int))


#     # # find arrays that are NOT read-only. For them, we will add an SSA (update-counter) dimension
#     # def add_versions_to_arrays_SDFG(self, sdfg: dace.SDFG):
#     #     for state in sdfg.nodes():
#     #         self.add_verstions_to_arrays_State(state, sdfg)
        

#     # def add_versions_to_arrays_State(self, state: dace.SDFGState, 
#     #                                 sdfg: dace.SDFG):
#     #     snodes = state.nodes()
    
#     #     for node in snodes:
#     #         if isinstance(node, Tasklet):                
#     #             tasklet_parents = [t for t in nx.ancestors(state.nx, node) if isinstance(t, dace.nodes.Tasklet)]
#     #             for e in state.out_edges(node) + state.in_edges(node):
#     #                 arrName = e.data.data
#     #                 num_previous_updates = len([prev_upd for prev_upd in tasklet_parents if \
#     #                     any([outEdge.data.data == arrName  for outEdge in state.out_edges(prev_upd)])])

#     #                 soap_array = SOAPArray(arrName)
#     #                 soap_array.version = num_previous_updates
#     #                 e.soap_array = soap_array
        
#     #         elif isinstance(node, dace.nodes.NestedSDFG):
#     #             self.add_versions_to_arrays_SDFG(node.sdfg)

        
#     # fix buggy DaCe ranges (they are doubled, one indexed by a symbol, other by a string)
#     # also, it updates executions property, as now it is absolute, not relative to parent state
#     def FixRangesSDFG(self, sdfg: dace.SDFG, 
#                     ranges: Dict[str, Range] = None,
#                     replacements: Dict[str, str] = None,
#                     numExecutions = []):
#         if not replacements:
#             replacements = {}
#         if not numExecutions:
#             numExecutions = [(sp.sympify("iter_begin"), sp.sympify("1"))]
#         sdfg.SOAPranges = ranges
#         for state in sdfg.nodes():
#             orderedRanges = {k:v[0] for k, v in state.ranges.items() if isinstance(k, str)}

#             # orderedRangesSwap = {}
#             # for k, v in orderedRanges.items():
#             #     # if we have a ranges like  {'i': (0, N, 1), 'j' : (0, i - 1, 1)}, then we replace BOTH:
#             #     # ranges 'j' : (0, i_N - 1, 1), and then, keys. Resulting ranges dict will look like:
#             #     # {'i_N' : (0, N, 1), 'j_i_N' : (0, i_N - 1, 1)}
                
#             #     # first, fix ranges:
#             #     newV = list(v)
#             #     for i in range(2):                
#             #         for var in v[i].free_symbols:
#             #             if str(var) in orderedRanges.keys():
#             #                 varRange = orderedRanges[str(var)]
#             #                 newVar = '%s_%s' % (var, '_'.join(map(str, varRange[0].free_symbols | varRange[1].free_symbols)))                
#             #                 # new stuff! 
#             #                 newVar = '%s_%s' % (var, '_'.join(map(str, varRange[1].free_symbols)))
#             #                 # very new stuff!
#             #                 newVar = AddRangeToIter(var, varRange)
#             #                 newV[i] = v[i].subs(var, dace.symbol(newVar))                            
                
#             #     newK = '%s_%s' % (k, '_'.join(map(str, newV[0].free_symbols | newV[1].free_symbols)))
#             #     #new stuff!
#             #     newK = '%s_%s' % (k, '_'.join(map(str, newV[1].free_symbols)))
#             #     # very new stuff!
#             #     newK = AddRangeToIter(k, newV)

#             #     # now we can end up with iteration variable names like 'j_i_N_N', where N appers twice
#             #     # we want every parameter to appear at most once                
#             #     syms = newK.split('_')
#             #     duplicateVars = set([x for x in syms if syms.count(x) > 1])
#             #     for dupVar in duplicateVars:
#             #         newK = re.sub('(_' + dupVar + ')\\1+', r'\1', newK)

#             #     if len(state.ranges[k].ranges) > 1:
#             #         a = 1
#             #     state.ranges[k].ranges[0] = tuple(newV)
#             #     state.ranges[newK] = state.ranges[k]
#             #     del state.ranges[k]   
#             #     newRange = []
#             #     for i in range(3):
#             #         r = orderedRanges[k][i]
#             #         if len(r.free_symbols) > 0:
#             #             oldvar = str(r.free_symbols.pop())
#             #             if oldvar in orderedRanges.keys():
#             #                 newvar = AddRangeToIter(oldvar, orderedRanges[oldvar])
#             #                 newRange.append(r.subs(dace.symbol(oldvar), dace.symbol(newvar)))
#             #             else:
#             #                 newRange.append(r)    
#             #         else:
#             #             newRange.append(r)

#             #     orderedRangesSwap[newK] = tuple(newRange) #orderedRanges[k]
#             #     sdfg.replace(k, newK)    
#             # orderedRanges = orderedRangesSwap 

#             if orderedRanges and ranges:
#                 orderedRanges.update(ranges)  
#             elif ranges:
#                 orderedRanges = ranges                      

#             state.SOAPranges = orderedRanges 
#             if len(state.free_symbols) > 0:
#                 itervar = sp.sympify(list(state.free_symbols)[0])
#             else:
#                 itervar = sp.sympify("i_" + state.label)
#             state.SOAPexecutions = numExecutions + [(itervar, state.executions)]
#             b = state.executions
#             if state.label == "s73_12":
#                 a = 1

#             if state.name == "T83":
#                 a = 1
#             # for x, cur_range in state.SOAPranges.items():
#             #     state.SOAPexecutions = sp.Sum(state.SOAPexecutions, (dace.symbol(x), cur_range[0], cur_range[1])).doit()
#             # while (any(str(x) in state.SOAPranges for x in state.SOAPexecutions.free_symbols)):                
#             #     x = [x for x in state.SOAPexecutions.free_symbols if str(x) in state.SOAPranges][0]
#             #     cur_range = state.SOAPranges[str(x)]
#             #     state.SOAPexecutions = (sp.Sum(state.SOAPexecutions, (x, cur_range[0], cur_range[1])).doit())
#             #state.SOAPexecutions = state.executions * numExecutions
#             # while (any(str(x) in state.SOAPranges for x in state.SOAPexecutions.free_symbols)):                
#             #     x = [x for x in state.SOAPexecutions.free_symbols if str(x) in state.SOAPranges][0]
#             #     cur_range = state.SOAPranges[str(x)]
#             #     state.SOAPexecutions = (sp.Sum(state.SOAPexecutions, (x, cur_range[0], cur_range[1])).doit())

#             self.FixRangesScope(state, state.SOAPranges, None, replacements, numExecutions) 
        

#     def FixRangesScope(self, state: dace.SDFGState, 
#                     ranges: Dict[str, Range],                    
#                     scope: Optional[dace.nodes.EntryNode],
#                     replacements: Dict[str, str] = None,
#                     numExecutions = []):
        
#         snodes = state.scope_children()[scope]
#         for node in snodes:
#             node.SOAPranges = copy.deepcopy(ranges)
#             if isinstance(node, dace.nodes.EntryNode):   
#                 # add range name to iteration variables
#                 # # Name convention: __{iteration variable}_{all}_{symbols}_{in}_{range}
#                 # newreplacements = {k :'%s_%s' % (k, '_'.join(map(str, v[0].free_symbols | v[1].free_symbols))) \
#                 #         for k, v in zip(node.params, node.range.ranges)}
#                 # # new stuff!
#                 # newreplacements = {k :'%s_%s' % (k, '_'.join(map(str, v[1].free_symbols))) \
#                 #         for k, v in zip(node.params, node.range.ranges)}
#                 # # very new stuff !
#                 # newreplacements = {k : AddRangeToIter(k, v) \
#                 #         for k, v in zip(node.params, node.range.ranges)}
#                 # node.params = list(newreplacements.values()) #[r[1] for r in newreplacements]
#                 # newRanges = []
#                 # for rng in node.range.ranges:                    
#                 #     newRng = []
#                 #     for i in range(3):
#                 #         try:
#                 #             if len(rng[i].free_symbols) > 1:
#                 #                 a = 1
#                 #             if len(rng[i].free_symbols) == 0:                            
#                 #                 newRng.append(rng[i])      
#                 #                 continue                
#                 #             if str(rng[i].free_symbols.pop()) in replacements.keys():
#                 #                 oldSymbol = rng[i].free_symbols.pop()
#                 #                 newSymbol = dace.symbol(replacements[str(oldSymbol)])
#                 #                 newRng.append(rng[i].subs(oldSymbol, newSymbol))
#                 #             else:
#                 #                 newRng.append(rng[i])
#                 #         except:
#                 #             newRng.append(rng[i])
#                 #             a = 1
#                 #     newRng = tuple(newRng)
#                 #     newRanges.append(newRng)
#                 # node.range.ranges = newRanges
#                 # subgraph = state.scope_subgraph(node)
#                 # for name, rep in {**replacements, **newreplacements}.items():
#                 #     subgraph.replace(name, rep)

#                 orderedRanges = {k: v for k, v in zip(node.params, node.range.ranges)}
#                 if orderedRanges and ranges:
#                     orderedRanges.update(ranges) 
#                 elif ranges:
#                     orderedRanges = ranges       
#                 node.SOAPranges = copy.deepcopy(orderedRanges)
#                 # self.FixRangesScope(state, node.SOAPranges, node, {**replacements, **newreplacements}, numExecutions)
#                 self.FixRangesScope(state, node.SOAPranges, node, replacements, numExecutions)
#             elif isinstance(node, dace.nodes.NestedSDFG): 

#                 # nested_numExecs = state.executions
#                 # while (any(str(x) in state.SOAPranges for x in nested_numExecs.free_symbols)):                
#                 #     x = [x for x in nested_numExecs.free_symbols if str(x) in state.SOAPranges][0]
#                 #     cur_range = state.SOAPranges[str(x)]
#                 #     nested_numExecs = sp.Sum(nested_numExecs, (x, cur_range[0], cur_range[1])).doit()
#                 # for x, cur_range in state.SOAPranges.items():
#                 #     nested_numExecs = sp.Sum(nested_numExecs, (dace.symbol(x), cur_range[0], cur_range[1])).doit()
#                 if len(state.free_symbols) > 0:
#                     itervar = sp.sympify(list(state.free_symbols)[0])
#                 else:
#                     itervar = sp.sympify("i_" + state.label)

#                 if state.name == "T83":
#                     a = 1

#                 self.FixRangesSDFG(node.sdfg, copy.copy(ranges), replacements, numExecutions + [(itervar, state.executions)])
            
#             elif isinstance(node, Tasklet):            
#                 for e in (state.in_edges(node) + state.out_edges(node)):
#                     if isinstance(e.data.subset, Indices):
#                         e.data.subset = Range.from_indices(e.data.subset)


#     # replace WCR edges with one in-edge and one out-edge
#     def resolve_WCR_SDFG(self, sdfg: dace.SDFG):
#         for state in sdfg.nodes():
#             self.resolve_WCR_Scope(state, None)


#     def resolve_WCR_Scope(self, state: dace.SDFGState, 
#                     scope: Optional[dace.nodes.EntryNode]):
        
#         snodes = state.scope_children()[scope]

#         for node in snodes:
#             if isinstance(node, (dace.nodes.Tasklet, dace.nodes.LibraryNode)):
#                 self.resolve_WCR_Node(state, node)

#             elif isinstance(node, dace.nodes.EntryNode):            
#                 self.resolve_WCR_Scope(state, node)
                
#             elif isinstance(node, dace.nodes.NestedSDFG):            
#                 self.resolve_WCR_SDFG(node.sdfg)

    
#     def resolve_WCR_Node(self, state: dace.SDFGState, node):
#         if any(ker in node.name for ker in ['tasklet788', 'set_w3']):
#             a = 1

#         node.reductionRanges = []
#         ranges = node.SOAPranges 
#         for e in state.out_edges(node):
#             if e.data.wcr:  
#                 memlet_in = []
#                 # the input edge is a transient scalar
#                 if e.data.subset is None or \
#                         len(e.data.subset.ranges) == 0 or \
#                         len(e.data.subset.ranges[0][0].free_symbols) == 0:
#                     if e.data.data != None:
#                         memlet_in = e.data

#                 memlet = append_outer_outranges(e, state, state.SOAPranges)
#                 # used to avoid duplicating memlet ranges
#                 present_ranges = [str(k[0]) for k in memlet.subset.ranges]
#                 # check if this transient buffer is a scalar. If so, remove the empty (0,0,1) range
#                 if present_ranges[0] == '0':
#                     memlet.subset.ranges = []

#                 # check if we are writing to transient buffer. If so, find its size
#                 if memlet.data in state.parent.arrays:
#                     if state.parent.arrays[memlet.data].transient:
#                         # Reduction dimensions
#                         reduction_dims = set()
#                         path = state.memlet_path(e)
#                         for pe in path:
#                             if isinstance(pe.dst, dace.nodes.MapExit):
#                                 reduction_dims |= set(str(p) for p in pe.dst.map.params)

#                                 not_re_ranges = [(dace.symbol(k), dace.symbol(k), 1) \
#                                     for k in ranges.keys() if (k not in reduction_dims \
#                                         and str(k) not in present_ranges)]
#                                 memlet.subset.ranges += not_re_ranges

#                 memlet_iter_vars = set(
#                         [str(rng[0].free_symbols.pop())
#                         for rng in memlet.subset.ranges
#                          if len(rng[0].free_symbols) > 0])
#                 memlet_in = copy.deepcopy(memlet)              

#                 if not memlet_in:
#                     memlet_in.subset.ranges = [range for range in memlet_in.subset.ranges \
#                                 if str(range[0]) not in set(ranges) - memlet_iter_vars] 

#                 incomingEdge = state.in_edges(node)[0]
#                 state.add_edge(incomingEdge.src, incomingEdge.src_conn, e.src, e.src_conn, memlet_in)

#                 # for W/D analysis - add reduction ranges
#                 reductionRanges = [ [dace.symbol(k), ranges[k][0], ranges[k][1]] \
#                     for k in set(ranges) - set(memlet.subset.free_symbols) \
#                         if ranges[k][2] == 1 ]
#                 if hasattr(node, 'reductionRanges'):
#                     node.reductionRanges += reductionRanges
#                 else:
#                     node.reductionRanges = reductionRanges
        

#     # resolve transients
#     def unsqueeze_SDFG(self, sdfg: dace.SDFG):
#         for state in sdfg.nodes():
#             self.unsqueeze_Scope(state, None)
        

#     def unsqueeze_Scope(self, state: dace.SDFGState, 
#                     scope: Optional[dace.nodes.EntryNode]):
        
#         snodes = state.scope_children()[scope]

#         for node in snodes:
#             if isinstance(node, (dace.nodes.Tasklet, dace.nodes.LibraryNode)):
#                 self.unsqueeze_Node(state, node)

#             elif isinstance(node, dace.nodes.EntryNode):            
#                 self.unsqueeze_Scope(state, node)
                
#             elif isinstance(node, dace.nodes.NestedSDFG):            
#                 self.unsqueeze_SDFG(node.sdfg)


#     def unsqueeze_Node(self, state: dace.SDFGState, node):
#         self.taskletStatistics[state][node.label] = len(state.in_edges(node))

#         if not state.out_edges(node):
#             return

#         if any(x in node.name for x in ['T176',
#                 'adi_84',
#                 'declareTasklettasklet788',
#                 'comp_t2']):
#             edges = state.in_edges(node)
#             a = 1
                 
#         ranges = node.SOAPranges   

#         for e in state.out_edges(node):
#             # check if this is an out-edge without any data 
#             if (e.data.subset is None): # or len(e.data.subset.ranges[0][0].free_symbols) == 0):
#                 continue
#             memlet = append_outer_outranges(e, state, state.SOAPranges)    
#             e.data = memlet
        

#         for e in state.in_edges(node):
#             if e.data.data is None:
#                 continue
#             # check if this is an in-edge without any data 
#             if e.data.data in state.parent.arrays:
#                 if (not state.parent.arrays[e.data.data].transient) and \
#                         e.data.subset is None or \
#                         len(e.data.subset.ranges) == 0 or \
#                         len(e.data.subset.ranges[0][0].free_symbols) == 0:
#                     continue
#             if e.data.data == "r":
#                 a = 1
#             memlet = append_outer_inranges(e, state, state.SOAPranges)

#             if memlet.subset is None or \
#                     len(memlet.subset.ranges) == 0 or \
#                     len(memlet.subset.ranges[0][0].free_symbols) == 0:
#                 continue                    
#             e.data = memlet

#         if any(x in node.name for x in ['T176',
#                 'declareTasklettasklet428',
#                 'declareTasklettasklet788',
#                 'k_loop2']):
#             edges = state.in_edges(node)
#             a = 1


        
#     # add SSA dimension
#     def SSA_SDFG(self, sdfg: dace.SDFG):
#         for state in sdfg.nodes():
#             self.SSA_Scope(state, None)
        

#     def SSA_Scope(self, state: dace.SDFGState, 
#                     scope: Optional[dace.nodes.EntryNode]):
        
#         snodes = state.scope_children()[scope]

#         for node in snodes:
#             if isinstance(node, (dace.nodes.Tasklet, dace.nodes.LibraryNode)):
#                 self.SSA_Node(state, node)

#             elif isinstance(node, dace.nodes.EntryNode):            
#                 self.SSA_Scope(state, node)
                
#             elif isinstance(node, dace.nodes.NestedSDFG):            
#                 self.SSA_SDFG(node.sdfg)


#     def SSA_Node(self, state: dace.SDFGState, node):
#         self.taskletStatistics[state][node.label] = len(state.in_edges(node))

#         if not state.out_edges(node):
#             return

#         if any(x in node.name for x in ['T176',
#                 'adi_84',
#                 'declareTasklettasklet788',
#                 'comp_t2']):
#             edges = state.in_edges(node)
#             a = 1
                 
#         # quick check. If all ranges are present in the union of input ranges, then we don't SSA it.
#         # Example: MMM, all ranges I, J, K are present in some of the inputs (IK, IJ, KJ)
#         # For jacobi, ranges I, T, only I is explicitly present in the inputs. And then we add it        
#         SSAing = check_if_SSAing(state, node)

#         # SSA versioning. We check if any of the tasklet ancestors updated any of the accessed arrays
#         # the number of previous updates indicate current version number of the array
#         computed_edges = [state.out_edges(n) for n in (nx.ancestors(state.nx, node)) if isinstance(n, dace.nodes.Tasklet)]
#         computed_arrs = [edge.data.data for edges in computed_edges for edge in edges]

#         #will_compute_edges = [state.out_edges(n) for n in (nx.descendants(state.nx, node).union(set([node]))) if isinstance(n, dace.nodes.Tasklet)]
#         will_compute_edges = [state.out_edges(n) for n in nx.descendants(state.nx, node).union(set([node])) if isinstance(n, dace.nodes.Tasklet)]
#         will_compute_arrs = [edge.data.data for edges in will_compute_edges for edge in edges]

#         ranges = node.SOAPranges   

#         for e in state.out_edges(node):
#             # check if this is an out-edge without any data 
#             if (e.data.subset is None): # or len(e.data.subset.ranges[0][0].free_symbols) == 0):
#                 continue
#             memlet = append_outer_outranges(e, state, state.SOAPranges)
#             memlet.SSADim = []

#             # check which version of the array we are looking at (for SSA dim)
#             ver = computed_arrs.count(memlet.data) + 1
#             # check if this data will be used ever again
#             will_reuse = will_compute_arrs.count(memlet.data)

#             soap_array = SOAPArray(e.data.data)
#             soap_array.version = ver

#             if will_reuse + ver > 0:
#                 memlet_iter_vars = set(
#                         [str(rng[0].free_symbols.pop())
#                         for rng in memlet.subset.ranges
#                          if len(rng[0].free_symbols) > 0])
#                 SSADim =  [ [dace.symbol(k) + ver,
#                             dace.symbol(k) + ver,
#                         1] \
#                         for k in set(ranges) - memlet_iter_vars]

#                 if not memlet.subset.ranges == [range for range in memlet.subset.ranges \
#                         if str(range[0]) not in set(ranges) - memlet_iter_vars]: 
#                     a = 1
#                 if SSAing:
#                     memlet.subset.ranges += SSADim
#                     soap_array.SSAed = True


            
#             memlet.soap_array = soap_array
#             e.data = memlet
        

#         for e in state.in_edges(node):
#             # check if this is an in-edge without any data 
#             #(not state.parent.arrays[e.data.data].transient) and \                
#             if e.data.subset is None or \
#                     len(e.data.subset.ranges) == 0 or \
#                     len(e.data.subset.ranges[0][0].free_symbols) == 0:
#                 continue
#             if e.data.data == "r":
#                 a = 1
#             memlet = append_outer_inranges(e, state, state.SOAPranges)

#             if memlet.subset is None or len(memlet.subset.ranges[0][0].free_symbols) == 0:
#                 continue            
#             memlet.SSADim = []

#             # check which version of the array we are looking at (for SSA dim)
#             ver = computed_arrs.count(memlet.data)
            
#             # check if this data will be used ever again
#             will_reuse = will_compute_arrs.count(memlet.data)

#             if will_reuse + ver > 0:
#                 memlet_iter_vars = set(
#                         [str(rng[0].free_symbols.pop())
#                         for rng in memlet.subset.ranges
#                          if len(rng[0].free_symbols) > 0])
#                 SSADim =  [ [dace.symbol(k) + ver,
#                                 dace.symbol(k) + ver,
#                                 1] \
#                             for k in set(ranges) - memlet_iter_vars]
                
#                 if any(str(range[0]) in set(ranges) - memlet_iter_vars for \
#                     range in memlet.subset.ranges):
#                     a = 1
#                 if not memlet.subset.ranges == [range for range in memlet.subset.ranges \
#                             if str(range[0]) not in set(ranges) - memlet_iter_vars]:
#                     a = 1

#                 if SSAing:
#                     memlet.subset.ranges += SSADim

#             soap_array = SOAPArray(e.data.data)
#             soap_array.version = ver
#             memlet.soap_array = soap_array
#             e.data = memlet

#         if any(x in node.name for x in ['T176',
#                 'declareTasklettasklet428',
#                 'declareTasklettasklet788',
#                 'k_loop2']):
#             edges = state.in_edges(node)
#             a = 1