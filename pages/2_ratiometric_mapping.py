#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 29 11:27:34 2025

@author: jonah
"""
# --- Imports --- #
# Standard library imports
import os 
from pathlib import Path 
# Third-party imports
import streamlit as st
# Local application imports
from custom import st_functions

# --- Constants for app setup --- #
SITE_ICON = "custom/icons/ksp.ico"
LOADING_GIF_PATH = Path("custom/icons/loading.gif")

# --- Class for managing temporary directories --- #
class TempDirManager:
    """
    Manages session-specific temporary directories.
    
    Crucially, it uses a __del__ finalizer to ensure
    these directories are cleaned up when the Streamlit
    session is garbage collected (e.g., user closes tab or times out).
    """
    def __init__(self):
        self._upload_dir = None
        self._results_dir = None
    
    def get_upload_dir(self):
        """Get or create the temp upload dir for this session."""
        if self._upload_dir is None or not os.path.isdir(self._upload_dir):
            self._upload_dir = tempfile.mkdtemp(prefix="precat_upload_")
        return self._upload_dir
    
    def get_results_dir(self):
        """Get or create the temp results dir for this session."""
        if self._results_dir is None or not os.path.isdir(self._results_dir):
            self._results_dir = tempfile.mkdtemp(prefix="precat_results_")
        return self._results_dir

    def _cleanup(self):
        """Safely removes the directories."""
        if self._upload_dir and os.path.isdir(self._upload_dir):
            try:
                shutil.rmtree(self._upload_dir)
            except Exception as e:
                # Log this error for debugging on your server
                print(f"Error cleaning up {self._upload_dir}: {e}")
        
        if self._results_dir and os.path.isdir(self._results_dir):
            try:
                shutil.rmtree(self._results_dir)
            except Exception as e:
                print(f"Error cleaning up {self._results_dir}: {e}")

    def cleanup_now(self):
        """Forcibly clean up and reset paths (used by 'Reset' button)."""
        self._cleanup()
        self._upload_dir = None
        self._results_dir = None

    def __del__(self):
        """Finalizer called by Python garbage collector on session end."""
        self._cleanup()

# --- Session state management --- #
def initialize_session_state():
    """
    Initializes all necessary state condition variables with a checklist system.
    """
    defaults = {
        # Core app state
        "is_submitted": False,
        "processing_active": False,
        "is_processed": False,
        "display_data": False,
        # User selections
        "submitted_data": {},
        # Checklist for pipeline stages
        "pipeline_status": {
            "install_done": False,
            },
        # Data storage
    
        # Log messages
        "log_messages": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def clear_session_state():
    """
    Clears all keys from the session state.
    This is used to reset the app.
    """
    if "temp_dir_manager" in st.session_state:
        st.session_state.temp_dir_manager.cleanup_now()
    for key in list(st.session_state.keys()):
        del st.session_state[key]

# --- UI functions --- #
def render_sidebar():
    """
    Renders sidebar content (disclaimers, contact info, etc.)
    """
    with st.sidebar:
        st.page_link("app.py", label="Pre-CAT", icon="🐈")
        spsp_url = "https://github.com/jweigandwhittier/spspCEST"
        st.write("""## Instructions
Follow each step after carefully reading associated instructions. Data can be uploaded as raw GE/Siemens files (P-Files/TWIX) *or* DICOM.

For open-source implementations of ratiometric mapping sequences please request access to [this repository](%s) and send me a message with your intended use case.

## Disclaimer
This webapp is for *research purposes only* and is *not* intended for use as a diagnostic tool. \n
Do *not* submit data with protected health information (PHI). This webapp is selfhosted.

        """ % spsp_url)
        st.write("""## Citation
This webapp is associated with the following paper, please cite this work when using this tool. \n
Ayala C, Luo H, Godines K, et al. *Individually tailored spatial-spectral pulsed CEST MRI for ratiometric mapping of myocardial energetic species at 3T*. Magn Reson Med (2023). 10.1002/mrm.29801. 
""")
        st_functions.inject_hover_email_css()
        st.write("## Contact")
        st.markdown(f"""
        <p style="margin-bottom: 0">
        Contact me with any issues or questions: 
        <span class="hoverable-email">
            <a href="mailto:jweigandwhittier@berkeley.edu">jweigandwhittier@berkeley.edu</a>
            <span class="image-tooltip">
                <img src="https://i.ibb.co/M5h9MyF1/Subject-5.png" alt="Hover image">
            </span>
        </span>
        </p>
        <br>
        """, unsafe_allow_html=True)
        st.write("Please add **[Pre-CAT]** to the subject line of your email.")

def do_data_submission():
    """
    Handles the data submission form.
    """
    options = ['Raw', 'DICOM']
    organs = ['Cardiac', 'Other']
    col1, col2 = st.columns((1,1))
    with col1:
        selection = st.pills("Data type", options)
    with col2:
        anatomy = st.pills("ROI", organs)
    if selection and anatomy:
        if selection == 'Raw':
            datatype = ["dat", "h5"]
        elif selection == 'DICOM':
            datatype = "dcm"
        manager = st.session_state.temp_dir_manager
        gauss_file = st.file_uploader("Upload image with *Gaussian* saturation pulses", type=datatype)
        spsp_file = st.file_uploader("Upload image with *PCr selective* saturation pulses", type=datatype)

        folder_path = None 
        base_folder_name = None

        if gauss_file and spsp_file:
            # Create a temp directory to extract the zip file
            temp_upload_dir = manager.get_upload_dir()
            gauss_path = os.path.join(temp_dir, gauss_file.name)
            spsp_path = os.path.join(temp_dir, spsp_file.name)
        else:
            all_fields_filled = False
            
        final_save_name = st.text_input('Output filename',
            placeholder = 'ID_1913_10-31-25')
        if final_save_name:
            st.success(f"Final output name will be: **{final_save_name}.zip**")
        else:
            all_fields_filled = False
        if all_fields_filled:
            if st.button("Submit"):
                st.session_state.is_submitted = True
                st.session_state.processing_actve = True
                temp_results_dir = manager.get_results_dir()
                save_path = temp_results_dir
                st.session_state.submitted_data = {
                            "gauss_path": gauss_path,
                            "spsp_path": spsp_path,
                            "save_path": save_path,
                            "save_name": final_save_name,
                            "selection": selection,
                            "organ": anatomy}
                st.rerun()
        else:
            st.error("Please fill in all the required fields before submitting.")

def do_processing_pipeline():
    """
    Manages the sequential processing pipeline for all experiment types.
    """
    # Retrieve submitted experiment types 
    submitted = st.session_state.submitted_data



# --- Main app --- #
def main():
    """
    Main function to run the Streamlit app.
    """
    # Setup
    st.set_page_config(page_title="PCr/Cr-CAT", initial_sidebar_state="expanded", page_icon=SITE_ICON)
    if LOADING_GIF_PATH.exists():
        st_functions.inject_custom_loader(LOADING_GIF_PATH)
    st_functions.inject_spinning_logo_css(SITE_ICON)
    initialize_session_state()
    if "temp_dir_manager" not in st.session_state:
        st.session_state.temp_dir_manager = TempDirManager()
    render_sidebar()
    hoverable_pre_cat = st_functions.add_hoverable_title_with_image_inline(
        "PCr/Cr-CAT", "https://i.ibb.co/gMQ7MCb/Subject-4.png")
    st.markdown(
        f"<h1 style='font-size: 3rem; font-weight: bold;'>Welcome to {hoverable_pre_cat}</h1>",
        unsafe_allow_html=True
    )
    render_sidebar()
    st.write("### Ratiometric mapping of energetic species.")
    # Main state machine
    with st.expander("Load data", expanded=not st.session_state.is_submitted):
        do_data_submission()
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
            do_processing_pipeline()

if __name__ == "__main__":
    main()