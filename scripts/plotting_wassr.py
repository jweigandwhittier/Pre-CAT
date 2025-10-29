#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 24 16:21:48 2024

@author: jonah
"""
import os
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from mpl_toolkits.axes_grid1 import make_axes_locatable

def plot_wassr_aha(wassr_aha_fits, save_path):
    plot_path = os.path.join(save_path, 'Plots')
    if not os.path.isdir(plot_path):
        os.makedirs(plot_path)
    fits = {k: v for k, v in wassr_aha_fits.items() if "lv" not in k.lower()}
    data = []
    for segment, b0_values in fits.items():
        for val in b0_values:
            data.append({'Segment': segment, 'B0 Shift (ppm)': val})
    df = pd.DataFrame(data)

    sns.set(style="whitegrid")
    fig, ax = plt.subplots(figsize=(9, 6))  
    palette = sns.color_palette("husl", len(df['Segment'].unique()))
    sns.boxplot(x='Segment', y='B0 Shift (ppm)', data=df, palette=palette, width=0.4, ax=ax)

    ax.set_title('B$_0$ Shift by AHA Segment', fontsize=28, fontname='Arial', weight='bold')
    ax.set_xlabel('', fontsize=18)

    ax.set_ylabel('B$_0$ Shift (ppm)', fontsize=16, fontname='Arial')
    ax.tick_params(labelsize=14)
    fig.tight_layout()

    plot_file = os.path.join(plot_path, 'WASSR_Boxplot.png')
    fig.savefig(plot_file, dpi=300)
    st.pyplot(fig) 

def plot_wassr(image, user_geometry, wassr_masked_fits, save_path, wassr_full_map = None):
    """
    Visualizes WASSR B0 map. Handles both full map and masked-only data.
    """
    image_path = os.path.join(save_path, 'Images')
    if not os.path.isdir(image_path):
        os.makedirs(image_path)
        
    # Case 1: Full B0 map is available
    if wassr_full_map is not None:
        # Create the masked overlay from the full map
        masked_b0 = np.zeros_like(wassr_full_map, dtype=float)
        if user_geometry['aha']:
            segment_masks = user_geometry["aha"]
            for label, coord_list in segment_masks.items():
                for i, j in coord_list:
                    masked_b0[i, j] = wassr_full_map[i, j]
        else:
            for mask in user_geometry["masks"].values():
                masked_b0[mask] = wassr_full_map[mask]

        y_min, y_max, x_min, x_max = 0, image.shape[0], 0, image.shape[1]
        if user_geometry['aha']:
            lv_mask = user_geometry["masks"]["lv"]
            y_indices, x_indices = np.where(lv_mask)
            x_min, x_max = max(np.min(x_indices) - 20, 0), min(np.max(x_indices) + 20, lv_mask.shape[1])
            y_min, y_max = max(np.min(y_indices) - 20, 0), min(np.max(y_indices) + 20, lv_mask.shape[0])

        transparent_b0_overlay = np.ma.masked_where(masked_b0 == 0, masked_b0)

        fig, axs = plt.subplots(1, 2, figsize=(12, 6))
        fig.suptitle('WASSR B$_0$ Map Visualization', fontsize=26, fontname='Arial', weight='bold')
        
        v_abs_max = np.nanmax(np.abs(wassr_full_map))
        vmin, vmax = -v_abs_max, v_abs_max
        
        im0 = axs[0].imshow(wassr_full_map, cmap='BrBG', vmin=vmin, vmax=vmax)
        axs[0].set_title('Full B$_0$ Map', fontsize=20, fontname='Arial', weight='bold')
        axs[0].axis('off')
        
        axs[1].imshow(image[y_min:y_max, x_min:x_max], cmap='gray')
        im1 = axs[1].imshow(transparent_b0_overlay[y_min:y_max, x_min:x_max], cmap='BrBG', alpha=0.9, vmin=vmin, vmax=vmax)
        axs[1].set_title('Masked B$_0$ on Reference', fontsize=20, fontname='Arial', weight='bold')
        axs[1].axis('off')

        divider = make_axes_locatable(axs[1])
        cax = divider.append_axes("right", size="5%", pad=0.05)
        cbar = fig.colorbar(im0, cax=cax)
        cbar.ax.tick_params(labelsize=14)
        cbar.set_label('B$_0$ Shift (ppm)', fontname='Arial', fontsize=16)

        fig.tight_layout(rect=[0, 0, 1, 0.95])

        final_map_to_return = transparent_b0_overlay
        
    # Case 2: Only masked data is available
    else:
        b0_image = np.zeros_like(image, dtype='float')
        if user_geometry['aha']:
            lv_mask = user_geometry["masks"]["lv"]
            y_indices, x_indices = np.where(lv_mask)
            x_min, x_max = max(np.min(x_indices) - 20, 0), min(np.max(x_indices) + 20, lv_mask.shape[1])
            y_min, y_max = max(np.min(y_indices) - 20, 0), min(np.max(y_indices) + 20, lv_mask.shape[0])
            segment_masks = user_geometry["aha"]
            for label, coord_list in segment_masks.items():
                data = wassr_masked_fits.get(label, [])
                for idx, (i, j) in enumerate(coord_list):
                    if idx < len(data):
                        b0_image[i, j] = data[idx]
        else:
            masks = user_geometry["masks"]
            x_min, x_max = 0, image.shape[1]
            y_min, y_max = 0, image.shape[0]
            for label, mask in masks.items():
                data = wassr_masked_fits.get(label, [])
                mask_indices = np.argwhere(mask)
                for idx, (i, j) in enumerate(mask_indices):
                    if idx < len(data):
                        b0_image[i, j] = data[idx]

        transparent_b0 = np.ma.masked_where(b0_image == 0, b0_image)
        fig, ax = plt.subplots(1, 1, figsize=(6, 6))
        ax.imshow(image[y_min:y_max, x_min:x_max], cmap='gray')
        v_abs_max = np.nanmax(np.abs(transparent_b0))
        vmin, vmax = -v_abs_max, v_abs_max
        im = ax.imshow(transparent_b0[y_min:y_max, x_min:x_max], cmap='BrBG', alpha=0.9, vmin=vmin, vmax=vmax)
        ax.set_title('WASSR Map', fontsize=28, fontname='Arial', weight='bold')
        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="5%", pad=0.05)
        cbar = fig.colorbar(im, cax=cax)
        cbar.ax.tick_params(labelsize=14)
        cbar.set_label('B$_0$ Shift (ppm)', fontname='Arial', fontsize=16)
        ax.axis('off')
        final_map_to_return = transparent_b0

    st.pyplot(fig)
    plt.savefig(os.path.join(image_path, 'B0_Map_Comparison.png'), dpi=300, bbox_inches="tight")
    return final_map_to_return