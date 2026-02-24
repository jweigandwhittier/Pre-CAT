#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 23 16:27:44 2026

@author: jonah
"""
import os
import io
import zipfile
import tempfile
import shutil
import streamlit as st

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

def create_zip_in_memory(directory_path):
    """
    Zips an entire directory and returns it as an in-memory BytesIO object.
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                # Create a relative path for files in zip
                archive_name = os.path.relpath(file_path, directory_path)
                zip_file.write(file_path, archive_name)
    zip_buffer.seek(0)
    return zip_buffer

def prepare_data_for_saving(pixel_maps, b1_map, wassr_map, t1_map, quesp_maps):
    """
    Selects only the necessary, final data from session_state for saving.
    It dynamically builds the 'fits' dictionary to only include
    data that was actually calculated and all generated pixelwise maps.
    """
    # 1. Start with the essentials
    data_to_save = {
        'submitted_data': st.session_state.submitted_data,
        'user_geometry': st.session_state.user_geometry,
        'log_messages': st.session_state.log_messages,
        'fits': {} # Initialize an empty dict
    }
    # 2. Define all *possible* non-map fit keys
    possible_fit_keys = [
        'cest', 'wassr', 'damb1', 
        'quesp', 't1', 'cest-mrf'
    ]
    # 3. Dynamically add *only* the data that actually exists
    for key in possible_fit_keys:
        fit_data = st.session_state.fits.get(key)
        if fit_data is not None:
            data_to_save['fits'][key] = fit_data
    # 4. Add all generated pixelwise maps
    if pixel_maps is not None:
        data_to_save['fits']['cest_maps'] = pixel_maps
    if b1_map is not None:
        data_to_save['fits']['b1_interpolated_map'] = b1_map
    if wassr_map is not None:
        data_to_save['fits']['b0_map'] = wassr_map
    if t1_map is not None:
        data_to_save['fits']['t1_map'] = t1_map
    if quesp_maps is not None:
        data_to_save['fits']['quesp_maps'] = quesp_maps
    return data_to_save    