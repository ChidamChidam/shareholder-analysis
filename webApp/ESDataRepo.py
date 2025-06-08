import os
import streamlit as st
from core import *
import pandas as pd
import logging
logging.basicConfig(level=logging.DEBUG)

###----------------------------------------------
### - Streamlit
###----------------------------------------------
def fetch_entity_data():
    print(es_client)
    print(os.environ.get("ELASTIC_API_KEY"))
    print(es_client)
    if not es_client.indices.exists(index=elastic_index_name):
        st.write("No Data Found")
    else:
        df = query_elasticsearch()
        st.session_state.es_data = df
        st.dataframe(st.session_state.es_data)
        # if df is not None:
        #     st.session_state.es_data = df
        # if st.session_state.es_data is not None:
        #     st.dataframe(st.session_state.es_data)
        
def app():
    st.markdown("### Elasticsearch Data Repository")
    st.markdown("""
    <style>
    .stRadio > div { margin-top: -20px; } /* Adjust the margin-top value */
    </style>
    """, unsafe_allow_html=True)
    
    fetch_entity_data()