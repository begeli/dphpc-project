import importlib
from subprocess import check_output
import subprocess
import json
import argparse
from mpi4py import MPI
import os
import numpy as np
import functools as ft

schedule_file = '__tc_schedule.txt'


def to_json(s):
    clean = s.replace('\'', '"').replace('(', '[').replace(')', ']')
    clean_json = json.loads(clean)
    '''for _, input_slices in clean_json.items():
        for var in variables:
            if not var in input_slices.keys():
                input_slices[var] = [0, 0]'''

    return clean_json


def get_schedule(processors, einsum, iterationSpace, from_file):
    sdg_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "sdg")
    env = os.environ.copy()
    env["PYTHONPATH"] = sdg_path
    if from_file is not None:
        dir_path = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(dir_path, from_file) if from_file[0] != '/' else from_file
        out = [x.encode() for x in open(file_path).readlines()]
    else:
        out = check_output(
            ["/usr/bin/python3", os.path.join(sdg_path, "tests/sdg_test.py"), "--processors", str(processors),
             '--einsum',
             einsum, '--iterationSpace', ','.join(iterationSpace)], env=env, cwd=sdg_path).splitlines()
        cwdir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(cwdir_path, schedule_file), 'w+') as text_file:
            for line_idx in range(len(out)):
                text_file.write(out[line_idx].decode() + '\n')

    processor_input_slices = []
    processor_output_slices = []
    processor_var_limits = []

    for line_idx in range(len(out)):
        if "should receive the following" in out[line_idx].decode():
            if len(out[line_idx + 1].decode()) != 0:
                print(out[line_idx + 1].decode())
                json_slices = to_json(out[line_idx + 1].decode())
                inputs = []
                outputs = []
                limits = {}
                for slice_name, input_slices in sorted(json_slices.items()):
                    ranges = []
                    for var_name, slices in sorted(input_slices.items()):
                        ranges.append((slices[0], slices[1]))
                        if var_name not in limits:
                            limits[var_name] = 0
                        limits[var_name] = max(limits[var_name], slices[1] - slices[0])

                    if "inp" in slice_name:
                        inputs.append(ranges)
                    elif "out" in slice_name:
                        outputs.extend(ranges)

                processor_input_slices.append(inputs)
                processor_output_slices.append(outputs)
                processor_var_limits.append([limit for _, limit in sorted(limits.items())])
                line_idx += 1
            else:
                processor_slices.append({})

    print("Successfully got the schedule.")
    return processor_input_slices, processor_output_slices, processor_var_limits


def contract():
    pass


# def do_contraction(*operands, iterationSpace="64,64,64,64", processors=8):
#     einsum = operands[0]
#
#     inputs_split = einsum.split('->')[0].split(',')
#     outputs_split = einsum.split('->')[1]
#     inputs_cnt = len(inputs_split)
#     outputs_cnt = len(outputs_split)
#
#     variables = sorted(set([var for i in range(inputs_cnt) for var in inputs_split[i]]))
#
#     inputRankIDs = [[variables.index(var) for var in inputs_split[i]] for i in range(inputs_cnt)]
#     inputDims = [[int(iterationSpace.split(',')[variables.index(var)]) for var in inputs_split[i]] for i in
#                  range(inputs_cnt)]
#
#     outputRankIDs = [variables.index(var) for var in outputs_split]
#     outputDims = [int(iterationSpace.split(',')[variables.index(var)]) for var in outputs_split]
#
#     comm = MPI.COMM_WORLD
#     rank = comm.Get_rank()
#
#     if rank == 0:
#         inputRanges, outputRanges, iteration_var_limits = get_schedule(processors, einsum, iterationSpace,
#                                                                        from_file=True)
#     else:
#         inputRanges = outputRanges = iteration_var_limits = None
#
#     inputRanges = comm.bcast(inputRanges, root=0)
#     outputRanges = comm.bcast(outputRanges, root=0)
#     iteration_var_limits = comm.bcast(iteration_var_limits, root=0)
#
#     ptc = importlib.import_module("cmake-build-tc-rel.src.pybind_gjk")
#
#     if rank == 0:
#         return ptc.do_contraction(len(variables), inputRankIDs, outputRankIDs, inputDims, outputDims, inputRanges,
#                                   outputRanges, iteration_var_limits,
#                                   [operands[i].flatten() for i in range(1, len(operands))])
#     else:
#         return ptc.do_contraction(len(variables), inputRankIDs, outputRankIDs, inputDims, outputDims, inputRanges,
#                                   outputRanges, iteration_var_limits, [[]])


parser = argparse.ArgumentParser(description="Minimal communication contraction")
parser.add_argument("einsum", default='ijk,kl,jl->il',
                    help="The contraction to be performed in einsum notation.")
parser.add_argument('-p', "--num_procs", type=int, default=8,
                    help="The number of processors/nodes that perform the contraction.")
parser.add_argument('-i', "--iterationSpace", nargs='?', default=None,
                    help="The dimensions of the iteration space.")
parser.add_argument('-f', '--inputfiles', nargs='+', type=argparse.FileType('rb'),
                    help='Paths or filenames to the files storing the input tensors in numpy array format (ending with .npy).')
parser.add_argument('-o', '--outputfile', default='__tc_output.npy',
                    help='Paths or filename to a file storing the output tensor in numpy array format (ending with .npy).')
parser.add_argument('-s', '--schedulefile', default=None,
                    help='Paths or filename to a file storing the distribution / partition scheme.')
parser.add_argument('--distribute', dest='distribute', action='store_true')
parser.add_argument('--no-distribute', dest='distribute', action='store_false')
parser.set_defaults(distribute=True)
# parser.add_argument('-d', '--distribute', default=True, type=bool,
#                     help='If we should distribute the data from rank 0 (true) or assume the data is partitioned across the ranks (false).')
args = parser.parse_args()

comm = MPI.COMM_WORLD
rank = comm.Get_rank()


def handle_filename_with_rank(file):
    cwdir_path = os.path.dirname(os.path.realpath(__file__))

    if not os.path.isabs(file):
        file = os.path.join(cwdir_path, file)
    if file.endswith('_rank_' + str(rank) + '.npy'):
        return file
    if not file.endswith('.npy'):
        return file + '_rank_' + str(rank) + '.npy'
    return file[:-4] + '_rank_' + str(rank) + '.npy'


def handle_filename(file):
    cwdir_path = os.path.dirname(os.path.realpath(__file__))
    if not os.path.isabs(file):
        file = os.path.join(cwdir_path, file)
    if not file.endswith('.npy'):
        return file + '.npy'
    return file


def execute_nodistrib(op, n_procs, iterationSpace, inputfiles, outputfile, schedulefile):
    [lhs, rhs] = op.split('->')
    inputs_split = lhs.split(',')
    inputs_cnt = len(inputs_split)
    variables = sorted(set([var for i in range(inputs_cnt) for var in inputs_split[i]]))
    print(variables)

    if iterationSpace is not None:
        iteration_ranges = iterationSpace

        # unfortunately we have to "cheat": we can't call matlab more than once in parallel
        # so we actually distribute the schedule from rank 0 to the rest again
        if rank == 0:
            inputRanges, outputRanges, iteration_var_limits = get_schedule(n_procs, op, iteration_ranges,
                                                                           from_file=schedulefile)
        else:
            inputRanges = outputRanges = iteration_var_limits = None
        inputRanges = comm.bcast(inputRanges, root=0)
        outputRanges = comm.bcast(outputRanges, root=0)
        iteration_var_limits = comm.bcast(iteration_var_limits, root=0)

        iteration_limits = iteration_var_limits[rank]

        if not inputfiles:
            dims = [ft.reduce(lambda x, y: x * y, [iteration_limits[variables.index(var)] for var in inputs_split[i]])
                    for i in range(inputs_cnt)]
            counter = 0
            inputfiles = []
            for dim in dims:
                inp_arr = np.random.rand(dim)
                dir_path = os.path.dirname(os.path.realpath(__file__))
                full_path = os.path.join(dir_path, '__tc_input_' + str(counter) + '_rank_' + str(rank) + '.npy')
                np.save(full_path, inp_arr)
                inputfiles.append(full_path)
                counter += 1

        inputfiles = [handle_filename_with_rank(file) for file in inputfiles]
        outputfile = handle_filename(outputfile)
        arrays = [np.load(array) for array in inputfiles]

    else:  # if iterationSpace is None, we require the input files
        inputfiles = [handle_filename_with_rank(file) for file in inputfiles]
        outputfile = handle_filename(outputfile)
        arrays = [np.load(array) for array in inputfiles]

        dim_dict = dict()
        for subscripts, input_array in zip(inputs_split, arrays):
            dim_dict.update(zip(list(subscripts), input_array.shape))
        iteration_ranges = [v for (k, v) in sorted(list(dim_dict.items()))]

        inputRanges, outputRanges, iteration_var_limits = get_schedule(n_procs, op, iteration_ranges,
                                                                       from_file=schedulefile)

    inputRankIDs = [[variables.index(var) for var in inputs_split[i]] for i in range(inputs_cnt)]
    outputRankIDs = [variables.index(var) for var in rhs]
    inputDims = [[int(iteration_ranges[variables.index(var)]) for var in inputs_split[i]] for i in range(inputs_cnt)]
    outputDims = [int(iteration_ranges[variables.index(var)]) for var in rhs]

    # All ranks execute do_contraction with their respective input shards.
    ptc = importlib.import_module("cmake-build-tc-rel.src.pybind_gjk")
    res = ptc.do_contraction(False, len(variables), inputRankIDs, outputRankIDs, inputDims, outputDims, inputRanges,
                             outputRanges, iteration_var_limits,
                             [array.ravel() for array in arrays])
    if rank == 0:
        res = np.reshape(res, outputDims)

        np.set_printoptions(precision=3, threshold=100)
        print("Actual ")
        print(res)
        # TODO compare with actual result.
        #  for this we will have to build the actual inputs from the shards
        # whole_inputs = [np.zeros(*inputDims[i]) for i in range(len(arrays))]
        # for inp, i in zip(whole_inputs, range(inputs_cnt)):
        #     for proc in range(n_procs):
        #         inp[:] = arrays[i]
        # print("Expected: ")
        # print("_____________________________________")
        #
        # print(np.einsum(args.einsum, *(np.reshape(arr, *inputDims[i]) for arr, i in zip(arrays, range(len(arrays))))))
        # print("_____________________________________")
        np.save(outputfile, res)
        return res


# begin here
def execute(op, n_procs, iterationSpace, inputfiles, outputfile, schedulefile, distribute):
    if not distribute:
        print("Not distributing...")
        return execute_nodistrib(op, n_procs, iterationSpace, inputfiles, outputfile, schedulefile)

    [lhs, rhs] = op.split('->')
    inputs_split = lhs.replace("'", '').split(',')
    inputs_cnt = len(inputs_split)

    iteration_ranges = []
    if rank == 0:
        if not inputfiles:
            iteration_ranges = iterationSpace
            variables = sorted(set([var for i in range(inputs_cnt) for var in inputs_split[i]]))
            print(variables)

            inputDims = [[int(iteration_ranges[variables.index(var)]) for var in inputs_split[i]] for i in
                         range(inputs_cnt)]
            counter = 0
            inputfiles = []
            for dim in inputDims:
                inp_arr = np.random.rand(*dim)
                dir_path = os.path.dirname(os.path.realpath(__file__))
                full_path = os.path.join(dir_path, '__tc_input_' + str(counter) + '.npy')
                np.save(full_path, inp_arr)
                inputfiles.append(full_path)
                counter += 1

        # Now input files are guaranteed to exist
        inputfiles = [handle_filename(file) for file in inputfiles]
        arrays = [np.load(array) for array in inputfiles]

        if iterationSpace is not None:
            iteration_ranges = iterationSpace
        else:
            dim_dict = dict()
            for subscripts, input_array in zip(inputs_split, arrays):
                dim_dict.update(zip(list(subscripts), input_array.shape))
            iteration_ranges = [v for (k, v) in sorted(list(dim_dict.items()))]

        inputRanges, outputRanges, iteration_var_limits = get_schedule(n_procs, op, iteration_ranges,
                                                                       from_file=schedulefile)
    else:
        arrays = []
        inputRanges = outputRanges = iteration_var_limits = None

    # Broadcast metadata information from rank 0 to all other ranks.
    iteration_ranges = comm.bcast(iteration_ranges, root=0)
    inputRanges = comm.bcast(inputRanges, root=0)
    outputRanges = comm.bcast(outputRanges, root=0)
    iteration_var_limits = comm.bcast(iteration_var_limits, root=0)

    # Compute remaining metadata
    variables = sorted(set([var for i in range(inputs_cnt) for var in inputs_split[i]]))
    inputRankIDs = [[variables.index(var) for var in inputs_split[i]] for i in range(inputs_cnt)]
    outputRankIDs = [variables.index(var) for var in rhs]

    inputDims = [[int(iteration_ranges[variables.index(var)]) for var in inputs_split[i]] for i in
                 range(inputs_cnt)]
    outputDims = [int(iteration_ranges[variables.index(var)]) for var in rhs]

    ptc = importlib.import_module("cmake-build-tc-rel.src.pybind_gjk")
    if rank == 0:
        res = ptc.do_contraction(True, len(variables), inputRankIDs, outputRankIDs, inputDims, outputDims, inputRanges,
                                 outputRanges, iteration_var_limits,
                                 [array.ravel() for array in arrays])
        res = np.reshape(res, outputDims)

        np.set_printoptions(precision=3, threshold=100)
        print("Actual ")
        print(res)
        print("Expected: ")
        print("_____________________________________")
        print(np.einsum(args.einsum, *arrays))
        print("_____________________________________")
        outputfile = handle_filename(outputfile)
        np.save(outputfile, res)
        return res
    else:
        res = ptc.do_contraction(True, len(variables), inputRankIDs, outputRankIDs, inputDims, outputDims, inputRanges,
                                 outputRanges, iteration_var_limits, [[]])

print(args.distribute)
execute(args.einsum, args.num_procs, args.iterationSpace.split(','), args.inputfiles, args.outputfile, args.schedulefile,
        bool(args.distribute))
