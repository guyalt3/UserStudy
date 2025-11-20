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

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    service_account_info,
    scope
)

client = gspread.authorize(creds)
time.sleep(1)

# Load all data once
spreadsheet = client.open("User Study Ranked Examples")
examples_df = pd.DataFrame(spreadsheet.worksheet("examples").get_all_records())
assignments_df = pd.DataFrame(spreadsheet.worksheet("assignments").get_all_records())
# results_sheet will be used only at the end
results_sheet = spreadsheet.worksheet("results")

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
# 3. Show example
# ------------------------------
def show_example():
    current_example_id = example_ids[st.session_state.current_index]
    example_row = examples_df[examples_df['example_id'] == int(current_example_id)].iloc[0]

    st.write("### Claim:")
    st.write(example_row['claim'])

    # Get list of sentences
    sentences = [example_row[f'sentence_{i}'] for i in range(1, 51)
                 if f'sentence_{i}' in example_row and example_row[f'sentence_{i}']]

    # Show next sentence button
    if st.button("Next sentence"):
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
    with col1:
        if st.button("Support"):
            st.session_state.user_answers.append({
                'user_id': user_id,
                'example_id': current_example_id,
                'claim': example_row['claim'],
                'sentences_shown': st.session_state.sentences_shown,
                'decision': 'support',
                'timestamp': str(datetime.now())
            })
            st.session_state.current_index += 1
            st.session_state.sentences_shown = 0
            st.session_state.shown_sentences = []
    with col2:
        if st.button("Refute"):
            st.session_state.user_answers.append({
                'user_id': user_id,
                'example_id': current_example_id,
                'claim': example_row['claim'],
                'sentences_shown': st.session_state.sentences_shown,
                'decision': 'refute',
                'timestamp': str(datetime.now())
            })
            st.session_state.current_index += 1
            st.session_state.sentences_shown = 0
            st.session_state.shown_sentences = []
    with col3:
        if st.button("Can't Decide"):
            st.session_state.user_answers.append({
                'user_id': user_id,
                'example_id': current_example_id,
                'claim': example_row['claim'],
                'sentences_shown': st.session_state.sentences_shown,
                'decision': 'cannot_decide',
                'timestamp': str(datetime.now())
            })
            st.session_state.current_index += 1
            st.session_state.sentences_shown = 0
            st.session_state.shown_sentences = []

# ------------------------------
# 4. Main app logic
# ------------------------------
if user_id:
    st.write("### Instructions")
    st.write("""
    You will see a claim and a set of evidence sentences.  
    Click **Next sentence** to reveal the evidence one by one.  
    When you feel you have enough information, choose:

    - **Support** — if the evidence supports the claim  
    - **Refute** — if the evidence contradicts the claim  
    - **Can't Decide** — if the evidence is unclear or insufficient  
    """)

    # Load assigned examples for the user
    user_row = assignments_df[assignments_df['user_id'] == user_id]
    if user_row.empty:
        st.write("User not found.")
    else:
        example_ids_str = user_row.iloc[0]['example_ids']  # e.g., "[35695,52186,...]"
        example_ids_str = example_ids_str.strip("[]")
        example_ids = [x.strip() for x in example_ids_str.split(",")]

        # Show current example
        if st.session_state.current_index < len(example_ids):
            show_example()
        else:
            st.write("🎉 You have completed all examples.")

    # ------------------------------
    # 5. Finish session button
    # ------------------------------
    if st.session_state.user_answers:
        if st.button("Finish Session"):
            # Prepare all rows at once
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
            # Append all rows in one API call
            results_sheet.append_rows(rows_to_append)
            st.success("All answers saved successfully!")
            st.session_state.user_answers = []  # clear after saving
