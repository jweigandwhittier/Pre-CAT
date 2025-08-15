import numpy as np
import streamlit as st
import numpy.linalg as la
import scipy.io as sio

def mrf_dot_prod(dict_path, image_stack, roi_masks):
    """
    Wrapper function to run dot-product matching for all ROIs and display progress.
    """
    dictionary = sio.loadmat(dict_path)
    results_by_roi = {}

    # --- >> NEW: Create Streamlit elements for progress tracking << ---
    st.write("Performing MRF dot-product matching...")
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    total_rois = len(roi_masks)
    for i, (roi_name, mask) in enumerate(roi_masks.items()):
        status_text.text(f"Fitting ROI: '{roi_name}' ({i + 1}/{total_rois})...")
        progress_bar.progress(0) # Reset bar for each new ROI
        
        quantitative_maps = dot_prod_matching_roi(
            dictionary=dictionary,
            image_stack=image_stack, # Corrected variable name from mrf_image_stack
            roi_mask=mask,
            progress_bar=progress_bar, # Pass the progress bar
            status_text=status_text      # Pass the status text element
        )
        results_by_roi[roi_name] = quantitative_maps
        
    # --- >> NEW: Finalize the status display << ---
    status_text.text("Fitting complete!")
    progress_bar.progress(100)
    
    return results_by_roi


def dot_prod_matching_roi(dictionary, image_stack, roi_mask, batch_size=256, progress_bar=None, status_text=None):
    """
    Performs dot-product matching on pixels within a specified ROI.
    Corrected for image stacks with shape (rows, cols, n_iter).
    """
    # --- [Section 1: No changes needed here] ---
    # ... (dictionary parsing logic is unaffected)
    synt_dict = dictionary
    if len(synt_dict.keys()) < 4:
        for k in synt_dict.keys():
            if k[0] != '_':
                key = k
        synt_dict = synt_dict[key][0]
        dict_t1w = synt_dict['t1w'][0].transpose()
        dict_t2w = synt_dict['t2w'][0].transpose()
        dict_t1s = synt_dict['t1s'][0].transpose()
        dict_t2s = synt_dict['t2s'][0].transpose()
        dict_fs = synt_dict['fs'][0].transpose()
        dict_ksw = synt_dict['ksw'][0].transpose()
        synt_sig = synt_dict['sig'][0]
    else:
        dict_t1w = synt_dict['t1w']
        dict_t2w = synt_dict['t2w']
        dict_t1s = synt_dict['t1s_0']
        dict_t2s = synt_dict['t2s_0']
        dict_fs = synt_dict['fs_0']
        dict_ksw = synt_dict['ksw_0']
        synt_sig = np.transpose(synt_dict['sig'])

    # --- 2. Select and Reshape Data from the ROI (Corrected) ---
    # Unpack dimensions according to the (rows, cols, n_iter) format
    rows, cols, n_iter = image_stack.shape
    
    # -->> THE FIX: Correctly index with the mask and transpose the result <<--
    # This creates a 2D array of shape (n_iter, n_roi_pixels)
    data = image_stack[roi_mask].T
    n_roi_pixels = data.shape[1]
    
    if n_roi_pixels == 0:
        print("Warning: The provided ROI mask is empty. Returning empty maps.")
        return {key: np.zeros((rows, cols)) for key in ['dp', 't1w', 't2w', 'fs', 'ksw', 't1s', 't2s']}

    # --- [Sections 3, 4, 5, and 6: No other changes needed] ---
    # The rest of the function works correctly with the properly shaped 'data' array.
    dp = np.zeros(n_roi_pixels)
    t1w = np.zeros(n_roi_pixels)
    t2w = np.zeros(n_roi_pixels)
    t1s = np.zeros(n_roi_pixels)
    t2s = np.zeros(n_roi_pixels)
    fs = np.zeros(n_roi_pixels)
    ksw = np.zeros(n_roi_pixels)
    norm_dict = synt_sig / (la.norm(synt_sig, axis=0) + 1e-10)
    norm_data = data / (la.norm(data, axis=0) + 1e-10)

    for i in range(0, n_roi_pixels, batch_size):
        batch_end = min(i + batch_size, n_roi_pixels)
        batch_data = norm_data[:, i:batch_end]
        
        current_score = np.dot(batch_data.T, norm_dict)
        dp_ind = np.argmax(current_score, axis=1)
        
        dp[i:batch_end] = np.max(current_score, axis=1)
        t1w[i:batch_end] = dict_t1w[0, dp_ind]
        t2w[i:batch_end] = dict_t2w[0, dp_ind]
        t1s[i:batch_end] = dict_t1s[0, dp_ind]
        t2s[i:batch_end] = dict_t2s[0, dp_ind]
        fs[i:batch_end] = dict_fs[0, dp_ind]
        ksw[i:batch_end] = dict_ksw[0, dp_ind]
        
        if progress_bar is not None:
            progress_percent = batch_end / n_roi_pixels
            progress_bar.progress(int(progress_percent * 100))
        if status_text is not None:
            status_text.text(f"Processing batch... {batch_end}/{n_roi_pixels} pixels ({int(progress_percent * 100)}%)")

    quant_maps = {}
    results = {'dp': dp, 't1w': t1w, 't2w': t2w, 'fs': fs, 'ksw': ksw, 't1s': t1s, 't2s': t2s}
    for key, values in results.items():
        map_image = np.zeros((rows, cols))
        map_image[roi_mask] = values
        quant_maps[key] = map_image

    return quant_maps