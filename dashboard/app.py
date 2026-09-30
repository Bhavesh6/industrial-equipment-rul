"""
PredicTwin™ Enterprise IIoT Predictive Maintenance & Health Digital Twin
High-End SCADA & Prognostic Control Platform
"""

import streamlit as st
import streamlit.components.v1 as components
import os
import sys

# Set full-bleed ultra-clean page configuration
st.set_page_config(
    page_title="PredicTwin™ Enterprise | RS-380 Health & RUL",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Eliminate default Streamlit padding and header chrome for a true native SaaS feel
st.markdown("""
<style>
    /* Remove standard Streamlit margins and header clutter */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
        padding-left: 0rem !important;
        padding-right: 0rem !important;
        max-width: 100% !important;
    }
    iframe {
        border-radius: 0px;
        border: none;
    }
</style>
""", unsafe_allow_html=True)

# Read the HTML5 / Tailwind Glassmorphism Digital Twin application
html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

if os.path.exists(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # Render with responsive height
    components.html(html_content, height=1150, scrolling=True)
else:
    st.error("Dashboard template not found. Please verify dashboard/index.html.")