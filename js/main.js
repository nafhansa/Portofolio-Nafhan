// === Nonaktifkan overlay di desktop ===
document.addEventListener("DOMContentLoaded", () => {
  const gate = document.querySelector(".device-gate");
  if (gate && window.innerWidth > 1024) gate.style.display = "none";
});

// === Chatbot Logic ===
document.addEventListener("DOMContentLoaded", () => {
  const chatbot = document.getElementById("chatbot");
  const toggleBtn = document.getElementById("chatbotToggle");
  const closeBtn = document.querySelector(".chatbot__close");
  const form = document.querySelector(".chatbot__form");
  const input = document.querySelector(".chatbot__input");
  const messages = document.getElementById("chatbot-messages");

  // ganti ke domain Railway kamu
  const API_BASE = window.location.hostname.includes("localhost")
    ? "http://localhost:8080"
    : "https://portofolio-nafhan-production.up.railway.app";

  function render(role, text) {
    const msg = document.createElement("div");
    msg.className = `chat-msg chat-msg--${role}`;
    msg.innerHTML = `<div class="chat-msg__bubble">${text}</div>`;
    messages.appendChild(msg);
    messages.scrollTop = messages.scrollHeight;
  }

  // buka tutup panel
  toggleBtn.addEventListener("click", () => {
    chatbot.classList.toggle("chatbot--open");
    const expanded = chatbot.classList.contains("chatbot--open");
    toggleBtn.setAttribute("aria-expanded", expanded);
    if (expanded) input.focus();
  });

  closeBtn.addEventListener("click", () => {
    chatbot.classList.remove("chatbot--open");
    toggleBtn.setAttribute("aria-expanded", "false");
  });

  // kirim pesan
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = input.value.trim();
    if (!msg) return;

    render("user", msg);
    input.value = "";

    const typing = document.createElement("div");
    typing.className = "chat-msg chat-msg--bot";
    typing.innerHTML = '<div class="chat-msg__bubble">...</div>';
    messages.appendChild(typing);

    try {
      console.log("➡️ sending to:", `${API_BASE}/chat`);
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg }),
      });

      // kalau CORS masih salah, bagian ini nggak pernah kepanggil
      const data = await res.json();
      typing.remove();
      render("bot", data.reply || "Tidak ada respon dari server.");
    } catch (err) {
      console.error("❌ fetch error:", err);
      typing.remove();
      render("bot", "⚠️ Gagal terhubung ke server. (cek CORS / Railway)");
    }
  });

  // salam awal
  render("bot", "Halo! Saya asisten AI Nafhan 🤖. Mau tahu project, skill, atau pengalaman saya?");
});
