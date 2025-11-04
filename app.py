import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from PyPDF2 import PdfReader

# watsonx (boleh gagal, nanti kita fallback)
from ibm_watsonx_ai.foundation_models import ModelInference

load_dotenv()

app = Flask(__name__)

# ✅ CORS: izinkan domain kamu + localhost
CORS(
    app,
    resources={r"/*": {"origins": [
        "https://nafhan.space",
        "https://www.nafhan.space",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]}},
)

# ==========================
# KONFIG
# ==========================
PDF_PATH = "./Nafhan_Profile.pdf"

WATSONX_APIKEY = os.getenv("WATSONX_APIKEY")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
WATSONX_URL = os.getenv("WATSONX_URL", "https://jp-tok.ml.cloud.ibm.com")

# ini kita isi pas startup
PDF_TEXT = ""


# ==========================
# HELPER: baca PDF
# ==========================
def load_pdf_text() -> str:
    """Baca seluruh teks PDF jadi 1 string."""
    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"PDF tidak ditemukan di {PDF_PATH}")

    reader = PdfReader(PDF_PATH)
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


# ==========================
# HELPER: watsonx model
# ==========================
def get_llm() -> ModelInference:
    """
    Balikin instance watsonx.
    Di sini kita TIDAK raise kalau env kosong — nanti di /chat kita cek lagi,
    biar server nggak 500/502.
    """
    if not (WATSONX_APIKEY and WATSONX_PROJECT_ID):
        return None  # nanti pakai fallback

    return ModelInference(
        model_id="meta-llama/llama-3-3-70b-instruct",
        params={
            "decoding_method": "greedy",
            "max_new_tokens": 350,   # biar nggak kelamaan
        },
        credentials={
            "apikey": WATSONX_APIKEY,
            "url": WATSONX_URL,
        },
        project_id=WATSONX_PROJECT_ID,
    )


# ==========================
# HELPER: fallback jawaban lokal
# ==========================
def simple_answer_from_pdf(question: str, pdf_text: str) -> str:
    """Fallback kalau watsonx gagal / nggak ada.
       Cuma nyari kata kunci di PDF lalu balas singkat.
    """
    q = question.lower()

    # kamu boleh bikin rule lebih banyak di sini
    if "sekolah" in q or "kuliah" in q:
        return "Di PDF kamu belum ada bagian pendidikan yang jelas. Tambahin di PDF kalau mau dijawab AI ya 🙂"

    # ambil potongan awal PDF buat ditampilin
    snippet = pdf_text.strip().split("\n")[0][:300] if pdf_text else ""
    if snippet:
        return f"Aku nemu ini di PDF kamu:\n\n{snippet}\n\n(untuk jawaban lebih spesifik, aktifkan kredensial watsonx di Railway)."

    return "Maaf, aku nggak menemukan info itu di PDF dan watsonx belum aktif."


# ==========================
# STARTUP: load PDF sekali
# ==========================
try:
    PDF_TEXT = load_pdf_text()
    print("✅ PDF loaded, length:", len(PDF_TEXT))
except Exception as e:
    print("⚠️ gagal load PDF:", e)
    PDF_TEXT = ""


# ==========================
# ROUTES
# ==========================
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "portfolio chatbot running"})


@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    # Preflight CORS (kadang browser kirim OPTIONS dulu)
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()

    if not question:
        return jsonify({"reply": "Pertanyaannya kosong."}), 200

    # coba pakai watsonx kalau kredensial ada
    llm = get_llm()

    # prompt RAG sederhana
    prompt = f"""
Kamu adalah asisten yang hanya boleh menjawab dari dokumen berikut.

=== DOKUMEN ===
{PDF_TEXT}
=== AKHIR DOKUMEN ===

Pertanyaan pengguna: "{question}"

Jika di dokumen tidak ada jawabannya, jawab pakai kalimat ini:
"Maaf, di PDF saya tidak menemukan info itu."

Jawab dalam bahasa Indonesia yang rapi, maksimal 2 paragraf.
""".strip()

    # kalau watsonx tidak diset → langsung fallback
    if llm is None:
        fallback = simple_answer_from_pdf(question, PDF_TEXT)
        return jsonify({"reply": fallback}), 200

    # kalau watsonx ada → coba panggil
    try:
        answer = llm.generate_text(prompt)
        return jsonify({"reply": answer}), 200
    except Exception as e:
        # kalau watsonx error (timeout, kredensial salah, dsb) → jangan 500
        fallback = simple_answer_from_pdf(question, PDF_TEXT)
        # tambahkan info error sedikit biar kamu bisa cek di UI
        return jsonify({"reply": f"{fallback}\n\n(catatan server: watsonx error: {e})"}), 200


if __name__ == "__main__":
    # Railway kasih PORT lewat env
    port = int(os.environ.get("PORT", 8080))
    # host 0.0.0.0 biar bisa diakses publik
    app.run(host="0.0.0.0", port=port)
