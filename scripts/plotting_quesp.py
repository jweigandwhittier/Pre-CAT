#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul 10 18:23:03 2025

@author: jonah
"""
import os
import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable

def plot_t1_map(t1_fits, reference_image, masks, save_path):
    """
    Reconstructs and plots the T1 map from pixel-wise fit results.
    """
    t1_map = np.full(reference_image.shape, np.nan)
    
    # Reconstruct the T1 map from the fitted data
    for roi_label, fit_data in t1_fits.items():
        if roi_label in masks:
            y_coords, x_coords = np.where(masks[roi_label])
            for i, (y, x) in enumerate(zip(y_coords, x_coords)):
                if i < len(fit_data):
                    t1_map[y, x] = fit_data[i]
            
    combined_mask = np.zeros_like(reference_image, dtype=bool)
    for mask in masks.values():
        combined_mask = np.logical_or(combined_mask, mask)

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(reference_image, cmap='gray')
    
    valid_t1_values = t1_map[combined_mask]
    vmin, vmax = (np.nanpercentile(valid_t1_values, [5, 95]) if np.any(valid_t1_values) else (0, 1000))
    
    t1_map_masked = np.ma.masked_where(~combined_mask, t1_map)
    overlay = ax.imshow(t1_map_masked, cmap='plasma', alpha=0.9, vmin=vmin, vmax=vmax)
    
    # Create a dedicated axis for the colorbar so it doesn't shrink the plot
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.05)
    cbar = fig.colorbar(overlay, cax=cax)

    cbar.set_label('T₁ (ms)', fontsize=24, fontweight='bold')
    cbar.ax.tick_params(labelsize=18)
    
    ax.axis('off')
    ax.set_title('T₁ Map', fontsize=28, fontweight='bold')
    
    # Use tight_layout after creating all axes elements
    fig.tight_layout()
    st.pyplot(fig)

    # Save
    image_path = os.path.join(save_path, 'Images')
    if not os.path.isdir(image_path):
    	os.makedirs(image_path)
    plt.savefig(os.path.join(image_path, 'T1_Maps.png'), dpi=300, bbox_inches="tight")
    return t1_map_masked

def plot_quesp_maps(quesp_fits, masks, reference_image, save_path, plotmin, plotmax):
    """
    Reconstructs and plots fb, kb, and R² maps for each fitted pool,
    using robust percentile-based colormaps to handle outliers.
    """
    if not quesp_fits:
        st.warning("No QUESP fit data available to plot.")
        return

    # Get a list of all unique chemical pools that were fitted
    first_roi_label = next(iter(quesp_fits))
    all_pool_names = list(quesp_fits[first_roi_label].keys())

    # Get the coordinates for each mask once for efficiency
    coords_by_roi = {label: np.argwhere(mask) for label, mask in masks.items()}
    
    # Create a combined mask for plotting all ROIs
    combined_mask = np.zeros_like(reference_image, dtype=bool)
    for mask in masks.values():
        combined_mask = np.logical_or(combined_mask, mask)

    # Empty list for saving maps
    maps_to_return = {}

    # Iterate through each chemical pool to create a set of maps
    for pool_name in all_pool_names:
        st.subheader(f"Results for {pool_name}")

        # Initialize empty maps for the current pool
        fb_map = np.full(reference_image.shape, np.nan)
        kb_map = np.full(reference_image.shape, np.nan)
        r2_map = np.full(reference_image.shape, np.nan)

        # Reconstruct the full maps from the per-ROI pixel data
        for roi_label, fit_data in quesp_fits.items():
            if pool_name in fit_data:
                coords = coords_by_roi[roi_label]
                pool_fit_data = fit_data[pool_name]
                
                for i, (y, x) in enumerate(coords):
                    if i < len(pool_fit_data['fb_values']):
                        fb_map[y, x] = pool_fit_data['fb_values'][i]
                        kb_map[y, x] = pool_fit_data['kb_values'][i]
                        r2_map[y, x] = pool_fit_data['r2_values'][i]
        
        # Calculate robust color limits using percentiles to ignore outliers
        valid_fb = fb_map[combined_mask]
        fb_vmin, fb_vmax = (np.nanpercentile(valid_fb, [plotmin, plotmax]) if np.any(valid_fb) else (0, 0.1))

        valid_kb = kb_map[combined_mask]
        kb_vmin, kb_vmax = (np.nanpercentile(valid_kb, [plotmin, plotmax]) if np.any(valid_kb) else (0, 2000))
        
        # Plotting the three maps
        fig, axs = plt.subplots(1, 3, figsize=(24, 8))
        fig.suptitle(f'QUESP Maps for {pool_name}', fontsize=32, fontweight='bold')

        # Plot fb map
        fb_masked = np.ma.masked_where(~combined_mask, fb_map)
        axs[0].imshow(reference_image, cmap='gray')
        im0_overlay = axs[0].imshow(fb_masked, cmap='viridis', alpha=0.9, vmin=fb_vmin, vmax=fb_vmax)
        axs[0].set_title('Proton Volume Fraction (f$_b$)', fontsize=24, fontweight='bold')
        axs[0].axis('off')
        fb_cbar = fig.colorbar(im0_overlay, ax=axs[0], fraction=0.046, pad=0.04)
        fb_cbar.set_label('f$_{b}$', fontsize=24, fontweight='bold')
        fb_cbar.ax.tick_params(labelsize=18)

        # Plot kb map
        kb_masked = np.ma.masked_where(~combined_mask, kb_map)
        axs[1].imshow(reference_image, cmap='gray')
        im1_overlay = axs[1].imshow(kb_masked, cmap='magma', alpha=0.9, vmin=kb_vmin, vmax=kb_vmax)
        axs[1].set_title('Exchange Rate (k$_b$)', fontsize=24, fontweight='bold')
        axs[1].axis('off')
        kb_cbar = fig.colorbar(im1_overlay, ax=axs[1], fraction=0.046, pad=0.04)
        kb_cbar.set_label('k$_{b}$ (s$^{-1}$)', fontsize=24, fontweight='bold')
        kb_cbar.ax.tick_params(labelsize=18)
        
        # Plot R² map (R² is naturally bounded between 0 and 1)
        r2_masked = np.ma.masked_where(~combined_mask, r2_map)
        axs[2].imshow(reference_image, cmap='gray')
        im2_overlay = axs[2].imshow(r2_masked, cmap='cividis', vmin=0, vmax=1)
        axs[2].set_title('Fit Quality (R²)', fontsize=24, fontweight='bold')
        axs[2].axis('off')
        r2_cbar = fig.colorbar(im2_overlay, ax=axs[2], fraction=0.046, pad=0.04)
        r2_cbar.set_label('$R^2$', fontsize=24, fontweight='bold')
        r2_cbar.ax.tick_params(labelsize=18)

        plt.tight_layout(rect=[0, 0, 1, 0.95])
        st.pyplot(fig)

        # Save
        image_path = os.path.join(save_path, 'Images')
        if not os.path.isdir(image_path):
        	os.makedirs(image_path)
        plt.savefig(os.path.join(image_path, f'{pool_name}_QUESP_Maps.png'), dpi=300, bbox_inches="tight")

        maps_to_return[pool_name] = {
            'fb_map': fb_masked,
            'kb_map': kb_masked,
            'r2_map': r2_masked
        }
    
    return maps_to_return


def calculate_quesp_stats(quesp_fits, t1_fits, statmin, statmax):
    """
    Calculates statistics (mean, std) for each ROI and chemical pool,
    including T1 values, and excludes outliers.
    """
    stats_list = []
    
    for roi_label, pools in quesp_fits.items():
        
        # --- HIGHLIGHTED CHANGE ---
        # Calculate T1 stats directly from the list of values
        if roi_label in t1_fits:
            # t1_fits[roi_label] is now the list of T1 values
            t1_values = np.array(t1_fits[roi_label])
            t1_valid = t1_values[~np.isnan(t1_values)]
            if t1_valid.size > 0:
                t1_min, t1_max = np.percentile(t1_valid, [statmin, statmax])
                t1_filtered = t1_valid[(t1_valid >= t1_min) & (t1_valid <= t1_max)]
                t1_mean = np.mean(t1_filtered)
                t1_std = np.std(t1_filtered)
            else:
                t1_mean, t1_std = np.nan, np.nan
        else:
            t1_mean, t1_std = np.nan, np.nan
        # --- END CHANGE ---
            
        for pool_name, params in pools.items():
            
            # Filter fb_values
            fb_values = np.array(params['fb_values'])
            fb_valid = fb_values[~np.isnan(fb_values)]
            if fb_valid.size > 0:
                fb_min, fb_max = np.percentile(fb_valid, [statmin, statmax])
                fb_filtered = fb_valid[(fb_valid >= fb_min) & (fb_valid <= fb_max)]
                fb_mean = np.mean(fb_filtered)
                fb_std = np.std(fb_filtered)
            else:
                fb_mean, fb_std = np.nan, np.nan

            # Filter kb_values
            kb_values = np.array(params['kb_values'])
            kb_valid = kb_values[~np.isnan(kb_values)]
            if kb_valid.size > 0:
                kb_min, kb_max = np.percentile(kb_valid, [statmin, statmax])
                kb_filtered = kb_valid[(kb_valid >= kb_min) & (kb_valid <= kb_max)]
                kb_mean = np.mean(kb_filtered)
                kb_std = np.std(kb_filtered)
            else:
                kb_mean, kb_std = np.nan, np.nan

            r2_values = np.array(params['r2_values'])
            r2_valid = r2_values[~np.isnan(r2_values)]
            r2_min, r2_max = np.percentile(r2_valid, [statmin, statmax])
            r2_filtered = r2_valid[(r2_valid >= r2_min) & (r2_valid <= r2_max)]
            r2_mean = np.mean(r2_filtered)

            stats_list.append({
                'ROI': roi_label,
                'Pool': pool_name,
                'T1a Mean (ms)': t1_mean,
                'T1a Std Dev (ms)': t1_std,
                'fb Mean': fb_mean,
                'fb Std Dev': fb_std,
                'kb Mean (s⁻¹)': kb_mean,
                'kb Std Dev (s⁻¹)': kb_std,
                'Mean R²': r2_mean
            })
            
    if not stats_list:
        return pd.DataFrame()

    # Create and format the DataFrame
    stats_df = pd.DataFrame(stats_list)
    return stats_df.set_index(['ROI', 'Pool'])