import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

data_euler = pd.read_csv('/Users/daniel/Documents/DPHPC/tensor-contraction/code/output_mm_euler_again.csv', delimiter=';')
data_gjk = pd.read_csv('/Users/daniel/Documents/DPHPC/tensor-contraction/code/output_mm_gjk_again.csv', delimiter=';')

n_procs_euler = np.flip(data_euler['n_procs'].to_numpy())
n_procs_gjk = np.flip(data_gjk['n_procs'].to_numpy())
actual = np.flip(data_gjk['actual'].to_numpy())
cyclops = np.flip(data_euler['cyclops'].to_numpy())
theory = np.flip(data_gjk['theory'].to_numpy())

plt.plot(n_procs_euler, cyclops, '^', label='Cyclops', color='tab:green', markersize=15)
plt.plot(n_procs_gjk, theory, 'x-', label='Theoretical lower bound', color='tab:orange', markersize=15)
plt.plot(n_procs_gjk, actual, 'o', label='SDG-based TC (our code)', color='tab:blue', markersize=15)\

plt.legend(prop={'size': 25})

font = {
    'family': 'sans serif',
    'color': 'black',
    'weight': 'normal'
}
plt.xlabel('Number of ranks', fontdict=font, fontsize=25)
plt.grid(axis='y')
bolded_string = r"$\bf{MMM}$ $\bf{square}$ $\bf{(i=1024,}$ $\bf{j=1024,}$ $\bf{k=1024)}$"
plt.title(bolded_string + "\nTotal communication [bytes sent]", fontdict=font,loc='left', fontsize=25)
plt.xticks(range(0, 1001, 50), range(0, 1001, 50), fontsize=25, rotation=270)
print(max(cyclops))
print(max(actual))
print(list(range(0, int(max(actual) * 1.2), 10000000)))
plt.yticks(range(0, int(max(actual) * 1.2), 10000000), ['0.0', '1.0×10⁷', '2.0×10⁷', '3.0×10⁷', '4.0×10⁷', '5.0×10⁷', '6.0×10⁷', '7.0×10⁷', '8.0×10⁷', '9.0×10⁷', '10.0×10⁷', '11.0×10⁷', '12.0×10⁷', '13.0×10⁷', '14.0×10⁷', '15.0×10⁷'], fontsize=25)
figure = plt.gcf()
#plt.yscale('log')
figure.set_size_inches(12 * 1.3, 9 * 1.6)
plt.savefig('output_mm.pdf')
plt.close()