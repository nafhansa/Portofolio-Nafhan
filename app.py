import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# muat env
load_dotenv()

app = Flask(__name__)
CORS(app)

# ====== CONFIG ======
PDF_PATH = "./Nafhan_Profile.pdf"
WATSONX_APIKEY = os.getenv("WATSONX_APIKEY")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
WATSONX_URL = os.getenv("WATSONX_URL", "https://jp-tok.ml.cloud.ibm.com")

# kita bikin variabel global tapi None dulu
retriever = None
llm = None


def init_vectorstore():
    """Load PDF dan bikin retriever. Dipanggil cuma kalau belum ada."""
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import Chroma
    from langchain_community.embeddings import HuggingFaceEmbeddings

    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"PDF tidak ditemukan di {PDF_PATH}. Pastikan filenya ikut ke repo Railway.")

    loader = PyPDFLoader(PDF_PATH)
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)
    chunks = splitter.split_documents(docs)

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectordb = Chroma.from_documents(chunks, embedding=embeddings)
    return vectordb.as_retriever(search_kwargs={"k": 8})


def init_llm():
    """Init watsonx model. Dipanggil cuma kalau dibutuhkan."""
    from ibm_watsonx_ai.foundation_models import ModelInference

    if not WATSONX_APIKEY or not WATSONX_PROJECT_ID:
        raise RuntimeError("WATSONX_APIKEY atau WATSONX_PROJECT_ID belum diset di Railway variables.")

    model = ModelInference(
        model_id="meta-llama/llama-3-3-70b-instruct",
        params={
            "decoding_method": "greedy",
            "max_new_tokens": 512,
        },
        credentials={
            "apikey": WATSONX_APIKEY,
            "url": WATSONX_URL,
        },
        project_id=WATSONX_PROJECT_ID,
    )
    return model


@app.route("/")
def home():
    return jsonify({"status": "ok", "message": "Portfolio chatbot is running"})


@app.route("/chat", methods=["POST"])
def chat():
    global retriever, llm

    # lazy init di sini supaya Railway gak timeout pas startup
    if retriever is None:
        retriever = init_vectorstore()
    if llm is None:
        llm = init_llm()

    data = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()

    if not question:
        return jsonify({"reply": "⚠️ Pertanyaan kosong."})

    # ambil konteks dari PDF
    docs = retriever.invoke(question)
    context = "\n\n".join(d.page_content for d in docs)

    prompt = f"""
Kamu adalah asisten AI pribadi Nafhan. Jawab hanya dari konteks berikut.

KONTEKS:
{context}

PERTANYAAN:
{question}

Jika tidak ada di konteks, bilang dengan sopan: "Maaf, datanya tidak ada di PDF."
Jawab dengan paragraf singkat, jelas, dan profesional.
""".strip()

    try:
        reply = llm.generate_text(prompt)
    except Exception as e:
        reply = f"⚠️ Gagal memanggil watsonx: {e}"

    return jsonify({"reply": reply})


if __name__ == "__main__":
    # Railway ngasih PORT lewat env
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
