###----------------------------------
###  Python Modules
###----------------------------------
from core import *
import streamlit as st
import logging
logging.basicConfig(level=logging.DEBUG)

###----------------------------------------------
### - Streamlit
###----------------------------------------------
def app():
    st.markdown("### Checker")
    st.markdown("""
    <style>
    .stRadio > div { margin-top: -20px; } /* Adjust the margin-top value */
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize the chat history if it doesn't exist
    if 'messages' not in st.session_state:
        st.session_state['messages'] = []

    # Input for new question
    question = st.chat_input("Enter a topic")
    
    if debug_mode: print("Its in debug mode")

    if question:
        # Add the user's question to the chat history
        st.session_state['messages'].append({"role": "user", "content": question})

        # Process the question
        response = processflow_graph_invoke(question)
        
        #print(response)

        # Add the assistant's response to the chat history
        st.session_state['messages'].append({"role": "assistant", "content": response["output"]})
        
        if response.get("pdf_pages"):
            pdf_message = "**Access to PDF Pages:**\n" + "\n".join(response.get("pdf_pages"))
            st.session_state['messages'].append({"role": "assistant", "content": pdf_message})
            
    # Display the chat history
    for message in st.session_state['messages']:
        if message["role"] == "user":
            st.chat_message("user").markdown(message["content"])
        else:
            st.chat_message("assistant").markdown(message["content"], unsafe_allow_html=True)
