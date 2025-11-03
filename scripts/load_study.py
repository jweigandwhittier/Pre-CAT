#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb  6 11:44:38 2024

@author: jonah
"""
import os
import sys
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from scipy.interpolate import interpn
from custom import st_functions
from custom.st_functions import time_it

if 'BART_TOOLBOX_PATH' in os.environ and os.path.exists(os.environ['BART_TOOLBOX_PATH']):
	sys.path.append(os.path.join(os.environ['BART_TOOLBOX_PATH'], 'python'))
elif 'TOOLBOX_PATH' in os.environ and os.path.exists(os.environ['TOOLBOX_PATH']):
	sys.path.append(os.path.join(os.environ['TOOLBOX_PATH'], 'python'))
else:
	raise RuntimeError("BART_TOOLBOX_PATH is not set correctly!")

from bart import bart
import scripts.BrukerMRI as bruker

# --- Reconstruction and data loading functions --- #
def load_bruker_img(num, directory):
    """
    Loads a single Bruker image stack directly (processed image data).
    """
    data = bruker.ReadExperiment(directory, num)
    imgs = data.proc_data
    imgs = np.rot90(imgs, k=2) # Rotates image, may not be necessary 
    return imgs

@time_it    
def recon_bruker(num, directory):
    """
    Loads CEST data from Bruker processed image data.
    """
    data = bruker.ReadExperiment(directory, num)
    try:
        offsets = np.round(data.method["Cest_Offsets"] / data.method["PVM_FrqWork"][0], 1)
    except KeyError:
        offsets = None # This handles the CEST-MRF case
    imgs = data.proc_data
    #visu = data.visu
    # Flips data to match raw (NU)FFT reconstruction, this DOES NOT ALWAYS WORK (return to this)
    #orientation = np.array(visu['VisuCoreOrientation'].reshape(3,3))
    #flip_y = orientation[0, 1] < 0 
    #if flip_y == True:
        #imgs = np.flip(imgs, axis=1)
    # End flipping
    study = {"imgs": imgs, "offsets": offsets}
    return study

@time_it
def recon_bart(num, directory):
    """
    Reconstructs radial CEST data using BART.
    """
    data = bruker.ReadExperiment(directory, num)
    imgs = []
    offsets = np.round(data.method["Cest_Offsets"] / data.method["PVM_FrqWork"][0], 2)
    traj = data.traj
    ksp = data.GenerateKspace()
    loading_bar = st.progress(0, text="Reconstructing images...")
    for i in range(len(offsets)):
        offset_ksp = ksp[:, :, :, i]
        offset_ksp = np.expand_dims(offset_ksp, axis=0)
        img = bart(1, 'nufft -i', traj, offset_ksp)
        img = bart(1, 'rss 8', img)
        img = np.abs(img)
        imgs.append(img)
        loading_bar.progress((i + 1) / len(offsets), text="Reconstructing images...")
        if i+1 == len(offsets):
            loading_bar.progress((i + 1) / len(offsets), text="Reconstruction complete.")
    imgs = np.stack(imgs, axis=2)
    study = {"imgs": imgs, "offsets": offsets}
    return study

@time_it
def recon_quesp(num, directory):
    """
    Retrieves and organizes QUESP processed image data.
    """
    # 1. Retrieve images and relevant parameters
    data = bruker.ReadExperiment(directory, num)
    images = data.proc_data
    freq = data.method['PVM_FrqWork'][0]
    powers = data.method['Fp_SatPows']
    tsats = data.method['Fp_SatDur']
    trecs = data.method['Fp_TRDels']
    offsets = data.method['Fp_SatOffset']
    offsets_ppm = np.round(offsets / freq, 2)
    study = {"imgs": images, "powers": powers, "tsats": tsats, "trecs": trecs, "offsets": offsets_ppm}
    return study

def process_quesp(recon_data):
    """
    Performs normalization steps on raw QUESP data.
    """
    images = recon_data["imgs"]
    powers = recon_data["powers"]
    tsats = recon_data["tsats"]
    trecs =  recon_data["trecs"]
    offsets_ppm = recon_data["offsets"]
    # 1. Normalize
    THRESHOLD_PPM = 15
    ref_index = np.where((offsets_ppm > THRESHOLD_PPM) | (powers == 0))[0]
    for i in range(len(ref_index)):
        m0 = images[:, :, ref_index[i]]
        if i < len(ref_index) - 1:
            next_index = ref_index[i + 1]
        else:
            next_index = images.shape[2]
        for j in range(ref_index[i] + 1, next_index):
            images[:, :, j] /= m0
    # 2. Calculate MTRasym and MTRrex
    images = np.nan_to_num(images)
    mtr_maps = calc_mtr(images, powers, tsats, trecs, offsets_ppm)
    reference = images[:,:,ref_index[0]]
    study = {"mtr_maps": mtr_maps, "m0": reference}
    return study

def calc_mtr(images, powers, tsats, trecs, offsets_ppm):
    """
    Calculates MTRasym/MTRrex maps for QUESP.
    """
    mtr_maps = []
    unique_powers = sorted([p for p in np.unique(powers) if p > 0])
    positive_offsets = sorted([o for o in np.unique(offsets_ppm) if o > 0])
    for power in unique_powers:
        for pos_offset in positive_offsets:
            pos_idx = np.where((powers == power) & (offsets_ppm == pos_offset))[0]
            neg_idx = np.where((powers == power) & (offsets_ppm == -pos_offset))[0]
            pos_img = images[:,:,pos_idx]
            neg_img = images[:,:,neg_idx]
            tsat = tsats[pos_idx[0]]
            trec = trecs[pos_idx[0]]
            mtr_asym_img = np.squeeze(neg_img - pos_img)
            mtr_rex_img = np.squeeze(1/pos_img - 1/neg_img)
            map_data = {
                    'mtr_asym': mtr_asym_img, 
                    'mtr_rex': mtr_rex_img,
                    'b1': power, 
                    'tsat': tsat,
                    'trec': trec,
                    'offset': pos_offset
                }
            mtr_maps.append(map_data)
    return mtr_maps

@time_it
def recon_t1map(num, directory):
    """
    Load images and TRs for T1 mapping from VTR acquisition.
    """
    data = bruker.ReadExperiment(directory, num)
    return {"imgs": data.proc_data, "trs": data.method['MultiRepTime']}

@time_it
def recon_damb1(directory, theta_path, two_theta_path):
    """
    Reconstructs B1 maps from two double angle (DAMB1) experiments.
    """
    exp_theta = bruker.ReadExperiment(directory, theta_path)
    exp_two_theta = bruker.ReadExperiment(directory, two_theta_path)
    theta = np.squeeze(exp_theta.proc_data)
    two_theta = np.squeeze(exp_two_theta.proc_data)
    #visu = exp_theta.visu
    flip = exp_theta.acqp['ACQ_flip_angle']
    #orientation = np.array(visu['VisuCoreOrientation'].reshape(3,3))
    #flip_y = orientation[0, 1] < 0
    #if flip_y == True:
        #theta = np.flip(theta, axis=1)
        #two_theta = np.flip(two_theta, axis=1)
    imgs = np.stack([theta, two_theta], axis=-1)
    study = {"imgs": imgs, "nominal_flip": flip}
    return study

# --- Image processing functions --- #
def rotate_image_stack(image_stack, k):
    """
    Rotates a 3D image stack k * 90deg counterclockwise.
    """
    return np.rot90(image_stack, k=k, axes=(0, 1))

def flip_image_stack_vertically(image_stack):
    """
    Flips a 3D image stack horizontally.
    """
    return np.flip(image_stack, axis=1)

@time_it
def thermal_drift(recon_data):
    """
    Performs thermal drift correction on an image stack.
    Accepts a dictionary with 'imgs' and 'offsets' and returns an updated one.
    """
    THRESHOLD_PPM = 15
    images = recon_data['imgs']
    offsets = recon_data['offsets']
    ref_index = np.where(offsets > THRESHOLD_PPM)[0]
    m0 = images[:, :, ref_index]
    corrected_offsets = np.delete(offsets, ref_index)
    corrected_images = np.delete(images, ref_index, axis=2)
    if np.size(ref_index) > 1:
        # Interpolation logic
        m0_indices = ref_index
        points = (np.arange(images.shape[0]), np.arange(images.shape[1]), m0_indices)
        # 2. The query points are the indices of the 'corrected' images
        all_indices = np.arange(len(offsets))
        corrected_indices = np.delete(all_indices, ref_index)
        # 3. Create the meshgrid of query points
        xi, yi, fi = np.meshgrid(np.arange(images.shape[0]), np.arange(images.shape[1]), corrected_indices, indexing='ij')
        query_points = np.stack((xi, yi, fi), axis=-1)
        # 4. Interpolate m0 data at the query points
        try:
            m0_interp = interpn(points, m0, query_points)
        except ValueError:
            st_functions.message_logging(
                        f"Interpolation failed. Falling back to normalization by single $S_0$ image.",
                        msg_type='warning'
                    )
            corrected_images = np.nan_to_num(corrected_images / m0[:, :, 0][..., np.newaxis])
            return {
                "imgs": corrected_images, "offsets": corrected_offsets,
                "m0": np.squeeze(m0[:, :, 0])
            }
        corrected_images = np.nan_to_num(corrected_images / m0_interp)
        return {
            "imgs": corrected_images, "offsets": corrected_offsets,
            "m0": m0[:, :, 0], "m0_final": m0[:, :, -1], "m0_interp": m0_interp
        }
    else:
        # Simple normalization
        corrected_images = np.nan_to_num(corrected_images / m0)
        return {
            "imgs": corrected_images, "offsets": corrected_offsets,
            "m0": np.squeeze(m0[:, :, 0])
        }

# --- Interactive UI functions --- #
def show_rotation_ui(image_stack, exp_type):
    """
    Handles the Streamlit UI for interactively rotating and flipping an image.
    Returns a tuple (k, flip_vertically) once finalized.
    """
    st.subheader(f"Orient {exp_type} Data")
    # Use a separate key for each experiment type to avoid state conflicts
    rot_stage_key = f'rotation_stage_{exp_type}'
    selected_rot_key = f'selected_rotation_{exp_type}'
    flip_key = f'flip_{exp_type}'
    # Initialize states if they don't exist
    if rot_stage_key not in st.session_state:
        st.session_state[rot_stage_key] = 'select_transform'
    if selected_rot_key not in st.session_state:
        st.session_state[selected_rot_key] = 0
    if flip_key not in st.session_state:
        st.session_state[flip_key] = False
    # 1. Select rotation and flip
    if st.session_state[rot_stage_key] == 'select_transform':
        fig, ax = plt.subplots()
        ax.imshow(image_stack[:, :, 0], cmap='gray')
        ax.axis('off')
        st.pyplot(fig, use_container_width=False)
        selected_k = st.selectbox(
            'Select 90-degree counterclockwise rotations:',
            [0, 1, 2, 3],
            index=st.session_state[selected_rot_key],
            key=f"rotation_select_{exp_type}"
        )
        st.session_state[selected_rot_key] = selected_k
        # Add a checkbox for the vertical flip
        flip_vertical = st.checkbox(
            "Flip image horizontally?",
            value=st.session_state[flip_key],
            key=f"flip_checkbox_{exp_type}"
        )
        st.session_state[flip_key] = flip_vertical
        if st.button('Preview Transform', key=f"preview_button_{exp_type}"):
            st.session_state[rot_stage_key] = 'confirm_transform'
            st.rerun()
    # 2. Confirm transform
    elif st.session_state[rot_stage_key] == 'confirm_transform':
        # Apply rotation
        transformed_img = rotate_image_stack(image_stack, st.session_state[selected_rot_key])
        # Apply flip if selected
        if st.session_state[flip_key]:
            transformed_img = flip_image_stack_vertically(transformed_img)
        st.write("Is this orientation correct?")
        fig, ax = plt.subplots()
        ax.imshow(transformed_img[:, :, 0], cmap='gray')
        ax.axis('off')
        st.pyplot(fig)
        col1, col2 = st.columns(2)
        with col1:
            finalize_button = st.button('Finalize Orientation', key=f"submit_transform_{exp_type}")
        with col2:
            go_back_button = st.button('Go Back', key=f"retry_transform_{exp_type}")
        if finalize_button:
            st.session_state[rot_stage_key] = 'finalized'
            st_functions.message_logging(f"{exp_type} orientation finalized!")
            st.rerun()
        if go_back_button:
            st.session_state[rot_stage_key] = 'select_transform'
            st.rerun()
    # 3. Return the transform values only when finalized
    if st.session_state[rot_stage_key] == 'finalized':
        return (st.session_state[selected_rot_key], st.session_state[flip_key])
    return None # Return None if not yet finalized