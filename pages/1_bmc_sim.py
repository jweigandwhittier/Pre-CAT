#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep 26 13:30:02 2025

@author: jonah
"""
# --- Imports --- #
# Standard library imports
import os 
import subprocess
import sys
import importlib.metadata
from pathlib import Path 
# Third-party imports
import streamlit as st
# Local application imports
from custom import st_functions

# --- Constants for app setup --- #
SITE_ICON = "custom/icons/ksp.ico"
LOADING_GIF_PATH = Path("custom/icons/loading.gif")

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
    for key in list(st.session_state.keys()):
        del st.session_state[key]

# --- Data validation -- #
def validate_method(directory, method_path):
    """
    Check to make sure the sequece is actually fp_EPI.
    """
    exp = BrukerMRI.ReadExperiment(directory, method_path)
    check = exp.method['Method']
    if check != "<User:fp_EPI>":
        return True, check
    else:
        return False, check

# --- UI functions --- #
def render_sidebar():
    """
    Renders sidebar content (disclaimers, contact info, etc.)
    """
    with st.sidebar:
        st.page_link("app.py", label="Pre-CAT", icon="🐈")
        pulseq_url = "https://github.com/kherz/pulseq-cest-library"
        st.write("""## Instructions
Follow each step after carefully reading associated instructions.

Example scenarios, sequences, and Pulseq files can be found at the [Pulseq-CEST library](%s) repository.
        """ % pulseq_url)
        st.write("""## Citation
This webapp is associated with the following papers, please cite this work when using the **BMC Simulation Platform**. \n
Vladimirov N, Cohen O, Heo H-Y, et al. *Quantitative molecular imaging using deep magnetic resonance fingerprinting*. Nat Protocols (2025). 10.1038/s41596-025-01152-w. \n
Herz K, Mueller S, Perlman O, et al. *Pulseq-CEST: Towards multi-site multi-vendor compatibility and reproducibility of CEST experiments using an open-source sequence standard*. Magn Reson Med (2021). 10.1002/mrm.28825. 
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
    data_validation = True
    config_path = st.text_input('Input CEST scenario path', placeholder = "/Pre-CAT/configs/sim/example_config.yaml", help="Example config file available at */Pre-CAT/configs/sim/example_config.yaml*")
    if config_path:
        config_exists = os.path.isfile(config_path)
        if not config_exists:
            st.error(f"Config file does not exist: {config_path}")
            data_validation = False
        else:
            seq_type = st.radio('Load sequence', ['From .seq file', 'From method file'], horizontal=True)
            if seq_type == 'From .seq file':
                seq_path = st.text_input('Input sequence path', placeholder = "/Pre-CAT/configs/sim/seq/gauss_sim.seq", help="Example config file available at */Pre-CAT/configs/sim/seq/gauss_sim.seq*")
            if seq_type == 'From method file':
                method_path = st.text_input('Input method file path', placeholder = "User/Documents/MRI_Data/Project/Scan_ID/Exp_Num/method", help="Currently, only data acquired using the 'fp_EPI' sequence are supported.")




# --- Main app --- #
def main():
    """
    Main function to run the Streamlit app.
    """
    # Setup
    st.set_page_config(page_title="BMCSim", initial_sidebar_state="expanded", page_icon=SITE_ICON)
    if LOADING_GIF_PATH.exists():
        st_functions.inject_custom_loader(LOADING_GIF_PATH)
    st_functions.inject_spinning_logo_css(SITE_ICON)
    initialize_session_state()
    render_sidebar()
    st.title("BMC Simulation Platform")
    st.write("### A GUI for BMCTool simulations.")
    # Main state machine
    with st.expander("Simulation parameters", expanded=not st.session_state.is_submitted):
        do_data_submission()

if __name__ == "__main__":
    main()