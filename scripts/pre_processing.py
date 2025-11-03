#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun  9 15:07:25 2025

@author: jonah
"""
import numpy as np
import streamlit as st
from scipy.ndimage import uniform_filter1d
from sklearn.decomposition import PCA
import scripts.BrukerMRI as bruker 
from bart import bart 
from custom import st_functions
from custom.st_functions import time_it

# --- Constants (tunable) --- #
SPIKE_THRESHOLD_STD = 0.5
MOVING_AVG_WINDOW = 5

# --- Helper functions --- #
def recon(ksp, traj):
    """
    Function for reconstructing a single image using BART.
    """
    img = bart(1, 'nufft -i', traj, ksp)
    img = bart(1, 'rss 8', img)
    img = np.abs(img)
    img = np.squeeze(img)
    return img

@time_it
def motion_correction(ksp, traj, method, experiment_type):
    """
    Performs motion correction by identifying and deleting corrupted segments.
    """
    points, n_spokes, n_coils, n_offsets = ksp.shape
    seg = method['Num_Traj_per_Seg']
    offsets_ppm = np.round(method["Cest_Offsets"] / (method["PVM_FrqWork"][0]), 2)
    n_segments = n_spokes // seg
    if experiment_type == 'cest':
        ranges = [(-4.0, -1.4), (1.4, 4.0)]
        # Assign to 'indices' for consistency
        indices = np.where(
            (offsets_ppm >= ranges[0][0]) & (offsets_ppm <= ranges[0][1]) |
            (offsets_ppm >= ranges[1][0]) & (offsets_ppm <= ranges[1][1])
        )[0]
    elif experiment_type == 'wassr':
        indices = np.arange(n_offsets)
    counts = {}
    for index in indices:
        coil_spike_info = []
        for coil in range(n_coils):
            proj_coil = np.fft.fftshift(np.fft.fft(ksp[:, :, coil, index], axis=0), axes=0)
            mag_proj_coil = np.abs(proj_coil)
            reshaped_proj = mag_proj_coil[:, :n_segments * seg].reshape((points, n_segments, seg))
            segment_totals_coil = np.sum(reshaped_proj, axis=(0, 2))
            moving_avg = uniform_filter1d(segment_totals_coil, size=MOVING_AVG_WINDOW, mode='nearest')
            std_dev = np.std(segment_totals_coil - moving_avg)
            is_spike = segment_totals_coil < (moving_avg - SPIKE_THRESHOLD_STD * std_dev) if std_dev > 0 else np.zeros_like(segment_totals_coil, dtype=bool)
            total_magnitude = np.sum(moving_avg[is_spike] - segment_totals_coil[is_spike]) if np.any(is_spike) else 0
            coil_spike_info.append({'total_magnitude': total_magnitude, 'num_spikes': np.sum(is_spike)})
        best_coil_info = max(coil_spike_info, key=lambda x: x['total_magnitude'])
        counts[index] = best_coil_info['num_spikes']
    N_to_remove = max(counts.values()) if counts else 0
    st.warning(f"Motion correction will remove {N_to_remove} segments from each {experiment_type.upper()} offset image.")
    st_functions.message_logging(f"Motion correction removed {N_to_remove} segments from each {experiment_type.upper()} offset image.", msg_type='info')
    filtered_images_list = []
    loading_bar = st.progress(0, text="Applying motion correction and reconstructing...")
    for offset_idx in range(n_offsets):
        coil_spike_info_mc = []
        for coil in range(n_coils):
            proj_coil = np.fft.fftshift(np.fft.fft(ksp[:, :, coil, offset_idx], axis=0), axes=0)
            mag_proj_coil = np.abs(proj_coil)
            reshaped_proj = mag_proj_coil[:, :n_segments * seg].reshape((points, n_segments, seg))
            segment_totals_coil = np.sum(reshaped_proj, axis=(0, 2))
            moving_avg = uniform_filter1d(segment_totals_coil, size=MOVING_AVG_WINDOW, mode='nearest')
            severity = moving_avg - segment_totals_coil
            severity[severity < 0] = 0
            coil_spike_info_mc.append({'coil_index': coil, 'severity_data': severity})
        best_coil_idx = max(coil_spike_info_mc, key=lambda x: np.sum(x['severity_data']))['coil_index']
        final_severity = next(item['severity_data'] for item in coil_spike_info_mc if item['coil_index'] == best_coil_idx)
        indices_of_worst_segments = np.argsort(final_severity)[-N_to_remove:] if N_to_remove > 0 else []
        spokes_to_delete = []
        for seg_idx in indices_of_worst_segments:
            spokes_to_delete.extend(np.arange(seg_idx * seg, (seg_idx + 1) * seg))
        spokes_to_delete.sort()
        ksp_single_offset = ksp[..., offset_idx]
        ksp_deleted = np.delete(ksp_single_offset, spokes_to_delete, axis=1)
        traj_deleted = np.delete(traj, spokes_to_delete, axis=2)
        ksp_for_recon = np.expand_dims(ksp_deleted, axis=0)
        filtered_img_single = recon(ksp_for_recon, traj_deleted)
        filtered_images_list.append(filtered_img_single)
        progress = (offset_idx + 1) / n_offsets
        loading_bar.progress(progress, text=f"Applying motion correction: {offset_idx + 1}/{n_offsets}")
    loading_bar.progress(1.0, text="Motion correction complete.")
    return np.stack(filtered_images_list, axis=-1)

@time_it
def denoise_data(image_stack):
    """
    Denoises a stack of images using Global PCA.
    """
    height, width, n_offsets_s = image_stack.shape
    data_matrix = image_stack.reshape((height * width, n_offsets_s))
    pca = PCA()
    pca.fit(data_matrix)
    eigenvalues = pca.explained_variance_
    n_samples_m, n_features_n = data_matrix.shape
    indicator_values = []
    for i in range(1, n_features_n):
        numerator = np.sum(eigenvalues[i:])
        denominator = n_samples_m * ((n_features_n - (i-1))**5)
        indicator_values.append(np.sqrt(numerator / denominator) if denominator > 1e-9 else np.inf)
    n_components_to_keep = np.argmin(indicator_values) + 1
    st.warning(f"Denoising with {n_components_to_keep} components.")
    st_functions.message_logging(f"Denoised with {n_components_to_keep} components.", msg_type='info')
    pca_denoising = PCA(n_components=n_components_to_keep)
    transformed_data = pca_denoising.fit_transform(data_matrix)
    denoised_data_matrix = pca_denoising.inverse_transform(transformed_data)
    return denoised_data_matrix.reshape((height, width, n_offsets_s))

# --- Main pre-processing function --- #
def run_radial_preprocessing(directory, num_exp, use_pca, experiment_type = 'cest'):
    """
    Main pipeline for radial pre-processing.
    Loads data, performs motion correction, and optionally denoises.
    """
    # 1. Load Data
    exp = bruker.ReadExperiment(directory, num_exp)
    ksp = exp.GenerateKspace()
    traj = exp.traj
    method = exp.method
    offsets = np.round(method["Cest_Offsets"] / (method["PVM_FrqWork"][0]), 2)
    
    # 2. Motion Correction
    motion_corrected_stack = motion_correction(ksp, traj, method, experiment_type)
    
    # 3. Optional Denoising
    final_stack = motion_corrected_stack
    if use_pca:
        st.info("Denoising data with PCA...")
        final_stack = denoise_data(motion_corrected_stack)

    return {"imgs": final_stack, "offsets": offsets}