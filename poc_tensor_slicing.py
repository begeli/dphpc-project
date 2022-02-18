from random import randint

# --- THIS IS CONSTRUCTING THE DATA THAT WILL BE INPUT IN THE REAL CASE ---
vars = ['i', 'j', 'k', 'l']

x = []
for g in range(5):
    f = []
    for gg in range(5):
        f2 = []
        for ggg in range(5):
            f2.append(list(range(g * 125 + gg * 25 + ggg * 5, g * 125 + gg * 25 + ggg * 5 + 5)))
        
        f.append(f2)
    
    x.append(f)

# Print the tensor
print(x)

# We take a random slice
slice = {}
for var in vars:
    first = randint(0, 4)
    if randint(0, 1) == 0:
        slice[var] = (first, randint(first, 4))
    else:
        slice[var] = (randint(0, first), first)

# Print the slice we want to take of the tensor
print("")
print(slice)

# --- END OF CONSTRUCTING DATA ---

# --- THIS IS COMPUTING THE DESIRED OUTPUT
desired_output = []
for i in range(slice['i'][0], slice['i'][1] + 1):
    for j in range(slice['j'][0], slice['j'][1] + 1):
        for k in range(slice['k'][0], slice['k'][1] + 1):
            for l in range(slice['l'][0], slice['l'][1] + 1):
                desired_output.append(x[i][j][k][l])
# --- END OF COMPUTING DESIRED OUTPUT

# --- HERE THE RANK-AGNOSTIC VERSION BEGINS
sizes = [slice['i'][1] - slice['i'][0] + 1, slice['j'][1] - slice['j'][0] + 1, slice['k'][1] - slice['k'][0] + 1, slice['l'][1] - slice['l'][0] + 1]
y = []

product = sizes[0] * sizes[1] * sizes[2] * sizes[3]
for t in range(product): 
    x_ = x.copy()

    product = sizes[0] * sizes[1] * sizes[2] * sizes[3]
    for var_i in range(len(vars)):
        product = int(product / sizes[var_i])
        var = vars[var_i]
        x_ = x_[slice[var][0] + (int(t / product) % sizes[var_i])]

    y.append(x_)

print("\n\nComputed:")
print(y)
print("Desired output:")
print(desired_output)
print("Equal:")
print(len(y) == len(desired_output) and sorted(y) == sorted(desired_output))
