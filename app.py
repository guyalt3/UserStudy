import json
import time

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# ------------------------------
# 1. Connect to Google Sheets
# ------------------------------
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

service_account_info = st.secrets["gcp_service_account"]

if 'gs_client' not in st.session_state:
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"],
        ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    )
    st.session_state.gs_client = gspread.authorize(creds)
    time.sleep(1)
    spreadsheet = st.session_state.gs_client.open("User Study Ranked Examples")
    st.session_state.examples_df = pd.DataFrame(spreadsheet.worksheet("examples").get_all_records())
    st.session_state.assignments_df = pd.DataFrame(spreadsheet.worksheet("assignments").get_all_records())
    st.session_state.results_sheet = spreadsheet.worksheet("results")

# ------------------------------
# 2. User login
# ------------------------------
user_id = st.text_input("Enter your user ID (e.g., user_1):")

# Initialize session state
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'sentences_shown' not in st.session_state:
    st.session_state.sentences_shown = 0
if 'shown_sentences' not in st.session_state:
    st.session_state.shown_sentences = []
if 'user_answers' not in st.session_state:
    st.session_state.user_answers = []

# ------------------------------
# 3. Prepare user examples once
# ------------------------------
if user_id:
    user_row = st.session_state.assignments_df[st.session_state.assignments_df['user_id'] == user_id]
    if user_row.empty:
        st.write("User not found.")
    else:
        example_ids_str = user_row.iloc[0]['example_ids'].strip("[]")
        example_ids = [x.strip() for x in example_ids_str.split(",")]
        if 'example_ids' not in st.session_state:
            st.session_state.example_ids = example_ids

# ------------------------------
# 4. Show example
# ------------------------------
def show_example():
    current_example_id = int(st.session_state.example_ids[st.session_state.current_index])
    example_row = st.session_state.examples_df[st.session_state.examples_df['example_id'] == current_example_id].iloc[0]

    st.write("### Claim:")
    st.write(example_row['claim'])

    # Get list of sentences
    sentences = [example_row[f'sentence_{i}'] for i in range(1, 51)
                 if f'sentence_{i}' in example_row and example_row[f'sentence_{i}']]

    # Show next sentence button
    if st.button("Next sentence", key=f"next_{current_example_id}"):
        if st.session_state.sentences_shown < len(sentences):
            next_sentence = sentences[st.session_state.sentences_shown]
            st.session_state.shown_sentences.append(next_sentence)
            st.session_state.sentences_shown += 1

    # Display all sentences shown so far
    for s in st.session_state.shown_sentences:
        st.write(s)

    # ------------------------------
    # Decision buttons
    # ------------------------------
    col1, col2, col3 = st.columns(3)

    def save_answer(decision):
        st.session_state.user_answers.append({
            'user_id': user_id,
            'example_id': current_example_id,
            'claim': example_row['claim'],
            'sentences_shown': st.session_state.sentences_shown,
            'decision': decision,
            'timestamp': str(datetime.now())
        })
        st.session_state.current_index += 1
        st.session_state.sentences_shown = 0
        st.session_state.shown_sentences = []

    with col1:
        if st.button("Support", key=f"support_{current_example_id}"):
            save_answer('support')
    with col2:
        if st.button("Refute", key=f"refute_{current_example_id}"):
            save_answer('refute')
    with col3:
        if st.button("Can't Decide", key=f"cannot_decide_{current_example_id}"):
            save_answer('cannot_decide')

# ------------------------------
# 5. Main app logic
# ------------------------------
if user_id and 'example_ids' in st.session_state:
    st.write("### Instructions")
    st.write("""
    Click **Next sentence** to reveal the evidence one by one.
    When you feel you have enough information, choose:

    - **Support**
    - **Refute**
    - **Can't Decide**
    """)

    if st.session_state.current_index < len(st.session_state.example_ids):
        show_example()
    else:
        st.write("🎉 You have completed all examples.")

# ------------------------------
# 6. Finish session button
# ------------------------------
if st.session_state.user_answers:
    if st.button("Finish Session"):
        # Append all answers in one API call
        rows_to_append = [
            [
                ans['user_id'],
                ans['example_id'],
                ans['claim'],
                ans['sentences_shown'],
                ans['decision'],
                ans['timestamp']
            ]
            for ans in st.session_state.user_answers
        ]
        st.session_state.results_sheet.append_rows(rows_to_append)
        st.success("All answers saved successfully!")
        st.session_state.user_answers = []
