## Example CEST scenario configs (2-pool and 3-pool examples)
# Adapted from code by Nikita Vladimirov 
# https://github.com/momentum-laboratory/molecular-mrf

import numpy as np

# ====================================================================
# USER-EDITABLE PARAMETERS
# ====================================================================

# ## Scanner parameters
B0 = 7 # T
gamma = 267.5153 
b0_inhom = 0 # B0 inhomogeneity
rel_b1 = 1 # Relative B1

# ## Water pool (a)
t1 = np.arange(1300.0, 2600.0 + 100, 100) / 1000  # (s)
t2 = np.arange(40.0, 130.0 + 10, 10) / 1000  # (s)

# ## Solute pool (b)
pool_b_name = 'Cr'
pool_b_dw = 2.0  # Chemical shift of the CEST pool in [ppm]
pool_b_t1 = 2.5  # (s) 
pool_b_t2 = 1e-3  # (s)
pool_b_num_exchangeable_protons = 4.0  # Number of exchangeable solute protons
pool_b_concentration = np.arange(2.0, 100.0 + 2.0, 2.0)  # Solute concentration (mM)
k_b = np.arange(100.0, 500.0 + 5.0, 5.0)  # Solute chemical exchange rate (s^-1)
# Proton fraction can be defined directly OR calculated from concentration
f_b = pool_b_num_exchangeable_protons * pool_b_concentration / 111e3  # Proton fraction [0,1]

# ## MT pool (c)
pool_c_name = 'MT'
pool_c_dw = -2.5  # Chemical shift of the CEST pool in [ppm]
pool_c_t1 = 2.5  # (s) 
pool_c_t2 = 40e-6  # (s)
k_c = np.arange(1.0, 50.0 + 0.5, 0.5)
# Proton fraction can be defined directly OR calculated from concentration
f_c = np.arange(0, 0.5 + 0.01, 0.01)  # Proton fraction [0,1]

# ## Simulation settings
num_workers = 4 # Number of CPU cores to use

# ====================================================================
# DO NOT EDIT BELOW THIS LINE (Handled by the parser)
# ====================================================================

# ## Filenames for the sequence and dictionary output
yaml_fn = 'configs/scenario.yaml'
seq_fn = 'configs/acq_protocol.seq'
dict_fn = 'configs/dict.mat'

# ## Other fixed parameters
scale = 1
reset_init_mag = 0
verbose = 0
max_pulse_samples = 100
