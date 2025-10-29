#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan  8 10:36:34 2025

@author: jonah

Credit for all cat photos goes to Clara Flynn.
"""

import streamlit as st
import pickle
import os
import base64
import pandas as pd

def get_img_as_base64(file):
    """
    Reads an image file and returns it as a base64 encoded string.
    """
    with open(file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

def inject_custom_loader(gif_path):
    """
    Injects CSS to replace the Streamlit status icon with a custom GIF.
    """
    img_base64 = get_img_as_base64(gif_path)
    custom_loader_css = f"""
        <style>
            /* Target the container that holds the icon and text */
            [data-testid="stStatusWidget"] > div {{
                position: relative; /* Needed for positioning the pseudo-element */
            }}

            /* Hide the original SVG icon completely */
            [data-testid="stStatusWidget"] svg {{
                display: none !important;
            }}

            /* Hide the original text ("Running...") but keep its space to avoid layout shifts */
            [data-testid="stStatusWidget"] span {{
                visibility: hidden !important;
            }}
            
            /* Create the new icon using a pseudo-element */
            [data-testid="stStatusWidget"] > div::before {{
                /* This is our new icon */
                content: '';
                position: absolute;
                
                /* Perfectly center the icon in the container */
                top: 50%;
                left: 10%;
                transform: translate(-50%, -50%);
                z-index: 9999;
                
                /* Set the size of our icon */
                width: 45px;
                height: 45px;
                
                /* Apply the GIF */
                background-image: url("data:image/gif;base64,{img_base64}");
                background-size: contain;
                background-repeat: no-repeat;
                background-position: center;
            }}
        </style>
    """
    st.markdown(custom_loader_css, unsafe_allow_html=True)

# Define CSS and HTML for hover effect
def add_hoverable_title_with_image(title_text, image_url):
    # CSS for the hover effect
    hover_css = f"""
        <style>
        .hoverable-title {{
            position: relative;
            display: inline-block;
            cursor: pointer;
            color: black; /* Ensure text color matches the main title */
            font-weight: bold;
            font-size: 3rem; /* Match main title font size */
        }}
        .hoverable-title .image-tooltip {{
            visibility: hidden;
            opacity: 0;
            position: absolute;
            top: 120%; /* Adjust tooltip position */
            left: 50%;
            transform: translateX(-50%);
            transition: opacity 0.3s, visibility 0.3s;
            z-index: 999;
            background: white;
            padding: 5px;
            border: 1px solid #ddd;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            border-radius: 8px;
        }}
        .hoverable-title:hover .image-tooltip {{
            visibility: visible;
            opacity: 1;
        }}
        .image-tooltip img {{
            max-width: 200px; /* Adjust the image size */
            border-radius: 8px;
        }}
        </style>
    """

    # HTML structure for the title with hoverable image
    hover_html = f"""
        <div class="hoverable-title">
            {title_text}
            <div class="image-tooltip">
                <img src="{image_url}" alt="Tooltip Image">
            </div>
        </div>
    """

    # Inject the CSS and HTML into Streamlit
    st.markdown(hover_css, unsafe_allow_html=True)
    st.markdown(hover_html, unsafe_allow_html=True)
    
# Define CSS and HTML for hoverable title with image
def add_hoverable_title_with_image_inline(title_text, image_url):
    # CSS for the hover effect
    hover_css = f"""
        <style>
        .hoverable-title {{
            position: relative;
            display: inline; /* Ensure inline display */
            cursor: pointer;
            font-weight: inherit; /* Match parent font weight */
            font-size: inherit; /* Match parent font size */
            color: inherit; /* Match parent color */
        }}
        .hoverable-title .image-tooltip {{
            visibility: hidden;
            opacity: 0;
            position: absolute;
            top: 0; /* Align with the text */
            left: 90%; /* Position slightly to the right of the text */
            transform: translateX(10px); /* Add a small gap from the text */
            transition: opacity 0.3s, visibility 0.3s;
            z-index: 999;
        }}
        .hoverable-title:hover .image-tooltip {{
            visibility: visible;
            opacity: 1;
        }}
        .image-tooltip img {{
            max-width: 80px; /* Slightly smaller image size */
            background: transparent; /* Transparent background */
            border-radius: 8px;
        }}
        </style>
    """

    # HTML structure for the title with hoverable image
    hover_html = f"""
        <span class="hoverable-title">
            {title_text}
            <span class="image-tooltip">
                <img src="{image_url}" alt="Tooltip Image">
            </span>
        </span>
    """

    # Inject the CSS and HTML into Streamlit
    st.markdown(hover_css, unsafe_allow_html=True)
    return hover_html

def inject_hover_email_css():
    hover_css = """
    <style>
    .hoverable-email {
        position: relative;
        display: inline-block;
        cursor: pointer;
        font-size: 1.0rem;
        color: #1f77b4;
    }
    .hoverable-email .image-tooltip {
        visibility: hidden;
        opacity: 0;
        position: absolute;
        top: 350%;
        left: 80%;
        transform: translateX(-50%);
        transition: opacity 0.3s, visibility 0.3s;
        z-index: 999;
    }
    .hoverable-email:hover .image-tooltip {
        visibility: visible;
        opacity: 1;
    }
    .image-tooltip img {
        width: 200px;
        height: auto;
        border-radius: 10px;
        background: transparent;
    }
    </style>
    """
    st.markdown(hover_css, unsafe_allow_html=True)

def inject_spinning_logo_css(logo_path):
    """
    Injects CSS to replace the default Streamlit spinner with a spinning logo.
    """
    logo_base64 = get_img_as_base64(logo_path)
    
    spinner_css = f"""
        <style>
            /* Define the spinning animation */
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}

            /* --- THE DEFINITIVE FIX --- */

            /* 1. Hide the default SVG spinner icon */
            [data-testid="stSpinner"] svg {{
                display: none;
            }}

            /* 2. Make the spinner's container a flexbox to align items horizontally */
            [data-testid="stSpinner"] > div {{
                display: flex;
                align-items: center;
                justify-content: flex-start;
            }}

            /* 3. Create the spinning logo as a new element before the text */
            [data-testid="stSpinner"] > div::before {{
                content: '';
                display: inline-block;
                width: 30px;
                height: 30px;
                margin-right: 0.5rem;  /* Space between logo and text */
                
                /* Apply the logo as the background */
                background-image: url("data:image/png;base64,{logo_base64}");
                background-size: contain;
                background-repeat: no-repeat;
                background-position: center;

                /* Apply the spinning animation */
                animation: spin 2s linear infinite;
            }}
        </style>
    """
    st.markdown(spinner_css, unsafe_allow_html=True)
        
def save_raw(session_state):
    """
    Save session state to file.
    """
    save_path = session_state.submitted_data["save_path"]
    file_path = os.path.join(save_path, "Raw")
    if not os.path.isdir(file_path):
        os.makedirs(file_path)
    pickle_path = os.path.join(file_path, "raw_data.pkl")
    with open(pickle_path, "wb") as f:
        pickle.dump(dict(session_state), f)

def save_df_to_csv(dataframe, save_path, type):
    """
    Save QUESP dataframe to CSV.
    """
    data_path = os.path.join(save_path, 'Raw')
    if not os.path.isdir(data_path):
        os.makedirs(data_path)
    dataframe.to_csv(os.path.join(data_path, f'{type}.csv'), index=False)       

def message_logging(message, msg_type='success'):
    """
    Prints success message and saves to session state.
    """
    if not isinstance(message, str):
        str(message)
    st.session_state.log_messages.append((message, msg_type))

