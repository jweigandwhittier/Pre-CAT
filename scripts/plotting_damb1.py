#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 22 12:29:12 2025
@author: jonah
"""
import os
import streamlit as st
import numpy as np 
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from mpl_toolkits.axes_grid1 import make_axes_locatable
from scipy import ndimage

def plot_damb1(b1_fits, reference_image, user_geometry, save_path):
    """
    Visualizes the B1 map, either raw or interpolated on a reference.
    """
    image_path = os.path.join(save_path, 'Images')
    os.makedirs(image_path, exist_ok=True)

    max_deviation = np.nanmax(np.abs(b1_fits - 1.0))
    vmin = 1.0 - max_deviation
    vmax = 1.0 + max_deviation

    # If no reference image is provided, just show the raw B1 map.
    if reference_image is None:
        fig, ax = plt.subplots(1, 1, figsize=(8, 8))    
        im = ax.imshow(b1_fits, cmap='RdBu_r')
        ax.set_title('Relative $B_1$ Map', fontsize=22, fontname='Arial', weight='bold')
        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="5%", pad=0.05)
        cbar = fig.colorbar(im, cax=cax)
        cbar.ax.tick_params(labelsize=18)
        cbar.set_label('$\\kappa$', fontsize=18)
        ax.axis('off')
        st.pyplot(fig)
        plt.savefig(os.path.join(image_path, 'Relative_B1_Map_Raw.png'), dpi=300, bbox_inches="tight")
        map_to_return = b1_fits
    else:
        # If a reference is provided, create a side-by-side comparison
        zoom_factors = (
            reference_image.shape[0] / b1_fits.shape[0],
            reference_image.shape[1] / b1_fits.shape[1]
        )
        b1_interp = ndimage.zoom(b1_fits, zoom=zoom_factors, order=1)
        
        # Apply mask based on organ type
        if user_geometry['aha']:
            combined_mask = user_geometry["masks"]["lv"]
            y_indices, x_indices = np.where(combined_mask)
            x_min, x_max = max(np.min(x_indices) - 20, 0), min(np.max(x_indices) + 20, combined_mask.shape[1])
            y_min, y_max = max(np.min(y_indices) - 20, 0), min(np.max(y_indices) + 20, combined_mask.shape[0])
        else: # 'Other'
            combined_mask = np.zeros_like(b1_interp, dtype=bool)
            for mask in user_geometry['masks'].values():
                combined_mask |= mask
            y_min, y_max = 0, b1_interp.shape[0]
            x_min, x_max = 0, b1_interp.shape[1]

        transparent_b1 = np.ma.masked_where(~combined_mask, b1_interp)
        fig, axs = plt.subplots(1, 2, figsize=(12, 6))
        fig.suptitle('$B_1$ Field Mapping', fontsize=26, fontname='Arial', weight='bold')

        axs[0].imshow(b1_fits, cmap='RdBu_r', vmin=vmin, vmax=vmax)
        axs[0].set_title('Raw Relative $B_1$', fontsize=20, fontname='Arial', weight='bold')
        axs[0].axis('off')

        axs[1].imshow(reference_image[y_min:y_max, x_min:x_max], cmap='gray')
        im1 = axs[1].imshow(transparent_b1[y_min:y_max, x_min:x_max], cmap='RdBu_r', alpha=0.9, vmin=vmin, vmax=vmax)
        axs[1].set_title('Anatomical Overlay', fontsize=20, fontname='Arial', weight='bold')
        axs[1].axis('off')

        divider = make_axes_locatable(axs[1])
        cax = divider.append_axes("right", size="5%", pad=0.05)
        cbar = fig.colorbar(im1, cax=cax)
        cbar.ax.tick_params(labelsize=18)
        cbar.set_label('$\\kappa$', fontsize=18)

        fig.tight_layout(rect=[0, 0, 1, 0.95])
        st.pyplot(fig)
        plt.savefig(os.path.join(image_path, 'Relative_B1_Maps.png'), dpi=300, bbox_inches="tight")
        map_to_return = transparent_b1
    return map_to_return

def plot_damb1_aha(b1_fits, reference_image, aha_segments, save_path):
    """
    Creates a boxplot of B1 flip angle error by AHA segment.
    """
    plot_path = os.path.join(save_path, 'Plots')
    os.makedirs(plot_path, exist_ok=True)
    
    zoom_factors = (
        reference_image.shape[0] / b1_fits.shape[0],
        reference_image.shape[1] / b1_fits.shape[1]
    )
    b1_interp = ndimage.zoom(b1_fits, zoom=zoom_factors, order=1)
    
    data = []
    for segment, coord_list in aha_segments.items():
        for (i, j) in coord_list:
            if i < b1_interp.shape[0] and j < b1_interp.shape[1]:
                val = b1_interp[i, j]
                data.append({'Segment': segment, '$\\kappa$': val})

    df = pd.DataFrame(data)

    sns.set(style="whitegrid")
    fig, ax = plt.subplots(figsize=(9, 6))
    palette = sns.color_palette("husl", len(df['Segment'].unique()))
    sns.boxplot(x='Segment', y='$\\kappa$', data=df, palette=palette, width=0.4, ax=ax)

    ax.axhline(1.0, color='black', linestyle='--', linewidth=1.5, alpha=0.7)

    ax.set_title('Relative Flip Angle by AHA Segment', fontsize=28, fontname='Arial', weight='bold')
    ax.set_xlabel('', fontsize=18)
    ax.set_ylabel('$\\kappa$', fontsize=16, fontname='Arial')
    ax.tick_params(labelsize=14)
    fig.tight_layout()

    plot_file = os.path.join(plot_path, 'B1_Boxplot.png')
    fig.savefig(plot_file, dpi=300)
    st.pyplot(fig)