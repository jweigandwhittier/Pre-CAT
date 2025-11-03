#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul 10 12:58:21 2025

@author: jonah
"""
import numpy as np
from scipy.optimize import curve_fit
from sklearn.metrics import r2_score
import pandas as pd
import streamlit as st
from custom import st_functions
from custom.st_functions import time_it

# --- Constants --- #
# Proton gyromagnetic ratio (rad/T/s)
GAMMA = 2.675221e8

# --- Dictionary to match CEST pool to frequency offset. Feel free to add to/update this! --- #
pool_dict = {
    'Cr': 2.0,
    'PCr': 2.6,
    'Amide': 3.5,
    'Amine': 2.5,
    'Glutamate': 3.0,
}

# --- Model definitions --- #
def standard_model(b1, r1, tsat, trecs, fb, kb):
    """
    MODIFIED: This model now handles a series of recovery times (trecs).
    The initial magnetization (Zi) for the first scan is 1. For subsequent scans,
    Zi is calculated based on the preceding trec.
    """
    omega = GAMMA * b1

    # Calculate Zi for each scan based on the recovery from the *previous* scan
    zi_values = np.ones_like(b1) # Initialize all Zi to 1
    # For scans after the first, calculate Zi based on the preceding trec
    if len(trecs) > 1:
        zi_values[1:] = 1 - np.exp(-r1 * trecs[:-1])
    alpha = omega**2 / (omega**2 + kb**2)
    return (fb * kb * alpha) / (r1 + fb * kb * alpha) + (zi_values - 1) * np.exp(-r1 * tsat) - (zi_values - r1 / (r1 + fb * kb * alpha)) * np.exp(-(r1 + fb * kb * alpha) * tsat)

def inverse_model(b1, r1, fb, kb):
    omega = GAMMA * b1
    return 1 / r1 * fb * kb * omega**2 / (omega**2 + kb**2)

def omega_plot(b1, r1, fb, kb):
    omega = GAMMA * b1
    return r1 / (fb * kb) + r1 * kb / (fb * omega**2)

def t1_model(tr, m0, t1):
    return m0 * (1 - np.exp(-tr / t1))

# --- Misc. functions -- #
def calc_proton_volume_fraction(conc, num_protons):
    """
    Calculates proton volume fraction from concentration and number of labile protons, assuming 55.5 M water
    """
    return (num_protons * conc) / (111e3)

# --- Fitting functions --- #
@time_it
def fit_quesp_map(quesp_data, t1_pixel_fits, masks, fit_type, fixed_fb=None):
    """
    Performs a pixel-wise QUESP fit for each ROI, with a single unified progress bar.
    """
    if not quesp_data:
        st.error("QUESP data is empty. Cannot perform fit.")
        return {}

    df = pd.DataFrame(quesp_data['mtr_maps'])

    # Check for constant saturation time
    if df['tsat'].nunique() > 1:
        st.error(
            "Saturation times ($t_{sat}$) are not constant. This may be a QUEST "
            "experiment, which is not currently supported. Please use data "
            "with a single $t_{sat}$ value for QUESP analysis."
        )
        return {}

    unique_offsets = df['offset'].unique()
    results_by_roi = {}

    # Pre-calculate the total number of fits for the progress bar
    total_fits = sum(len(t1_pixel_fits.get(label, [])) for label in masks) * len(unique_offsets)
    if total_fits == 0:
        st.warning("No pixels to fit for QUESP analysis.")
        return {}

    progress_bar = st.progress(0, text="Starting QUESP fitting...")
    fit_counter = 0

    # Prepare data for each solute pool once to be efficient
    pools_data = {}
    for offset in unique_offsets:
        pool_name = next((pool for pool, off in pool_dict.items() if off == offset), f"{offset} ppm")
        offset_df = df[df['offset'] == offset]
        pools_data[pool_name] = {
            'b1_values': offset_df['b1'].values * 1e-6,
            'tsat': offset_df['tsat'].iloc[0] * 1e-3, # tsat is constant
            'trecs': offset_df['trec'].values, # Use array of trecs
            'mtr_asym_stack': np.stack(offset_df['mtr_asym'].values, axis=-1),
            'mtr_rex_stack': np.stack(offset_df['mtr_rex'].values, axis=-1)
        }
        # Initialize results structure
        for roi_label in masks:
            if roi_label not in results_by_roi:
                results_by_roi[roi_label] = {}
            results_by_roi[roi_label][pool_name] = {'fb_values': [], 'kb_values': [], 'r2_values': []}

    # Iterate through each ROI to perform checks and then fit
    for roi_label, mask in masks.items():
        if roi_label not in t1_pixel_fits:
            continue
        y_coords, x_coords = np.where(mask)
        t1_values_for_roi = t1_pixel_fits[roi_label]

        # Calculate mean T1 for assumption checks
        t1_mean_s = np.nanmean(np.array(t1_values_for_roi) * 1e-3)
        
        if t1_mean_s: # Proceed only if mean T1 is a valid number
            if fit_type in ['Inverse (MTRrex)', 'Omega Plot']:
                tsat_s = next(iter(pools_data.values()))['tsat']
                trecs_s = next(iter(pools_data.values()))['trecs']
                t1_threshold = 5 * t1_mean_s
                problematic_trecs = trecs_s[trecs_s < t1_threshold]
                if problematic_trecs.size > 0:
                    # Format the list of problematic Trec values for the message
                    trecs_list_str = ", ".join([f"{t:.2f}" for t in problematic_trecs])
                    st_functions.message_logging(
                        f"For **{roi_label}**, spins may not be fully relaxed. "
                        f"The following recovery time(s) ($T_{{rec}}$) are less than "
                        f"$5 \\times$ the mean $T_1$ ({t1_mean_s:.2f} s): **{trecs_list_str} s**. "
                        f"This invalidates the MTRrex and Omega Plot model.",
                        msg_type='warning'
                    )
                if tsat_s < 3 * t1_mean_s:
                    st_functions.message_logging(
                        f"For **{roi_label}**, the steady-state saturation assumption may be invalid. "
                        f"The saturation time ($t_{{sat}}$ = {tsat_s:.2f} s) is less than $3 \\times$ the mean $T_1$ ({t1_mean_s:.2f} s). "
                        f"This can affect the accuracy of the MTRrex and Omega Plot models.",
                        msg_type='warning'
                    )
                
        # Iterate through each pixel in the current ROI
        for i in range(len(y_coords)):
            y, x = y_coords[i], x_coords[i]
            t1_val_ms = t1_values_for_roi[i]
            # Perform the fit for each chemical pool for the current pixel
            for pool_name, data in pools_data.items():
                fit_counter += 1
                progress_bar.progress(fit_counter / total_fits, text=f"Fitting {pool_name} in {roi_label}...")

                if np.isnan(t1_val_ms) or t1_val_ms == 0:
                    results_by_roi[roi_label][pool_name]['fb_values'].append(np.nan)
                    results_by_roi[roi_label][pool_name]['kb_values'].append(np.nan)
                    results_by_roi[roi_label][pool_name]['r2_values'].append(np.nan)
                    continue

                r1_pixel = 1.0 / (t1_val_ms * 1e-3)
                if fixed_fb is not None:
                    if fit_type == 'Standard (MTRasym)':
                        model_to_fit = lambda b1, kb: standard_model(b1, r1_pixel, data['tsat'], data['trecs'], fixed_fb, kb)
                    elif fit_type == 'Inverse (MTRrex)':
                        model_to_fit = lambda b1, kb: inverse_model(b1, r1_pixel, fixed_fb, kb)
                    elif fit_type == 'Omega Plot':
                        model_to_fit = lambda b1, kb: omega_plot(b1, r1_pixel, fixed_fb, kb)
                    p0 = [1000]
                    bounds = ([0.1], [5000])
                else:
                    if fit_type == 'Standard (MTRasym)':
                        model_to_fit = lambda b1, fb, kb: standard_model(b1, r1_pixel, data['tsat'], data['trecs'], fb, kb)
                    elif fit_type == 'Inverse (MTRrex)':
                        model_to_fit = lambda b1, fb, kb: inverse_model(b1, r1_pixel, fb, kb)
                    elif fit_type == 'Omega Plot':
                        model_to_fit = lambda b1, fb, kb: omega_plot(b1, r1_pixel, fb, kb)
                    p0=[0.01, 1000]
                    bounds=([0, 0.1], [10, 5000])

                if fit_type == 'Standard (MTRasym)':
                    curve = data['mtr_asym_stack'][y, x, :]
                elif fit_type == 'Inverse (MTRrex)':
                    curve = data['mtr_rex_stack'][y, x, :]
                elif fit_type == 'Omega Plot':
                    curve = 1 / data['mtr_rex_stack'][y, x, :]

                try:
                    popt, _ = curve_fit(
                        model_to_fit, data['b1_values'], curve,
                        p0=p0, bounds=bounds
                    )
                    if fixed_fb is not None:
                        fb = fixed_fb
                        kb = popt[0]
                    else:
                        fb, kb = popt
                    r2 = r2_score(curve, model_to_fit(data['b1_values'], *popt))
                    results_by_roi[roi_label][pool_name]['fb_values'].append(fb)
                    results_by_roi[roi_label][pool_name]['kb_values'].append(kb)
                    results_by_roi[roi_label][pool_name]['r2_values'].append(r2)
                except RuntimeError:
                    results_by_roi[roi_label][pool_name]['fb_values'].append(np.nan)
                    results_by_roi[roi_label][pool_name]['kb_values'].append(np.nan)
                    results_by_roi[roi_label][pool_name]['r2_values'].append(np.nan)

    progress_bar.empty()
    st_functions.message_logging("QUESP fitting complete!")
    return results_by_roi

@time_it
def fit_t1_map(t1_data, masks):
    """
    Performs a pixel-wise T1 fit for each ROI, with a single unified progress bar.
    """
    images = t1_data['imgs']
    trs = t1_data['trs']
    pixelwise_fits = {}
    all_coords = []
    for label, mask in masks.items():
        coords = np.argwhere(mask)
        all_coords.extend([(label, tuple(coord)) for coord in coords])
        pixelwise_fits[label] = []

    if not all_coords:
        return {}
    progress_bar = st.progress(0, text="Fitting T₁ map...")
    total = len(all_coords)

    for i, (label, (y, x)) in enumerate(all_coords):
        signal_curve = images[y, x, :]
        try:
            popt, _ = curve_fit(
                f=t1_model,
                xdata=trs,
                ydata=signal_curve,
                p0=[np.max(signal_curve), 300.0],
                bounds=([0, 0], [np.inf, np.inf])
            )
            pixelwise_fits[label].append(popt[1]) # Append T1 value
        except RuntimeError:
            pixelwise_fits[label].append(np.nan)
        progress_bar.progress((i + 1) / total, text="Fitting T₁ map...")
    progress_bar.progress(1.0, text="T₁ map fitting complete.")
    progress_bar.empty()
    return pixelwise_fits