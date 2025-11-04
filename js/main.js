// ===== Feedback (localStorage) =====
(function () {
  const STORAGE_KEY = 'feedbacks_v1';

  const form = document.querySelector('.feedback__form');
  const textarea = document.getElementById('fb-message');
  const list = document.getElementById('feedbackList');

  if (!form || !textarea || !list) return;

  function renderItem(item, { prepend = false } = {}) {
    const card = document.createElement('article');
    card.className = 'feedback__item';

    const p = document.createElement('p');
    p.className = 'feedback__msg';
    p.textContent = item.message;

    const time = document.createElement('time');
    time.className = 'feedback__time';
    time.dateTime = new Date(item.ts).toISOString();
    time.textContent = new Date(item.ts).toLocaleString();

    card.appendChild(p);
    card.appendChild(time);

    if (prepend) {
      list.prepend(card);
    } else {
      list.append(card);
    }
  }

  function loadAll() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      const arr = raw ? JSON.parse(raw) : [];
      arr.forEach(item => renderItem(item)); 
    } catch (e) {
      console.warn('Failed load feedbacks:', e);
    }
  }

  function save(item) {
    const raw = localStorage.getItem(STORAGE_KEY);
    const arr = raw ? JSON.parse(raw) : [];
    arr.push(item);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(arr));
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const msg = textarea.value.trim();
    if (!msg) return;

    const item = { message: msg, ts: Date.now() };
    save(item);
    renderItem(item, { prepend: true }); 
    form.reset();
    textarea.focus();
  });

  loadAll();
})();

// === Floating Chatbot (bottom-right) =====================================
(function(){
  var root = document.getElementById('chatbot');
  if(!root) return; // safe exit if HTML not present

  var toggleBtn = document.getElementById('chatbotToggle');
  var panel = document.getElementById('chatbot-panel');
  var closeBtn = panel && panel.querySelector('.chatbot__close');
  var list = document.getElementById('chatbot-messages');
  var form = panel && panel.querySelector('.chatbot__form');
  var input = panel && panel.querySelector('.chatbot__input');

  var STORAGE_KEY = 'chatbot_history_v1';

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
    try{ localStorage.setItem(STORAGE_KEY, JSON.stringify(arr.slice(-10))); }catch(_){ }
  }
  function loadHistory(){
    try{ return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); }catch(_){ return []; }
  }

  var history = loadHistory();
  if(history.length === 0){
    history = [{ role:'bot', text:'Halo! Ada yang bisa saya bantu? 😊' }];
  }
  history.forEach(function(m){ render(m.role, m.text); });

  function openPanel(){
    root.classList.add('chatbot--open');
    toggleBtn.setAttribute('aria-expanded', 'true');
    setTimeout(function(){ input && input.focus(); }, 50);
  }
  function closePanel(){
    root.classList.remove('chatbot--open');
    toggleBtn.setAttribute('aria-expanded', 'false');
    toggleBtn.focus();
  }

  toggleBtn && toggleBtn.addEventListener('click', function(){
    if(root.classList.contains('chatbot--open')) closePanel(); else openPanel();
  });
  closeBtn && closeBtn.addEventListener('click', closePanel);

  // Close on Escape when panel is open
  document.addEventListener('keydown', function(e){
    if(e.key === 'Escape' && root.classList.contains('chatbot--open')) closePanel();
  });

  // Basic canned reply logic (no external calls)
  function replyTo(msg){
    var t = msg.toLowerCase();
    if(/halo|hai|hi/.test(t)) return 'Halo! Senang bertemu. Ingin tanya soal project, sertifikasi, atau kontak?';
    if(/project|proyek/.test(t)) return 'Lihat bagian PROJECTS untuk contoh karya. Mau link GitHub?';
    if(/github/.test(t)) return 'Kunjungi: github.com/nafhansa — ada beberapa repo menarik di sana.';
    if(/kontak|contact|email|wa|whatsapp/.test(t)) return 'Kamu bisa email ke nafhan.sh@gmail.com atau klik tombol WhatsApp di bagian hero.';
    if(/cv|resume/.test(t)) return 'CV bisa diunduh dari tombol “Download CV” di halaman utama.';
    return 'Terima kasih! Saya akan segera menanggapi. Coba ketik "project", "github", atau "kontak".';
  }

  form && form.addEventListener('submit', function(e){
    e.preventDefault();
    var msg = (input.value || '').trim();
    if(!msg) return;

    // render user
    render('user', msg);
    history.push({ role:'user', text: msg });
    saveHistory(history);

    // simulate bot thinking
    setTimeout(function(){
      var bot = replyTo(msg);
      render('bot', bot);
      history.push({ role:'bot', text: bot });
      saveHistory(history);
    }, 250);

    input.value = '';
    input.focus();
  });
})();
// ========================================================================
