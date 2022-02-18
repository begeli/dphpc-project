total_comm = 0

lines = open("output_mpip.txt").readlines()
for idx in range(len(lines)):
    if "Callsite Message Sent statistics (all, sent bytes)" in lines[idx]:
        idx_ = idx + 3
        while True:
            if "-------" in lines[idx_]:
                break
            
            info = lines[idx_].split()
            idx_ += 1

            if len(info) == 0 or info[2] == '*':
                continue

            total_comm += float(info[-1])

print(total_comm)