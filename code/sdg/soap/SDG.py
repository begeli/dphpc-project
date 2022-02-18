from collections import defaultdict
import copy
import sympy as sp
import networkx as nx
import graphviz
from numpy import nanargmax
from soap.SOAP import SOAP_statement, SOAPArray
from soap.utils import *
from soap.DAGification import DAGify_and_resolve_loops_SDFG
import dace
from dace.sdfg.graph import MultiConnectorEdge
# from soap.SOAP import *
from dace.codegen import control_flow
from dace.sdfg.nodes import *
from dace.subsets import Range
from dace.codegen.control_flow import structured_control_flow_tree
from typing import Optional, List
# from dace.sdfg import Scope

from dace.symbolic import pystr_to_symbolic, issymbolic
from dace import subsets
from warnings import warn


class SDG_Path:
    def __init__(self, values):
        self.path = copy.copy(values)
        
    def __deepcopy__(self, memo):
        node = object.__new__(SDG_Path)

        node.path = copy.copy(self.path)
        return node

    def append(self, value):
        self.path.append(value)
        
    def __getitem__(self, item):
        return self.path.__getitem__(item)
    
# ------------------------------------
# Symbolic Directed Graph abstraction
# ------------------------------------
class SDG_scope:
    def __init__(self, sdfg_entry_node : Node = None):
        self.n_iterations = 1
        self.ranges = {}
        self.map_ranges = {}
        self.loop_ranges = {}
        self.sdfg_path = SDG_Path([sdfg_entry_node])
        self.sdfg_mapping = {}
        self.SOAP_executions = 1
        self.SDFG_arrays = {}
        self.input_SDFG_arrays = []



class SDG_node:
    def __init__(self, scope : SDG_scope = None, 
                sdfg_node : Node = None, 
                statement : SOAP_statement = None):
        self.scope = scope
        self.sdfg_node = sdfg_node
        self.statement = statement




class SDG:
    def __init__(self, sdfg : dace.SDFG = None, params : global_parameters = None):
        self.params = params
        self.graph = nx.MultiDiGraph()
        self.statements = []
        self.node_relabeler = {}
        self.array_version_counter = defaultdict(int)
        if sdfg is not None:
            self.from_SDFG(sdfg, params)

    @property
    def nodes(self):
        return list(self.graph.nodes())

    @property
    def edges(self):
        return list(self.graph.edges())

    def in_edges(self, node):
        return list(self.graph.in_edges(node, data = True))

    def out_edges(self, node):
        return list(self.graph.out_edges(node, data = True))


    def add_edge(self, u, v, _base_access, access_params, _st : SOAP_statement, is_wcr = False, in_transient = False, out_transient = False):
        
        if v in self.graph.nodes:
            self.graph.nodes[v]['st'] = _st
        else:
            self.graph.add_node(v, st = _st)
        phi_str = '[' + _base_access.replace('*', ',') + '] ' + str(access_params.offsets).replace(',)',')')
        if is_wcr:
            phi_str += '*'
        self.graph.add_edge(u, v, label = str(phi_str), 
                        base_access = _base_access, 
                        offsets = access_params,
                        wcr = is_wcr)
        
        self.graph.nodes[u]['transient'] = in_transient                
        self.graph.nodes[v]['transient'] = out_transient                
       # self.graph = nx.relabel_nodes(self.graph, {u : uStr, v : vStr})

        #a = 1

    def get_node_label(self, u):
        basePhi = (u[0], u[1])
        if basePhi in self.node_relabeler.keys():
            previousInd = int(self.node_relabeler[basePhi].split('_')[-1])

        else:
            self.node_relabeler[basePhi] = u[0] + '[' + u[1] + ']_0'


    
    def from_SDFG(self, sdfg : dace.SDFG, params : global_parameters):     
        """
        """   
        sdg_scope = SDG_scope()
        dace.propagate_memlets_sdfg(sdfg)
        sdfg.save("tmp.sdfg", hash=False)        
        # get all output arrays within a given STATE (for SSA purposes)
        sdg_scope.output_arrays = self._get_output_arrays_sdfg(sdfg, sdg_scope)
        self._from_SDFG_sdfg(sdfg, sdg_scope, params)
        return self


    def _from_SDFG_sdfg(self, sdfg: dace.SDFG, sdg_scope : SDG_scope, params : global_parameters):
        control_tree = structured_control_flow_tree(sdfg, lambda x: None)
       
        # TODO: topological sort?
        for control_node in control_tree.children:
            if isinstance(control_node, control_flow.SingleState):
                state = control_node.state
                inner_scope = copy.deepcopy(sdg_scope)
                inner_scope.sdfg_path.append(state)
                sdg_scope = self._from_SDFG_scope(state, None, inner_scope, params)
            
            elif isinstance(control_node, control_flow.ForScope):
                inner_scope = copy.deepcopy(sdg_scope)
                inner_scope.sdfg_path.append(control_node.guard)    
                
                # TODO: when the loop annotation pass is fixed, we need to add the string parsing thing (below)
                # loop_ranges = {k: v for k, v in zip(control_node.guard.ranges.keys(),
                #            [x.ranges[0] for x in control_node.guard.ranges.values() ] ) if isinstance(k, str)}   
                loop_ranges = {str(k): v for k, v in zip(control_node.guard.ranges.keys(),
                            [x.ranges[0] for x in control_node.guard.ranges.values() ] )}
                inner_scope.ranges = {**sdg_scope.ranges, **loop_ranges}
                inner_scope.loop_ranges = {**sdg_scope.loop_ranges, **loop_ranges}
                inner_scope.innermost_ranges = loop_ranges
                self._from_SDFG_loop(control_node, inner_scope, params)
                
            elif isinstance(control_node, control_flow.IfScope):
                a = 1
                

    def _from_SDFG_loop(self, loop : control_flow.ForScope, sdg_scope: SDG_scope, params : global_parameters):
        # TODO: loop iterations are already propagated into the nested scopes?
        # num_executions = loop.guard.executions
        # sdg_scope.SOAP_executions *= num_executions
        
        # TODO: topological sort?
        for control_node in loop.body.children:
            if isinstance(control_node, control_flow.SingleState):
                state = control_node.state
                inner_scope = copy.deepcopy(sdg_scope)
                inner_scope.sdfg_path.append(state)              
                sdg_scope = self._from_SDFG_scope(state, None, inner_scope, params)
            
            elif isinstance(control_node, control_flow.ForScope):
                inner_scope = copy.deepcopy(sdg_scope)
                inner_scope.sdfg_path.append(control_node.guard)       
                # TODO: when the loop annotation pass is fixed, we need to add the string parsing thing (below)
                # loop_ranges = {k: v for k, v in zip(control_node.guard.ranges.keys(),
                #            [x.ranges[0] for x in control_node.guard.ranges.values() ] ) if isinstance(k, str)}   
                loop_ranges = {str(k): v for k, v in zip(control_node.guard.ranges.keys(),
                            [x.ranges[0] for x in control_node.guard.ranges.values() ] )}
                inner_scope.loop_ranges = {**sdg_scope.loop_ranges, **loop_ranges}
                inner_scope.ranges = {**sdg_scope.ranges, **loop_ranges}
                inner_scope.innermost_ranges = loop_ranges
                self._from_SDFG_loop(control_node, inner_scope, params)


    def _from_SDFG_scope(self, state: dace.SDFGState, 
                    scope: Optional[dace.nodes.EntryNode], sdg_scope : SDG_scope, params : global_parameters):
        num_executions = state.executions
        sdg_scope.SOAP_executions *= num_executions
        sdg_scope.SDFG_arrays = {**sdg_scope.SDFG_arrays, **state.parent.arrays}
        sdg_scope.input_SDFG_arrays += [src_node.data for src_node in state.source_nodes() if isinstance(src_node, AccessNode)]
        if "stateFOR166" in state.label:
            a = 1
                
        snodes = [n for n in nx.topological_sort(state.nx) if n in state.scope_children()[scope]]
        for node in snodes:
            if isinstance(node, (dace.nodes.Tasklet, dace.nodes.LibraryNode)):
                inner_scope = copy.deepcopy(sdg_scope)
                self._from_SDFG_node(node, state, inner_scope, params)
            elif isinstance(node, (dace.nodes.AccessNode)):
                if node.label == "__tmp2":
                    a = 1
                # if the access node has a single in-edge coming from a different access node, 
                # then it is a projection. We then add this to the sdfg mapping.
                in_edges = state.in_edges(node)
                if len(in_edges) > 0:
                    in_node = in_edges[0].src
                    
                    # check if this is a projection (access_node -> access_node)
                    if isinstance(in_node, dace.nodes.AccessNode):
                        # retreiving the original (non-projected) memlet
                        src_edges = state.in_edges(in_node)
                        if len(src_edges) <= 1 and len(state.out_edges(node)) == 1:
                            self.add_projection(in_edges[0].data, state.out_edges(node)[0].data, sdg_scope)
                        # elif len(src_edges) == 1 and len(state.out_edges(node)) == 1:
                        #     self.add_projection(src_edges[0].data, state.out_edges(node)[0].data, sdg_scope)
                        else:                            
                            a = 1
                    
                    # check if this is an initialization of transient (access_node -> tasklet -> transient access_node)
                    if sdg_scope.SDFG_arrays[node.data].transient:
                        if isinstance(in_node, dace.nodes.Tasklet):
                            in_edges = state.in_edges(in_node)
                            if len(in_edges) > 0:
                                in_in_node = in_edges[0].src
                                if isinstance(in_in_node, dace.nodes.AccessNode):
                                    # now we need to propagate the updated sdfg_mapping one layer higher
                                    sdg_scope.sdfg_mapping = {**sdg_scope.sdfg_mapping, **{node.data: in_edges[0].data}}
                        
            elif isinstance(node, dace.nodes.EntryNode): 
                if 'stateFOR31_map' in node.label:
                    a = 1
                inner_scope = copy.deepcopy(sdg_scope)
                inner_scope.sdfg_path.append(node)       
                map_ranges = {k: v for k, v in zip(node.params, node.range.ranges) if isinstance(k, str)}
                inner_scope.ranges = {**sdg_scope.ranges, **map_ranges}
                inner_scope.map_ranges = {**sdg_scope.map_ranges, **map_ranges}
                inner_scope.innermost_ranges = map_ranges
                num_executions = state.executions
                inner_scope.SOAP_executions = num_executions
                self._from_SDFG_scope(state, node, inner_scope, params)
            elif isinstance(node, dace.nodes.NestedSDFG):
                inner_scope = self._add_ranges_and_mappings(state, sdg_scope, node)
                self._from_SDFG_sdfg(node.sdfg, inner_scope, params)
                
        # return updated sdg_scope (e.g., sdfg_mapping updated by transients)
        return sdg_scope
        


    # the core SDG creation function. The elementary building block for SDG is the SDFG's tasklet
    def _from_SDFG_node(self, node : dace.nodes, state: dace.SDFGState, sdg_scope : SDG_scope, params : global_parameters):            
        if "compute_sum" in node.label:
            a = 1           
            
        if not state.out_edges(node) or not state.in_edges(node):
            return   
                           
        S = SOAP_statement()    
        S.name = node.label
        S.tasklet = node
        if "stateFOR115" in sdg_scope.sdfg_path[-1].label:
            a = 1
        S.daceRanges[sdg_scope.sdfg_path[-1].label] = sdg_scope.ranges      
        S.output_arrays = sdg_scope.output_arrays  

        # add WCR (write conflict resolution) edges to the input edges
        input_edges = state.in_edges(node)
        S.wcr_edges = []
        for e in state.out_edges(node):
            if e.data.wcr:  
                # leave transients alone. They will have empty ranges that will be added by
                # the _get_outer_memlet call
                if not sdg_scope.SDFG_arrays[e.data.data].transient:
                    e.data.src_subset = e.data.dst_subset
                input_edges.append(e)                
                        

        for e in input_edges:
            # resolve transients, inner scope mappings, etc. Retreive outermost ranges and array names.
            outer_memlet = SDG._get_outer_memlet(e.data, sdg_scope, False)
            
            # check if the resolved memlet exists, is not empty, and is not scalar
            if not outer_memlet or len(outer_memlet.subset.ranges) == 0 \
                 or len(outer_memlet.subset.ranges[0][0].free_symbols) == 0:
                     #                # or (len(outer_memlet.subset.ranges) == 1 and \
                continue
                      
            # if the edge is WCR, add it to the list
            SSA_dim = []
            
            # old, fishy version. This "e.data.src_subset is None" seems broken for the polybench/doitgen
            if e.data.wcr:
                if e.data.src_subset is None or e.data.dst_subset.ranges != e.data.src_subset.ranges:
                    # SSA_dim = e.data.dst_subset 
                    a = e.data.dst_subset 
                else:
                    a = 1  
            
            if e.data.wcr:
                S.wcr_edges.append(outer_memlet)
                if e.data.src_subset is not None and (e.data.dst_subset.ranges != e.data.src_subset.ranges):
                    SSA_dim = e.data.dst_subset    
                    a = 1
                else:
                    a = 1          
                             
            if not SSA_dim:
                # determine the SSA dimension if we have the same input and output access (overwriting the data)
                # if the memlet is coming from the outside of the map, we don't include them
                if isinstance(e.src, dace.nodes.MapEntry):
                    SSA_dim = []
                    if  SDG._get_SSA_dim(outer_memlet, sdg_scope) != []:
                        a = 1
                        SSA_dim = SDG._get_SSA_dim(outer_memlet, sdg_scope)
                else:
                    SSA_dim = SDG._get_SSA_dim(outer_memlet, sdg_scope)
                
            # add this input access to the elementary SOAP statement
            S.add_edge_to_statement(outer_memlet, SSA_dim, params)            
            
            
        
        for e in state.out_edges(node):           
            # resolve transients, inner scope mappings, etc. Retreive outermost ranges and array names.
            outer_memlet = SDG._get_outer_memlet(e.data, sdg_scope, True)
            if not outer_memlet or len(outer_memlet.subset.ranges) == 0:
                continue
            # deterimne the SSA dimension if we have the same input and output access (overwriting the data)
            SSA_dim = SDG._get_SSA_dim(outer_memlet, sdg_scope)
                   
            # add this output access to the elementary SOAP statement
            S.add_output_edge_to_statement(outer_memlet, SSA_dim)    
            

        if not S.output_accesses:
            return
        if not any(S.daceRanges.values()):
            return
        S.numExecutions = sdg_scope.SOAP_executions 

        if params.IOanalysis:
            S.solve(params.solver, params)
            if S.Dom_size == 0 or len(S.phis) == 0 or S.Q == 0:
                return

        # perform WD analysis
        if params.WDanalysis:
            S.reductionRanges = node.reductionRanges
            S.update_ranges()        
            S.calculate_dominator_size_2()  
            S.count_V()
            S.count_D()

        # everything is fine with this statement, it is well defined and ready for the further SDG analysis
        node.soap_statement = S
        
        # now we update the SDG
        self._add_statement_to_SDG(S, sdg_scope)
        
        self.plot_SDG()
        return
          
    
    def _add_ranges_and_mappings(self, state : dace.SDFGState, sdg_scope : SDG_scope, node : dace.nodes):        
        inner_scope = copy.deepcopy(sdg_scope)
        inner_scope.sdfg_path.append(node) 
        
        # # First, we update the current mapping and check
        # # if we map something to transient arrays. 
        # # If yes, we need to add the outer ranges to them
        # for inner_mem, outer_mem in inner_scope.sdfg_mapping.items():
        #     if sdg_scope.SDFG_arrays[outer_mem.data].transient:
        #         inner_scope.sdfg_mapping[inner_mem].subset.ranges += \
        #             [(dace.symbol(i), dace.symbol(i), 1) 
        #              for i in sdg_scope.innermost_ranges.keys()]
        
        src_sdfg_mapping = {e.dst_conn : e.data for e in state.in_edges(node)}                
        dst_sdfg_mapping = {e.src_conn : e.data for e in state.out_edges(node)}                
        # if the arrays are created inside the map scopes, we need to add the map ranges to
        # the mapped memlets' ranges.
        # e.g., polybench's doitgen. If we create a "sum[p]" array within the two nested maps q and r,
        # the resulting array should be "sum[p,q,r]"                
        if len(sdg_scope.ranges) > 0:            
            vars_to_add = list(map(dace.symbol, [v for v in sdg_scope.map_ranges.keys()]))
            
            # If the array is initialized inside a scope (meaning it is NOT a source node in the nested SDFG,
            # but rather it has an initialization tasklet), then we add also loop ranges, not only the map ones            
            for arr, mem in dst_sdfg_mapping.items():
                tmp_mem = copy.deepcopy(mem)
                if tmp_mem.data in sdg_scope.sdfg_mapping.keys():
                    tmp_mem = sdg_scope.sdfg_mapping[mem.data]                  
                if tmp_mem.data not in sdg_scope.input_SDFG_arrays:
                    vars_to_add_in = vars_to_add + list(map(dace.symbol, [v for v in sdg_scope.loop_ranges.keys()]))
                else:
                    vars_to_add_in = vars_to_add
                mem.subset.ranges += [(x, x, 1) for x in vars_to_add_in if str(x) not in mem.subset.free_symbols ]
                mem.subset = Range(mem.subset.ranges)                
                
                # # BUT, we remove empty ranges (0,0,1)
                # # TODO: not sure what is the proper way how to filter them correctly.
                # # we DON'T want to filter ranges like (0, N, 1), as they are needed for memlet.subset.compose
                # # test1 = [rng for rng in mem.subset.ranges if len(rng[0].free_symbols) > 0]
                # test2 = [rng for rng in mem.subset.ranges if len(rng[1].free_symbols) > 0]
                # # if test1 != test2:
                # #     a = 1
                # mem.subset.ranges = test2
        
        cur_scope_mapping = {**src_sdfg_mapping, ** dst_sdfg_mapping}
        
        #inner_scope.sdfg_mapping = cur_scope_mapping
        
        # transitive mapping
        fused_mapping = {}
        for inner_mem, outer_mem in cur_scope_mapping.items():
            # resolve dynamic arrays and like scalars. If the memlet is dynamic, inherit ranges from 
            # the tasklet it is assigned in
            if outer_mem.dynamic:
                outer_mem.subset.ranges = self._find_transient_assignement(state, sdg_scope, node)
            
            if outer_mem.data in inner_scope.sdfg_mapping.keys():
                outmost_mem = copy.deepcopy(inner_scope.sdfg_mapping[outer_mem.data])
                outmost_mem.subset = SDG._proj_compose(outmost_mem, outer_mem) #outmost_mem.subset.compose(outer_mem.subset)
                fused_mapping[inner_mem] = outmost_mem
            else:
                fused_mapping[inner_mem] = outer_mem
        
        # # After this step, we check the current mapping
        # # if we map something to transient arrays. 
        # # If yes, we need to add the outer ranges to them
        # if len(inner_scope.sdfg_mapping) > 0:
        #     for inner_mem, outer_mem in fused_mapping.items():
        #         if sdg_scope.SDFG_arrays[outer_mem.data].transient:
        #             rngs_to_update = []
        #             i = 0
        #             for rng in fused_mapping[inner_mem].subset.ranges:
        #                 if len(rng[0].free_symbols) == 0:
        #                     it_var = dace.symbol(list(sdg_scope.loop_ranges)[-1 - i])                   
        #                     rngs_to_update += [(it_var, it_var, 1)]
        #                     i += 1
        #                 else:
        #                     rngs_to_update += [rng]
        #             fused_mapping[inner_mem].subset.ranges = rng_to_update
                            
        #             # fused_mapping[inner_mem].subset.ranges += \
        #             #     [(dace.symbol(i), dace.symbol(i), 1) 
        #             #     for i in sdg_scope.innermost_ranges.keys()]
        
        
        inner_scope.sdfg_mapping = fused_mapping
        
        return inner_scope
    
    
    def _find_transient_assignement(self, state : dace.SDFGState, sdg_scope : SDG_scope, node : dace.nodes):
        a = 1
    

    @staticmethod
    def _proj_compose(outer_mem : dace.Memlet, inner_mem : dace.Memlet):
        outer_rng = outer_mem.subset.ranges
        inner_rng = inner_mem.subset.ranges
        
        if np.prod(outer_mem.subset.size()) == np.prod(inner_mem.subset.size()):
            # return len(outer_rng) > len(inner_rng) ? outer_rng : inner_rng
            return Range(outer_rng if len(outer_rng) < len(inner_rng) else inner_rng)
        
        if len(outer_rng) < len(inner_rng):
            # injective
            a = 1
            # inner_mem.subset.ranges = outer_mem.subset.ranges
        elif len(outer_rng) > len(inner_rng):
            # surjective
            a = 1
            # outer_mem.subset.ranges = inner_mem.subset.ranges
        elif not set(inner_mem.subset.ranges) == set(outer_mem.subset.ranges):
            # Example situation:
            # outer_rng == [(r, r, 1), (0, NQ - 1, 1), (0, NP - 1, 1)]
            # inner_rng == [(0, NQ - 1, 1), (0, 0, 1), (0, NP - 1, 1)]
            # expected output:
            # [(r, r, 1), (0, NQ - 1, 1), (0, NP - 1, 1)]
            # reference example:
            # npbench/polybench/doitgen
            return outer_mem.subset
                
        return outer_mem.subset.compose(inner_mem.subset)



    def _add_statement_to_SDG(self, S : SOAP_statement, sdg_scope : SDG_scope):
        output_arrays_vers = []
        wcr_arrays = [e.data for e in S.wcr_edges]
        for output_array in S.output_accesses.keys():
            # !!!! CAREFUL !!!!
            # THIS SHOULD BE THE ONLY PLACE WHERE THIS COUNTER IS INCREMENTED
            self.array_version_counter[output_array] += 1
            output_arrays_vers.append(output_array + "_" + str(self.array_version_counter[output_array]))
            
            # check if it's transient
            if output_array in sdg_scope.SDFG_arrays.keys() and  \
                        sdg_scope.SDFG_arrays[output_array].transient:  
                out_transient = True
            else:
                out_transient = False
            
        # iterate over input accesses     
        for array_name, array_accesses in S.phis.items():
            if array_name in S.output_accesses.keys():                
                input_array_ver = array_name + "_" + str(self.array_version_counter[array_name] - 1)
            else:
                input_array_ver = array_name + "_" + str(self.array_version_counter[array_name])
            
            # check if it's transient
            if array_name in sdg_scope.SDFG_arrays.keys() and  \
                        sdg_scope.SDFG_arrays[array_name].transient:  
                in_transient = True
            else:
                in_transient = False
                
            # check if it's wcr
            if array_name in wcr_arrays:
                wcr = True
            else:
                wcr = False
            
            # iterate over different base accesses to the same array 
            for base_access, access_params in array_accesses.items():       
                for output_array in output_arrays_vers:            
                    self.add_edge(input_array_ver, output_array, base_access, access_params, S,
                                  wcr, in_transient, out_transient)



    def add_projection(self,
                       project_from : dace.memlet,
                       project_to : dace.memlet,
                       sdg_scope : SDG_scope):
        # we need to add missing projection dimensions
        from_ranges = project_from.subset.ranges
        to_ranges = project_to.subset.ranges
        
        if len(from_ranges) < len(to_ranges):
            # injective
            src_memlet = copy.deepcopy(project_from)
            src_memlet.subset.ranges += [(0, 0, 1)] * (len(to_ranges) - len(from_ranges))
            sdg_scope.sdfg_mapping[project_to.data] = src_memlet
        if len(from_ranges) > len(to_ranges):
            # surjective
            # to_expr = sp.prod([y for (x,y,z) in project_to.subset.ranges])
            # from_expr = sp.prod([y for (x,y,z) in project_from.subset.ranges])
            # a = int_to_real(to_expr)
            dst_memlet = copy.deepcopy(project_to)
            # dst_memlet.subset.ranges += [(0, 0, 1)] * (len(from_ranges) - len(to_ranges))
            sdg_scope.sdfg_mapping[dst_memlet.data] = project_from
        if len(from_ranges) == len(to_ranges):
            # bijective
            sdg_scope.sdfg_mapping[project_to.data] = project_from
           

    # ------------------------------------
    # SDFG preprocessing
    # ------------------------------------
    
    def _get_output_arrays_sdfg(self, sdfg: dace.SDFG, sdg_scope : SDG_scope):
        output_arrays = {}
        control_tree = structured_control_flow_tree(sdfg, lambda x: None) 
        
        # [n for n in nx.topological_sort(state.nx) if n in state.scope_children()[scope]]
        for control_node in control_tree.children:
            if isinstance(control_node, control_flow.SingleState):
                state = control_node.state
                inner_scope = copy.deepcopy(sdg_scope)
                inner_scope.sdfg_path.append(state)              
                output_arrays = {**output_arrays, **self._get_output_arrays_state(state, None, inner_scope)}
            
            elif isinstance(control_node, control_flow.ForScope):
                inner_scope = copy.deepcopy(sdg_scope)
                inner_scope.sdfg_path.append(control_node.guard)       
                loop_ranges = {str(k): v for k, v in zip(control_node.guard.ranges.keys(),
                            [x.ranges[0] for x in control_node.guard.ranges.values() ] )}
                inner_scope.ranges = {**sdg_scope.ranges, **loop_ranges}
                inner_scope.loop_ranges = {**sdg_scope.loop_ranges, **loop_ranges}
                inner_scope.innermost_ranges = loop_ranges
                output_arrays = {**output_arrays, **self._get_output_arrays_loop(control_node, inner_scope)}
                
        return output_arrays
                

    def _get_output_arrays_loop(self, loop : control_flow.ForScope, sdg_scope: SDG_scope):
        output_arrays = {}
        
        #[n for n in nx.topological_sort(state.nx) if n in state.scope_children()[scope]]
        for control_node in loop.body.children:
            if isinstance(control_node, control_flow.SingleState):
                state = control_node.state
                inner_scope = copy.deepcopy(sdg_scope)
                inner_scope.sdfg_path.append(state)              
                output_arrays = {**output_arrays, **self._get_output_arrays_state(state, None, inner_scope)}
            
            elif isinstance(control_node, control_flow.ForScope):
                inner_scope = copy.deepcopy(sdg_scope)
                inner_scope.sdfg_path.append(control_node.guard)       
                loop_ranges = {k: v for k, v in zip(control_node.guard.ranges.keys(),
                            [x.ranges[0] for x in control_node.guard.ranges.values()]) if isinstance(k, str)}
                inner_scope.ranges = {**sdg_scope.ranges, **loop_ranges}
                output_arrays = {**output_arrays, **self._get_output_arrays_loop(control_node, inner_scope)}
                
        return output_arrays

    
    def _get_output_arrays_state(self, state: dace.SDFGState, scope: Optional[dace.nodes.EntryNode], sdg_scope : SDG_scope):
        output_arrays = {}
        if len(sdg_scope.ranges) == 0:
            # then we are not in any parametric range scope            
            iter_vars = []
        else:
            iter_vars = set(map(dace.symbol, [v for v in sdg_scope.ranges.keys()]))
        snodes = state.scope_children()[scope]    
        sdg_scope.SDFG_arrays = {**sdg_scope.SDFG_arrays, **state.parent.arrays}
        sdg_scope.input_SDFG_arrays += [src_node.data for src_node in state.source_nodes() if isinstance(src_node, AccessNode)]
        for node in snodes:
            if isinstance(node, (dace.nodes.Tasklet, dace.nodes.LibraryNode)):      
                inner_scope = copy.deepcopy(sdg_scope)  
                for e in state.out_edges(node):
                    # resolve transients, inner scope mappings, etc. Resolve outermost ranges and array names
                    outer_memlet = SDG._get_outer_memlet(e.data, inner_scope, True)
                    if not outer_memlet or not iter_vars:
                        continue                    
                    (arrayName, baseAccess, offsets) =  get_access_from_memlet(outer_memlet, iter_vars)
                    
                    # This check is needed to exclude output arrays that do not have any SSA dim. 
                    # That is, if the arrays dimension (baseAccess) is the same as iteration dimension
                    # (sdg_scope.ranges), even though it is an output array, we don't include it.
                    # Otherwise, we might attach to it a wrong SSA_dim later.
                    if set(sdg_scope.ranges.keys()) != set(baseAccess.split('*')):
                        output_arrays[arrayName] = (baseAccess, offsets)
                    else:
                        a = 1
                    
                    
            elif isinstance(node, dace.nodes.EntryNode):       
                inner_scope = copy.deepcopy(sdg_scope)
                inner_scope.sdfg_path.append(node)       
                map_ranges = {k: v for k, v in zip(node.params, node.range.ranges) if isinstance(k, str)}
                if "stateFOR115" in node.label:
                    a = 1
                inner_scope.ranges = {**sdg_scope.ranges, **map_ranges}
                inner_scope.map_ranges = {**sdg_scope.map_ranges, **map_ranges}
                num_executions = state.executions
                inner_scope.SOAP_executions = num_executions
                output_arrays = {**output_arrays, **self._get_output_arrays_state(state, node, inner_scope)}
                
            elif isinstance(node, dace.nodes.NestedSDFG):
                inner_scope = self._add_ranges_and_mappings(state, sdg_scope, node)
                output_arrays = {**output_arrays, **self._get_output_arrays_sdfg(node.sdfg, inner_scope)}
                                   
        return output_arrays
    
    
    
    # ------------------------------------
    # static SDG functions
    # ------------------------------------

    @staticmethod
    def _get_outer_memlet(inner_memlet : dace.Memlet, sdg_scope : SDG_scope, output : bool) -> dace.Memlet:
        if inner_memlet.data in sdg_scope.sdfg_mapping:
            outer_memlet = copy.deepcopy(sdg_scope.sdfg_mapping[inner_memlet.data])
            # TODO: new
            if sdg_scope.SDFG_arrays[inner_memlet.data].transient:
                return outer_memlet
            
            # a controversial trick for triangular dimensions. If the outer memlet ranges
            # are, e.g., [(0:N),( i + 1:M)], then we cut out this variable offset i and leave
            # only [(0:N),(0:M)]. Otherwise, we will have problems later.
            
            if any([len(x.free_symbols) > 0 for (x,y,z) in outer_memlet.subset.ranges]):
                a = 1
            outer_memlet.subset.ranges = [(0,y,z) if (x != y) else (x,y,z)  
                                          for (x,y,z) in outer_memlet.subset.ranges]
            if output:
                outer_memlet.subset = outer_memlet.subset.compose(inner_memlet.dst_subset)
            else:
                try:
                    outer_memlet.subset = outer_memlet.subset.compose(inner_memlet.src_subset)
                except:
                    outer_memlet.subset = outer_memlet.dst_subset.compose(inner_memlet.src_subset)
        else:
            outer_memlet = inner_memlet            
            
        if outer_memlet.subset is None or \
                        len(outer_memlet.subset.ranges) == 0 or \
                        len(outer_memlet.subset.ranges[0][0].free_symbols) == 0:
                            
            # TODO: New. We now always add these ranges. Before, we filtered out suspicious memlets            
            # I really don't like the following part... Looks hacky
            if outer_memlet.data in sdg_scope.SDFG_arrays.keys() and  \
                        sdg_scope.SDFG_arrays[outer_memlet.data].transient:  
                if len(sdg_scope.map_ranges) == 0:
                    outer_memlet.subset.ranges = rng_to_subset(sdg_scope.loop_ranges)
                else:
                    outer_memlet.subset.ranges = rng_to_subset(sdg_scope.map_ranges)
            elif outer_memlet.dynamic:
                outer_memlet.subset.ranges = rng_to_subset(sdg_scope.loop_ranges)
            else:  
                warn('Unable to parse memlet ' + str(outer_memlet) 
                    + " in state "  + str(sdg_scope.sdfg_path.path[-1]) + "\n")
                # I SUPER dislike this
                outer_memlet = []                
            
        return outer_memlet
    
    
    @staticmethod
    def _get_SSA_dim(memlet : dace.Memlet, sdg_scope : SDG_scope, preliminary_check = False):
        SSA_dim = []
        if len(sdg_scope.ranges) == 0:
            iter_vars = []
        else:
            iter_vars = set(map(dace.symbol, [v for v in sdg_scope.ranges.keys()]))
        # check if the memlet's array is the same as one of the outputs:
        if preliminary_check or memlet.data in sdg_scope.output_arrays.keys():
            # the same array is used for input and output. Determining the input's base access
            (array_name, base_access, offsets) = get_access_from_memlet(memlet, iter_vars)
            
            if preliminary_check or eq_accesses(base_access, sdg_scope.output_arrays[memlet.data][0]):
                # now we need to determine the SSA dimension
                memlet_iter_vars = set(
                        [str(rng[0].free_symbols.pop())
                        for rng in memlet.subset.ranges
                            if len(rng[0].free_symbols) > 0])
                
                # TODO: experimental. Previously, the SSA_dim was chosen from between loop_ranges and innermost_ranges                
                # # if the tasklet is in a nested loop, then this will constitute our SSA dim
                # if len(sdg_scope.loop_ranges) > 0:
                #     SSA_dim =  [ [dace.symbol(k), dace.symbol(k), 1] \
                #                 for k in set(sdg_scope.loop_ranges) - memlet_iter_vars]
                # else:    
                #     SSA_dim =  [ [dace.symbol(k), dace.symbol(k), 1] \
                #                 for k in set(sdg_scope.innermost_ranges) - memlet_iter_vars]
                # Now we always take the innermost.
                SSA_dim =  [ [dace.symbol(k), dace.symbol(k), 1] \
                                 for k in set(sdg_scope.innermost_ranges) - memlet_iter_vars]
                
                # we first try to add the SSA_dim as the innermost range (the one from the innermost loop).
                # If it fails, we then look for the SSA dim in the outer ranges.
                if not SSA_dim:
                    SSA_dim =  [ [dace.symbol(k), dace.symbol(k), 1] \
                            for k in set(sdg_scope.loop_ranges) - memlet_iter_vars]
        
        return SSA_dim


    
    # ------------------------------------
    # helper functions
    # ------------------------------------

    
    def plot_SDG(self, filename : str = 'SDG.dot'):
        nx.nx_pydot.write_dot(self.graph, filename)



    # ------------------------------------
    # SDG PARTITIONING
    # ------------------------------------
    def perform_loop_swapping(self, node : str, swaplist : Dict[str, str], 
                              visited: Set[str], first : bool) -> bool:
        """
        Propagates loop variables swapping. E.g., if we have a transient, whose 
        input edge is [i, j], but the output edge is [i, k], we try to propagate it
        to all consecutive nodes in the graph, swapping j with k
        """
        if node in visited:
            return True
        visited |= {node}
        inv_swaplist = {v : k for k,v in swaplist.items()}
        
        if not first:
            # if not, then the node is NOT a SOAP statement, but some input array
            if 'st' in self.graph.nodes[node].keys():
                statement = self.graph.nodes[node]['st']
                
                # if '__tmp7' in self.graph.nodes['__tmp8_1']['st'].phis.keys() and \
                #         list(self.graph.nodes['__tmp8_1']['st'].phis['__tmp8'].keys())[0] == list(self.graph.nodes['__tmp8_1']['st'].phis['__tmp7'].keys())[0]:
                #     a = 1
                if node == "__return_1":
                    self.plot_SDG()
                    a = 1
                statement.swap_iter_vars(swaplist, inv_swaplist, self.params.solver)
                
                # if '__tmp7' in self.graph.nodes['__tmp8_1']['st'].phis.keys() and \
                #         list(self.graph.nodes['__tmp8_1']['st'].phis['__tmp8'].keys())[0] == list(self.graph.nodes['__tmp8_1']['st'].phis['__tmp7'].keys())[0]:
                #     a = 1
                 
            
        valid_swapping = True
        for e in (list(self.out_edges(node)) + list(self.in_edges(node))):            
            in_node = e[0]                
            out_node = e[1]
            if in_node in visited and out_node in visited:
                continue
            _base_access = e[2]["base_access"]
            if any(((iter in swaplist.keys()) or (iter in inv_swaplist.keys())) 
                    for iter in _base_access.split('*')):
                    
                e[2]["base_access"] = swap_in_string( e[2]["base_access"], swaplist, inv_swaplist)
                e[2]["label"] = "[" + ",".join(e[2]["base_access"].split('*')) + "]" + \
                                e[2]["label"].split(']')[1]
            
            valid_swapping = valid_swapping and (self.perform_loop_swapping(in_node, swaplist, visited, False)
                and self.perform_loop_swapping(out_node, swaplist, visited, False))
        
        return valid_swapping
                                
                
                            
                            

            
    
    
    
    # --- preprocessing ---
    def remove_transient_arrays(self):
        """
        removes transient nodes in the sdfg if there is only a single
        in-edge and single out-edge
        """
        all_nodes = list(nx.topological_sort(self.graph))
        # since we will be removing elemnts from the list, we iterate over the indices
        num_nodes = len(all_nodes)
        i = 0
        while (i < num_nodes):
            node = all_nodes[i]
            if len(self.in_edges(node)) == 1 and len(self.out_edges(node)) == 1:
                if self.graph.nodes[node]['transient'] == True:
                    # check if the accesses match
                    in_access = self.in_edges(node)[0]
                    out_access = self.out_edges(node)[0]
                    # remove this node
                    pred = self.in_edges(node)[0][0]
                    succ = self.out_edges(node)[0][1]
                    
                    edge = self.in_edges(node)[0][2]
                    _label  = edge["label"]
                    _base_access = edge["base_access"]
                    _offsets = edge["offsets"]
                    _wcr = edge["wcr"]
                    base_st = self.graph.nodes[node]['st']
                    next_st = self.graph.nodes[succ]['st']
                    
                    # check if the input base access is the same as the output base access.
                    # If not, we need to propagate loop variable swap:
                    out_base_access = self.out_edges(node)[0][2]["base_access"]
                    
                    invalid_swapping = False
                    if out_base_access != _base_access:
                        if len(out_base_access.split('*')) != len(_base_access.split('*')):
                            invalid_swapping = True
                        else:
                            swaplist = {k : v for k,v in 
                                        dict(zip(out_base_access.split('*'), _base_access.split('*'))).items()
                                        if k != v}
                            visited_nodes = set(nx.single_source_shortest_path(
                                self.graph.reverse(), node).keys())
                            visited_nodes.remove(node)
                            if node == "fc2_1":
                                a = 1
                            if not self.perform_loop_swapping(node, swaplist, visited_nodes, first = True):
                                invalid_swapping = True                            
                            self.plot_SDG()
                            
                            
                        
                    if invalid_swapping:
                        i+=1
                        continue
                    
                    # we need to remove the transient from phis of the next_st,
                    # and instead, add the phis from the base_st
                    del next_st.phis[strip(node)]
                    prev_phi = list(base_st.phis.items())[0]
                    if prev_phi[0] in next_st.phis:
                        next_st.phis[prev_phi[0]] = {**next_st.phis[prev_phi[0]], **prev_phi[1]}
                    else:
                        next_st.phis[prev_phi[0]] = prev_phi[1]
                    
                    self.graph.remove_node(node)
                    self.graph.add_edge(pred, succ, label = _label, 
                        base_access = _base_access, 
                        offsets = _offsets,
                        wcr = _wcr)
                    all_nodes.remove(node)
                    num_nodes -= 1
                    i -= 1
                   
            i+=1
                    
        self.plot_SDG()
    
        

    # we don't merge A and B if there is an edge (A,B) but also (A,C), (C,B)
    # this will be taken care of once we are in C
    def is_shortest_pred(self, source_node, pred_node):
        shortest_pred = True
        for sibling in self.graph.successors(pred_node):   
            if sibling != source_node:
                # our brother has to diverge from our recursive path
                if any([source_node == n for n in nx.descendants(self.graph, sibling)]):
                #any([source_node == n for n in nx.ancestors(self.graph, sibling)]) or \                    
                    shortest_pred = False
                    return shortest_pred
        return shortest_pred


    def recursive_SDG_subgraphing(self, node, checked_subgraphs : set) -> List[SOAP_statement]:
        if "all_subgraphs" in self.graph.nodes[node].keys():
            return self.graph.nodes[node]["all_subgraphs"]
        base_st = self.graph.nodes[node]['st']
        if node == "dace_w_0_4":
            a = 1
        S = copy.deepcopy(base_st)
        S.name = node
        S.subgraph = set([node])
        sdg_statements = []
        sdg_statements.append(S)


        for pred in self.graph.predecessors(node): 
            # TODO: new version doesn't differentiate between transients, since they should
            # be handled in the remove_transient_nodes step
            
            # # for transients, we just go deeper      
            # if self.graph.nodes[pred]['transient'] == True:      
            #     if len(self.in_edges(pred)) > 0:            
            #         # TODO: pruning. What's the best strategy here?   
            #         if self.is_shortest_pred(node, pred):
            #             if pred == "dace_w_0_6":
            #                 a = 1
            #             pred_statements = self.recursive_SDG_subgraphing(pred, checked_subgraphs)   

            #             for cur_stat in sdg_statements:                                 
            #                 for pred_stat in pred_statements:            
            #                     cur_stat.concatenate_sdg_statements(None, pred_stat)                    
            #         else:
            #             a = 1
            if False:
                a = 1

            else:
                # merging horizontally - input reuse
                for sibling in self.graph.successors(pred):   
                    if sibling != node:
                        # our brother has to diverge from our recursive path
                        is_divergent = not any([node == n for n in nx.ancestors(self.graph, sibling)]) \
                                    and not any([node == n for n in nx.descendants(self.graph, sibling)])
                        if is_divergent:
                            s_st = self.graph.nodes[sibling]['st']
                            s_st.name = sibling
                            s_st.subgraph = set([sibling])
                            if "transient" not in self.graph.nodes[sibling].keys():
                                self.graph.nodes[sibling]['transient'] = False

                            if self.graph.nodes[sibling]['transient'] == True: 
                                continue
                            
                            # if the brother has no other parents than our shared parent, always add - do not branch
                            if len(list(self.graph.predecessors(sibling))) == 1:
                                for cur_stat in sdg_statements:                                 
                                    cur_stat.concatenate_sdg_statements(None, s_st)                            
                            else:
                                sibling_statements = copy.deepcopy(sdg_statements)
                                for sib_stat in sibling_statements:                                 
                                    S = copy.deepcopy(sib_stat)
                                    S.concatenate_sdg_statements(None, s_st)
                                    if S.subgraph not in checked_subgraphs.union(set([frozenset(sg.subgraph) for sg in sdg_statements])):
                                        sdg_statements.append(S)    
                                    else:
                                        a = 1

                pred_arr_name = strip(pred)
                # the first condition catches the case where the scope dimension changed, and the array is no longer transient
                # if S accesses array pred with different base accesses (e.g., A[i,k], A[k,j]), we don't go any deeper
                if pred_arr_name not in base_st.phis.keys() or \
                    len(base_st.phis[pred_arr_name]) > 1:
                        continue
                    
                # don't fuse over the WCR edge
                edge = self.graph.edges[pred, node, 0]
                if edge['wcr'] == True:
                    continue
                    
                if pred == "dace_R_4_1":
                    a = 1
                
                if len(self.in_edges(pred)) > 0:            
                    # TODO: pruning. What's the best strategy here?            
                    pred_st = self.graph.nodes[pred]['st']
                    if len(pred_st.rhoOpts.free_symbols) > 0 and any([pred_arr_name in in_arr for in_arr in pred_st.phis.keys()]):
                        continue
                    if any([len(base_accesses) > 1 for base_accesses in pred_st.phis.values()]):
                        a = 1
                        continue
                    
                    # if len(par_st.rhoOpts.free_symbols) == 0: 
                    # if not e[2]['wcr']:           # e[2] is the dict of properties of the edge     
                    if self.is_shortest_pred(node, pred):
                        if pred == 'dace_y_3_1':
                            a = 1
                        # 'dace_y_3_1;dace_w_0_6'
                        pred_statements = self.recursive_SDG_subgraphing(pred, checked_subgraphs)   

                        # perform all-to-all possible mergings
                        sibling_statements = copy.deepcopy(sdg_statements)
                        for sib_stat in sibling_statements:
                            for pred_stat in pred_statements:      
                                # check if the concatenation crosses a WCR edge
                                if not self.crosses_wcr(pred_stat.name, sib_stat.name):
                                    S = copy.deepcopy(sib_stat)
                                    S.concatenate_sdg_statements(pred, pred_stat)
                                    if S.subgraph not in checked_subgraphs.union(set([frozenset(sg.subgraph) for sg in sdg_statements])):
                                        sdg_statements.append(S)    
                                    else:
                                        a = 1  
                    else:
                        a = 1

        if node == "dace_w_0_6":
            a = 1
        self.graph.nodes[node]["all_subgraphs"] = sdg_statements
        
        return sdg_statements



    def crosses_wcr(self, subgraph_1 : str, subgraph_2 : str):
        nodes_1 = subgraph_1.split(';')
        nodes_2 = subgraph_2.split(';')
        for node_1 in nodes_1:
            for node_2 in nodes_2:
                if [node_1, node_2, 0] in self.graph.edges:
                    edge = self.graph.edges[node_1, node_2, 0]
                    if edge['wcr'] == True:
                        return True
        return False


    def propagate_SDG_rho(self, S : SOAP_statement):    
        SDG_subgraph  = S.name.split(';')
        for SDG_node in SDG_subgraph:
            node_S = self.graph.nodes[SDG_node]['st']
            if not node_S.parent_subgraph:
                node_S.parent_subgraph = S
            else:
                # find the best embedding subgraph
                [better_subgraph, Q_val] = compare_st(S, node_S.parent_subgraph)
                node_S.parent_subgraph = better_subgraph


    # structure-aware partitioning
    def calculate_IO_of_SDG(self, params : global_parameters):
        # clean up the SDG.
        # 1. remove intermediate transients:
        self.remove_transient_arrays()
        # 2. remove output transients:
        sinks = [u for u, deg in self.graph.out_degree() if not deg]
        final_sinks = [u for u in sinks if not self.graph.nodes[u]['transient']]
        if len(final_sinks) > 0:
            for v in sinks:
                if self.graph.nodes[v]['transient']:
                    self.graph.remove_node(v)
        self.plot_SDG()   
        
        Q_total = sp.sympify(0)
        checked_subgraphs = set()
        all_nodes = list(reversed(list(nx.topological_sort(self.graph))))
        processed_nodes = []
        for node in all_nodes: #final_sinks: #all_nodes:
            # input node
            if len(self.in_edges(node)) == 0:
                continue

            # optimal rho already found for the node
            if node in processed_nodes:
                continue

            if node == "y_1":
                a = 1

            subgraph_opt = SOAP_statement()
            subgraph_opt.Q = 0        
            Q_opt_val = 0
            sdg_subgraphs_statements = self.recursive_SDG_subgraphing(node, checked_subgraphs)
            # append checked sugraphs from this node to the global set
            checked_subgraphs = checked_subgraphs.union(set([frozenset(sg.subgraph) for sg in sdg_subgraphs_statements]))

            for subgraph_st in sdg_subgraphs_statements:    
                if "linear_with_bias_1_linear_with_bias_48_4___tmp4_1;normed1_1" in subgraph_st.name:
                    a = 1
                subgraph_st.solve(params.solver, params)                
                if "S" in str(subgraph_st.Q):
                    a = 1
                if subgraph_st.parent_subgraph:
                    [better_subgraph, Q_val] = compare_st(subgraph_st, subgraph_st.parent_subgraph)
                    subgraph_st.rhoOpts = better_subgraph.rhoOpts
                    subgraph_st.name = better_subgraph.name
                    subgraph_st.Q = subgraph_st.V / subgraph_st.rhoOpts                
                [subgraph_opt, Q_opt_val] = compare_st(subgraph_st, subgraph_opt, Q_opt_val)

            self.graph.nodes[node]['st'] = subgraph_opt
            processed_nodes += subgraph_opt.name.split(';')
            # if subgraph_opt != subgraph_opt.parent_subgraph:
            #     propagate_SDG_rho(sdg, subgraph_opt)
            if 'j' in str(subgraph_opt.Q) or 'i' in str(subgraph_opt.Q):
                a = 1
            
            subgraph_opt.print_schedule()
            Q_total = sp.simplify(Q_total + subgraph_opt.Q)
            
            #subgraph_opt.init_decomposition([("p", 64), ("Ss", 32*1024), ("S0", 512), ("S1", 512), ("S2", 512), ("S3", 512)],  params)  
            #subgraph_opt.init_decomposition([("p", 1059), ("Ss", 32*1024), ("S0", 512), ("S1", 512), ("S2", 512), ("S3", 512)],  params)  
            
            subgraph_opt.init_decomposition(params.param_values,  params)                    
            sample_ranks = range(dict(params.param_values)["p"])
            for rank in sample_ranks:                
                print("\nrank {} should receive the following subsets of input arrays:".format(rank))
                print(subgraph_opt.get_data_decomposition(rank))
            

        return Q_total


    # structure-aware WD analysis
    def CalculateWDofSDG(self, params : global_parameters):
        # set edge weights to match destination node weights. We need numerical values
        # potentialParams = ['n']                
        potentialParams = ['n', 'm', 'w', 'h', 'N', 'M', 'W', 'H', 'NI', 'NJ', 'NK', 'NP', 'NQ', 'NR', 'step']  
        for v in self.graph.nodes:
            if "st" in self.graph.nodes[v].keys():
                subsList = []
                v_D = self.graph.nodes[v]['st'].D
                for symbol in v_D.free_symbols:
                    if any([(param in str(symbol)) for param in potentialParams]):
                        subsList.append([symbol, 1000])                           
                v_D = v_D.subs(subsList)  
                for e in self.graph.in_edges(v):
                    self.graph[e[0]][e[1]][0]['weight'] = v_D
        critical_path = nx.dag_longest_path(self.graph)
        D = sum([self.graph.nodes[v]['st'].D for v in critical_path if "st" in self.graph.nodes[v].keys()])
        W = sum([self.graph.nodes[v]['st'].W for v in self.graph.nodes if "st" in self.graph.nodes[v].keys()])
        return [W,D]







# def update_sdg_array_ver(sdg :SDG, array : str, output = False, out_arr = []):
#     arr_name = array # '_'.join(array.split('_')[:-1])
#     arr_no = int(output) #= int(array.split('_')[-1])
    
#     if out_arr:
#         out_arr_name = '_'.join(out_arr.split('_')[:-1]) 
#         out_arr_no = int(out_arr.split('_')[-1])
#         if out_arr_name == arr_name:
#             return arr_name + '_' + str(out_arr_no -1) 

#     last_update_no = 0
#     last_updates = [n for n in nx.topological_sort(sdg.graph) if arr_name in n]                    
#     if last_updates:
#         last_update_no = int(last_updates[-1].split('_')[-1])   
#         # arr_no += last_update_no   
#         #return arr_name + '_' + str(arr_no + last_update_no)    
#    # return array
#     return arr_name + '_' + str(arr_no + last_update_no)    
