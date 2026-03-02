#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan  7 12:35:44 2025

@author: jonah

TODO:
- Add option to upload data as Numpy array or DICOM
- Add page for quick Cr/PCr analysis (with DICOM upload)
- Change from automatically saving at path to download button
"""
# --- Imports --- #
from pathlib import Path 
import multiprocessing
import streamlit as st
from app import submission, processing, results, ui, state_management, data_management, validation
from custom import st_functions

# --- Constants for app setup --- #
SITE_ICON = "./custom/icons/ksp.ico"
LOADING_GIF_PATH = Path("custom/icons/loading.gif")

# --- Cached resources --- #
@st.cache_resource
def setup_assets():
    if LOADING_GIF_PATH.exists():
        st_functions.inject_custom_loader(LOADING_GIF_PATH)
    st_functions.inject_spinning_logo_css(SITE_ICON)
    return True

@st.cache_resource
def check_tools_cached():
    return validation.check_mrf_tools_installed()
    

# --- Main app --- #
def main():
    """
    Main function to run the Streamlit app.
    """
    # Setup
    st.set_page_config(page_title="Pre-CAT", initial_sidebar_state="expanded", page_icon=SITE_ICON)
    setup_assets()
    state_management.initialize_session_state()
    if "temp_dir_manager" not in st.session_state:
        st.session_state.temp_dir_manager = data_management.TempDirManager()
    ui.render_sidebar()
    hoverable_pre_cat = st_functions.add_hoverable_title_with_image_inline(
        "Pre-CAT", "https://i.ibb.co/gMQ7MCb/Subject-4.png"
    )
    st.markdown(
        f"<h1 style='font-size: 3rem; font-weight: bold;'>Welcome to {hoverable_pre_cat}</h1>",
        unsafe_allow_html=True
    )
    st.write("### A preclinical CEST-MRI analysis toolbox.")
    if not check_tools_cached:
        st.error('CEST-MRF tools not found.')
        st.markdown("""
        The required simulation libraries are missing or not compiled. 
        
        **To fix this:**
        1. Open your terminal in the `Pre-CAT` folder.
        2. Ensure your environment is active: `conda activate pre-cat`
        3. Navigate to the correct directory: `cd open-py-cest-mrf`
        4. Run the setup script: `python setup.py install`
        5. Close the app and rerun.
        """)
        st.stop()
    # Main state machine
    with st.expander("Load data", expanded=not st.session_state.is_submitted):
        submission.do_data_submission()
    if st.session_state.is_submitted:
        with st.expander("Process data", expanded=st.session_state.processing_active):
            for msg, msg_type in st.session_state.get("log_messages", []):
                if msg_type == 'success':
                    st.success(msg)
                elif msg_type == 'warning':
                    st.warning(msg)
                elif msg_type == 'error':
                    st.error(msg)
                else:
                    st.info(msg)
            processing.do_processing_pipeline()
    if st.session_state.is_processed:
        with st.expander("Display and save results", expanded=st.session_state.display_data):
            results.display_results()

    if st.button("Reset"):
        state_management.clear_session_state()
        st.rerun()

if __name__ == "__main__":
    multiprocessing.set_start_method('spawn', force=True)
    main()