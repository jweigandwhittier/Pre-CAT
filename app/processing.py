#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 23 15:56:30 2026

@author: jonah
"""
import os
import streamlit as st
from scripts import pre_processing, load_study, draw_rois, cest_fitting, quesp_fitting
from scripts.mrf_scripts import load_mrf, mrf_fitting
from custom import st_functions

def do_processing_pipeline():
    """
    Manages the sequential processing pipeline for all experiment types.
    """
    # Retrieve submitted experiment types 
    submitted = st.session_state.submitted_data
    selection = [s.lower() for s in submitted.get('selection', [])]

    # --- Stage 0.5: Set up all required MRF files --- #
    if not st.session_state.pipeline_status.get('mrf_gen_done', False):
        if 'cest-mrf' in selection:
            load_mrf.write_yaml(submitted['mrf_config'])
            load_mrf.seq_from_method(submitted['mrf_path'], submitted['folder_path'], submitted['mrf_config'])
            if not (submitted['upload_dict']):
                load_mrf.generate_dictionary(submitted['mrf_config'])
            else:
                st_functions.message_logging("Using pre-calculated MRF dictionary.", msg_type='info')
        st.session_state.pipeline_status['mrf_gen_done'] = True
        st.rerun()

    # --- Stage 1: Reconstruction --- #
    # Reconstruct all selected data types if they haven't been already.
    if st.session_state.pipeline_status.get('mrf_gen_done') and not st.session_state.pipeline_status.get('recon_done', False):
        with st.spinner("Reconstructing data..."):
            tasks_to_run = [exp for exp in selection if exp not in st.session_state.recon_data]
            # Sort tasks
            task_order = ['cest', 'quesp', 'cest-mrf', 'wassr', 'damb1']
            tasks_to_run.sort(key=task_order.index)
            for exp_type in tasks_to_run:
                if exp_type == 'cest':
                    cest_type = submitted.get('cest_type')
                    if cest_type == 'Radial':
                        use_moco = submitted.get('moco_cest', False)
                        use_pca = submitted.get('pca', False)
                        if use_moco:
                            # With motion correction (with or without PCA)
                            st.session_state.recon_data['cest'] = pre_processing.run_radial_preprocessing(
                                submitted['folder_path'],
                                submitted['cest_path'],
                                use_pca,
                                exp_type
                            )
                        else:
                            # Without motion correction
                            recon_data = load_study.recon_bart(
                                submitted['cest_path'], submitted['folder_path']
                            )
                    else: # Rectilinear
                        st.session_state.recon_data['cest'] = load_study.recon_bruker(
                            submitted['cest_path'], submitted['folder_path'])
                    if use_pca:
                        # Apply PCA denoising
                        denoised_images = pre_processing.denoise_data(recon_data['imgs'])
                        st.session_state.recon_data['cest'] = {
                            "imgs": denoised_images,
                            "offsets": recon_data['offsets']
                        }
                    else:
                        # Just reconstruction
                        st.session_state.recon_data['cest'] = recon_data

                if exp_type == 'wassr':
                    wassr_type = submitted.get('wassr_type')
                    if wassr_type == 'Radial' and submitted.get('moco_wassr'):
                        st.session_state.recon_data['wassr'] = pre_processing.run_radial_preprocessing(
                            submitted['folder_path'],
                            submitted['wassr_path'],
                            False,
                            exp_type 
                        )
                    elif wassr_type == 'Radial':
                        st.session_state.recon_data['wassr'] = load_study.recon_bart(
                            submitted['wassr_path'], submitted['folder_path']
                        )
                    else: # Rectilinear
                        st.session_state.recon_data['wassr'] = load_study.recon_bruker(
                            submitted['wassr_path'], submitted['folder_path']
                        )
                if exp_type == "damb1":
                    st.session_state.recon_data['damb1'] = load_study.recon_damb1(submitted['folder_path'], submitted['theta_path'], submitted['two_theta_path'])
                if exp_type == "quesp":
                    st.session_state.recon_data['quesp'] = load_study.recon_quesp(submitted['quesp_path'], submitted['folder_path'])
                    if submitted['t1_path']:
                        st.session_state.recon_data['t1'] = load_study.recon_t1map(submitted['t1_path'], submitted['folder_path'])
                if exp_type == "cest-mrf":
                    st.session_state.recon_data['cest-mrf'] = load_study.recon_bruker(submitted['mrf_path'], submitted['folder_path'])
            st.session_state.pipeline_status['recon_done'] = True
            st_functions.message_logging("All reconstruction complete!")
            st.rerun()
    
    # --- Stage 2: Group experiments and orient each group --- #
    if st.session_state.pipeline_status.get('recon_done') and not st.session_state.pipeline_status.get('orientation_done', False):
        # Group experiments by their trajectory type
        radial_exps = [exp for exp in ['cest', 'wassr'] if exp in st.session_state.recon_data and submitted.get(f'{exp}_type') == 'Radial']
        rectilinear_exps = [exp for exp in ['cest', 'wassr'] if exp in st.session_state.recon_data and submitted.get(f'{exp}_type') == 'Rectilinear']
        if 'damb1' in st.session_state.recon_data:
            rectilinear_exps.append('damb1')
        if 'quesp' in st.session_state.recon_data:
            rectilinear_exps.append('quesp')
        if 'cest-mrf' in st.session_state.recon_data:
            rectilinear_exps.append('cest-mrf')
        # Orient radial group
        if radial_exps and st.session_state.orientation_params.get('radial') is None:
            primary_exp = radial_exps[0] # Orient using the first radial experiment
            transforms = load_study.show_rotation_ui(st.session_state.recon_data[primary_exp]['imgs'], 'Radial')
            if transforms:
                st.session_state.orientation_params['radial'] = transforms
                st.rerun()
            else:
                return
        # Orient rectilinear group
        if rectilinear_exps and st.session_state.orientation_params.get('rectilinear') is None:
            primary_exp = rectilinear_exps[0] # Orient using the first rectilinear experiment
            transforms = load_study.show_rotation_ui(st.session_state.recon_data[primary_exp]['imgs'], 'Rectilinear')
            if transforms:
                st.session_state.orientation_params['rectilinear'] = transforms
                st.rerun()
            else:
                return
        # Check for completion
        radial_done = not radial_exps or st.session_state.orientation_params.get('radial') is not None
        rectilinear_done = not rectilinear_exps or st.session_state.orientation_params.get('rectilinear') is not None
        if radial_done and rectilinear_done:
            st.session_state.pipeline_status['orientation_done'] = True
            st_functions.message_logging("All orientations finalized!")
            st.rerun()

    # --- Stage 3: Apply transformations and corrections --- #
    if st.session_state.pipeline_status.get('orientation_done') and not st.session_state.pipeline_status.get('processing_done', False):
        with st.spinner("Applying orientation and corrections..."):
            for exp_type in selection:
                if exp_type in selection:
                    # Determine which orientation params to use
                    orientation_type = 'rectilinear' if exp_type in ['damb1', 'quesp', 'cest-mrf'] or submitted.get(f'{exp_type}_type') == 'Rectilinear' else 'radial'
                    k, flip = st.session_state.orientation_params[orientation_type]
                    recon = st.session_state.recon_data[exp_type]
                    oriented = load_study.rotate_image_stack(recon['imgs'], k)
                    if flip:
                        oriented = load_study.flip_image_stack_vertically(oriented)
                    # Apply further corrections
                    if exp_type == 'cest-mrf':
                        processed_mrf = recon.copy()
                        processed_mrf['imgs'] = oriented
                        st.session_state.processed_data[exp_type] = processed_mrf
                    elif 'offsets' in recon and 'powers' not in recon: # CEST/WASSR
                        corrected = load_study.thermal_drift({"imgs": oriented, "offsets": recon['offsets']})
                        st.session_state.processed_data[exp_type] = corrected
                    elif 'powers' in recon: # QUESP
                        corrected = load_study.process_quesp({"imgs": oriented, "powers": recon['powers'], "tsats": recon['tsats'], "trecs": recon['trecs'], "offsets": recon['offsets']}, denoise = submitted.get('quesp_denoise'))
                        st.session_state.processed_data[exp_type] = corrected
                    else: # DAMB1
                        st.session_state.processed_data[exp_type] = {"imgs": oriented, "nominal_flip": recon['nominal_flip']}
            st.session_state.pipeline_status['processing_done'] = True
            st_functions.message_logging("All data transformed and corrected!")
            st.rerun()

    # --- Stage 4: ROI drawing --- #
    if st.session_state.pipeline_status.get('processing_done') and not st.session_state.pipeline_status.get('rois_done', False):
        roi_canvas_placeholder = st.empty()
        with roi_canvas_placeholder.container():
            # Determine the best reference image for drawing ROIs
            primary_exp = selection[0]
            processed_exp_data = st.session_state.processed_data[primary_exp]
            if 'm0' in processed_exp_data:
                canvas_shape_ref = processed_exp_data['m0']
            elif 'imgs' in processed_exp_data:
                img_stack = processed_exp_data['imgs']
                canvas_shape_ref = img_stack[:, :, 0] if img_stack.ndim >= 3 else img_stack
            if submitted.get('reference') is not None:
                canvas_bg_image = submitted['reference']
            else:
                canvas_bg_image = canvas_shape_ref
            rois = draw_rois.cardiac_roi(canvas_bg_image, canvas_shape_ref) if submitted['organ'] == 'Cardiac' else draw_rois.draw_rois(canvas_bg_image, canvas_shape_ref)
        if rois:
            st.session_state.user_geometry['rois'] = rois
            st.session_state.pipeline_status['rois_done'] = True
            st_functions.message_logging("ROI definition complete!")
            roi_canvas_placeholder.empty()
            st.rerun()
        else:
            return

    # --- Stage 5: Fitting --- #
    if st.session_state.pipeline_status.get('rois_done') and not st.session_state.pipeline_status.get('fitting_done', False):
        with st.spinner("Performing final analysis..."):
            # --- Generate masks and AHA segments ---
            # Determine reference image
            primary_exp = selection[0]
            processed_exp_data = st.session_state.processed_data[primary_exp]
            if 'm0' in processed_exp_data:
                mask_creation_ref_image = processed_exp_data['m0']
            elif 'imgs' in processed_exp_data:
                img_stack = processed_exp_data['imgs']
                mask_creation_ref_image = img_stack[:, :, 0] if img_stack.ndim >= 3 else img_stack
            masks = draw_rois.convert_rois_to_masks(mask_creation_ref_image, st.session_state.user_geometry['rois'])
            st.session_state.user_geometry['masks'] = masks
            
            if submitted['organ'] == 'Cardiac':
                lv_mask = draw_rois.calc_lv_mask(masks)
                st.session_state.user_geometry['masks']['lv'] = lv_mask
                st.session_state.user_geometry['aha'] = draw_rois.aha_segmentation(lv_mask, masks['insertion_points'])

            # --- Run fitting for all selected types --- #
            if "cest" in selection:
                proc_data = st.session_state.processed_data['cest']
                spectra = cest_fitting.calc_spectra(proc_data['imgs'], st.session_state.user_geometry)
                st.session_state.fits['cest'] = cest_fitting.fit_all_rois(spectra, proc_data['offsets'], submitted.get('custom_contrasts'))
                if submitted.get('pixelwise'):
                    pixel_spectra = cest_fitting.calc_spectra_pixelwise(proc_data['imgs'], st.session_state.user_geometry)
                    st.session_state.fits['cest_pixelwise'] = cest_fitting.fit_all_pixels(pixel_spectra, proc_data['offsets'], submitted.get('custom_contrasts'))
                if submitted['organ'] == 'Cardiac':
                    cest_fits = st.session_state.fits.get('cest', {})
                    segments_to_check = ["Anterior", "Anteroseptal"] # Can be changed if needed
                    for segment in segments_to_check:
                        fit_data = cest_fits.get(segment)
                        if fit_data:
                            rmse = fit_data.get("RMSE")
                            if rmse is not None and rmse > 0.02:
                                st_functions.message_logging(f"Fit RMSE in {segment.lower()} segment > 2% (RMSE = {rmse*100:.3f}%)!", msg_type='warning')

            if "quesp" in selection:
                if submitted['t1_path']:
                    t1_fits = quesp_fitting.fit_t1_map(st.session_state.recon_data['t1'], masks)
                else:
                    t1_fits = quesp_fitting.fixed_t1_map(submitted['fixed_t1'], masks)
                st.session_state.fits['t1'] = t1_fits
                st.session_state.fits['quesp'] = quesp_fitting.fit_quesp_map(st.session_state.processed_data['quesp'], t1_fits, masks, submitted.get('quesp_type'), submitted.get('fixed_fb'))
            
            if "wassr" in selection:
                proc_data = st.session_state.processed_data['wassr']
                if submitted.get('full_b0_mapping'):
                    st.session_state.fits['wassr'], st.session_state.fits['wassr_full_map'] = cest_fitting.fit_wassr_full(proc_data['imgs'], proc_data['offsets'], st.session_state.user_geometry)
                else:
                    st.session_state.fits['wassr'] = cest_fitting.fit_wassr_masked(proc_data['imgs'], proc_data['offsets'], st.session_state.user_geometry)

            if "damb1" in selection:
                proc_data = st.session_state.processed_data['damb1']
                st.session_state.fits['damb1'] = cest_fitting.fit_b1(proc_data['imgs'], proc_data['nominal_flip'])

            if "cest-mrf" in selection:
                if st.session_state.submitted_data['mrf_method'] == 'Dot product':
                    dictionary_to_use = submitted['mrf_config']['dict_fn']
                    if submitted.get('mrf_upload_dict'):
                        st_functions.message_logging(f"Fitting with user-uploaded dictionary: {os.path.basename(dictionary_to_use)}", msg_type='info')
                    else:
                        st_functions.message_logging(f"Fitting with generated dictionary: {os.path.basename(dictionary_to_use)}", msg_type='info') 
                    st.session_state.fits['cest-mrf'] = mrf_fitting.mrf_dot_prod(dictionary_to_use, st.session_state.processed_data['cest-mrf']['imgs'], masks)

            st_functions.message_logging("All processing complete!")
            st.session_state.pipeline_status['fitting_done'] = True
            st.session_state.is_processed = True
            st.session_state.display_data = True
            st.session_state.processing_active = False
            st.rerun()