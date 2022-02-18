import csv
import math

total_comm = 0
mode = -1
cores = -1
total_comms = [dict(), dict(), dict(), dict()]
sent = [dict(), dict(), dict(), dict()]

lines = open("/Users/daniel/Documents/DPHPC/tensor-contraction/euler/run_for_all_cores_mm.txt").readlines()
for idx in range(len(lines)):
    if "Computing MMM thicc" in lines[idx]:
        if total_comm != 0:
            total_comms[mode][cores] = total_comm
            total_comm = 0

        mode = 0
        cores = lines[idx].split()[-2]
    elif "Computing MMM skinny" in lines[idx]:
        if total_comm != 0:
            total_comms[mode][cores] = total_comm
            total_comm = 0

        mode = 1
        cores = lines[idx].split()[-2]
    elif "Computing Batch MMM thicc" in lines[idx]:
        if total_comm != 0:
            total_comms[mode][cores] = total_comm
            total_comm = 0

        mode = 2
        cores = lines[idx].split()[-2]
    elif "Computing Batch MMM skinny" in lines[idx]:
        if total_comm != 0:
            total_comms[mode][cores] = total_comm
            total_comm = 0

        mode = 3
        cores = lines[idx].split()[-2]
    elif "Callsite Message Sent statistics (all, sent bytes)" in lines[idx]:
        idx_ = idx + 3
        while True:
            if "-------" in lines[idx_]:
                break
            
            info = lines[idx_].split()
            idx_ += 1

            if len(info) == 0 or info[2] == '*':
                continue

            total_comm += float(info[-1])
            cores = int(cores)

            if cores not in sent[mode]:
                sent[mode][cores] = dict()

            if int(info[2]) not in sent[mode][cores]:
                sent[mode][cores][int(info[2])] = float(info[-1])
            else:
                sent[mode][cores][int(info[2])] += float(info[-1])

if total_comm != 0:
    total_comms[mode][cores] = total_comm
    total_comm = 0

jgk_actual = dict()
jgk_theory = dict()
with open('/Users/daniel/Documents/DPHPC/tensor-contraction/euler/jgk_output_mm_1000.csv') as csvfile:
    jgk_reader = csv.reader(csvfile, delimiter=';')
    for row in jgk_reader:
        try:
            jgk_actual[int(row[0])] = int(row[1])
            jgk_theory[int(row[0])] = int(row[2])
        except:
            continue

with open('/Users/daniel/Documents/DPHPC/tensor-contraction/code/output_mm_euler_again.csv', 'w') as csv_file:
    writer = csv.writer(csv_file, delimiter=';')
    writer.writerow(["n_procs", "cyclops"])
    for k, value in sorted(total_comms[0].items(), key=lambda item: int(item[0])):
        writer.writerow([k, math.floor(value)])

with open('/Users/daniel/Documents/DPHPC/tensor-contraction/code/output_mm_euler_thicc_dist_skinny.csv', 'w') as csv_file:
    writer = csv.writer(csv_file, delimiter=';')
    writer.writerow(["n_procs", "core", "bytes"])
    for i in sent[0].keys():
        for k, value in sorted(sent[1][i].items(), key=lambda item: int(item[0])):
            writer.writerow([i, k, math.floor(value)])

with open('/Users/daniel/Documents/DPHPC/tensor-contraction/code/output_mm_gjk_again.csv', 'w') as csv_file:
    writer = csv.writer(csv_file, delimiter=';')
    writer.writerow(["n_procs", "actual", "theory"])
    for k, value in sorted(jgk_actual.items(), key=lambda item: int(item[0])):
        writer.writerow([k, jgk_actual[int(k)], jgk_theory[int(k)]])