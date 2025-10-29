#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 22 12:29:12 2025

@author: jonah
"""
import os
import itertools
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from matplotlib.patches import Patch
from scipy.signal import medfilt2d
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.colors import Normalize

def pixelwise_mapping(image, pixelwise_fits, user_geometry, custom_contrasts, smoothing_filter, save_path):
    """
    Generates and displays pixelwise CEST contrast maps.
    """
    if user_geometry['aha']:
        masks = {"lv": user_geometry["masks"]["lv"]}
        y_indices, x_indices = np.where(masks["lv"])
        x_min, x_max = max(np.min(x_indices) - 20, 0), min(np.max(x_indices) + 20, masks["lv"].shape[1])
        y_min, y_max = max(np.min(y_indices) - 20, 0), min(np.max(y_indices) + 20, masks["lv"].shape[0])
    else:
        masks = user_geometry["masks"]
        x_min, x_max = 0, image.shape[1] 
        y_min, y_max = 0, image.shape[0]
    image_path = os.path.join(save_path, 'Images')
    os.makedirs(image_path, exist_ok=True)
    contrasts_to_plot = custom_contrasts if custom_contrasts is not None else ['Amide', 'Creatine', 'NOE (-3.5 ppm)', 'NOE (-1.6 ppm)']
    contrasts_to_plot = ['MT'] + contrasts_to_plot
    contrast_images = {contrast: np.full_like(image, np.nan, dtype=float) for contrast in contrasts_to_plot}
    for label, mask in masks.items():
        data = pixelwise_fits.get(label, [])
        for contrast in contrasts_to_plot:
            contrast_list = [datum["Contrasts"].get(contrast, np.nan) for datum in data]
            mask_indices = np.argwhere(mask)
            for idx, (i, j) in enumerate(mask_indices):
                if idx < len(contrast_list):
                    contrast_images[contrast][i, j] = contrast_list[idx]
    if smoothing_filter:
        for contrast in contrast_images:
            contrast_images[contrast] = medfilt2d(contrast_images[contrast], kernel_size=3)

    def plot_contrast(base_image, contrast_image, title):
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.imshow(base_image[y_min:y_max,x_min:x_max], cmap="gray")
        im = ax.imshow(contrast_image[y_min:y_max,x_min:x_max], cmap="viridis", alpha=0.9, 
                       norm=Normalize(vmin=0, vmax=np.nanmax(contrast_image)))
        ax.set_title(title, fontsize=28, weight='bold', fontname='Arial')
        ax.axis("off")
        cbar = fig.colorbar(im, ax=ax, shrink=0.8)
        cbar.set_label("CEST Contrast (%)", fontsize=16)
        cbar.ax.tick_params(labelsize=14)
        return fig
    st.subheader("Pixelwise Maps")
    contrasts = list(contrast_images.values())
    titles = list(contrast_images.keys())
    for i in range(0, len(contrasts), 2):  # Iterate in steps of 2
        with st.container():
            cols = st.columns(2)
            with cols[0]:
                fig = plot_contrast(image, contrasts[i], titles[i])
                plt.savefig(image_path + '/' + titles[i] + '_Contrast_Map.png', dpi=300, bbox_inches="tight")
                st.pyplot(fig)
            # Check if i+1 is a valid index
            if i + 1 < len(contrasts):
                with cols[1]:
                    fig = plot_contrast(image, contrasts[i + 1], titles[i + 1])
                    plt.savefig(image_path + '/' + titles[i + 1] + '_Contrast_Map.png', dpi=300, bbox_inches="tight")
                    st.pyplot(fig)
    return contrast_images

def show_segmentation(image, mask, labeled_segments, save_path):
    """
    Displays the AHA segmentation on a reference image.
    """
    # Get vars from session state
    image_path = os.path.join(save_path, 'Images')
    if not os.path.isdir(image_path):
        os.makedirs(image_path)
    # Initialize an empty RGB array for the segmentation
    segmented = np.zeros((image.shape[0], mask.shape[1], 3), dtype=np.uint8)
    # Zoom into the region based on the mask with a margin of ±20 pixels
    y_indices, x_indices = np.where(mask)
    x_min, x_max = max(np.min(x_indices) - 20, 0), min(np.max(x_indices) + 20, mask.shape[1])
    y_min, y_max = max(np.min(y_indices) - 20, 0), min(np.max(y_indices) + 20, mask.shape[0])
    # Define segment colors
    coords = {
        'Inferoseptal': (255, 0, 0),      # red       inferoseptal
        'Anteroseptal': (0, 255, 0),      # green     anteroseptal
        'Anterior': (0, 0, 255),          # blue      anterior
        'Anterolateral': (255, 165, 0),   # orange    anterolateral
        'Inferolateral': (255, 255, 100), # yellow    inferolateral
        'Inferior': (128, 0, 128)         # purple    inferior
    }
    # Apply colors to each segment
    for segment, color in coords.items():
        for coord in labeled_segments[segment]:
            segmented[coord[0], coord[1]] = np.array(color, dtype=np.uint8)
    # Set up subplots for the original image and segmentation overlay
    fig, ax = plt.subplots(1, 1, figsize=(9, 12))
    # Display the cropped original image with segmentation overlay
    ax.imshow(image[y_min:y_max, x_min:x_max], cmap='gray')
    ax.imshow(segmented[y_min:y_max, x_min:x_max], alpha=0.5)
    # Create legend for segmentation
    legend_elements = [Patch(facecolor=np.array(color) / 255, edgecolor='black', label=label) for label, color in coords.items()]
    ax.legend(handles=legend_elements, loc="center left", bbox_to_anchor=(1, 0.5), fontsize = 24)
    # Remove axis labels
    ax.axis('off')
    st.subheader('AHA Segmentation')
    st.pyplot(fig)
    plt.savefig(image_path + '/AHA_Segmentation.png', dpi = 300, bbox_inches="tight")
    
def show_rois(image, masks, save_path):
    """
    Displays drawn ROIs on reference image.
    """
    image_path = os.path.join(save_path, 'Images')
    if not os.path.isdir(image_path):
        os.makedirs(image_path)
    colors = plt.cm.get_cmap('tab20', len(masks))
    segmented = np.zeros((image.shape[0], image.shape[1], 3), dtype=np.uint8)
    for i, (label, mask) in enumerate(masks.items()):
        y_indices, x_indices = np.where(mask)
        segmented[y_indices, x_indices] = (np.array(colors(i)[:3]) * 255).astype(np.uint8)
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(image, cmap='gray')
    ax.imshow(segmented, alpha=0.5)
    # Create legend for ROIs
    legend_elements = [
        Patch(facecolor=np.array(colors(i)[:3]), edgecolor='black', label=label) 
        for i, label in enumerate(masks.keys())
    ]
    ax.legend(handles=legend_elements, loc="center left", bbox_to_anchor=(1, 0.5), fontsize=15)
    ax.axis('off')
    ax.set_title('ROI Key', fontsize=28, fontweight='bold')
    # Add tight_layout for consistent spacing
    fig.tight_layout()
    st.pyplot(fig)
    plt.savefig(os.path.join(image_path, 'ROIs.png'), dpi=300, bbox_inches="tight")

def plot_zspec(fits, save_path):
    """
    Generate and display Z-spectra and Lorentzian difference plots for each ROI.
    """
    roi_count = len(fits)
    plot_path = os.path.join(save_path, 'Plots')
    if not os.path.isdir(plot_path):
        os.makedirs(plot_path)
    # Dynamically calculate number of rows and columns
    n_cols = 3
    n_rows = -(-roi_count // n_cols)  # Ceiling division for rows

    # Z-Spectra Plots
    st.subheader("Z-Spectra")
    for row in range(n_rows):
        cols = st.columns(min(n_cols, roi_count - row * n_cols))
        for i, roi in enumerate(list(fits.keys())[row * n_cols:(row + 1) * n_cols]):
            with cols[i]:
                fit = fits[roi]
                data_dict = fit['Data_Dict']
                OffsetsInterp = data_dict['Offsets_Interp']
                Offsets = data_dict['Offsets_Corrected']
                Spectrum = data_dict['Zspec']
                Fits = {key: value for key, value in data_dict.items() if 'Fit' in key}
                # Plot Z-Spectra
                fig, ax = plt.subplots(figsize=(12, 10))
                ax.plot(Offsets, Spectrum, '.', markersize=15, fillstyle='none', color='black', label="Raw")
                total_fit = np.zeros_like(next(iter(Fits.values())))
                contrast_colors = {
                    'Water_Fit': '#0072BD',
                    'MT_Fit': '#EDB120',
                    'NOE (-3.5 ppm)_Fit': '#A6761D',
                    'Amide_Fit': '#7E2F8E',
                    'Amine_Fit': '#F8961E',  
                    'Creatine_Fit': '#6F1D1B',  
                    'Hydroxyl_Fit': '#4DBEEE',
                    'NOE (-1.6 ppm)_Fit':"#E144C4"    
                }
                # Get a color cycle for any remaining fits
                color_cycle = itertools.cycle(plt.get_cmap('viridis').colors)  # Change colormap if needed
                for contrast, fit in Fits.items():
                    label = contrast.replace('_Fit', '')  # Extract the label
                    color = contrast_colors.get(contrast, next(color_cycle))  # Use predefined color or cycle
                
                    ax.plot(OffsetsInterp, 1 - fit, linewidth=4, color=color, label=label)
                    total_fit += fit
                ax.plot(OffsetsInterp, 1 - total_fit,
                        linewidth=4, color='#D95319', label="Fit")
                ax.legend(fontsize=16)
                ax.invert_xaxis()
                ax.tick_params(axis='both', which='major', labelsize=16)
                ax.set_ylim([0, 1])
                ax.set_xlabel("Offset frequency (ppm)", fontsize=18, fontname='Arial')
                ax.set_ylabel("$S/S_0$", fontsize=18, fontname='Arial')
                fig.suptitle(roi, fontsize=28, weight='bold', fontname='Arial')
                plt.grid(False)
                st.pyplot(fig)
                plt.savefig(plot_path + '/' + roi + '_Zspec.png', dpi = 300, bbox_inches="tight")

    # Lorentzian Difference Plots
    st.subheader("Lorentzian Difference Plots")
    for row in range(n_rows):
        cols = st.columns(min(n_cols, roi_count - row * n_cols))
        for i, roi in enumerate(list(fits.keys())[row * n_cols:(row + 1) * n_cols]):
            with cols[i]:
                fit = fits[roi]
                data_dict = fit['Data_Dict']
                OffsetsInterp = data_dict['Offsets_Interp']
                Offsets = data_dict['Offsets_Corrected']
                Lorentzian_Difference = data_dict['Lorentzian_Difference']
                # Plot Lorentzian Difference
                fig, ax = plt.subplots(figsize=(12, 10))
                ax.fill_between(Offsets, Lorentzian_Difference * 100, 0, color='gray', alpha=0.5, label="Raw")
                total_fit = np.zeros_like(next(iter(Fits.values())))
                total_fit_noe = np.zeros_like(next(iter(Fits.values())))
                # Automatically plot available fits with assigned colors
                for contrast in data_dict.keys():
                    if 'Fit' in contrast and contrast not in ['Water_Fit', 'MT_Fit']:
                        color = contrast_colors.get(contrast, '#000000')  # Default to black if missing
                        ax.plot(OffsetsInterp, data_dict[contrast] * 100, linewidth=4, color=color, label=contrast.replace("_Fit", ""))
                        if 'NOE' not in contrast:
                            total_fit += data_dict[contrast] * 100
                        else:
                            total_fit_noe += data_dict[contrast] * 100
                ax.plot(OffsetsInterp, total_fit, linewidth=4, color='#D95319', label="CEST Fit")
                ax.plot(OffsetsInterp, total_fit_noe, linewidth=4, color='#00876C', label="rNOE Fit")
                ax.legend(fontsize=16)
                ax.invert_xaxis()
                ax.tick_params(axis='both', which='major', labelsize=16)
                ax.set_xlabel("Offset frequency (ppm)", fontsize=18, fontname='Arial')
                ax.set_ylabel("CEST Contrast (%)", fontsize=18, fontname='Arial')
                fig.suptitle(roi, fontsize=28, weight='bold', fontname='Arial')
                plt.grid(False)
                st.pyplot(fig)
                plt.savefig(plot_path + '/' + roi + '_Lorentzian_Dif.png', dpi=300, bbox_inches="tight")