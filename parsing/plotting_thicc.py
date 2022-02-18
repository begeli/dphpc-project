import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

data = pd.read_csv('tensor-contraction/code/output_1k_thicc.csv', delimiter=';')

n_procs = np.flip(data['n_procs'].to_numpy())
actual = np.flip(data['actual'].to_numpy())
cyclops = np.flip(data['cyclops'].to_numpy())
theory = np.flip(data['theory'].to_numpy())

print(actual)
print(theory)

plt.plot(n_procs, actual, 'o', label='SDG-based TC (our code)', color='tab:blue', markersize=15)
plt.plot(n_procs, cyclops, '^', label='Cyclops', color='tab:green', markersize=15)
plt.plot(n_procs, theory, 'x-', label='Theoretical lower bound', color='tab:orange', markersize=15)



#plt.legend(fontsize='xxx-large')
plt.legend(prop={'size': 25})
font = {
    'family': 'sans serif',
    'color': 'black',
    'weight': 'normal'
}
plt.xlabel('Number of ranks', fontdict=font, fontsize=25)
plt.grid(axis='y')
bolded_string = r"$\bf{MTTKRP}$ $\bf{square}$ $\bf{(i=1024,}$ $\bf{j=1024,}$ $\bf{k=1024,}$ $\bf{l=1024)}$"
#bolded_string = r"$\bf{MTTKRP}$ $\bf{Total}$ $\bf{Communication}$"
plt.title(bolded_string + "\nTotal communication [bytes sent]", fontdict=font,loc='left', fontsize=25)
plt.xticks(range(0, 1001, 50), range(0, 1001, 50), fontsize=25, rotation=270)
print(list(range(0, int(max(cyclops) * 1.2), 5000000000)))
#plt.yticks(range(0, int(max(actual) * 1.2), 500000000), ['0.5×10⁹', '1.0×10⁹', '1.5×10⁹', '2.0×10⁹', '2.5×10⁹', '3.0×10⁹', '3.5×10⁹', '4.0×10⁹', '4.5×10⁹', '5.0×10⁹', '5.5×10⁹', '6.0×10⁹', '6.5×10⁹', '7.0×10⁹'], fontsize=20)
plt.yticks(range(0, int(max(cyclops) * 1.2), 5000000000), ['0.0', '0.5×10¹⁰', '1.0×10¹⁰', '1.5×10¹⁰', '2.0×10¹⁰', '2.5×10¹⁰', '3.0×10¹⁰', '3.5×10¹⁰', '4.0×10¹⁰', '4.5×10¹⁰'], fontsize=25)
figure = plt.gcf()
figure.set_size_inches(12 * 1.3, 9 * 1.6)
plt.savefig('output_1k_thicc.pdf')
plt.close()