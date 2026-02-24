#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 23 15:42:19 2026

@author: jonah
"""
import streamlit as st

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
        "custom_contrasts": None,
        "reference": None,
        # Checklist for pipeline stages
        "pipeline_status": {
            "mrf_gen_done": False,
            "recon_done": False,
            "orientation_done": False,
            "processing_done": False,
            "rois_done": False, # ROI drawing is a single event
            "fitting_done": [],
            },
        # Data storage
        "recon_data": {},
        "orientation_params": {"radial": None, "rectilinear": None},
        "processed_data": {},
        "user_geometry": {"rois": None, "masks": None, "aha": None},
        "fits": {},
        # Log messages
        "timing_log": [],
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