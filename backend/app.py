import os
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from flask import Flask, request, jsonify
from flask_cors import CORS
import chromadb
from chromadb.config import Settings
import hashlib

# Optional OpenAI imports
try:
    from openai import OpenAI
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
except Exception:
    client = None

# -------------------- CONFIG --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_FOLDER = os.path.join(BASE_DIR, "data")
DB_FOLDER = os.path.join(BASE_DIR, "vector_db")
CHUNK_SIZE = 300  # words per chunk

os.makedirs(PDF_FOLDER, exist_ok=True)
os.makedirs(DB_FOLDER, exist_ok=True)

# -------------------- FLASK SETUP --------------------
app = Flask(__name__)
CORS(app)

# -------------------- CHROMA DB --------------------
chroma_client = chromadb.Client(Settings(persist_directory=DB_FOLDER))
collection = chroma_client.get_or_create_collection(name="pdf_collection")

# -------------------- LOGGING --------------------
@app.before_request
def log_request_info():
    print("\n📥 Incoming Request:")
    print(f"Method: {request.method}, URL: {request.url}")
    try:
        print(f"Body: {request.get_json()}")
    except Exception:
        print("Body: Not JSON or empty")

@app.after_request
def log_response_info(response):
    print("📤 Outgoing Response:")
    try:
        print(response.get_data(as_text=True))
    except Exception:
        print("Response not JSON")
    return response

# -------------------- EMBEDDINGS --------------------
def get_embedding(text):
    if client:
        # OpenAI embeddings
        return client.embeddings.create(model="text-embedding-3-small", input=text)["data"][0]["embedding"]
    else:
        # Offline mock embedding
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return [int(h[i:i+4], 16) % 1000 for i in range(0, 64, 4)]

# -------------------- TEXT EXTRACTION --------------------
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text_content = []
    for page in doc:
        text = page.get_text("text")
        if not text.strip():
            try:
                text = page.get_text("ocr")
            except Exception:
                text = ""
        text_content.append(text)
    return "\n".join(text_content)

def extract_text_from_image(image_path):
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        return text
    except Exception:
        return ""

# -------------------- TEXT CHUNKING --------------------
def chunk_text(text, chunk_size=CHUNK_SIZE):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[i:i+chunk_size]))
    return chunks

# -------------------- UPLOAD FILES --------------------
@app.route("/upload", methods=["POST"])
def upload_files():
    uploaded_files = request.files.getlist("files")
    saved_files = []

    for f in uploaded_files:
        save_path = os.path.join(PDF_FOLDER, f.filename)
        f.save(save_path)
        saved_files.append(f.filename)

    return jsonify({"message": f"Uploaded files: {saved_files}"})

# -------------------- INGEST PDF/IMAGE --------------------
@app.route("/ingest", methods=["POST"])
def ingest_files():
    files = os.listdir(PDF_FOLDER)
    if not files:
        return jsonify({"error": "No files to ingest"}), 400

    processed_count = 0
    skipped_count = 0

    for file in files:
        path = os.path.join(PDF_FOLDER, file)
        text = ""
        if file.lower().endswith(".pdf"):
            text = extract_text_from_pdf(path)
        elif file.lower().endswith((".png", ".jpg", ".jpeg")):
            text = extract_text_from_image(path)

        if not text.strip():
            skipped_count += 1
            continue

        chunks = chunk_text(text)
        for idx, chunk in enumerate(chunks):
            embedding = get_embedding(chunk)
            collection.add(
                ids=[f"{file}_chunk{idx}"],
                documents=[chunk],
                embeddings=[embedding],
                metadatas=[{"filename": file, "chunk": idx}]
            )
        processed_count += 1

    collection.persist()
    return jsonify({
        "message": "Ingestion completed",
        "processed": processed_count,
        "skipped": skipped_count
    })

# -------------------- ASK PDF / IMAGE --------------------
@app.route("/ask", methods=["POST"])
def ask_vector():
    query = request.json.get("query", "")
    if not query:
        return jsonify({"error": "Query is required"}), 400

    query_embed = get_embedding(query)
    results = collection.query(query_embeddings=[query_embed], n_results=3)
    top_chunks = results["documents"][0]

    if client:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Summarize the following:\n" + "\n\n".join(top_chunks)}]
        )
        answer = response.choices[0].message["content"].strip()
    else:
        answer = "\n\n".join(top_chunks)

    return jsonify({"answer": answer})

# -------------------- CHAT --------------------
@app.route("/chat", methods=["POST"])
def chat():
    user_msg = request.json.get("message", "").strip()
    reply = None

    basic_commands = {
        "hi": "Hello! 👋 How can I help you today?",
        "hello": "Hi there! How’s your day going?",
        "how are you": "I'm doing great! Thanks for asking 😊",
        "help": "I can answer questions from PDFs/images or chat with you."
    }

    for cmd, response in basic_commands.items():
        if cmd in user_msg.lower():
            reply = response
            break

    if not reply:
        reply = f"You asked: '{user_msg}'. Right now I'm in offline mode."

        if client:
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": user_msg}]
                )
                reply = response.choices[0].message["content"].strip()
            except Exception as e:
                reply = f"[OpenAI Error] {str(e)}"

    return jsonify({"reply": reply})

# -------------------- RUN SERVER --------------------
if __name__ == "__main__":
    app.run(port=5000, debug=True)
