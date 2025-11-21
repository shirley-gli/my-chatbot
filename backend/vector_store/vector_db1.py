import os
import fitz  # PyMuPDF
import chromadb
from chromadb.config import Settings
import hashlib
from PIL import Image
import pytesseract

# -------------------------
# CONFIG
# -------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_FOLDER = os.path.join(BASE_DIR, "../Data")        # PDF folder
DB_FOLDER = os.path.join(BASE_DIR, "../vector_db")    # Persistent vector DB
CHUNK_SIZE = 300  # words per chunk

os.makedirs(PDF_FOLDER, exist_ok=True)
os.makedirs(DB_FOLDER, exist_ok=True)

print(f"📂 PDF folder: {PDF_FOLDER}")
print(f"📂 Vector DB folder: {DB_FOLDER}")

# -------------------------
# EMBEDDINGS
# -------------------------
def get_embedding(text):
    # Offline embedding using hash
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return [int(h[i:i+4], 16) % 1000 for i in range(0, 64, 4)]

# -------------------------
# TEXT EXTRACTION
# -------------------------
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
        return pytesseract.image_to_string(img)
    except Exception:
        return ""

# -------------------------
# CHUNKING
# -------------------------
def chunk_text(text, chunk_size=CHUNK_SIZE):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[i:i+chunk_size]))
    return chunks

# -------------------------
# VECTOR DB SETUP
# -------------------------
def get_chroma_collection():
    client = chromadb.Client(Settings(persist_directory=DB_FOLDER))
    collection = client.get_or_create_collection(name="pdf_collection")
    return client, collection

# -------------------------
# BUILD VECTOR DB
# -------------------------
def build_vector_db():
    client, collection = get_chroma_collection()
    print(f"\n🔍 Scanning folder: {PDF_FOLDER}\n")

    processed_count = 0
    skipped_count = 0

    for file in os.listdir(PDF_FOLDER):
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
        print(f"✅ Added {len(chunks)} chunks from {file}")

    # Persist DB safely
    try:
        client.persist()
    except Exception as e:
        print(f"⚠ Error persisting vector DB: {e}")

    print("\n🎉 Vector DB creation completed!")
    print(f"✅ PDFs processed: {processed_count}")
    print(f"⚠ PDFs skipped (no text): {skipped_count}")
    print(f"📁 Vector DB stored at: {DB_FOLDER}")

# -------------------------
# MAIN
# -------------------------
if __name__ == "__main__":
    build_vector_db()
