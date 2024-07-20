import streamlit as st
import base64
import openai
import requests
import json
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
        return pd.DataFrame()  # Return an empty DataFrame in case of error

data = get_data_from_gsheet(spreadsheet_url, worksheet_id)

# Condensed initial system message for token efficiency
initial_system_message = "Product List:\n" + "\n".join(
    f"{row['Product Name']}* Definition: {row['Definition']}* Material: {row['Material']}* HS Code: {row['HS Code']}* Specifications: {row['Specifications']}"
    for index, row in data.iterrows()
)

# Display title and description
st.title("HS Code Lookup System")
st.write("Automated and accurate HS Code information at your fingertips.")

# Function to read image bytes and encode them in base64
def read_image_base64(image_path):
    with open(image_path, 'rb') as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Processing prompt to OpenAI API with image handling
def process_prompt_openai(chat_history, image_paths=None):
    base64_images = [read_image_base64(image_path) for image_path in image_paths] if image_paths else []
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    messages = [{"role": "system", "content": initial_system_message}] + chat_history[-4:]  # Send only the last 4 messages for context

    if base64_images:
        for base64_image in base64_images:
            messages.append({"role": "user", "content": f"data:image/jpeg;base64,{base64_image}"})

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
        chat_history.extend([{"role": "user", "content": imgpath} for imgpath in imgpaths])

    # Call the OpenAI API with the chat history
    response = process_prompt_openai(chat_history, imgpaths)
    chat_history.append({"role": "assistant", "content": response})
    st.experimental_rerun()  # Trigger rerun to clear input and update chat history

# UI Components for input and file upload
user_input = st.text_input("Type your message here:", key="input_buffer")
uploaded_files = st.file_uploader("Upload up to 3 image files", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
st.button("Send", on_click=send_message)

# Display metrics in the sidebar or floating box
metrics_data = {
    "Last Chat ID": chat_history[-1]["content"]["id"] if chat_history else "N/A",
    "Total Tokens Used": chat_history[-1]["content"]["usage"]["total_tokens"] if chat_history else 0
}
st.sidebar.write("Chat Metrics")
st.sidebar.json(metrics_data)

# Display data from Google Sheets
st.write("## Product Data")
st.dataframe(data)
