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
        
    status_text.text("Fitting complete!")
    progress_bar.progress(100)
    
    return results_by_roi


import numpy as np
import numpy.linalg as la

def dot_prod_matching_roi(dictionary, image_stack, roi_mask, batch_size=256, progress_bar=None, status_text=None):
    """
    Performs a full MRF matching workflow by combining the correct matching logic
    with robust dictionary parsing and parameter lookup.
    """
    # --- 1. Robustly Parse the Dictionary (from our diagnosis) ---
    param_key_map = {
        't1w': ['t1w'], 't2w': ['t2w'], 't1s': ['t1s_0', 't1s'],
        't2s': ['t2s_0', 't2s'], 'fs':  ['fs_0', 'fs', 'f'], 'ksw': ['ksw_0', 'ksw'],
    }
    param_vectors = {}
    for name, keys in param_key_map.items():
        for key in keys:
            if key in dictionary:
                param_vectors[name] = dictionary[key].flatten()
                break
    
    synt_sig = dictionary['sig'].T # Transpose to get shape (iters, entries)

    # --- 2. Prepare Acquired Data (adapting to Pre-CAT's format) ---
    # Your original code assumes (iters, H, W). Pre-CAT gives us (H, W, iters).
    # We transpose the axes to match the required input format.
    img_stack_transposed = np.transpose(image_stack, (2, 0, 1)) # New shape: (iters, H, W)
    n_iter, rows, cols = img_stack_transposed.shape

    # Use the ROI mask to select and reshape data
    data = img_stack_transposed[:, roi_mask]
    n_roi_pixels = data.shape[1]

    if n_roi_pixels == 0:
        return {}

    # --- 3. Normalize Signals (using L2-Norm from your working code) ---
    norm_dict = synt_sig / (la.norm(synt_sig, axis=0) + 1e-10)
    norm_data = data / (la.norm(data, axis=0) + 1e-10)
    
    # --- 4. Perform Matching in Batches ---
    results_1d = {key: np.zeros(n_roi_pixels) for key in param_vectors.keys()}
    results_1d['dp'] = np.zeros(n_roi_pixels)
    
    # The batch loop and matching logic are taken directly from your dot_prod_indexes function.
    for i in range(0, n_roi_pixels, batch_size):
        batch_end = min(i + batch_size, n_roi_pixels)
        batch_data = norm_data[:, i:batch_end]
        
        # This matrix multiplication correctly calculates all scores for the batch.
        current_score = batch_data.T @ norm_dict
        
        # Argmax correctly finds the index of the best match for each pixel.
        dp_ind = np.argmax(current_score, axis=1)
        
        results_1d['dp'][i:batch_end] = np.max(current_score, axis=1)
        
        # --- 5. Perform the Parameter Lookup (The Fixed Step) ---
        # This now works because param_vectors are correctly parsed 1D arrays.
        for key, vec in param_vectors.items():
            results_1d[key][i:batch_end] = vec[dp_ind]
            
        if progress_bar: progress_bar.progress(int((batch_end / n_roi_pixels) * 100))
        if status_text: status_text.text(f"Processing batch... {batch_end}/{n_roi_pixels} pixels")
            
    # --- 6. Reshape Results into 2D Maps ---
    quant_maps = {}
    for key, values in results_1d.items():
        map_image = np.zeros((rows, cols))
        map_image[roi_mask] = values
        quant_maps[key] = map_image
        
    return quant_maps