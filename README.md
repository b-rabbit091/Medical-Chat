# 🧠 Medical AI Assistant

## Overview
This project automates retrieval, transcription, deidentification, and querying of patient medical data using AI.

### Project Phases
0. Setup environment and structure ✅
1. Gmail authentication and file retrieval
2. Asynchronous download with Celery
3. Audio → PDF transcription using VOSK
4. Deidentification of PHI/PII
5. Embeddings + FAISS
6. Chatbot + LLM comparison + ClinicalBERT scoring

### Run App
```bash
streamlit run app.py
```

### Install Dependencies
```bash
pip install -r requirements.txt
```
