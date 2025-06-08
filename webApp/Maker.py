import os
import streamlit as st
from core import *
import pandas as pd
import logging

logging.basicConfig(level=logging.DEBUG)

###----------------------------------------------
### - Streamlit
###----------------------------------------------
def process_maker_code(maker_url):
    # Initialize log area in session state if it doesn't exist
    if "log_text" not in st.session_state:
        st.session_state.log_text = ""

    # Append new log entries
    log_text = f"🔹 Started to scrape {maker_url}...\n"
    st.session_state.log_text += log_text  # Append to the session state log

    # Display the log area
    log_area = st.empty()
    log_area.text_area("Logs", st.session_state.log_text, height=200)

    # Process steps
    steps = [
        (scrapWebPage, (maker_url,)),
        (downloadPdf, None),
        (parse_pdf_load_to_es, None)
    ]
    
    prev_result = None
    for i, (func, args) in enumerate(steps):
        try:
            if args is None:
                #result = func(prev_result)
                result = func(*prev_result) if isinstance(prev_result, tuple) else func(prev_result)
            else:
                result = func(*args)
        
            log_text = f"✅ {func.__name__} completed successfully.\n"
            st.session_state.log_text += log_text  # Append new log message
            prev_result = result
        except Exception as e:
            log_text = f"❌ {func.__name__} failed: {str(e)}\n"
            st.session_state.log_text += log_text  # Append error to the log
            break
        
        log_area.text_area("Logs", st.session_state.log_text, height=200)

    # Final log message
    log_text = "🎉 Processing completed successfully!\n"
    st.session_state.log_text += log_text  # Append final message
    log_area.text_area("Logs", st.session_state.log_text, height=200)

    logging.debug(f"Processing Maker Code from URL: {maker_url}")
    print(f"Processing Maker Code from URL: {maker_url}")

def save_uploaded_file(uploaded_file):
    """Save the uploaded file to a local directory."""
    save_path = os.path.join(local_pdf_store, uploaded_file.name)
    os.makedirs("temp_uploads", exist_ok=True)
    
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return save_path
        
def app():
    st.markdown("### Maker")
    st.markdown("""
    <style>
    .stRadio > div { margin-top: -20px; } /* Adjust the margin-top value */
    </style>
    """, unsafe_allow_html=True)

    maker_url = st.text_input("Enter WebURL to Scrape", "")
    
    # Upload button to process the provided URL
    if st.button("Extract latest annual report from this URL"):
        if maker_url:
            try:
                st.session_state.log_text = ""
                process_maker_code(maker_url)  # Call function with URL input
                st.success(f"Uploaded Annual Report from {maker_url}")
            except Exception as e:
                st.warning("Failed to upload Annual Report from {maker_url}")    
        else:
            st.warning("Please enter a valid URL before uploading.")

    # PDF Upload Box
    uploaded_pdf = st.file_uploader("Upload PDF", type="pdf")

    # Action button to process the uploaded PDF
    if st.button("Process PDF and Load to ES"):
        if uploaded_pdf:
            try:
                pdf_path = save_uploaded_file(uploaded_pdf)
                # Call the function to process the uploaded PDF
                parse_pdf_load_to_es(None, None, pdf_path)  # Ensure this function accepts the uploaded PDF file directly
                st.success("PDF processed and data uploaded to Elasticsearch successfully!")
            except Exception as e:
                st.warning(f"Failed to process PDF: {str(e)}")
        else:
            st.warning("Please upload a PDF file before processing.")