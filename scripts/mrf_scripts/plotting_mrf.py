import streamlit as st
import numpy as np
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

    st.write(combined_maps)

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
        'ksw': {'name': 'Exchange Rate (ksw)', 'unit': 'Hz', 'cmap': 'magma'},
        't1w': {'name': 'T1 (Water)', 'unit': 's', 'cmap': 'plasma'},
        't2w': {'name': 'T2 (Water)', 'unit': 's', 'cmap': 'plasma'},
        'dp':  {'name': 'Dot Product', 'unit': 'a.u.', 'cmap': 'magma'},
        't1s': {'name': 'T1 (Solute)', 'unit': 's', 'cmap': 'plasma'},
        't2s': {'name': 'T2 (Solute)', 'unit': 's', 'cmap': 'plasma'},
    }

    plot_keys = [k for k in param_details.keys() if k in combined_maps]
    tabs = st.tabs([param_details[key]['name'] for key in plot_keys])

    for i, key in enumerate(plot_keys):
        with tabs[i]:
            fig, ax = plt.subplots(figsize=(6, 5))

            q_map = combined_maps[key]
            masked_q_map = np.ma.masked_where(q_map == 0, q_map)
            
            ax.imshow(reference_image, cmap='gray')
            
            colormap = param_details[key]['cmap']
            im = ax.imshow(masked_q_map, cmap=colormap, alpha=0.8)
            
            cbar = fig.colorbar(im, ax=ax, shrink=0.8)
            cbar.set_label(f"{param_details[key]['name']} ({param_details[key]['unit']})")
            
            ax.set_title(f"{param_details[key]['name']} Map")
            ax.axis('off')
            
            st.pyplot(fig)