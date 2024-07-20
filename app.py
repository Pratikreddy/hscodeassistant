import streamlit as st
import base64
import openai
import requests
import json
import os
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Set up the page
st.set_page_config(page_title="HS Code Lookup System", layout="wide")

# Load the OpenAI API key from Streamlit secrets
api_key = st.secrets["openai"]["api_key"]
openai.api_key = api_key

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
        return pd.DataFrame()

data = get_data_from_gsheet(spreadsheet_url, worksheet_id)

# Full system message including all details
initial_system_message = """
You are a virtual assistant providing HS Code information. Be professional and informative.
Do not make up any details you do not know. Always sound smart and refer to yourself as Jarvis.
Only output the information given below and nothing else of your own knowledge. This is the only truth. Translate everything to English to the best of your ability.
and only output when prompted towards something don't dump all the codes into the response.
*** always make a prediction of what the image could be and be open to be corrected.
IMPORTANT PRODUCT info:
some products could look the same in image but could vary in materials and dimensions etc.
few shot eg.
1) conveyer belts
2) small screws
3) clamps
4) pumps,
5) rings, etc.
so always list all available products in that type with dimensions and materials used. so an informed decision can be taken.
We help you find the right HS Code for your products quickly and accurately. Save time and avoid customs issues with our automated HS Code lookup tool.
always only produce the codes mentioned below and nothing else from your knowledge.
Product List:
"""
if not data.empty:
    for index, row in data.iterrows():
        initial_system_message += f"{row['Product Name']}* Definition: {row['Definition']}* Material: {row['Material']}* HS Code: {row['HS Code']}* Specifications: {row['Specifications']}\n"

# Title and description
st.title("HS Code Lookup System")
st.write("Automated and accurate HS Code information at your fingertips.")

# Helper function to read image bytes and encode them in base64
def read_image_base64(image_path):
    if os.path.exists(image_path):
        with open(image_path, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    else:
        st.error(f"File not found: {image_path}")
        return None

# Function to send a prompt (text and/or image) to OpenAI API
def process_prompt_openai(chat_history, image_paths=None):
    base64_images = [read_image_base64(image_path) for image_path in image_paths] if image_paths else []
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    messages = [{"role": "system", "content": initial_system_message}] + chat_history[-4:]  # Send only the last 4 messages for context

    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "max_tokens": 300
    }
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    return response.json()

# Local chat history for managing interactions
chat_history = []

# Handling message sending and processing
def send_message():
    user_prompt = st.session_state.input_buffer
    imgpaths = [f"temp_image_{i}.png" for i, _ in enumerate(uploaded_files)] if uploaded_files else []

    if user_prompt:
        chat_history.append({"role": "user", "content": user_prompt})
    if uploaded_files:
        # Save uploaded files and verify existence before processing
        for i, uploaded_file in enumerate(uploaded_files):
            file_path = f"temp_image_{i}.png"
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            if os.path.exists(file_path):
                chat_history.append({"role": "user", "content": file_path})

    if user_prompt or uploaded_files:
        response = process_prompt_openai(chat_history, imgpaths)
        chat_history.append({"role": "assistant", "content": response})
        st.experimental_rerun()  # Trigger rerun to clear input and update chat history

# UI Components for input and file upload
user_input = st.text_input("Type your message here:", key="input_buffer")
uploaded_files = st.file_uploader("Upload up to 3 image files", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
st.button("Send", on_click=send_message)

# Display thumbnails of uploaded images
if uploaded_files:
    for uploaded_file in uploaded_files:
        st.image(uploaded_file, width=100)

# Display data from Google Sheets
st.write("## Product Data")
st.dataframe(data)
