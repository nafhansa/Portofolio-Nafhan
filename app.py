import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# =========================================
# 🧠 Konfigurasi dasar
# =========================================
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

PDF_PATH = "./Nafhan_Profile.pdf"

# Watsonx credentials
WATSONX_APIKEY = os.getenv("WATSONX_APIKEY")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
WATSONX_URL = os.getenv("WATSONX_URL", "https://jp-tok.ml.cloud.ibm.com")

# =========================================
# 🧩 Konfigurasi cache model untuk Railway
# =========================================
HF_CACHE_DIR = "/root/.cache/huggingface"
os.environ["HF_HOME"] = HF_CACHE_DIR
os.environ["TRANSFORMERS_CACHE"] = HF_CACHE_DIR
os.makedirs(HF_CACHE_DIR, exist_ok=True)

retriever = None
llm = None


# =========================================
# 🔍 Fungsi inisialisasi vectorstore
# =========================================
def init_vectorstore():
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import Chroma
    from langchain_community.embeddings import HuggingFaceEmbeddings

    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"PDF tidak ditemukan di {PDF_PATH}")

    print("📄 Memuat dokumen PDF...")
    loader = PyPDFLoader(PDF_PATH)
    docs = loader.load()

    # Split teks untuk embedding
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=150,
    )
    chunks = splitter.split_documents(docs)
    print(f"✅ Total chunks: {len(chunks)}")

    # Embedding dengan cache HuggingFace
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vectordb = Chroma.from_documents(chunks, embedding=embeddings)
    return vectordb.as_retriever(search_kwargs={"k": 8})


# =========================================
# 🤖 Fungsi inisialisasi Watsonx LLM
# =========================================
def init_llm():
    from ibm_watsonx_ai.foundation_models import ModelInference
    if not WATSONX_APIKEY or not WATSONX_PROJECT_ID:
        raise RuntimeError("⚠️ Environment variable Watsonx belum diset")

    return ModelInference(
        model_id="meta-llama/llama-3-3-70b-instruct",
        params={"decoding_method": "greedy", "max_new_tokens": 512},
        credentials={"apikey": WATSONX_APIKEY, "url": WATSONX_URL},
        project_id=WATSONX_PROJECT_ID,
    )


# =========================================
# 🧭 Routes
# =========================================
@app.route("/")
def home():
    return jsonify({"status": "ok", "message": "Portfolio chatbot running"})


@app.route("/chat", methods=["POST"])
def chat():
    global retriever, llm
    if retriever is None:
        retriever = init_vectorstore()
    if llm is None:
        llm = init_llm()

    data = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()
    if not question:
        return jsonify({"reply": "⚠️ Pertanyaan kosong."})

    docs = retriever.invoke(question)
    context = "\n\n".join(d.page_content for d in docs)

    prompt = f"""
Kamu adalah asisten AI untuk portfolio Nafhan. Jawab berdasarkan konteks di bawah ini.

KONTEKS:
{context}

Pertanyaan: {question}

Jika informasi tidak ada di konteks, jawab sopan bahwa data tidak tersedia di PDF.
""".strip()

    try:
        reply = llm.generate_text(prompt)
    except Exception as e:
        reply = f"⚠️ Gagal memanggil watsonx: {e}"

    return jsonify({"reply": reply})


# =========================================
# 🚀 Run Flask di Railway
# =========================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 Running on port {port}")
    app.run(host="0.0.0.0", port=port)
