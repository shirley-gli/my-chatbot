import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib

# Optional OpenAI
try:
    from openai import OpenAI
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
except Exception:
    client = None

from vector_store.vector_db1 import get_chroma_collection, extract_text_from_pdf, extract_text_from_image, chunk_text, CHUNK_SIZE, PDF_FOLDER

# -------------------- FLASK SETUP --------------------
app = Flask(__name__)
CORS(app)

# -------------------- VECTOR DB --------------------
chroma_client, collection = get_chroma_collection()

# -------------------- EMBEDDINGS --------------------
def get_embedding(text):
    if client:
        try:
            return client.embeddings.create(model="text-embedding-3-small", input=text)["data"][0]["embedding"]
        except Exception:
            pass
    # Offline fallback
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return [int(h[i:i+4], 16) % 1000 for i in range(0, 64, 4)]

# -------------------- CHAT / BASIC COMMANDS --------------------
BASIC_COMMANDS = {
    "hi": "Hello! 👋 How can I help you today?",
    "hello": "Hi there! How’s your day going?",
    "how are you": "I'm doing great! Thanks for asking 😊",
    "help": "I can answer questions from PDFs/images or chat with you."
}

@app.route("/chat", methods=["POST"])
def chat():
    user_msg = request.json.get("message", "").strip()
    reply = None

    # 1️⃣ Check basic commands first
    for cmd, response in BASIC_COMMANDS.items():
        if cmd in user_msg.lower():
            reply = response
            break

    # 2️⃣ Fallback to vector DB
    if not reply:
        query_embed = get_embedding(user_msg)
        try:
            results = collection.query(query_embeddings=[query_embed], n_results=3, include=["documents", "metadatas"])
            top_docs = results["documents"][0] if results["documents"] else []
            if top_docs:
                reply = "\n\n".join(top_docs)
            else:
                reply = "Sorry, I found no results in the documents."
        except Exception:
            reply = "Offline: Unable to search the vector DB."

    return jsonify({"reply": reply})

# -------------------- INGEST UPLOADED FILES --------------------
@app.route("/upload", methods=["POST"])
def upload_files():
    uploaded_files = request.files.getlist("files")
    saved_files = []

    for f in uploaded_files:
        save_path = os.path.join(PDF_FOLDER, f.filename)
        f.save(save_path)
        saved_files.append(f.filename)

    return jsonify({"message": f"Uploaded files: {saved_files}"})

@app.route("/ingest", methods=["POST"])
def ingest_files():
    from vector_store.vector_db1 import build_vector_db
    build_vector_db()
    return jsonify({"message": "Ingestion completed"})

# -------------------- RUN SERVER --------------------
if __name__ == "__main__":
    app.run(port=5000, debug=True)
