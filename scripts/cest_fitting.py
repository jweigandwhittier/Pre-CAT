#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb  6 11:08:05 2024

@author: jonah
"""
import streamlit as st
import numpy as np
from sklearn.metrics import mean_squared_error
from scipy.optimize import curve_fit
from scipy.interpolate import CubicSpline
from custom.st_functions import time_it

# --- Curve fitting parameters. Feel free to modify, results not guaranteed. --- #
###Pre-correction###
##Starting points for curve fitting: amplitude, FWHM, peak center##
p0_water = [0.8, 1.8, 0]
p0_mt = [0.15, 40, -1]
##Lower bounds for curve fitting##
lb_water = [0.02, 0.3, -10]
lb_mt = [0.0, 30, -2.5]
##Upper bounds for curve fitting##
ub_water = [1, 10, 10]
ub_mt = [0.5, 60, 0]

##Combine for curve fitting##
#B0 correction (tissue)
p0_corr = p0_water + p0_mt
lb_corr = lb_water + lb_mt
ub_corr = ub_water + ub_mt 
#B0 correction (phantom)
p0_corr_ph = p0_water
lb_corr_ph = lb_water
ub_corr_ph = ub_water

###Post-correction###
##Starting points for curve fitting: amplitude, FWHM, peak center##
p0_water = [0.8, 0.2, 0]
p0_mt = [0.15, 40, -1]
p0_noe = [0.05, 1, -3.50]
p0_noe_neg_1_6 = [0.05, 1, -1.6]
p0_creatine = [0.05, 0.5, 2.0]
p0_amide = [0.05, 1.5, 3.5]
p0_amine = [0.05, 1.5, 2.5]
p0_hydroxyl = [0.05, 1.5, 0.6]
p0_salicylic = [0.05, 1.5, 9.3]
##Lower bounds for curve fitting##
lb_water = [0.02, 0.01, -1e-6]
lb_mt = [0.0, 30, -2.5]
lb_noe = [0.0, 0.5, -4.0]
lb_noe_neg_1_6 = [0.0, 0.5, -1.8]
lb_creatine = [0.0, 0.5, 1.6]
lb_amide = [0.0, 0.5, 3.2]
lb_amine = [0.0, 0.1, 2.2]
lb_hydroxyl = [0.0, 0.1, 0.4]
lb_salicylic = [0.0, 0.5, 8.0]
##Upper bounds for curve fitting##
ub_water = [1, 10, 1e-6]
ub_mt = [0.5, 60, 0]
ub_noe = [0.25, 5, -1.5]
ub_noe_neg_1_6 = [.25, 5, -1.2]
ub_creatine = [0.5, 5, 2.6]
ub_amide = [0.3, 5, 4.0]
ub_amine = [0.3, 5, 2.8]
ub_hydroxyl = [0.3, 5, 1.2]
ub_salicylic = [0.3, 5, 10.0]

##Combine for curve fitting##
#Step 1
p0_1 = p0_water + p0_mt
lb_1 = lb_water + lb_mt
ub_1 = ub_water + ub_mt 
#Step 2 (cardiac)
p0_2 = p0_noe + p0_creatine + p0_amide
lb_2 = lb_noe + lb_creatine + lb_amide
ub_2 = ub_noe + ub_creatine + ub_amide
#Single step (Cr phantom)
p0_ph = p0_water + p0_creatine
lb_ph = lb_water + lb_creatine
ub_ph = ub_water + ub_creatine

###Cutoffs and options for fitting###
cutoffs = [-4, -1.4, 1.4, 4]
options = {'xtol': 1e-10, 'ftol': 1e-4, 'maxfev': 50}


# --- Model definitions --- #
def lorentzian(x, amp, fwhm, offset):
    num = amp * 0.25 * fwhm ** 2
    den = 0.25 * fwhm ** 2 + (x - offset) ** 2
    return num / den

def step_1_fit(x, *fit_parameters):
    water_fit = lorentzian(x, fit_parameters[0], fit_parameters[1], fit_parameters[2])
    mt_fit = lorentzian(x, fit_parameters[3], fit_parameters[4], fit_parameters[5])
    fit = 1 - water_fit - mt_fit
    return fit

def water_fit_correction(x, *fit_parameters):
    water_fit = lorentzian(x, fit_parameters[0], fit_parameters[1], fit_parameters[2])
    fit = 1 - water_fit
    return fit

# --- CEST fitting functions --- #
def calc_spectra(imgs, user_geometry):
    """
    Calculates the mean spectrum for each ROI based on user defined geometry.
    """
    spectra = {}
    if user_geometry['aha']:
        # Cardiac logic
        labeled_segments = user_geometry['aha']
        for label, segment_coords in labeled_segments.items():
            segment_mask = np.zeros_like(imgs[:,:,0], dtype=bool)
            for y, x in segment_coords:
                segment_mask[y, x] = True
            pixels = imgs[segment_mask, :]
            spectra[label] = np.mean(pixels, axis=0)
    else:
        # Standard ROI logic
        masks = user_geometry['masks']
        for label, mask in masks.items():
            pixels = imgs[mask, :]
            spectra[label] = np.mean(pixels, axis=0)
    return spectra

def calc_spectra_pixelwise(imgs, masks):
    """
    Calculates the spectrum for each individual pixel within the given masks.
    """
    spectra_by_label = {}
    for label, mask in masks.items():
        # Get coordinates of all pixels in the mask
        y_coords, x_coords = np.where(mask)
        # Extract the spectral data for these pixels across all offsets
        pixel_spectra = imgs[y_coords, x_coords, :]
        spectra_by_label[label] = pixel_spectra
    return spectra_by_label

def two_step(spectrum, offsets, custom_contrasts = None):
    """
    Performs the two-step Lorentzian fitting on a single spectrum.
    This is the core fitting logic.
    """
    n_interp = 4000
    if custom_contrasts is None:
        custom_contrasts = ['Amide', 'Creatine', 'NOE (-3.5 ppm)', 'NOE (-1.6 ppm)']
    contrast_params = {
        'NOE (-3.5 ppm)': (p0_noe, lb_noe, ub_noe),
        'Creatine': (p0_creatine, lb_creatine, ub_creatine),
        'Amide': (p0_amide, lb_amide, ub_amide),
        'Amine': (p0_amine, lb_amine, ub_amine),
        'Hydroxyl': (p0_hydroxyl, lb_hydroxyl, ub_hydroxyl),
        'NOE (-1.6 ppm)': (p0_noe_neg_1_6, lb_noe_neg_1_6, ub_noe_neg_1_6),
        'Salicylic acid': (p0_salicylic, lb_salicylic, ub_salicylic)
    }
    p0_2, lb_2, ub_2 = [], [], []
    for contrast in custom_contrasts:
        p0_2 += contrast_params[contrast][0]
        lb_2 += contrast_params[contrast][1]
        ub_2 += contrast_params[contrast][2]
    def step_2_fit(x, *params):
        fit_sum = np.zeros_like(x)
        index = 0
        for contrast in custom_contrasts:
            fit_sum += lorentzian(x, params[index], params[index + 1], params[index + 2])
            index += 3
        return fit_sum
    try:
        if offsets[0] > 0:
            offsets = np.flip(offsets)
            spectrum = np.flip(spectrum)
        fit_1, _ = curve_fit(step_1_fit, offsets, spectrum, p0=p0_corr, bounds=(lb_corr, ub_corr), **options)
        correction = fit_1[2]
        offsets_corrected = offsets - correction
        if 'Hydroxyl' in custom_contrasts:
            cutoffs[2] = 0.4
        else:
            cutoffs[2] = 1.4
        condition = (offsets_corrected <= cutoffs[0]) | (offsets_corrected >= cutoffs[3]) | \
                    ((offsets_corrected >= cutoffs[1]) & (offsets_corrected <= cutoffs[2]))
        condition_rmse = ((offsets_corrected <= -1.4) & (offsets_corrected >= -4)) | \
                         ((offsets_corrected >= 1.4) & (offsets_corrected <= 4))
        offsets_cropped = offsets_corrected[condition]
        spectrum_cropped = spectrum[condition]
        if len(offsets_cropped) == 0:  # Handle empty offsets case
            raise RuntimeError("No valid offsets found after cropping")
        offsets_interp = np.linspace(offsets_corrected[0], offsets_corrected[-1], n_interp)
        fit_1, _ = curve_fit(step_1_fit, offsets_cropped, spectrum_cropped, p0=p0_1, bounds=(lb_1, ub_1), **options)
        water_fit = lorentzian(offsets_interp, fit_1[0], fit_1[1], fit_1[2])
        mt_fit = lorentzian(offsets_interp, fit_1[3], fit_1[4], fit_1[5])
        background = lorentzian(offsets_corrected, fit_1[0], fit_1[1], fit_1[2]) + \
                     lorentzian(offsets_corrected, fit_1[3], fit_1[4], fit_1[5])
        lorentzian_difference = 1 - (spectrum + background)
        step_1_fit_values = step_1_fit(offsets_corrected, *fit_1)
        step_1_rmse = np.sqrt(mean_squared_error(spectrum, step_1_fit_values))
        fit_2, _ = curve_fit(step_2_fit, offsets_corrected, lorentzian_difference, p0=p0_2, bounds=(lb_2, ub_2), **options)
        fit_curves = {}
        index = 0
        for contrast in custom_contrasts:
            fit_curves[contrast] = lorentzian(offsets_interp, fit_2[index], fit_2[index + 1], fit_2[index + 2])
            index += 3
        step_2_fit_values = step_2_fit(offsets_corrected, *fit_2)
        step_2_rmse = np.sqrt(mean_squared_error(lorentzian_difference, step_2_fit_values))
        total_fit = step_1_fit_values - step_2_fit_values
        spectrum_region = spectrum[condition_rmse]
        total_fit_region = total_fit[condition_rmse]
        rmse = np.sqrt(mean_squared_error(spectrum_region, total_fit_region))
        offsets_interp = np.flip(offsets_interp)
        water_fit = np.flip(water_fit)
        mt_fit = np.flip(mt_fit)
        fit_curves_named = {f"{contrast}_Fit": np.flip(fit_curves[contrast]) for contrast in fit_curves}
        contrasts = {'Water': 100 * fit_1[0], 'MT': 100 * fit_1[3]}
        for i, contrast in enumerate(custom_contrasts):
            contrasts[contrast] = 100 * fit_2[i * 3]
        data_dict = {'Zspec': spectrum, 'Offsets': offsets, 'Offsets_Corrected': offsets_corrected,
                     'Offsets_Interp': offsets_interp, 'Water_Fit': water_fit, 'MT_Fit': mt_fit,
                     **fit_curves_named, 'Lorentzian_Difference': lorentzian_difference}
        fit_parameters = [fit_1, fit_2]
    except RuntimeError:
        # Assign zeros instead of crashing
        fit_parameters = [np.zeros(len(p0_1)), np.zeros(len(p0_2))]
        contrasts = {key: 0 for key in ['Water', 'MT'] + custom_contrasts}
        data_dict = {'Zspec': spectrum, 'Offsets': offsets, 'Offsets_Corrected': np.zeros_like(offsets),
                     'Offsets_Interp': np.zeros(n_interp), 'Water_Fit': np.zeros(n_interp), 'MT_Fit': np.zeros(n_interp),
                     'Lorentzian_Difference': np.zeros(n_interp), **{f"{contrast}_Fit": np.zeros(n_interp) for contrast in custom_contrasts}}
        spectrum_region = np.array([])
        total_fit_region = np.array([])
        rmse = np.inf
    return {'Fit_Params': fit_parameters, 'Data_Dict': data_dict,
            'Contrasts': contrasts, 'Residuals': spectrum_region - total_fit_region, 'RMSE': rmse}

@time_it
def fit_all_rois(spectra_by_roi, offsets, custom_contrasts):
    """
    Iterates through all ROIs and applies the two-step fit.
    """
    fits = {}
    for roi, spectrum in spectra_by_roi.items():
        fits[roi] = two_step(spectrum, offsets, custom_contrasts)
    return fits

@time_it
def fit_all_pixels(spectra_by_pixel, offsets, custom_contrasts):
    """
    Iterates through all pixels in a mask and applies the two-step fit.
    """
    pixel_fits = {}
    for label, pixel_spectra in spectra_by_pixel.items():
        fits_for_label = []
        
        total_pixels = len(pixel_spectra)
        progress_bar = st.progress(0, text=f"Fitting pixels in {label}...")

        for i, spectrum in enumerate(pixel_spectra):
            fits_for_label.append(two_step(spectrum, offsets, custom_contrasts))
            progress_bar.progress((i + 1) / total_pixels)
        
        pixel_fits[label] = fits_for_label
        progress_bar.empty()
    return pixel_fits

# --- B1 fitting functions --- #
@time_it
def fit_b1(imgs, nominal_flip):
    """Calculates the B1 error map from DAMB1 images."""
    theta = imgs[:, :, 0]
    two_theta = imgs[:, :, 1]
    
    # Avoid division by zero
    with np.errstate(divide='ignore', invalid='ignore'):
        ratio = np.clip(two_theta / (2 * theta), -1.0, 1.0)
    
    theta_actual_rad = np.arccos(ratio)
    theta_actual_deg = np.rad2deg(theta_actual_rad)
    flip_error = theta_actual_deg / nominal_flip
    
    return np.nan_to_num(np.squeeze(flip_error))
    
# --- WASSR fitting functions --- #
@time_it
def fit_wassr_full(imgs, offsets, user_geometry):
    """
    Performs full (unmasked) WASSR fitting and returns the full B0 map as well as maskes results.
    """
    n_interp = 1000
    b0_full_map = np.full((imgs.shape[0], imgs.shape[1]), np.nan, dtype=float)
    total_pixels = imgs.shape[0] * imgs.shape[1]
    progress_bar = st.progress(0, text="Fitting full WASSR B₀ map...")
    progress_counter = 0
    for i in range(imgs.shape[0]):
        for j in range(imgs.shape[1]):
            progress_counter += 1
            if progress_counter % 100 == 0:
                 progress_bar.progress(progress_counter / total_pixels, text="Fitting full WASSR B₀ map...")
            if np.mean(imgs[i, j, :]) < 0.05 * np.max(imgs):
                continue
            spectrum = imgs[i, j, :]
            pixel_offsets = offsets.copy()
            if pixel_offsets[0] > pixel_offsets[-1]:
                pixel_offsets = np.flip(pixel_offsets)
                spectrum = np.flip(spectrum)
            try:
                cubic_spline = CubicSpline(pixel_offsets, spectrum)
                offsets_interp = np.linspace(pixel_offsets[0], pixel_offsets[-1], n_interp)
                spectrum_interp = cubic_spline(offsets_interp)
                min_idx = np.argmin(spectrum_interp)
                p0_corr[2] = offsets_interp[min_idx]
                fit_1, _ = curve_fit(step_1_fit, offsets_interp, spectrum_interp, p0=p0_corr, bounds=(lb_corr, ub_corr))
                water_fit = lorentzian(offsets_interp, fit_1[0], fit_1[1], fit_1[2])
                b0_shift = offsets_interp[np.argmax(water_fit)]
                b0_full_map[i, j] = b0_shift
            except (RuntimeError, ValueError):
                b0_full_map[i, j] = np.nan
    progress_bar.progress(1.0, text="WASSR B₀ fitting complete.")
    progress_bar.empty()
    pixelwise = {}
    if user_geometry['aha']:
        masks_dict = user_geometry.get('aha', {})
        for label, coord_list in masks_dict.items():
            valid_coords = [c for c in coord_list if not np.isnan(b0_full_map[c[0], c[1]])]
            pixelwise[label] = [b0_full_map[r, c] for r, c in valid_coords]
    else:
        masks_dict = user_geometry.get('masks', {})
        for label, mask in masks_dict.items():
            coords = np.argwhere(mask)
            valid_coords = [c for c in coords if not np.isnan(b0_full_map[c[0], c[1]])]
            pixelwise[label] = [b0_full_map[r, c] for r, c in valid_coords]
    return pixelwise, b0_full_map

@time_it
def fit_wassr_masked(imgs, offsets, user_geometry):
    """
    Performs masked WASSR fitting for B0 shifts.
    """
    n_interp = 1000
    pixelwise = {}
    if user_geometry['aha']:
        masks_dict = user_geometry.get('aha', {})
        all_coords = [(label, coord) for label, coords_list in masks_dict.items() for coord in coords_list]
    else:
        masks_dict = user_geometry.get('masks', {})
        all_coords = []
        for label, mask in masks_dict.items():
            coords = np.argwhere(mask)
            all_coords.extend([(label, tuple(coord)) for coord in coords])
    if not all_coords:
        return {}
    progress_bar = st.progress(0, text="Fitting WASSR B₀ shifts for masked region...")
    total = len(all_coords)
    progress_counter = 0
    for label in masks_dict:
        pixelwise[label] = []
    for i, (label, (y, x)) in enumerate(all_coords):
        spectrum = imgs[y, x, :]
        pixel_offsets = offsets.copy()
        if pixel_offsets[0] > pixel_offsets[-1]:
            pixel_offsets = np.flip(pixel_offsets)
            spectrum = np.flip(spectrum)
        try:
            cubic_spline = CubicSpline(pixel_offsets, spectrum)
            offsets_interp = np.linspace(pixel_offsets[0], pixel_offsets[-1], n_interp)
            spectrum_interp = cubic_spline(offsets_interp)
            min_idx = np.argmin(spectrum_interp)
            p0_corr[2] = offsets_interp[min_idx]
            fit_1, _ = curve_fit(step_1_fit, offsets_interp, spectrum_interp, p0=p0_corr, bounds=(lb_corr, ub_corr))
            water_fit = lorentzian(offsets_interp, fit_1[0], fit_1[1], fit_1[2])
            b0_shift = offsets_interp[np.argmax(water_fit)]
        except Exception:
            b0_shift = np.nan
        pixelwise[label].append(b0_shift)
        progress_counter += 1
        progress_bar.progress(progress_counter / total, text="Fitting WASSR B₀ shifts for masked region...")
    progress_bar.progress(1.0, text="WASSR B₀ fitting complete.")
    progress_bar.empty()
    return pixelwise