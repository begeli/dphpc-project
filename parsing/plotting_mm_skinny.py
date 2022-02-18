import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

data_euler = pd.read_csv('/Users/daniel/Documents/DPHPC/tensor-contraction/code/output_mm_euler_skinny.csv', delimiter=';')
data_gjk = pd.read_csv('/Users/daniel/Documents/DPHPC/tensor-contraction/code/output_mm_gjk_skinny.csv', delimiter=';')

print(data_gjk)

n_procs_euler = np.flip(data_euler['n_procs'].to_numpy())
n_procs_gjk = np.flip(data_gjk['n_procs'].to_numpy())
actual = np.flip(data_gjk['actual'].to_numpy())
cyclops = np.flip(data_euler['cyclops'].to_numpy())
theory = np.flip(data_gjk['theory'].to_numpy())

actual = list(actual)
cyclops = list(cyclops)

print(actual)
print(cyclops)


plt.plot(n_procs_gjk, actual, 'o', label='SDG-based TC (our code)', color='tab:blue', markersize=15)
plt.plot(n_procs_euler, cyclops, '^', label='Cyclops', color='tab:green', markersize=15)
plt.plot(n_procs_gjk, theory, 'x-', label='Theoretical lower bound', color='tab:orange', markersize=15)
plt.legend(prop={'size': 25})

font = {
    'family': 'sans serif',
    'color': 'black',
    'weight': 'normal'
}
plt.xlabel('Number of ranks', fontdict=font, fontsize=25)
plt.grid(axis='y')
#-i 1 -j 16777216 -k 1
bolded_string = r"$\bf{MMM}$ $\bf{skinny}$ $\bf{(i=1,}$ $\bf{j=16777216,}$ $\bf{k=1)}$"
plt.title(bolded_string + "\nTotal communication [bytes sent]", fontdict=font,loc='left', fontsize=25)
plt.xticks(range(0, 1001, 50), range(0, 1001, 50), fontsize=25, rotation=270)
print(max(cyclops))
print(max(actual))
print(list(range(0, int(max(cyclops) * 1.2), 50000000)))
plt.yticks(range(0, int(max(cyclops) * 1.2), 50000000), ['0.0', '0.5×10⁸', '1.0×10⁸', '1.5×10⁸', '2.0×10⁸', '2.5×10⁸', '3.0×10⁸', '3.5×10⁸', '4.0×10⁸', '4.5×10⁸', '5.0×10⁸', '5.5×10⁸', '6.0×10⁸', '6.5×10⁸'], fontsize=25)
figure = plt.gcf()
#plt.yscale('log')
figure.set_size_inches(12 * 1.3, 9 * 1.6)
plt.savefig('output_mm_skinny.pdf')
plt.close()