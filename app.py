import json
import time

import streamlit as st
import gspread
from gspread.exceptions import APIError
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# ------------------------------
# 1. Connect to Google Sheets
# ------------------------------
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

# creds = ServiceAccountCredentials.from_json_keyfile_name("test.json", scope)
# client = gspread.authorize(creds)

# Load credentials from Streamlit secrets
# (Streamlit will provide st.secrets["gcp_service_account"] as a dict when deployed)
service_account_info = st.secrets["gcp_service_account"]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    service_account_info,
    scope
)

client = gspread.authorize(creds)
time.sleep(1)


def safe_open(client, name, retries=3, delay=1):
    for attempt in range(retries):
        try:
            return client.open(name)
        except gspread.exceptions.APIError:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise


def safe_worksheet(sheet, name, retries=5, delay=1):
    """Get a worksheet safely with retries."""
    for attempt in range(retries):
        try:
            return sheet.worksheet(name)
        except gspread.exceptions.APIError:
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
            else:
                raise


# spreadsheet = client.open("User Study Ranked Examples")
# examples_sheet = spreadsheet.worksheet("examples")
# assignments_sheet = spreadsheet.worksheet("assignments")
# results_sheet = spreadsheet.worksheet("results")
spreadsheet = safe_open(client, "User Study Ranked Examples")
examples_sheet = safe_worksheet(spreadsheet, "examples")
assignments_sheet = safe_worksheet(spreadsheet, "assignments")
results_sheet = safe_worksheet(spreadsheet, "results")

# ------------------------------
# 2. User login
# ------------------------------
user_id = st.text_input("Enter your user ID (e.g., user_1):")


def safe_append(sheet, row, retries=3, delay=1):
    """Try to append a row, retrying on APIError."""
    for attempt in range(retries):
        try:
            sheet.append_row(row)
            return
        except APIError:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise


def show_example():
    # ------------------------------
    # 5. Show current example
    # ------------------------------
    if st.session_state.current_index < len(example_ids):
        current_example_id = example_ids[st.session_state.current_index]
        examples_df = pd.DataFrame(examples_sheet.get_all_records())
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
        # 6. Decision buttons
        # ------------------------------
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Support"):
                # results_sheet.append_row([
                #     user_id,
                #     current_example_id,
                #     example_row['claim'],
                #     st.session_state.sentences_shown,
                #     "support",
                #     str(datetime.now())
                # ])
                # st.session_state.current_index += 1
                # st.session_state.sentences_shown = 0
                # st.session_state.shown_sentences = []
                safe_append(results_sheet, [
                    user_id,
                    current_example_id,
                    example_row['claim'],
                    st.session_state.sentences_shown,
                    "support",
                    str(datetime.now())
                ])
                st.session_state.current_index += 1
                st.session_state.sentences_shown = 0
                st.session_state.shown_sentences = []
                st.experimental_rerun()
        with col2:
            if st.button("Refute"):
                # results_sheet.append_row([
                #     user_id,
                #     current_example_id,
                #     example_row['claim'],
                #     st.session_state.sentences_shown,
                #     "refute",
                #     str(datetime.now())
                # ])
                # st.session_state.current_index += 1
                # st.session_state.sentences_shown = 0
                # st.session_state.shown_sentences = []
                safe_append(results_sheet, [
                    user_id,
                    current_example_id,
                    example_row['claim'],
                    st.session_state.sentences_shown,
                    "refute",
                    str(datetime.now())
                ])
                st.session_state.current_index += 1
                st.session_state.sentences_shown = 0
                st.session_state.shown_sentences = []
                st.experimental_rerun()
        with col3:
            if st.button("Can't Decide"):
                # results_sheet.append_row([
                #     user_id,
                #     current_example_id,
                #     example_row['claim'],
                #     st.session_state.sentences_shown,
                #     "cannot_decide",
                #     str(datetime.now())
                # ])
                # st.session_state.current_index += 1
                # st.session_state.sentences_shown = 0
                # st.session_state.shown_sentences = []
                safe_append(results_sheet, [
                    user_id,
                    current_example_id,
                    example_row['claim'],
                    st.session_state.sentences_shown,
                    "cannot_decide",
                    str(datetime.now())
                ])
                st.session_state.current_index += 1
                st.session_state.sentences_shown = 0
                st.session_state.shown_sentences = []
                st.experimental_rerun()


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

    # ------------------------------
    # 3. Load assigned examples
    # ------------------------------
    assignments_df = pd.DataFrame(assignments_sheet.get_all_records())
    user_row = assignments_df[assignments_df['user_id'] == user_id]

    if user_row.empty:
        st.write("User not found.")
    else:
        example_ids_str = user_row.iloc[0]['example_ids']  # e.g., "[35695,52186,...]"
        example_ids_str = example_ids_str.strip("[]")
        example_ids = [x.strip() for x in example_ids_str.split(",")]

        # ------------------------------
        # 4. Track session state
        # ------------------------------
        if 'current_index' not in st.session_state:
            st.session_state.current_index = 0
        if 'sentences_shown' not in st.session_state:
            st.session_state.sentences_shown = 0
        if 'shown_sentences' not in st.session_state:
            st.session_state.shown_sentences = []

        if st.session_state.current_index >= len(example_ids):
            st.write("🎉 You have completed all examples. Thank you!")
        else:
            show_example()
