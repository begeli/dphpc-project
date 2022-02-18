import json

def to_json(s):
    clean = s.replace('\'', '"').replace('(', '[').replace(')', ']')
    clean_json = json.loads(clean)

    return clean_json

total_comm = 0

lines = open("__tc_schedule.txt").readlines()

for idx in range(len(lines)):
        if "should receive the following" in lines[idx] and "rank 0" not in lines[idx]:
            json_slices = to_json(lines[idx + 1])
            for slice in json_slices:
                comm = 1.0
                for dim in json_slices[slice]:
                    comm *= (float(json_slices[slice][dim][1]) - float(json_slices[slice][dim][0]))
                total_comm += (comm * 4.0)

print(total_comm)