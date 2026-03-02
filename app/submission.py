#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 23 15:57:39 2026

@author: jonah
"""
import os
import zipfile
from pathlib import Path 
from app import validation
from scripts import load_study, quesp_fitting, BrukerMRI
from scripts.mrf_scripts import parse_config
import streamlit as st

def do_data_submission():
    """
    Handles the data submission form.
    """
    options = ["CEST", "QUESP", "CEST-MRF", "WASSR", "DAMB1"]
    organs = ["Cardiac", "Other"]
    col1, col2 = st.columns((1,1))
    with col1:
        selection = st.multiselect("Experiment type(s)", options)
    with col2:
        anatomy = st.pills("ROI", organs)
    
    if selection and anatomy:

        manager = st.session_state.temp_dir_manager
        uploaded_zip = st.file_uploader("Upload entire ParaVision study (.zip file)", type="zip")

        folder_path = st.session_state.get("extracted_folder_path")
        base_folder_name = st.session_state.get("extracted_base_name")

        if uploaded_zip:
            zip_id = f"{uploaded_zip.name}_{uploaded_zip.size}"
            if st.session_state.get("last_zip_id") != zip_id:
                with st.spinner("Extracting and verifying study...") as status:
                    try:
                        # Create a temp directory to extract the zip file
                        temp_upload_dir = Path(manager.get_upload_dir()).resolve()
                        with zipfile.ZipFile(uploaded_zip, 'r') as zip_ref:
                            # Add some security checks
                            total_size = sum(file.file_size for file in zip_ref.infolist())
                            if total_size > 3*1024*1024*1024:
                                raise ValueError("Uncompressed data exceeds 3GB limit.")
                            for member in zip_ref.namelist():
                                target_path = (temp_upload_dir / member).resolve()
                                if temp_upload_dir not in target_path.parents and temp_upload_dir != target_path:
                                    raise PermissionError(f"Blocked malicious path: {member}")
                            zip_ref.extractall(temp_upload_dir)
                        safe_zip_name = os.path.basename(uploaded_zip.name)
                        expected_folder_name = Path(safe_zip_name).stem
                        potential_path = temp_upload_dir / expected_folder_name
                        folder_path = potential_path if potential_path.is_dir() else temp_upload_dir
                        base_folder_name = folder_path.name
                        # Store in session state
                        st.session_state.extracted_folder_path = folder_path
                        st.session_state.extracted_base_name = folder_path.name
                        st.session_state.last_zip_id = zip_id
                        st.success("Extraction complete!")
                    except Exception as e:
                        st.error(f"Security/Processing Error: {e}")
                        manager.cleanup_now()
                        folder_path = None

        save_suffix = st.text_input('Output suffix (optional)',
            placeholder = 'Liver_5uT_Radial_v1',
            help="This will be appended to the study folder name.")
        final_save_name = None
        if base_folder_name:
            if save_suffix:
                # Clean up suffix just in case
                clean_suffix = save_suffix.strip().replace(" ", "_")
                final_save_name = f"{base_folder_name}_{clean_suffix}"
            else:
                final_save_name = base_folder_name
            # Display the final name to the user
            st.success(f"Final output name will be: **{final_save_name}.zip**")
        
        cest_validation = True
        quesp_validation = True
        mrf_validation = True
        wassr_validation = True
        damb1_validation = True
        all_fields_filled = True  

        if not folder_path or not final_save_name:
            all_fields_filled = False
    
        if folder_path and os.path.isdir(folder_path):
            
            # CEST validation
            if "CEST" in selection:
                cest_path = st.text_input('Input CEST experiment number', placeholder='3')
                if not cest_path:
                    all_fields_filled = False  # CEST path is required
                if cest_path:
                    smoothing_filter = True
                    moco_cest = False
                    pca = False
                    pixelwise = False
                    cest_type = st.radio('CEST acquisition type', ["Radial", "Rectilinear"], horizontal=True)
                    st.markdown(
                    """
                    <style>
                    .custom-label {
                        font-size: 0.875rem; /* Matches theme.fontSizes.sm */
                        display: flex;
                        align-items: center;
                        margin-bottom: 0.25rem; /* Matches theme.spacing.twoXS */
                        min-height: 1.25rem; /* Matches theme.fontSizes.xl */
                        font-family: 'Source Sans Pro', sans-serif;
                        font-weight: normal; /* Ensure weight matches */
                        line-height: 1.6; /* Ensures vertical alignment */
                    }
                    </style>
                    <label class="custom-label">
                      Additional settings
                    </label>
                    </div>
                    """,
                    unsafe_allow_html=True,
                    )
                    if "CEST" in selection and cest_type == "Radial":
                        moco_cest = st.toggle('Motion correction (CEST)', help="Correct bulk motion by discarding spokes based on projection images.")
                    pca = st.toggle('Z-spectral denoising', help="Z-spectral denoising with principal component analysis. This is a *global* method using Malinowskis empirical indicator function.")
                    pixelwise = st.toggle(
                        'Pixelwise mapping', help="Accuracy is highly dependent on field homogeneity.")
                    if pixelwise:
                        smoothing_filter = st.toggle('Median smoothing filter', help="Apply a median filter to smooth contrast maps.")
                    if anatomy == "Other":
                        reference = st.toggle(
                            'Additional reference image', help="Use this option to load an additional reference image for ROI(s)/masking. By default, the unsaturated (S0/M0) image is used.")
                        if reference:
                            all_fields_filled = False
                            reference_path = st.text_input('Input reference experiment number', help='Reference image assumed to be rectilinear. Please only use single slice images.')
                            if reference_path:
                                reference_full_path = os.path.join(folder_path, reference_path)
                                all_fields_filled = True
                                reference_validation = False
                                if os.path.isdir(reference_full_path):  
                                    reference_validation = True
                                    missing_items = validation.validate_rectilinear(reference_full_path)
                                    if missing_items:
                                        st.error(f"Reference folder is missing the following required items: {', '.join(missing_items)}")
                                        reference_validation = False
                                    else:
                                        reference_image = load_study.load_bruker_img(reference_path, folder_path)
                                        if reference_image.shape[2] != 1:
                                            st.error("Reference image contains multislice data! Currently, only single slice data is allowed.")
                                            reference_validation = False
                                        else:
                                           st.session_state.reference = reference_image 
                                else:
                                    st.error(f"Reference folder does not exist: {reference_full_path}")
                                    reference_validation = False
                                
                        choose_contrasts = st.toggle(
                            'Choose contrasts', help="Default contrasts are: amide, creatine, NOE. Water and MT are always fit.")
                        if choose_contrasts:
                            contrasts = ["NOE (-3.5 ppm)", "Amide", "Creatine", "Amine", "Hydroxyl", "NOE (-1.6 ppm)", "Salicylic acid"]
                            default_contrasts = ["NOE (-3.5 ppm)", "Amide", "Creatine", "NOE (-1.6 ppm)"]
                            contrast_selection = st.pills ("Contrasts", contrasts, default=default_contrasts, selection_mode="multi")
                            st.session_state.custom_contrasts = contrast_selection
                        else:
                            st.session_state.custom_contrasts = None
                    elif anatomy == "Cardiac":
                        st.session_state.reference = None
                        st.session_state.custom_contrasts = None
                    if not cest_type:
                        all_fields_filled = False  
                    cest_full_path = os.path.join(folder_path, cest_path)
                    if os.path.isdir(cest_full_path):
                        if cest_type == "Rectilinear" and "traj" in os.listdir(cest_full_path):
                            st.warning("The presence of a gradient trajectory file suggests the data might be radial. Please verify your acquisition type.")
                        missing_items = validation.validate_radial(cest_full_path) if cest_type == "Radial" else validation.validate_rectilinear(cest_full_path)
                        if missing_items:
                            st.error(f"CEST folder is missing the following required items: {', '.join(missing_items)}")
                            cest_validation = False
                        if cest_validation:
                            st.success("CEST folder validation successful!")
                    else:
                        st.error(f"CEST folder does not exist: {cest_full_path}")
                        cest_validation = False

            # QUESP validation
            if "QUESP" in selection:
                if anatomy == 'Cardiac':
                    quesp_validation = False
                    st.error("QUESP analysis is only supported for non-cardiac ROIs at this time.")
                else:
                    t1_input_method = None
                    fixed_t1_s = None
                    t1_path = None
                    quesp_path = st.text_input('Input QUESP experiment number', placeholder='4', help="Currently, only QUESP data acquired using the 'fp_EPI' sequence are supported.")
                    
                    t1_input_method = st.radio("T1 Input Method", ["Use T1 Map", "Use Fixed T1 Value"], horizontal=True, key="quesp_t1_method")
                    
                    if t1_input_method == "Use T1 Map":
                        t1_path = st.text_input('Input T1 mapping experiment number', placeholder='5', help="Currently, only VTR RARE T1 mapping is supported.")
                    elif t1_input_method == "Use Fixed T1 Value":
                        fixed_t1_s = st.number_input("Input Fixed T1 Value (ms)", min_value=1, value=2000, step=1, format="%i", help="Enter the global T1 relaxation time in milliseconds.")
                    quesp_inputs_provided = quesp_path and \
                                          (t1_input_method == "Use T1 Map" and t1_path) or \
                                          (t1_input_method == "Use Fixed T1 Value" and fixed_t1_s is not None)

                    if quesp_inputs_provided:
                        fixed_fb = None
                        quesp_type = st.radio('QUESP analysis type', ["Standard (MTRasym)", "Inverse (MTRrex)", "Omega Plot"], horizontal=True)
                        quesp_denoise = st.toggle('Use PCA denoising (experimental)?')
                        if not quesp_type:
                            all_fields_filled = False
                        enforce_fb = st.toggle('Enforce fixed proton volume fraction?', help = "Can be used for phantoms with known solute concentrations. Assumes 55.5M water.")
                        if enforce_fb:
                            fixed_conc = st.number_input(
                            label='Input solute concentration (mM)',
                            min_value=0.0,
                            value=50.0,
                            format="%.2f")
                            labile_protons = st.number_input(
                            label='Input number of labile protons',
                            min_value=0, 
                            value=2,   
                            step=1)
                            fixed_fb = quesp_fitting.calc_proton_volume_fraction(fixed_conc, labile_protons)
                        
                        quesp_full_path = os.path.join(folder_path, quesp_path)
                        quesp_folder_exists = os.path.isdir(quesp_full_path)
                        
                        t1_full_path = None
                        t1_folder_exists = False

                        if t1_input_method == "Use T1 Map":
                            t1_full_path = os.path.join(folder_path, t1_path)
                            t1_folder_exists = os.path.isdir(t1_full_path)
                            if not t1_folder_exists:
                                st.error(f"T1 map folder does not exist: {t1_full_path}")
                                quesp_validation = False
                        elif t1_input_method == "Use Fixed T1 Value":
                            # Set to True to pass the next 'if' check, as no folder is needed
                            t1_folder_exists = True
                            st.success(f"Using fixed T1 value: {fixed_t1_s} ms")
                        
                        if not quesp_folder_exists:
                            st.error(f"QUESP folder does not exist: {quesp_full_path}")
                            quesp_validation = False
                        
                        if quesp_folder_exists and t1_folder_exists:
                            if t1_input_method == "Use T1 Map":
                                bad_quesp_method, check_quesp, check_t1 = validation.validate_fp_quesp(folder_path, quesp_path, t1_path)
                                if bad_quesp_method:
                                    quesp_validation = False
                                    if check_quesp != "<User:fp_EPI>":
                                        st.error(f"Incorrect QUESP method detected: **{check_quesp}**. Only **<User:fp_EPI>** is supported.")
                                    if check_t1 != "<Bruker:RAREVTR>":
                                        st.error(f"Incorrect T1 mapping method detected: **{check_t1}**. Only **<Bruker:RAREVTR>** is supported.")
                                else:
                                    st.success("Method validation successful!")
                            elif t1_input_method == "Use Fixed T1 Value":
                                # Only need to validate the QUESP method
                                try:
                                    exp_quesp = BrukerMRI.ReadExperiment(folder_path, quesp_path)
                                    check_quesp = exp_quesp.method['Method']
                                    if check_quesp != "<User:fp_EPI>":
                                        quesp_validation = False
                                        st.error(f"Incorrect QUESP method detected: **{check_quesp}**. Only **<User:fp_EPI>** is supported.")
                                    else:
                                        st.success("QUESP method validation successful!")
                                except Exception as e:
                                    st.error(f"Error validating QUESP method: {e}")
                                    quesp_validation = False
                    else:
                         all_fields_filled = False

            # CEST-MRF validation
            if "CEST-MRF" in selection:
                if anatomy == 'Cardiac':
                    st.error("CEST-MRF analysis is only supported for non-cardiac ROIs at this time.")
                else:
                    mrf_path = st.text_input('Input CEST-MRF experiment number', placeholder='4', help="Currently, only CEST-MRF data acquired using the 'fp_EPI' sequence are supported.")
                    if mrf_path:
                        mrf_full_path = os.path.join(folder_path, mrf_path)
                        mrf_folder_exists = os.path.isdir(mrf_full_path)
                        if not mrf_folder_exists:
                            st.error(f"MRF folder does not exist: {mrf_full_path}")
                            mrf_validation = False
                        else:
                            bad_mrf_method, check_mrf = validation.validate_mrf(folder_path, mrf_path)
                            if bad_mrf_method:
                                st.error(f"Incorrect CEST-MRF method detected: **{check_mrf}**. Only **<User:fp_EPI>** is supported.")
                                mrf_validation = False
                            else:
                                manager = st.session_state.temp_dir_manager
                                config_path = None
                                config_file = st.file_uploader("Upload Python config (.py fle)", type="py", help="Example config file available at */Pre-CAT/configs/mrf/example_config.py* or on *GitHub*")
                                if config_file is not None:
                                    # Get the session's temporary upload directory
                                    temp_dir = manager.get_upload_dir()
                                    # Construct the full path for the config inside the temp directory
                                    config_path = os.path.join(temp_dir, config_file.name)
                                    # Write the uploaded file's content to that path
                                    with open(config_path, 'wb') as f:
                                        f.write(config_file.getvalue())
                                    # st.success(f"Config saved to temporary path: {config_path}")
                                if config_path:
                                    config_exists = os.path.isfile(config_path)
                                    if not config_exists:
                                        st.error(f"Config file does not exist: {config_path}")
                                        mrf_validation = False
                                    else:
                                        try:
                                            config = parse_config.build_config_from_file(config_path)
                                            proton_params = parse_config.get_proton_params(config_path)
                                        except Exception as e:
                                            st.error(f"Error processing config file: {e}")
                                            mrf_validation = False
                                        upload_dict = st.toggle("Upload precalculated MATLAB dictionary?")
                                        dict_path = None 
                                        if upload_dict:
                                            st.warning('**WARNING** Double check that your dictionary matches BOTH the uploaded config file AND imaging acquisition schedule!!')
                                            dict_file = st.file_uploader("Upload MATLAB dictionary (.mat file)", type="mat")
                                            if dict_file is not None:
                                                temp_dir = manager.get_upload_dir()
                                                dict_path = os.path.join(temp_dir, dict_file.name)
                                                with open(dict_path, 'wb') as f:
                                                    f.write(dict_file.getvalue())
                                                    # st.success(f"Dictionary saved to temporary path: {dict_path}")
                                            else:
                                                all_fields_filled = False
                                else:
                                    all_fields_filled = False
                                if config_path and ((upload_dict and dict_path) or not upload_dict):
                                    dict_methods = ['Dot product', 'Deep learning']
                                    mrf_method = st.pills("Dictionary matching method", dict_methods, default='Dot product')
                                    if mrf_method == 'Deep learning':
                                        st.error("Deep learning recon has not been implemented. Please choose dot product matching for now.")
                                        mrf_validation = False
                    else:
                        all_fields_filled = False

            # WASSR validation
            if "WASSR" in selection:
                wassr_path = st.text_input('Input WASSR experiment number', placeholder='4')
                if not wassr_path:
                    all_fields_filled = False  # WASSR path is required
                if wassr_path:
                    moco_wassr = False
                    wassr_type = st.radio('WASSR acquisition type', ["Radial", "Rectilinear"], horizontal=True)
                    full_b0_mapping = st.toggle('Full B0 mapping', value=False, help="Fit B0 map for the entire image. Slower, but allows for full map visualization.") 
                    if "WASSR" in selection and wassr_type == "Radial":
                        moco_wassr = st.toggle('Motion correction (WASSR)', help="Correct bulk motion by discarding spokes based on projection images.")
                    if not wassr_type:
                        all_fields_filled = False  
                    wassr_full_path = os.path.join(folder_path, wassr_path)
                    if os.path.isdir(wassr_full_path):
                        if wassr_type == "Rectilinear" and "traj" in os.listdir(wassr_full_path):
                            st.warning("The presence of a gradient trajectory file suggests the data might be radial.")
                        missing_items = validation.validate_radial(wassr_full_path) if wassr_type == "Radial" else validation.validate_rectilinear(wassr_full_path)
                        if missing_items:
                            st.error(f"WASSR folder is missing the following required items: {', '.join(missing_items)}")
                            wassr_validation = False
                        if wassr_validation:
                            st.success("WASSR folder validation successful!")
                    else:
                        st.error(f"WASSR folder does not exist: {wassr_full_path}")
                        wassr_validation = False
    
            # DAMB1 validation
            if "DAMB1" in selection:
                theta_path = st.text_input('Input DAMB1 experiment number for α', placeholder='5')
                two_theta_path = st.text_input('Input DAMB1 experiment number for 2α', placeholder='6')
                if not theta_path or not two_theta_path:
                    all_fields_filled = False 
    
                if theta_path and two_theta_path:
                    theta_full_path = os.path.join(folder_path, theta_path)
                    two_theta_full_path = os.path.join(folder_path, two_theta_path)
    
                    if os.path.isdir(theta_full_path):
                        theta_missing_items = validation.validate_rectilinear(theta_full_path)
                        if theta_missing_items:
                            st.error(f"DAMB1 α folder is missing the following required items: {', '.join(theta_missing_items)}")
                            damb1_validation = False
                        else:
                            st.success("DAMB1 α folder validation successful!")
                    else:
                        st.error(f"DAMB1 α folder does not exist: {theta_full_path}")
                        damb1_validation = False
    
                    if os.path.isdir(two_theta_full_path):
                        two_theta_missing_items = validation.validate_rectilinear(two_theta_full_path)
                        if two_theta_missing_items:
                            st.error(f"DAMB1 2α folder is missing the following required items: {', '.join(two_theta_missing_items)}")
                            damb1_validation = False
                        else:
                            st.success("DAMB1 2α folder validation successful!")
                    else:
                        st.error(f"DAMB1 2α folder does not exist: {two_theta_full_path}")
                        damb1_validation = False

                    if os.path.isdir(theta_full_path) and os.path.isdir(two_theta_full_path):
                        bad_flips, theta, two_theta = validation.validate_double_angle(folder_path, theta_path, two_theta_path)  
                        if bad_flips:
                            st.error("Incorrect flip angles: α = %i, 2α = %i" % (theta, two_theta))
                        else:
                            st.success("Flip angle validation successful! ")
            
            # Check if all fields are filled before enabling submit
            if all_fields_filled and (cest_validation and wassr_validation and mrf_validation and damb1_validation and quesp_validation):
                if 'reference' in locals() and reference and reference_validation == False:
                    st.error("Please validate the additional reference image before submitting.")
                else:
                    if st.button("Submit"):
                        st.session_state.is_submitted = True
                        st.session_state.processing_active = True
                        temp_results_dir = manager.get_results_dir()
                        save_path = temp_results_dir
                        st.session_state.submitted_data = {
                            "folder_path": folder_path,
                            "save_path": save_path,
                            "save_name": final_save_name,
                            "selection": selection,
                            "organ": anatomy,
                            "reference": st.session_state.get("reference"),
                            "custom_contrasts": st.session_state.get("custom_contrasts"),}
                        if "CEST" in selection:
                            st.session_state.submitted_data['cest_path'] = cest_path
                            st.session_state.submitted_data['cest_type'] = cest_type
                            st.session_state.submitted_data['pixelwise'] = pixelwise
                            st.session_state.submitted_data['smoothing_filter'] = smoothing_filter
                            st.session_state.submitted_data['moco_cest'] = moco_cest
                            st.session_state.submitted_data['pca'] = pca
                        if "WASSR" in selection: 
                            st.session_state.submitted_data['wassr_path'] = wassr_path
                            st.session_state.submitted_data['wassr_type'] = wassr_type
                            st.session_state.submitted_data['full_b0_mapping'] = full_b0_mapping
                            st.session_state.submitted_data['moco_wassr'] = moco_wassr
                        if "DAMB1" in selection:
                            st.session_state.submitted_data['theta_path'] = theta_path
                            st.session_state.submitted_data['two_theta_path'] = two_theta_path
                        if "QUESP" in selection:
                            st.session_state.submitted_data['quesp_path'] = quesp_path
                            st.session_state.submitted_data['t1_path'] = t1_path
                            st.session_state.submitted_data['fixed_t1'] = fixed_t1_s
                            st.session_state.submitted_data['quesp_denoise'] = quesp_denoise
                            st.session_state.submitted_data['quesp_type'] = quesp_type
                            st.session_state.submitted_data['fixed_fb'] = fixed_fb
                        if "CEST-MRF" in selection:
                            mrf_files_dir = os.path.join(save_path, 'mrf_files') 
                            os.makedirs(mrf_files_dir, exist_ok=True)
                            if config is not None:
                                config['yaml_fn'] = os.path.join(mrf_files_dir, 'scenario.yaml')
                                config['seq_fn'] = os.path.join(mrf_files_dir, 'acq_protocol.seq')
                                if upload_dict and dict_path:
                                    config['dict_fn'] = dict_path
                                else:
                                    config['dict_fn'] = os.path.join(mrf_files_dir, 'dict.mat')
                            st.session_state.submitted_data['mrf_path'] = mrf_path
                            st.session_state.submitted_data['mrf_config'] = config
                            st.session_state.submitted_data['proton_params'] = proton_params
                            st.session_state.submitted_data['mrf_method'] = mrf_method
                            st.session_state.submitted_data['upload_dict'] = upload_dict
                            st.session_state.submitted_data['dict_path'] = dict_path
                        st.rerun()
            else:
                if not all_fields_filled:
                    st.error("Please fill in all the required fields before submitting.")
