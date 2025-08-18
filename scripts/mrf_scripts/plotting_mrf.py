import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def plot_mrf_maps(mrf_results_by_roi, reference_image, proton_params=None):
    """
    Displays CEST-MRF quantitative maps in Streamlit tabs.

    :param mrf_results_by_roi: The dictionary of results from mrf_dot_prod.
    :param reference_image: A 2D grayscale image for the background.
    """
    if not mrf_results_by_roi:
        st.warning("No MRF results found to display.")
        return

    # --- 1. Combine maps from all ROIs ---
    map_keys = list(next(iter(mrf_results_by_roi.values())).keys())
    
    combined_maps = {}
    for key in map_keys:
        first_map = next(iter(mrf_results_by_roi.values()))[key]
        composite_map = np.zeros_like(first_map)
        for roi_name in mrf_results_by_roi:
            composite_map += mrf_results_by_roi[roi_name][key]
        combined_maps[key] = composite_map

    if proton_params and 'pool_b_num_exchangeable_protons' in proton_params and 'fs' in combined_maps:
        num_protons = proton_params['pool_b_num_exchangeable_protons']
        if num_protons > 0:
            concentration_map = (combined_maps['fs'] * 111000) / num_protons
            del combined_maps['fs']
            combined_maps['concentration'] = concentration_map
            st.info("Displaying calculated solute concentration.")

    # --- 2. Create the UI and Plot ---
    st.header("CEST-MRF Quantitative Maps")

    param_details = {
        'fs':  {'name': 'Solute Fraction (fs)', 'unit': 'a.u.', 'cmap': 'viridis'},
        'concentration': {'name': 'Concentration', 'unit': 'mM', 'cmap': 'viridis'},
        'ksw': {'name': 'Exchange Rate (k$_{sw}$)', 'unit': 's$^{-1}$', 'cmap': 'magma'},
        't1w': {'name': 'T$_1$ (Water)', 'unit': 's', 'cmap': 'plasma'},
        't2w': {'name': 'T$_2$ (Water)', 'unit': 'ms', 'cmap': 'plasma'},
        'dp':  {'name': 'Dot Product', 'unit': 'a.u.', 'cmap': 'magma'},
        't1s': {'name': 'T$_1$ (Solute)', 'unit': 's', 'cmap': 'plasma'},
        't2s': {'name': 'T$_2$ (Solute)', 'unit': 'ms', 'cmap': 'plasma'},
    }

    plot_keys = [k for k in param_details.keys() if k in combined_maps]
    tabs = st.tabs([param_details[key]['name'] for key in plot_keys])

    for i, key in enumerate(plot_keys):
        with tabs[i]:
            fig, ax = plt.subplots(figsize=(6, 5))

            q_map = combined_maps[key]
            # Convert T2 maps from seconds to milliseconds
            if key in ['t2w', 't2s']:
                q_map = q_map * 1000
                
            masked_q_map = np.ma.masked_where(q_map == 0, q_map)
            
            ax.imshow(reference_image, cmap='gray')
            
            colormap = param_details[key]['cmap']
            im = ax.imshow(masked_q_map, cmap=colormap, alpha=0.8)
            
            cbar = fig.colorbar(im, ax=ax, shrink=0.8)
            cbar.set_label(f"{param_details[key]['name']} ({param_details[key]['unit']})")
            
            ax.set_title(f"{param_details[key]['name']} Map")
            ax.axis('off')
            
            st.pyplot(fig)

def get_mrf_param_details():
    """Returns a dictionary with details for MRF parameters."""
    return {
        'fs':            {'name': 'Solute Fraction (fs)', 'unit': 'a.u.'},
        'concentration': {'name': 'Concentration', 'unit': 'mM'},
        'ksw':           {'name': 'Exchange Rate (ksw)', 'unit': 'Hz'},
        't1w':           {'name': 'T1 (Water)', 'unit': 's'},
        't2w':           {'name': 'T2 (Water)', 'unit': 'ms'},
        'dp':            {'name': 'Dot Product', 'unit': 'a.u.'},
        't1s':           {'name': 'T1 (Solute)', 'unit': 's'},
        't2s':           {'name': 'T2 (Solute)', 'unit': 'ms'},
    }

def calculate_mrf_stats(mrf_results_by_roi, proton_params=None, statmin=0, statmax=100):
    """
    Calculates statistics for each ROI from CEST-MRF results.
    
    :param mrf_results_by_roi: The dictionary of results from mrf_dot_prod.
    :param proton_params: Dictionary with simulation parameters for concentration calculation.
    :param statmin: The lower percentile for statistical outlier removal.
    :param statmax: The upper percentile for statistical outlier removal.
    :return: A pivoted Pandas DataFrame with statistics, or None.
    """
    param_details = get_mrf_param_details()
    stats_list = []

    is_concentration_calculated = False
    if proton_params and 'pool_b_num_exchangeable_protons' in proton_params:
        num_protons = proton_params['pool_b_num_exchangeable_protons']
        if num_protons > 0:
            is_concentration_calculated = True

    for roi_name, roi_maps in mrf_results_by_roi.items():
        for key, single_roi_map in roi_maps.items():
            param_key = key
            values = single_roi_map[single_roi_map != 0]

            if not values.size > 0:
                continue

            if key == 'fs' and is_concentration_calculated:
                param_key = 'concentration'
                values = (values * 111000) / num_protons

            if param_key not in param_details:
                continue

            if param_key in ['t2w', 't2s']:
                values = values * 1000
            
            p_min, p_max = np.percentile(values, [statmin, statmax])
            filtered_values = values[(values >= p_min) & (values <= p_max)]

            mean_val = np.mean(filtered_values) if filtered_values.size > 0 else np.nan
            std_val = np.std(filtered_values) if filtered_values.size > 0 else np.nan

            details = param_details[param_key]
            param_name = f"{details['name']} ({details['unit']})"
            
            stats_list.append({
                'ROI': roi_name,
                'Parameter': param_name,
                'Mean': mean_val,
                'Std Dev': std_val
            })

    if not stats_list:
        return None

    stats_df = pd.DataFrame(stats_list)
    try:
        pivot_df = stats_df.pivot_table(index='ROI', columns='Parameter', values=['Mean', 'Std Dev'])
        pivot_df.columns = [f"{val} | {param}" for val, param in pivot_df.columns]
        return pivot_df
    except Exception:
        return stats_df.set_index(['ROI', 'Parameter'])