import streamlit as st
from streamlit_gsheets import GSheetsConnection
from groq import Groq
import pandas as pd
from datetime import datetime
import json

# Set up the page
st.set_page_config(page_title="HS Code Lookup System", layout="wide")

# Initialize the Groq client using the API key from Streamlit secrets
groq_api_key = st.secrets["GROQ_API_KEY"]
groq_client = Groq(api_key=groq_api_key)

# Google Sheets URL and worksheet ID from secrets
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1wgliY7XyZF-p4FUa1MiELUlQ3v1Tg6KDZzWuyW8AMo4/edit?gid=835818411#gid=835818411"
worksheet_id = "835818411"

# Set up connection to Google Sheets
conn = st.experimental_connection("gsheets", type=GSheetsConnection)

@st.cache_data
def get_data_from_gsheet(url, worksheet_id):
    data = conn.read(spreadsheet=url, usecols=list(range(5)), worksheet=worksheet_id)
    return data

data = get_data_from_gsheet(spreadsheet_url, worksheet_id)

# Construct the system message from the Google Sheets data
system_message = """
You are a virtual assistant providing HS Code information. Be professional and informative.
Do not make up any details you do not know. Always sound smart and refer to yourself as Jarvis.

Only output the information given below and nothing else of your own knowledge. This is the only truth. Translate everything to English to the best of your ability.

We help you find the right HS Code for your products quickly and accurately. Save time and avoid customs issues with our automated HS Code lookup tool.

Product List:
"""

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
    st.session_state.chat_history = []

if "worksheet_name" not in st.session_state:
    st.session_state.worksheet_name = None

# Function to handle sending a message
def send_message():
    if st.session_state.input_buffer:
        message = st.session_state.input_buffer  # Store the input in a variable
        
        # Append user input to chat history
        st.session_state.chat_history.append({"role": "user", "content": message, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

        # Create a new worksheet if it's the first message
        if st.session_state.worksheet_name is None:
            st.session_state.worksheet_name = f"Chat_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            conn.create(worksheet=st.session_state.worksheet_name, data=pd.DataFrame(st.session_state.chat_history))

        # Call Groq API with the entire chat history
        response = groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "system", "content": system_message}] + [{"role": chat["role"], "content": chat["content"]} for chat in st.session_state.chat_history],
            temperature=0.3,
            max_tokens=2000
        )
        chatbot_response = response.choices[0].message.content.strip()

        # Append chatbot response to chat history
        st.session_state.chat_history.append({"role": "assistant", "content": chatbot_response, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

        # Save chat history to the created worksheet
        data = pd.DataFrame(st.session_state.chat_history)
        conn.update(worksheet=st.session_state.worksheet_name, data=data)  # Update the created worksheet
        st.success("Chat history saved to Google Sheets")

        # Clear the input buffer and trigger rerun
        st.session_state.input_buffer = ""
        st.session_state.run_count += 1  # Trigger a rerun by updating session state

if "run_count" not in st.session_state:
    st.session_state.run_count = 0  # Initialize run count

# Streamlit app UI
st.title("HS Code Lookup System")
st.write("Automated and accurate HS Code information at your fingertips.")

# Display chat history with custom borders
st.markdown("### Chat")
for message in st.session_state.chat_history:
    if message["role"] == "user":
        st.markdown(
            f"<div style='border: 2px solid blue; padding: 10px; margin: 10px 0; border-radius: 8px; width: 80%; float: right; clear: both;'>{message['content']}</div>",
            unsafe_allow_html=True
        )
    elif message["role"] == "assistant":
        st.markdown(
            f"<div style='border: 2px solid green; padding: 10px; margin: 10px 0; border-radius: 8px; width: 80%; float: left; clear: both;'>{message['content']}</div>",
            unsafe_allow_html=True
        )

# Input for chat messages
user_input = st.text_input("Type your message here:", key="input_buffer")
st.button("Send", on_click=send_message)

# Display data from Google Sheets
st.write("## Product Data")
st.dataframe(data)

# Dummy element to force rerun without showing error
st.write(f"Run count: {st.session_state.run_count}")
