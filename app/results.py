#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 23 16:30:36 2026

@author: jonah
"""
import os
import pickle
from app import data_management
from scripts import plotting, plotting_wassr, plotting_damb1, plotting_quesp
from scripts.mrf_scripts import plotting_mrf
from custom import st_functions
import streamlit as st

def display_results():
    """
    Displays all the final plots and data.
    """
    submitted = st.session_state.submitted_data
    save_path = submitted['save_path']
    final_save_name = submitted.get('save_name', 'precat_results')

    # Initialize all map variables
    pixel_maps_for_saving = None
    b1_map_for_saving = None
    wassr_map_for_saving = None
    t1_map_for_saving = None
    quesp_maps_for_saving = None
    
    if "CEST" in submitted['selection']:
        st.header('CEST Results')
        ref_image = st.session_state.processed_data['cest']['m0']
        if submitted['organ'] == 'Cardiac':
            mask = st.session_state.user_geometry['masks']['lv']
            plotting.show_segmentation(ref_image, mask, st.session_state.user_geometry['aha'], save_path)
        else:
            plotting.show_rois(ref_image, st.session_state.user_geometry['masks'], save_path)
        if submitted.get('pixelwise') and 'cest_pixelwise' in st.session_state.fits:
            pixel_maps_for_saving = plotting.pixelwise_mapping(
                ref_image, st.session_state.fits['cest_pixelwise'], 
                st.session_state.user_geometry,
                submitted.get('custom_contrasts'), submitted.get('smoothing_filter'), save_path
            )

        plotting.plot_zspec(st.session_state.fits['cest'], save_path)
        
    if "QUESP" in submitted['selection']:
        st.header('QUESP Results')
        col1, col2 = st.columns(2)
        with col1:
            t1_map_for_saving = plotting_quesp.plot_t1_map(st.session_state.fits['t1'], st.session_state.processed_data['quesp']['m0'], st.session_state.user_geometry['masks'], save_path)
        with col2:
            plotting.show_rois(st.session_state.processed_data['quesp']['m0'], st.session_state.user_geometry['masks'], save_path)
        quespmin, quespmax = st.slider("Percentile range for plots and statistics display:", 0, 100, value=(5, 95))
        st.warning(f'Plot colorbars and statistics are displayed within the {quespmin}-{quespmax}th percentile range per ROI.')
        quesp_maps_for_saving = plotting_quesp.plot_quesp_maps(st.session_state.fits['quesp'], st.session_state.user_geometry['masks'], st.session_state.processed_data['quesp']['m0'], save_path, quespmin, quespmax)
        quesp_stats_df = plotting_quesp.calculate_quesp_stats(st.session_state.fits['quesp'], st.session_state.fits['t1'], quespmin, quespmax)
        st.dataframe(quesp_stats_df.style.format("{:.4f}"))
        st_functions.save_df_to_csv(quesp_stats_df, save_path, type='QUESP')

    if "CEST-MRF" in submitted['selection']:
        st.header('CEST-MRF Results')
        reference_image = st.session_state.processed_data['cest-mrf']['imgs'][:, :, 0]
        mrf_results = st.session_state.fits.get('cest-mrf')
        if mrf_results:
            plotting_mrf.plot_mrf_maps(mrf_results, reference_image, save_path, st.session_state.submitted_data['proton_params'])
        mrf_stats_df = plotting_mrf.calculate_mrf_stats(
            mrf_results,
            proton_params=st.session_state.submitted_data.get('proton_params')
        )
        if mrf_stats_df is not None and not mrf_stats_df.empty:
            st.dataframe(mrf_stats_df.style.format("{:.2f}"))
            st_functions.save_df_to_csv(mrf_stats_df, save_path, type='MRF')
        else:
            st.info("No statistics to display.")

    if "WASSR" in submitted['selection']:
        st.header('WASSR Results')
        ref_image = st.session_state.processed_data['cest']['m0'] if 'cest' in st.session_state.processed_data else st.session_state.processed_data['wassr']['m0']
        wassr_map_for_saving = plotting_wassr.plot_wassr(ref_image, st.session_state.user_geometry, st.session_state.fits.get('wassr'), save_path,st.session_state.fits.get('wassr_full_map'))
        if submitted['organ'] == 'Cardiac':
            plotting_wassr.plot_wassr_aha(st.session_state.fits['wassr'], save_path)

    if "DAMB1" in submitted['selection']:
        st.header('DAMB1 Results')
        ref_image = st.session_state.processed_data['cest']['m0'] if 'cest' in st.session_state.processed_data else st.session_state.processed_data['wassr']['m0'] if 'wassr' in st.session_state.processed_data else None
        b1_map_for_saving = plotting_damb1.plot_damb1(st.session_state.fits['damb1'], ref_image, st.session_state.user_geometry, save_path)
        if submitted['organ'] == 'Cardiac':
            plotting_damb1.plot_damb1_aha(st.session_state.fits['damb1'], ref_image, st.session_state.user_geometry['aha'], save_path)

    if "timing_log" in st.session_state and st.session_state.timing_log:
        try:
            # We need pandas for this
            import pandas as pd
            
            timing_df = pd.DataFrame(st.session_state.timing_log)
            
            # Define the path for the CSV inside the "Raw" folder
            raw_data_dir = os.path.join(save_path, "Raw")
            os.makedirs(raw_data_dir, exist_ok=True)
            csv_path = os.path.join(raw_data_dir, "processing_time_log.csv")
            
            # Save the CSV
            timing_df.to_csv(csv_path, index=False)

        except Exception as e:
            st_functions.message_logging(f"Failed to save timing log as CSV: {e}", msg_type='warning')

    data_to_save = data_management.prepare_data_for_saving(
        pixel_maps_for_saving,
        b1_map_for_saving,
        wassr_map_for_saving,
        t1_map_for_saving,
        quesp_maps_for_saving
        )

    raw_data_dir = os.path.join(save_path, "Raw")
    os.makedirs(raw_data_dir, exist_ok=True)
    raw_data_path = os.path.join(raw_data_dir, "session_data.pkl")

    try:
        with open(raw_data_path, 'wb') as f:
            pickle.dump(data_to_save, f)
    except Exception as e:
        st.error(f"Error saving raw data: {e}")
        st_functions.message_logging(f"Error saving raw data: {e}", msg_type='error')

    # --- 3. Zip and Provide Download ---
    if any(msg_type in ['warning', 'error'] for _, msg_type in st.session_state.log_messages):
        st.error("**One or more issues were noted during processing. Please review the log.**")
    try:
        zip_buffer = data_management.create_zip_in_memory(save_path) 
        st.success("Processing complete! Click the button below to download your results.")
        st.download_button(
            label="Download Results",
            data=zip_buffer,
            file_name=f"{final_save_name}.zip",
            mime="application/zip"
        )
    except Exception as e:
        st.error(f"An error occurred while creating the results zip file: {e}")
    # st_functions.save_raw(st.session_state)
    if any(msg_type in ['warning', 'error'] for _, msg_type in st.session_state.log_messages):
        st.error("**One or more issues were noted during processing. Please review the log in the 'Process data' expander.**")