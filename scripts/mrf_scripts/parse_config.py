import sys
import importlib.util
import numpy as np

def build_config_from_file(config_path):
    """
    Loads a user-defined config file and builds the dictionary required
    for the CEST-MRF simulation.
    """
    try:
        # Dynamically load the user's config file as a module
        spec = importlib.util.spec_from_file_location("user_config", config_path)
        user_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(user_config)
    except Exception as e:
        print(f"Error loading config file: {e}")
        return None

    # Start building the dictionary
    config = {}

    # --- File Names ---
    config['yaml_fn'] = getattr(user_config, 'yaml_fn', 'scenario.yaml')
    config['seq_fn'] = getattr(user_config, 'seq_fn', 'acq_protocol.seq')
    config['dict_fn'] = getattr(user_config, 'dict_fn', 'dict.mat')

    # --- Water Pool ---
    config['water_pool'] = {
        't1': getattr(user_config, 't1', np.array([1.5])).tolist(),
        't2': getattr(user_config, 't2', np.array([0.1])).tolist(),
        'f': 1
    }

    # --- Solute Pools ---
    config['cest_pool'] = {}
    
    # Primary Solute Pool (Pool B)
    pool_b_name = getattr(user_config, 'pool_b_name', 'solute')
    config['cest_pool'][pool_b_name] = {
        't1': [getattr(user_config, 'pool_b_t1', 1.0)],
        't2': [getattr(user_config, 'pool_b_t2', 0.01)],
        'k': getattr(user_config, 'k_b', np.array([500])).tolist(),
        'dw': getattr(user_config, 'pool_b_dw', 2.0),
        'f': getattr(user_config, 'f_b', np.array([0.001])).tolist()
    }

    # Optional MT Pool (Pool C) - check if it exists in the user's file
    if hasattr(user_config, 'pool_c_name'):
        pool_c_name = user_config.pool_c_name
        config['cest_pool'][pool_c_name] = {
            't1': [getattr(user_config, 'pool_c_t1', 1.0)],
            't2': [getattr(user_config, 'pool_c_t2', 20e-6)],
            'k': getattr(user_config, 'k_c', np.array([50])).tolist(),
        'dw': getattr(user_config, 'pool_b_dw', 2.0),
        'f': getattr(user_config, 'f_c', np.array([0.01])).tolist()
        }

    # --- Scanner Info ---
    config['b0'] = getattr(user_config, 'B0', 7.0)
    config['gamma'] = getattr(user_config, 'gamma', 267.5153)
    config['b0_inhom'] = getattr(user_config, 'b0_inhom', 0.0)
    config['rel_b1'] = getattr(user_config, 'rel_b1', 1.0)
    
    # --- Other Settings ---
    config['scale'] = getattr(user_config, 'scale', 1)
    config['reset_init_mag'] = getattr(user_config, 'reset_init_mag', 0)
    config['verbose'] = getattr(user_config, 'verbose', 0)
    config['max_pulse_samples'] = getattr(user_config, 'max_pulse_samples', 100)
    config['num_workers'] = getattr(user_config, 'num_workers', 18)

    return config

def get_proton_params(config_path):
    """
    Loads a user-defined config file and extracts the number of 
    exchangeable protons for each solute pool, if defined.
    
    Returns a separate dictionary with just these parameters.
    """
    proton_params = {}
    try:
        # Dynamically load the user's config file as a module
        # Use a unique name to avoid module caching issues
        spec = importlib.util.spec_from_file_location("user_config_protons", config_path)
        user_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(user_config)
    except Exception as e:
        # Fail gracefully if the file can't be read
        print(f"Could not read config file to check for proton params: {e}")
        return proton_params

    # Check for Pool B's exchangeable protons
    if hasattr(user_config, 'pool_b_num_exchangeable_protons'):
        proton_params['pool_b_num_exchangeable_protons'] = float(getattr(user_config, 'pool_b_num_exchangeable_protons'))
        
    # Optional: Also check for Pool C's protons
    if hasattr(user_config, 'pool_c_num_exchangeable_protons'):
        proton_params['pool_c_num_exchangeable_protons'] = float(getattr(user_config, 'pool_c_num_exchangeable_protons'))
            
    return proton_params