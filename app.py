import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import base64
import openai
import os
import requests
import json

# Set up the page
st.set_page_config(page_title="HS Code Lookup System", layout="wide")

# Load the OpenAI API key from Streamlit secrets
openai_api_key = st.secrets["openai"]["api_key"]
openai.api_key = openai_api_key

# Google Sheets URL and worksheet ID from secrets
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1wgliY7XyZF-p4FUa1MiELUlQ3v1Tg6KDZzWuyW8AMo4/edit?gid=835818411"
worksheet_id = "835818411"

# Set up connection to Google Sheets
conn = st.experimental_connection("gsheets", type=GSheetsConnection)

@st.cache_data
def get_data_from_gsheet(url, worksheet_id):
    try:
        st.write(f"Reading from Google Sheets URL: {url} and Worksheet ID: {worksheet_id}")
        data = conn.read(spreadsheet=url, usecols=list(range(5)), worksheet=worksheet_id)
        return data
    except Exception as e:
        st.error(f"Error reading from Google Sheets: {e}")
        return pd.DataFrame()  # Return an empty DataFrame in case of error

data = get_data_from_gsheet(spreadsheet_url, worksheet_id)

# Construct the system message from the Google Sheets data
system_message = """
You are a virtual assistant providing HS Code information. Be professional and informative.
Do not make up any details you do not know. Always sound smart and refer to yourself as Jarvis.

Only output the information given below and nothing else of your own knowledge. This is the only truth. Translate everything to English to the best of your ability.

We help you find the right HS Code for your products quickly and accurately. Save time and avoid customs issues with our automated HS Code lookup tool.

Product List:
"""

if not data.empty:
    for index, row in data.iterrows():
        system_message += f"""
{row['Product Name']}
* Definisi: {row['Definition']}
* Bahan: {row['Material']}
* HS Code: {row['HS Code']}
* Specifications: {row['Specifications']}
"""

# Initialize chat history as a session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "system", "content": system_message}]
if "input_buffer" not in st.session_state:
    st.session_state.input_buffer = ""

# Title and description
st.title("HS Code Lookup System")
st.write("Automated and accurate HS Code information at your fingertips.")

# Display chat history
for message in st.session_state.chat_history:
    if message["role"] == "user":
        st.markdown(f"<div style='border: 2px solid blue; padding: 10px; margin: 10px 0; border-radius: 8px; width: 80%; float: right; clear: both;'>{message['content']}</div>", unsafe_allow_html=True)
    elif message["role"] == "assistant":
        st.markdown(f"<div style='border: 2px solid green; padding: 10px; margin: 10px 0; border-radius: 8px; width: 80%; float: left; clear: both;'>{message['content']}</div>", unsafe_allow_html=True)

# Helper function to read image bytes and encode them in base64
def read_image_base64(image_path):
    with open(image_path, 'rb') as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Function to send a prompt (text and/or image) to OpenAI API
def process_prompt_openai(messages, image_path=None):
    base64_image = read_image_base64(image_path) if image_path else None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}"
    }
    payload = {
        "model": "gpt-4o",
        "response_format": {"type": "json_object"},
        "messages": messages,
        "max_tokens": 3000
    }
    if base64_image:
        payload["messages"].append({
            "role": "user",
            "content": {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            }
        })
    
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    return response.json()

# Function to handle message sending and processing
def send_message():
    user_prompt = st.session_state.input_buffer
    imgpath = "temp_image.png" if uploaded_file else None

    if not user_prompt and not uploaded_file:
        st.write("Please provide a text input, an image, or both.")
    else:
        if uploaded_file:
            # Save the uploaded file temporarily
            with open(imgpath, "wb") as f:
                f.write(uploaded_file.getbuffer())

        # Update chat history
        if user_prompt:
            st.session_state.chat_history.append({"role": "user", "content": user_prompt})
        if uploaded_file:
            st.session_state.chat_history.append({"role": "user", "content": f"Image: {uploaded_file.name}"})

        response = process_prompt_openai(st.session_state.chat_history, imgpath)

        st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.session_state.input_buffer = ""

    st.experimental_rerun()  # Trigger rerun to clear input and update chat history

# Input for chat messages
user_input = st.text_input("Type your message here:", key="input_buffer")

# File upload for image
uploaded_file = st.file_uploader("Upload an image file", type=["jpg", "jpeg", "png"])

# Send button
st.button("Send", on_click=send_message)

# Display data from Google Sheets
st.write("## Product Data")
st.dataframe(data)
