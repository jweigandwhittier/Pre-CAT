import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

def plot_mrf_maps(mrf_results_by_roi, reference_image):
    """
    Displays CEST-MRF quantitative maps in Streamlit tabs.

    :param mrf_results_by_roi: The dictionary of results from mrf_dot_prod.
    :param reference_image: A 2D grayscale image for the background.
    """
    if not mrf_results_by_roi:
        st.warning("No MRF results found to display.")
        return

    # --- 1. Combine maps from all ROIs into single composite maps ---
    # Get the keys for the maps (e.g., 't1w', 't2w') from the first ROI
    map_keys = list(next(iter(mrf_results_by_roi.values())).keys())
    
    combined_maps = {}
    for key in map_keys:
        # Initialize a zero-filled array with the correct shape
        first_map = next(iter(mrf_results_by_roi.values()))[key]
        composite_map = np.zeros_like(first_map)
        # Add the maps from each ROI together
        for roi_name in mrf_results_by_roi:
            composite_map += mrf_results_by_roi[roi_name][key]
        combined_maps[key] = composite_map

    # --- 2. Create the UI and Plot ---
    st.header("CEST-MRF Quantitative Maps")

    # Define nice names and units for plotting
    param_details = {
        't1w': {'name': 'T1 (Water)', 'unit': 's'},
        't2w': {'name': 'T2 (Water)', 'unit': 's'},
        'ksw': {'name': 'Exchange Rate (ksw)', 'unit': 'Hz'},
        'fs': {'name': 'Solute Fraction (fs)', 'unit': 'a.u.'},
        'dp': {'name': 'Dot Product', 'unit': 'a.u.'},
        't1s': {'name': 'T1 (Solute)', 'unit': 's'},
        't2s': {'name': 'T2 (Solute)', 'unit': 's'},
    }

    # Filter for keys that exist in our results and create tabs
    plot_keys = [k for k in param_details.keys() if k in combined_maps]
    tabs = st.tabs([param_details[key]['name'] for key in plot_keys])

    for i, key in enumerate(plot_keys):
        with tabs[i]:
            fig, ax = plt.subplots(figsize=(6, 5))

            q_map = combined_maps[key]
            
            # Mask out the zero values so they become transparent in the plot
            masked_q_map = np.ma.masked_where(q_map == 0, q_map)
            
            # Display the grayscale reference image as the background
            ax.imshow(reference_image, cmap='gray')
            
            # Overlay the colorful quantitative map with some transparency
            im = ax.imshow(masked_q_map, cmap='viridis', alpha=0.8)
            
            # Add a colorbar
            cbar = fig.colorbar(im, ax=ax, shrink=0.8)
            cbar.set_label(f"{param_details[key]['name']} ({param_details[key]['unit']})")
            
            ax.set_title(f"{param_details[key]['name']} Map")
            ax.axis('off')
            
            st.pyplot(fig)