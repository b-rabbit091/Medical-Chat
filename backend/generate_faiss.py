import pickle

import google.generativeai as genai
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
import os
import requests
import faiss

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def pdf_to_faiss(pdf_path, member_id):
    """
    Generate FAISS index from a PDF file using local SentenceTransformer embeddings.
    FAISS index is saved in: faiss/{member_id}/index.faiss
    Chunks are saved in: faiss/{member_id}/chunks.pkl
    """
    member_id = 1
    faiss_folder = os.path.join("faiss", str(member_id))
    os.makedirs(faiss_folder, exist_ok=True)
    pdf_path = "../data/attachments/member 1/pdf/doctor_note_noisy1.pdf"

    # Extract text from PDF
    reader = PdfReader(pdf_path)
    full_text = ""
    for page in reader.pages:
        full_text += (page.extract_text() or "") + " "
    full_text = full_text.strip()

    if not full_text:
        raise ValueError("No text found in PDF to index!")

    # Split text into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200, length_function=len
    )
    chunks = splitter.split_text(full_text)

    # Generate embeddings for each chunk
    embeddings = embedding_model.encode(
        chunks, convert_to_numpy=True, show_progress_bar=True
    )
    embeddings = embeddings.astype("float32")

    # Build FAISS index
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    # Save FAISS index
    faiss_path = os.path.join(faiss_folder, "index.faiss")
    faiss.write_index(index, faiss_path)

    # Save chunks so they can be retrieved later
    chunks_path = os.path.join(faiss_folder, "chunks.pkl")
    with open(chunks_path, "wb") as f:
        pickle.dump(chunks, f)

    return {"faiss_path": faiss_path, "chunks_path": chunks_path, "num_chunks": len(chunks)}


def llm_responses(query, member_id, top_k=3):
    """
    Given a question and member_id, query the FAISS index and return relevant text.

    Args:
        query (str): Doctor's question
        member_id (str/int): ID used for FAISS index folder
        top_k (int): Number of top results to retrieve

    Returns:
        str: Concatenated top_k chunks as answer
    """
    import os
    faiss_folder = os.path.join(BASE_DIR, "faiss", str(member_id))
    index_path = os.path.join(faiss_folder, "index.faiss")
    chunks_path = os.path.join(faiss_folder, "chunks.pkl")

    if not os.path.exists(index_path) or not os.path.exists(chunks_path):
        return "FAISS index or chunks not found. Please generate the index first."

    # Load FAISS index
    index = faiss.read_index(index_path)

    # Load text chunks
    with open(chunks_path, "rb") as f:
        chunks = pickle.load(f)  # list of text chunks

    if len(chunks) == 0:
        return "No text chunks found in the index."

    # Embed the query
    query_emb = embedding_model.encode([query], convert_to_numpy=True).astype("float32")

    # Search FAISS
    D, I = index.search(query_emb, top_k)  # I: indices of top chunks

    # Retrieve the relevant chunks safely
    relevant_texts = list(set([chunks[i] for i in I[0] if i < len(chunks)]))

    if not relevant_texts:
        return "No relevant text found for the query."

    context = relevant_texts

    # --- Combine into a prompt ---
    prompt = f"""
       You are a medical assistant helping a doctor.
       Use the following context from patient notes to answer the question accurately.
        Dont add content by your own. Create a friendly tone. If there's no any in the context,
        simply say answer not available in the content. Donot disclose patient PII such as name, ssn ,etc.
       Context:
       {context}

       Question:
       {query}

       Answer in a clear, professional medical tone:
       """

    try:
        model_gemini = genai.GenerativeModel("gemini-2.5-flash")
        response = model_gemini.generate_content(prompt)
        gemini_answer = response.text.strip()
    except Exception as e:
        gemini_answer = f"Server Error. Please try aga=in. {e}"

    try:
        GROQ_API_KEY = os.getenv("GROQ_API_KEY")

        groq_url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        body = {
            "model": "openai/gpt-oss-120b",  # Your desired model
            "messages": [
                {"role": "system", "content": "You are a helpful medical assistant."},
                {"role": "user", "content": prompt},
            ],
            "max_completion_tokens": 512,
            "temperature": 0.7,
            "n": 1,
        }
        resp = requests.post(groq_url, headers=headers, json=body)
        resp.raise_for_status()
        groq_answer = resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        groq_answer = f"Server Error. Please try again. {e}"

    return {'gemini_answer': gemini_answer,
            'groq_answer': groq_answer}
