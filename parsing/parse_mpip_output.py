import csv
import math

total_comm = 0
thicc = True
cores = -1
total_comms_thicc = {}
total_comms_skinny = {}
sent = [dict(), dict()]

lines = open("/Users/daniel/Documents/DPHPC/1k.txt").readlines()
for idx in range(len(lines)):
    if "Computing MTT-KRP thicc" in lines[idx]:
        total_cores = lines[idx].split()[-2]
        if total_comm != 0:
            if thicc == True:
                total_comms_thicc[cores] = total_comm
            else:
                total_comms_skinny[cores] = total_comm
            total_comm = 0

        thicc = True
        cores = lines[idx].split()[-2]
    elif "Computing MTT-KRP skinny" in lines[idx]:
        print(lines[idx])
        if total_comm != 0:
            if thicc == True:
                total_comms_thicc[cores] = total_comm
            else:
                total_comms_skinny[cores] = total_comm
            total_comm = 0

        thicc = False
        cores = lines[idx].split()[-2]
    if "Callsite Message Sent statistics (all, sent bytes)" in lines[idx]:
        print(lines[idx])
        idx_ = idx + 3
        while True:
            if "-------" in lines[idx_]:
                print(lines[idx_])
                #print(idx_ - idx)
                break
            
            info = lines[idx_].split()
            idx_ += 1

            if len(info) == 0 or info[2] == '*':
                continue

            total_comm += float(info[-1])

            total_cores = int(total_cores)
            if total_cores not in sent[thicc]:
                sent[thicc][total_cores] = dict()

            if int(info[2]) not in sent[thicc][total_cores]:
                sent[thicc][total_cores][int(info[2])] = float(info[-1])
            else:
                sent[thicc][total_cores][int(info[2])] += float(info[-1])

if total_comm != 0:
    if thicc == True:
        total_comms_thicc[cores] = total_comm
    else:
        total_comms_skinny[cores] = total_comm

print(len(total_comms_thicc))
print(total_comms_thicc)

print(len(total_comms_skinny))
print(total_comms_skinny)

jgk_thicc_actual = dict()
jgk_thicc_theory = dict()
with open('/Users/daniel/Documents/DPHPC/jgk_output_thicc_1000.csv') as csvfile:
    jgk_reader = csv.reader(csvfile, delimiter=';')
    for row in jgk_reader:
        try:
            jgk_thicc_actual[int(row[0])] = int(row[1])
            jgk_thicc_theory[int(row[0])] = int(row[2])
        except:
            continue

jgk_skinny_actual = dict()
jgk_skinny_theory = dict()
with open('/Users/daniel/Documents/DPHPC/jgk_output_skinny_1000.csv') as csvfile:
    jgk_reader = csv.reader(csvfile, delimiter=';')
    for row in jgk_reader:
        try:
            jgk_skinny_actual[int(row[0])] = int(row[1])
            jgk_skinny_theory[int(row[0])] = int(row[2])
        except:
            continue

with open('output_1k_thicc.csv', 'w') as csv_file:  
    writer = csv.writer(csv_file, delimiter=';')
    writer.writerow(["n_procs", "actual", "cyclops", "theory"])
    for key, value in sorted(total_comms_thicc.items(), key=lambda item: int(item[0])):
       writer.writerow([key, jgk_thicc_actual[int(key)], math.floor(value), jgk_thicc_theory[int(key)]])

with open('output_1k_skinny.csv', 'w') as csv_file:  
    writer = csv.writer(csv_file, delimiter=';')
    writer.writerow(["n_procs", "actual", "cyclops", "theory"])
    for key, value in sorted(total_comms_skinny.items(), key=lambda item: int(item[0])):
       writer.writerow([key, jgk_skinny_actual[int(key)], math.floor(value), jgk_skinny_theory[int(key)]])
