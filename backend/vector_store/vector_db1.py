import os
import fitz  # PyMuPDF
import chromadb
from chromadb.config import Settings
import hashlib

# -------------------------
# CONFIG
# -------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_FOLDER = os.path.join(os.path.dirname(BASE_DIR), "Data")
DB_FOLDER = os.path.join(BASE_DIR, "vector_store")
CHUNK_SIZE = 300  # words per chunk

# Ensure folders exist
os.makedirs(PDF_FOLDER, exist_ok=True)
os.makedirs(DB_FOLDER, exist_ok=True)

print(f"📂 PDF folder: {PDF_FOLDER}")
print(f"📂 Vector DB folder: {DB_FOLDER}")

# -------------------------
# MOCK EMBEDDING
# -------------------------
def mock_embedding(text):
    """
    Convert text into a numeric vector using hashing.
    Offline replacement for OpenAI embeddings.
    """
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    vector = [int(h[i:i+4], 16) % 1000 for i in range(0, 64, 4)]
    return vector

# -------------------------
# PDF / IMAGE LOADER
# -------------------------
def extract_text_from_pdf(pdf_path):
    """Extract text page-by-page including OCR for images."""
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

# -------------------------
# TEXT CHUNKING
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
    client_chroma = chromadb.Client(Settings(persist_directory=DB_FOLDER))
    return client_chroma.get_or_create_collection(name="pdf_collection")

# -------------------------
# BUILD VECTOR DB
# -------------------------
def build_vector_db():
    collection = get_chroma_collection()

    print(f"\n🔍 Scanning folder: {PDF_FOLDER}\n")

    processed_count = 0
    skipped_count = 0

    for file in os.listdir(PDF_FOLDER):
        if file.lower().endswith(".pdf"):
            pdf_path = os.path.join(PDF_FOLDER, file)
            print(f"📄 Loading: {file}")
            text = extract_text_from_pdf(pdf_path)

            if len(text.strip()) == 0:
                print(f"⚠ No text found in {file}, skipping...")
                skipped_count += 1
                continue

            # Split into chunks
            chunks = chunk_text(text)

            for idx, chunk in enumerate(chunks):
                embedding = mock_embedding(chunk)

                # store in vector DB
                collection.add(
                    ids=[f"{file}_chunk{idx}"],
                    documents=[chunk],
                    embeddings=[embedding],
                    metadatas=[{"filename": file, "chunk": idx}]
                )

            print(f"✅ Added {len(chunks)} chunks to vector DB: {file}")
            processed_count += 1

    collection.persist()
    print("\n🎉 Vector DB creation completed!")
    print(f"✅ PDFs processed: {processed_count}")
    print(f"⚠ PDFs skipped (no text): {skipped_count}")
    print(f"📁 Stored at: {DB_FOLDER}")

# -------------------------
# MAIN
# -------------------------
if __name__ == "__main__":
    build_vector_db()
