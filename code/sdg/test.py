from subprocess import check_output
import json
import argparse

parser = argparse.ArgumentParser(description="Minimal communication contraction")
parser.add_argument('-p', "--processors", default='8', help="The number of processors/nodes that perform the contraction")
parser.add_argument('-e', "--einsum", default='ijk,jl,kl->il', help="The contraction to be performed in einsum notation")

args = parser.parse_args()

inputs_cnt = len(args.einsum.split(','))
variables = sorted(set([var for i in range(inputs_cnt) for var in args.einsum.split('->')[0].split(',')[i]]))

def to_json(s):
    clean = s.replace('\'','"').replace('(', '[').replace(')', ']')
    clean_json = json.loads(clean)
    for _, input_slices in clean_json.items(): 
        for var in variables:
            if not var in input_slices.keys():
                input_slices[var] = [0, 0]

    return clean_json

out = check_output(["python", "tests/sdg_test.py", "--processors", args.processors, '--einsum', args.einsum]).splitlines()

processor_slices = []

for line_idx in range(len(out)):
    if "should receive the following" in out[line_idx].decode():
        if len(out[line_idx + 1].decode()) != 0:
            json_slices = to_json(out[line_idx + 1].decode())
            inputs = []
            for _, input_slices in sorted(json_slices.items()):
                ranges = []
                for var in variables:
                    ranges.append(input_slices[var])
                inputs.append(ranges)
            
            processor_slices.append(inputs)
            line_idx += 1
        else:
            processor_slices.append({})


#Now, we should pass processor_slices to the C++ code
#It is of form: processors x input/outputs x variables
#If a variable is not relevant for the input/output, it has slice [0,0]
#The input/outputs are sorted (i.e. inp0, inp1, ..., out1)
#The variables within one input/output are sorted (i.e. i, j, k, ...)


