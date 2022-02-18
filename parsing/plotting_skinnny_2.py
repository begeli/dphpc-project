import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

data = pd.read_csv('/Users/daniel/Documents/DPHPC/tensor-contraction/euler/output_1k_skinny_2.csv', delimiter=';')

n_procs = np.flip(data['n_procs'].to_numpy())
actual = np.flip(data['actual'].to_numpy())
cyclops = np.flip(data['cyclops'].to_numpy())
theory = np.flip(data['theory'].to_numpy())

plt.plot(n_procs, actual, 'o', label='SDG-based TC (our code)', color='tab:blue', markersize=15)
plt.plot(n_procs, cyclops, '^', label='Cyclops', color='tab:green', markersize=15)
plt.plot(n_procs, theory, 'x-', label='Theoretical lower bound', color='tab:orange', markersize=15)
plt.legend(prop={'size': 25})
font = {
    'family': 'sans serif',
    'color': 'black',
    'weight': 'normal'
}
plt.xlabel('Number of ranks', fontdict=font, fontsize=25)
plt.grid(axis='y')
bolded_string = r"$\bf{MTTKRP}$ $\bf{skinny}$ $\bf{(i=2048,}$ $\bf{j=10,}$ $\bf{k=10,}$ $\bf{l=2048)}$"
plt.title(bolded_string + "\nTotal communication [bytes sent]", fontdict=font,loc='left', fontsize=25)
plt.xticks(range(0, 1001, 50), range(0, 1001, 50), fontsize=25, rotation=270)
print(max(cyclops))
print(max(actual))
print(list(range(0, int(max(cyclops) * 1.2), 5000000)))
print(len(range(0, int(max(cyclops) * 1.2), 5000000)))
plt.yticks(range(0, int(max(cyclops) * 1.2), 5000000), ['0.0', '0.5×10⁷', '1.0×10⁷', '1.5×10⁷', '2.0×10⁷', '2.5×10⁷', '3.0×10⁷', '3.5×10⁷', '4.0×10⁷', '4.5×10⁷', '5.0×10⁷', '5.5×10⁷'], fontsize=25)
figure = plt.gcf()
#plt.yscale('log')
figure.set_size_inches(12 * 1.3, 9 * 1.6)
plt.savefig('output_1k_skinny_2.pdf')
plt.close()