import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

data = pd.read_csv('tensor-contraction/code/weak_scaling_mttkrp.csv', delimiter=';')

dims = np.flip(data['dims'].to_numpy())
actual = np.flip(data['actual'].to_numpy())
theory = np.flip(data['theory'].to_numpy())

plt.plot(dims, theory, 'x-', label='Theoretical lower bound', color='tab:orange', markersize=15)
plt.plot(dims, actual, 'o', label='SDG-based TC (our code)', color='tab:blue', markersize=15)

plt.legend(prop={'size': 25})
font = {
    'family': 'sans serif',
    'color': 'black',
    'weight': 'normal'
}
plt.xlabel('Dimensions (all)', fontdict=font, fontsize=25)
plt.grid(axis='y')
bolded_string = r"$\bf{MTTKRP}$ $\bf{(processors}$ $\bf{=}$ $\bf{1000)}$"
#bolded_string = r"$\bf{MTTKRP}$ $\bf{Total}$ $\bf{Communication}$"
plt.title(bolded_string + "\nTotal communication [bytes sent]", fontdict=font,loc='left', fontsize=25)
plt.xticks(dims, dims, fontsize=25, rotation=270)
print(list(range(0, int(max(actual) * 1.2), 500000000000)))
#plt.yticks(range(0, int(max(actual) * 1.2), 500000000), ['0.5×10⁹', '1.0×10⁹', '1.5×10⁹', '2.0×10⁹', '2.5×10⁹', '3.0×10⁹', '3.5×10⁹', '4.0×10⁹', '4.5×10⁹', '5.0×10⁹', '5.5×10⁹', '6.0×10⁹', '6.5×10⁹', '7.0×10⁹'], fontsize=20)
plt.yticks(range(0, int(max(actual) * 1.2), 500000000000), ['0.0', '0.5×10¹²', '1.0×10¹²', '1.5×10¹²', '2.0×10¹²', '2.5×10¹²', '3.0×10¹²', '3.5×10¹²', '4.0×10¹²', '4.5×10¹²', '5.0×10¹²'], fontsize=25)
figure = plt.gcf()
figure.set_size_inches(12 * 1.3, 9 * 1.6)
plt.savefig('weak_scaling_mttkrp.pdf')
plt.close()