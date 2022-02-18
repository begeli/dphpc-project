import subprocess
import argparse
import os
import json
import math
from subprocess import check_output


def comp_schedule(einsum, processors, iterationSpace, schedule_file):
    sdg_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "sdg")
    env = os.environ.copy()
    env["PYTHONPATH"] = sdg_path
    out = check_output(
        ["/usr/bin/python3", os.path.join(sdg_path, "tests/sdg_test.py"), "--processors", str(processors),
         '--einsum',
         einsum, '--iterationSpace', ','.join(iterationSpace)], env=env, cwd=sdg_path).splitlines()
    cwdir_path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(cwdir_path, schedule_file), 'w+') as text_file:
        for line_idx in range(len(out)):
            text_file.write(out[line_idx].decode() + '\n')


def precompute(einsum, np_values, iter_space_values, schedule_filestem):
    for np in np_values:
        for iterationSpace in iter_space_values:
            iterationSpace = [str(i) for i in iterationSpace]
            print(einsum)
            print(np)
            print(iterationSpace)
            print(schedule_filestem)
            comp_schedule(einsum, np, iterationSpace, schedule_filestem + '_' + str(np) + '_d_' + '_'.join(iterationSpace) + '.txt')

    pass


def to_json(s):
    clean = s.replace('\'', '"').replace('(', '[').replace(')', ']')
    clean_json = json.loads(clean)

    return clean_json


def parse_file(filename):
    total_comm = 0
    lines = open(filename).readlines()
    for idx in range(len(lines)):
        if "should receive the following" in lines[idx] and "rank 0" not in lines[idx]:
            if len(lines[idx + 1]) < 4:
                continue
            json_slices = to_json(lines[idx + 1])
            for slice in json_slices:
                comm = 1.0
                for dim in json_slices[slice]:
                    comm *= (float(json_slices[slice][dim][1]) - float(json_slices[slice][dim][0]))
                total_comm += (comm * 4.0)
    return math.ceil(total_comm)


def theory(p, dims):
    [S0,S1,S2,S3] = dims
    return math.ceil(p * 4.0 * 5*2**(0.6)*(S0*S1*S2*S3/p)**(0.6)/2)


def compute_comm(np_list, dims, filestem):
    str_dims = [str(d) for d in dims]
    filelist = [filestem + '_' + str(n) + '_d_' + '_'.join(str_dims) + '.txt' for n in np_list]
    # TODO save to file
    commlist = [parse_file(filename) for filename in filelist]
    print('n_procs;Actual;Theory')
    for n, c in zip(np_list, commlist):
        print(str(n) + ';' + str(c) + ';' + str(theory(n, dims)))
    pass


def parse_counters(filename):
    total = 0
    lines = open(filename).readlines()
    for line in lines:
        if line.startswith('[') and not line.startswith('[0'):
            words = line.split()
            if words[2] == 'Bytes':
                total += int(words[4])
    return total


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Minimal communication contraction")
    parser.add_argument("einsum",
                        help="The contraction to be performed in einsum notation.")
    parser.add_argument('-p', "--num_procs", type=int, default=8,
                        help="The number of processors/nodes that perform the contraction.")
    parser.add_argument('-i', "--iterationSpace", nargs='*', default=None,
                        help="The dimensions of the iteration space.")
    parser.add_argument('-f', '--inputfiles', nargs='*',
                        help='Paths or filenames to the files storing the input tensors in numpy array format (ending with .npy).')
    parser.add_argument('-o', '--outputfile', default='__tc_output.npy',
                        help='Paths or filename to a file storing the output tensor in numpy array format (ending with .npy).')
    parser.add_argument('-s', '--schedulefile', default=None,
                        help='Paths or filename to a file storing the distribution / partition scheme.')
    parser.add_argument('--distribute', dest='distribute', action='store_true')
    parser.add_argument('--no-distribute', dest='distribute', action='store_false')
    parser.set_defaults(distribute=True)
    args = parser.parse_args()

    cwdir_path = os.path.dirname(os.path.realpath(__file__))
    call_args = ['mpirun', '-np', str(args.num_procs), 'python3', os.path.join(cwdir_path, 'handle_mpi.py'),
                 args.einsum,
                 '-p', str(args.num_procs)]
    if (args.iterationSpace):
        call_args.append('-i')
        call_args.append(','.join(str(s) for s in args.iterationSpace))
    if (args.inputfiles):
        call_args.append('-f')
        call_args += [f for f in args.inputfiles]
    call_args.append('-o')
    call_args.append(args.outputfile)
    if (args.schedulefile):
        call_args.append('-s')
        call_args.append(args.schedulefile)
    if (args.distribute):
        call_args.append('--distribute')
    else:
        call_args.append('--no-distribute')
    print(call_args)

    subprocess.call(call_args)
