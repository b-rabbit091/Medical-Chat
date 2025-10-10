import streamlit as st
from backend.gmail_utils import authenticate_gmail, search_emails, download_attachments
import datetime as dt

st.title("🧠 Medical AI Assistant - Phase 1")

# Initialize session state variables
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'service' not in st.session_state:
    st.session_state.service = None

# Step 1: Gmail Authentication
if not st.session_state.authenticated:
    if st.button("Authenticate Gmail"):
        service = authenticate_gmail()
        if service:
            st.session_state.authenticated = True
            st.session_state.service = service
else:
    # Step 2: Select Date Range and download attachments
    st.success("✅ Gmail authenticated successfully!")
    start_date = st.date_input("Start Date", dt.date.today() - dt.timedelta(days=7))
    end_date = st.date_input("End Date", dt.date.today())

    if st.button("Search & Download Attachments"):
        start = start_date.strftime("%Y/%m/%d")
        end = end_date.strftime("%Y/%m/%d")
        messages = search_emails(st.session_state.service, start, end)
        if not messages:
            st.warning("No emails with attachments found in this range.")
        else:
            download_attachments(st.session_state.service, messages)
            st.success(f"✅ {len(messages)} emails processed. Attachments saved to /data/audio/")
