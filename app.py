import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from ibm_watsonx_ai.foundation_models import ModelInference

load_dotenv()

app = Flask(__name__)

# CORS hanya untuk domain kamu
CORS(app, resources={
    r"/*": {
        "origins": [
            "https://nafhan.space",
            "https://www.nafhan.space",
            "http://localhost:5173",  # buat testing lokal
        ]
    }
})

PDF_PATH = "./Nafhan_Profile.pdf"
WATSONX_APIKEY = os.getenv("WATSONX_APIKEY")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
WATSONX_URL = os.getenv("WATSONX_URL", "https://jp-tok.ml.cloud.ibm.com")

PDF_TEXT = ""


def load_pdf_text():
    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"PDF tidak ditemukan di {PDF_PATH}")
    reader = PdfReader(PDF_PATH)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def get_llm():
    return ModelInference(
        model_id="meta-llama/llama-3-3-70b-instruct",
        params={"decoding_method": "greedy", "max_new_tokens": 400},
        credentials={"apikey": WATSONX_APIKEY, "url": WATSONX_URL},
        project_id=WATSONX_PROJECT_ID,
    )


try:
    PDF_TEXT = load_pdf_text()
    print("✅ PDF loaded, length:", len(PDF_TEXT))
except Exception as e:
    print("⚠️ gagal load PDF:", e)
    PDF_TEXT = ""


@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "portfolio chatbot running"})


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()
    if not question:
        return jsonify({"reply": "Pertanyaannya kosong."})

    llm = get_llm()

    prompt = f"""
Kamu adalah asisten yang menjawab HANYA dari dokumen berikut.

=== DOKUMEN ===
{PDF_TEXT}
=== AKHIR DOKUMEN ===

Pertanyaan: {question}

Jika di dokumen tidak ada jawabannya, bilang: "Maaf, di PDF saya tidak menemukan info itu."
Jawab dengan bahasa Indonesia yang rapi, 1–2 paragraf.
""".strip()

    try:
        answer = llm.generate_text(prompt)
    except Exception as e:
        answer = f"Gagal menghubungi watsonx: {e}"

    return jsonify({"reply": answer})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
