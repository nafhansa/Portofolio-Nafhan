import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# muat env kalau ada (.env di lokal, di Railway pakai Variables)
load_dotenv()

app = Flask(__name__)
# izinkan diakses dari GitHub Pages / domain mana pun
CORS(app, resources={r"/*": {"origins": "*"}})

# ====== KONFIGURASI DASAR ======
PDF_PATH = "./Nafhan_Profile.pdf"  # pdf kamu
WATSONX_APIKEY = os.getenv("WATSONX_APIKEY")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
WATSONX_URL = os.getenv("WATSONX_URL", "https://jp-tok.ml.cloud.ibm.com")

# kita siapkan variabel global, tapi nanti diisi belakangan (lazy)
retriever = None
llm = None


def init_vectorstore():
    """
    DIPANGGIL HANYA SAAT DIBUTUHKAN.
    Load PDF, potong jadi chunk, bikin Chroma, dan balikin retriever.
    Dibikin fungsi supaya Railway nggak timeout pas startup.
    """
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import Chroma
    from langchain_community.embeddings import HuggingFaceEmbeddings

    if not os.path.exists(PDF_PATH):
        # kalau Railway nggak nemu pdf-nya, kita bikin error jelas
        raise FileNotFoundError(f"PDF tidak ditemukan di {PDF_PATH}. Pastikan file ini ada di repo.")

    print("📄 [init_vectorstore] loading PDF...")
    loader = PyPDFLoader(PDF_PATH)
    docs = loader.load()

    # dokumen kamu kecil, jadi chunk boleh agak gede
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=150,
    )
    chunks = splitter.split_documents(docs)

    print(f"📦 [init_vectorstore] total chunks: {len(chunks)}")

    # embedding lokal
    embeddings = HuggingFaceEmbeddings(
        model_name="./models/all-MiniLM-L6-v2/snapshots/c9745ed1d9f207416be6d2e6f8de32d1f16199bf"
    )


    # simpan ke Chroma (in-memory)
    vectordb = Chroma.from_documents(chunks, embedding=embeddings)
    retriever_local = vectordb.as_retriever(search_kwargs={"k": 8})

    print("✅ [init_vectorstore] retriever siap")
    return retriever_local


def init_llm():
    """
    DIPANGGIL HANYA SAAT DIBUTUHKAN.
    Inisialisasi watsonx model.
    """
    from ibm_watsonx_ai.foundation_models import ModelInference

    if not WATSONX_APIKEY or not WATSONX_PROJECT_ID:
        raise RuntimeError("WATSONX_APIKEY atau WATSONX_PROJECT_ID belum diset di Railway.")

    print("🤖 [init_llm] init watsonx model...")
    model = ModelInference(
        model_id="meta-llama/llama-3-3-70b-instruct",
        params={
            "decoding_method": "greedy",
            "max_new_tokens": 512,
            # bisa tambah stop_sequences kalau mau
        },
        credentials={
            "apikey": WATSONX_APIKEY,
            "url": WATSONX_URL,
        },
        project_id=WATSONX_PROJECT_ID,
    )
    print("✅ [init_llm] watsonx siap")
    return model


@app.route("/", methods=["GET"])
def home():
    # endpoint buat cek: "Railway saya hidup gak sih?"
    return jsonify({"status": "ok", "message": "Portfolio chatbot running"})


@app.route("/chat", methods=["POST"])
def chat():
    """
    Endpoint utama yang dipanggil dari JS kamu.
    Dia akan:
    1. Lazy init retriever & llm kalau belum ada
    2. Ambil konteks dari PDF
    3. Kirim prompt ke watsonx
    4. Balikin jawaban dalam JSON
    """
    global retriever, llm

    # 1. pastikan retriever ada
    if retriever is None:
        retriever = init_vectorstore()

    # 2. pastikan llm ada
    if llm is None:
        llm = init_llm()

    data = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()

    if not question:
        return jsonify({"reply": "⚠️ Pertanyaan kosong."})

    # 3. ambil konteks dari PDF
    docs = retriever.invoke(question)
    context = "\n\n".join(d.page_content for d in docs)

    # 4. bikin prompt
    prompt = f"""
Kamu adalah asisten AI untuk portfolio Nafhan. Jawab HANYA dari konteks berikut.

================== KONTEKS ==================
{context}
================ END KONTEKS ================

Pertanyaan: {question}

Jika informasi tidak ada di konteks, jawab dengan sopan: "Maaf, data itu tidak ada di PDF."
Jawab dengan paragraf singkat, jelas, dan pakai bahasa Indonesia yang rapi.
""".strip()

    try:
        answer = llm.generate_text(prompt)
    except Exception as e:
        # kalau watsonx gagal, jangan bikin 500, tapi balikin info
        answer = f"⚠️ Gagal memanggil watsonx: {e}"

    return jsonify({"reply": answer})


if __name__ == "__main__":
    # Railway ngasih PORT via env PORT
    port = int(os.environ.get("PORT", 5001))
    # host 0.0.0.0 supaya bisa diakses dari luar container
    app.run(host="0.0.0.0", port=port)
