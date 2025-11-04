(function(){
  var root = document.getElementById('chatbot');
  if(!root) return;

  var toggleBtn = document.getElementById('chatbotToggle');
  var panel = document.getElementById('chatbot-panel');
  var closeBtn = panel && panel.querySelector('.chatbot__close');
  var list = document.getElementById('chatbot-messages');
  var form = panel && panel.querySelector('.chatbot__form');
  var input = panel && panel.querySelector('.chatbot__input');

  var STORAGE_KEY = 'chatbot_history_v1';

  // otomatis pilih API sesuai environment
  var API_BASE = window.location.hostname.includes("localhost")
    ? "http://localhost:8080"
    : "https://portofolio-nafhan-production.up.railway.app";

  function render(role, text){
    var item = document.createElement('div');
    item.className = 'chat-msg chat-msg--' + (role === 'user' ? 'user' : 'bot');
    var bubble = document.createElement('div');
    bubble.className = 'chat-msg__bubble';
    bubble.textContent = text;
    item.appendChild(bubble);
    list.appendChild(item);
    list.scrollTop = list.scrollHeight;
  }

  function saveHistory(arr){
    try{ localStorage.setItem(STORAGE_KEY, JSON.stringify(arr.slice(-10))); }catch(_){}
  }
  function loadHistory(){
    try{ return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); }catch(_){ return []; }
  }

  var history = loadHistory();
  if(history.length === 0){
    history = [{ role:'bot', text:'Halo! Saya asisten AI Nafhan 🤖. Mau tahu tentang project, skill, atau pengalaman saya?' }];
  }
  history.forEach(m => render(m.role, m.text));

  form && form.addEventListener('submit', async function(e){
    e.preventDefault();
    var msg = (input.value || '').trim();
    if(!msg) return;

    render('user', msg);
    history.push({ role:'user', text: msg });
    saveHistory(history);
    input.value = '';
    input.focus();

    var typing = document.createElement('div');
    typing.className = 'chat-msg chat-msg--bot typing';
    typing.innerHTML = '<div class="chat-msg__bubble">...</div>';
    list.appendChild(typing);
    list.scrollTop = list.scrollHeight;

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      typing.remove();
      render('bot', data.reply);
      history.push({ role:'bot', text: data.reply });
      saveHistory(history);

    } catch (err) {
      typing.remove();
      render('bot', '⚠️ Gagal terhubung ke server. Cek URL API atau redeploy Railway.');
      console.error("Chatbot error:", err);
    }
  });
})();
