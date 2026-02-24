#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 23 15:50:11 2026

@author: jonah
"""
import streamlit as st
from custom import st_functions

def render_sidebar():
    """
    Renders sidebar content (disclaimers, contact info, etc.)
    """
    with st.sidebar:
        # st.page_link("pages/1_bmc_sim.py", label="BMC Simulation", icon="🧲") # Ignore for now, not done
        # st.page_link("pages/2_ratiometric_mapping.py", label="PCr/Cr Ratiometric Mapping", icon="🫀") # Ignore for now, not done
        st.write("""## Instructions and Disclaimer
Specify experiment type(s), ROI, and uploade *full* zipped ParaVision archive.

Follow each subsequent step after carefully reading associated instructions.

**For users unfamiliar with cardiac anatomy and terminology, detailed instructions for ROI prescription are included in the [Github repository](https://github.com/jweigandwhittier/Pre-CAT/blob/main/instructions/cardiac_rois.pdf).**

When using **Pre-CAT**, please remember the following:
- **Pre-CAT** is not licensed for clinical use and is intended for research purposes only.
- Due to B0 inhomogeneities, cardiac CEST data is only useful in anterior segments.
- Each raw data file includes calculated RMSE in the CEST fitting region. Please refer to this if output data seem noisy.
- By default, **Pre-CAT** fits two rNOE peaks at frequency offsets -1.6 ppm (upper bound: -1.2 ppm, lower bound: -1.8 ppm) and -3.5 ppm (upper bound: -3.2 ppm, lower bound: -4.0 ppm) per *Zhang et al. Magnetic Resonance Imaging, Oct. 2016, doi: 10.1016/j.mri.2016.05.002*.
        """)
        st.write("""## Citation
This webapp is associated with the following paper, please cite this work when using **Pre-CAT**. \n
Weigand-Whittier J, Wendland M, Lam B, et al. *Ungated, plug-and-play cardiac CEST-MRI using radial FLASH with segmented saturation*. Magn Reson Med (2024). 10.1002/mrm.30382. \n
If you are using **Pre-CAT** for **CEST-MRF** analysis, please also cite the following. \n
Vladimirov N, Cohen O, Heo H-Y, et al. *Quantitative molecular imaging using deep magnetic resonance fingerprinting*. Nat Protocols (2025). 10.1038/s41596-025-01152-w. \n
Cohen O, Shuning H, McMahon MT, et al. *Rapid and quantitative chemical exchange saturation transfer (CEST) imaging with magnetic resonance fingerprinting (MRF)*. Magn Reson Med (2018). 10.1002/mrm.27221. 
""")
        st_functions.inject_hover_email_css()
        st.write("## Contact")
        st.markdown("""
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