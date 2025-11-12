import streamlit as st
from backend.gmail_utils import authenticate_gmail, search_emails, download_attachments
from backend.generate_faiss import llm_responses
import datetime as dt

st.title(" Medical AI Assistant ")

# --- Session state ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'service' not in st.session_state:
    st.session_state.service = None
if 'files' not in st.session_state:
    st.session_state.files = []
if 'faiss_ready' not in st.session_state:
    st.session_state.faiss_ready = False
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# --- Step 1: Gmail Authentication ---
if not st.session_state.authenticated:
    if st.button("Authenticate Gmail"):
        service = authenticate_gmail()
        if service:
            st.session_state.authenticated = True
            st.session_state.service = service

else:
    # --- Step 2: Select Date Range and download attachments ---
    st.success("✅ Gmail authenticated successfully!")
    start_date = st.date_input("Start Date", dt.date.today() - dt.timedelta(days=7))
    end_date = st.date_input("End Date", dt.date.today())

    pdf_analyse = st.toggle("📄 PDF Analyse")
    audio_analyse = st.toggle("🎤 Audio Analyse")

    if st.button("Search & Download Attachments"):
        start = start_date.strftime("%Y/%m/%d")
        end = end_date.strftime("%Y/%m/%d")
        messages = search_emails(st.session_state.service, start, end)
        if not messages:
            st.warning("No emails with attachments found in this range.")
        else:
            files = download_attachments(
                st.session_state.service, messages, pdf_analyse, audio_analyse
            )
            st.session_state.files = files
            if files:
                st.success(f"✅ {len(files)} files downloaded!")
                st.write("### Downloaded Files:")
                for f in files:
                    st.markdown(f"- `{f}`")
            else:
                st.warning("No supported attachments found.")

    # --- Step 3: Analyse & Chat Button ---
    if st.session_state.files:
        if st.button("Analyse & Chat"):
            st.session_state.faiss_ready = True
            # --- Run FAISS index generation for all PDFs ---
            for f in st.session_state.files:
                if f.endswith(".pdf"):
                    member_id = "member_1"  # you can get dynamically
                    # pdf_to_faiss(f, member_id)
            st.success("✅ FAISS index generated for uploaded PDFs!")
    # ----------------------------
    # Step 4: Chatbot interface
    # ----------------------------
    if st.session_state.faiss_ready:
        st.header("💬 Chatbot")
        user_input = st.text_input("Ask a question:")

        if st.button("Send Question") and user_input.strip():
            answers = llm_responses(user_input, 1)

            # Update chat history as a single dictionary entry
            st.session_state.chat_history.append({
                "query": user_input,
                "gemini": answers['gemini_answer'],
                "groq": answers['groq_answer']
            })

        # Display chat history
        st.subheader("Chat History")
        for entry in st.session_state.chat_history:
            st.markdown(f"**Your query:** {entry['query']}")
            st.markdown(f"**Gemini answer:** {entry['gemini']}")
            st.markdown(f"**Groq answer:** {entry['groq']}")
            st.markdown("---")  # separator between entries
