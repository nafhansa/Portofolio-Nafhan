from flask import Flask, request, jsonify
from flask_cors import CORS
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from ibm_watsonx_ai.foundation_models import ModelInference
import os

app = Flask(__name__)
CORS(app)  # Allow fetch from your GitHub Pages domain

# ====== ENV VARIABLES (diatur nanti di Railway) ======
PDF_PATH = "./Nafhan_Profile.pdf"
WATSONX_APIKEY = os.getenv("WATSONX_APIKEY")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
WATSONX_URL = os.getenv("WATSONX_URL", "https://jp-tok.ml.cloud.ibm.com")

# ====== LOAD PDF & VECTORSTORE ======
print("🔍 Loading profile PDF...")
loader = PyPDFLoader(PDF_PATH)
docs = loader.load()

splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)
chunks = splitter.split_documents(docs)

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectordb = Chroma.from_documents(chunks, embedding=embeddings)
retriever = vectordb.as_retriever(search_kwargs={"k": 8})

# ====== INIT MODEL ======
llm = ModelInference(
    model_id="meta-llama/llama-3-3-70b-instruct",
    params={"decoding_method": "greedy", "max_new_tokens": 512},
    credentials={"apikey": WATSONX_APIKEY, "url": WATSONX_URL},
    project_id=WATSONX_PROJECT_ID,
)

# ====== API ======
@app.route("/")
def home():
    return jsonify({"status": "AsliNusa Portfolio Chatbot active!"})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    question = data.get("message", "").strip()
    if not question:
        return jsonify({"reply": "⚠️ Pertanyaan kosong."})

    docs = retriever.invoke(question)
    context = "\n\n".join(d.page_content for d in docs)

    prompt = f"""
Kamu adalah asisten AI pribadi Nafhan, menjawab berdasarkan isi CV dan profil pribadinya.

KONTEKS:
{context}

PERTANYAAN:
{question}

Jawablah dengan gaya profesional, naratif, dan mudah dipahami.
Jika konteks tidak relevan, jawab dengan sopan bahwa datanya tidak tersedia.
"""
    try:
        reply = llm.generate_text(prompt)
    except Exception as e:
        reply = f"⚠️ Terjadi kesalahan: {str(e)}"

    return jsonify({"reply": reply})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
