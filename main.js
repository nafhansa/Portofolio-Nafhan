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

    if (prepend) list.prepend(card);
    else list.append(card);
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


// === Entrance & Scroll Reveal =======================
(function(){
  function setupReveal(){
    try{
      var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      if(reduceMotion) return;

      var groups = [
        '.header .navbar a, .header .logo',
        '.hero .avatar, .hero .title, .hero .hero__desc, .hero .hero__cta a',
        '.skills__title, .skills__list li',
        '.projects__title, .projects .project-card',
        '.cert__title, .cert .cert__item',
        '.exp__title, .exp .exp__item',
        '.feedback__title, .feedback__form, #feedbackList',
        '.contact__title, .contact__desc, .contact__email, .contact__social li'
      ];

      groups.forEach(function(sel, gi){
        document.querySelectorAll(sel).forEach(function(el, i){
          el.classList.add('reveal');
          el.style.setProperty('--stagger', (i * 70 + gi * 40) + 'ms');
        });
      });

      if(!('IntersectionObserver' in window)){
        document.querySelectorAll('.reveal').forEach(function(el){ el.classList.add('reveal--visible'); });
        return;
      }

      var io = new IntersectionObserver(function(entries, obs){
        entries.forEach(function(entry){
          if(entry.isIntersecting){
            entry.target.classList.add('reveal--visible');
            obs.unobserve(entry.target);
          }
        });
      }, { threshold: 0.15, rootMargin: '0px 0px -5% 0px' });

      document.querySelectorAll('.reveal').forEach(function(el){ io.observe(el); });
    }catch(err){
      document.querySelectorAll('.reveal').forEach(function(el){ el.classList.add('reveal--visible'); });
    }
  }

  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', setupReveal, { once: true });
    window.addEventListener('load', setupReveal, { once: true });
  } else setupReveal();
})();


// === Page Intro =====================================
(function(){
  var reduceMotion = false;
  try{ reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches; }catch(_){}
  try{
    if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
    window.scrollTo(0,0);
  }catch(_){}

  function runIntro(){
    if(reduceMotion) return;
    var intro = document.createElement('div');
    intro.className = 'intro';
    intro.setAttribute('aria-hidden', 'true');
    intro.innerHTML =
      '<div class="intro__brand">' +
        '<span class="brand__top">NAFHAN</span>' +
        '<span class="brand__sub">PORTFOLIO</span>' +
        '<div class="intro__progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">' +
          '<div class="intro__bar"></div>' +
        '</div>' +
        '<div class="intro__term"><b>init</b> [<span class="term__bar"></span>] <span class="term__percent">0%</span> <span class="term__cursor"></span></div>' +
      '</div>';
    document.body.appendChild(intro);
    document.body.classList.add('is-intro');

    requestAnimationFrame(()=> intro.classList.add('intro--enter'));
    var percentEl = intro.querySelector('.term__percent');
    var asciiBarEl = intro.querySelector('.term__bar');
    var progressEl = intro.querySelector('.intro__progress');
    var start = performance.now();
    var DURATION = 1200;
    var BAR_LEN = 20;

    function tick(now){
      var t = Math.min(1, (now - start) / DURATION);
      var pct = Math.round(t * 100);
      var filled = Math.round(t * BAR_LEN);
      var bar = '#'.repeat(filled) + '.'.repeat(BAR_LEN - filled);
      percentEl.textContent = pct + '%';
      asciiBarEl.textContent = bar;
      progressEl.setAttribute('aria-valuenow', String(pct));
      if(t < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);

    setTimeout(()=>{
      intro.classList.add('intro--exit');
      document.body.classList.remove('is-intro');
      try{ if ('scrollRestoration' in history) history.scrollRestoration = 'auto'; }catch(_){}
      setTimeout(()=> intro.remove(), 560);
    }, 1280);
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', runIntro, { once: true });
  }else runIntro();
})();


// === Floating Chatbot (AI-integrated) ================
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

  // ganti ini kalau nanti ganti nama service
  var API_BASE = "https://portofolio-nafhan-production.up.railway.app";

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

  function openPanel(){
    root.classList.add('chatbot--open');
    toggleBtn.setAttribute('aria-expanded', 'true');
    setTimeout(()=> input && input.focus(), 50);
  }
  function closePanel(){
    root.classList.remove('chatbot--open');
    toggleBtn.setAttribute('aria-expanded', 'false');
    toggleBtn.focus();
  }

  toggleBtn && toggleBtn.addEventListener('click', ()=> {
    if(root.classList.contains('chatbot--open')) closePanel(); else openPanel();
  });
  closeBtn && closeBtn.addEventListener('click', closePanel);
  document.addEventListener('keydown', e=>{
    if(e.key === 'Escape' && root.classList.contains('chatbot--open')) closePanel();
  });

  // ==== Integrasi AI Chatbot dengan Backend Flask ====
  form && form.addEventListener('submit', async function(e){
    e.preventDefault();
    var msg = (input.value || '').trim();
    if(!msg) return;

    render('user', msg);
    history.push({ role:'user', text: msg });
    saveHistory(history);
    input.value = '';
    input.focus();

    // bubble "typing..."
    var typing = document.createElement('div');
    typing.className = 'chat-msg chat-msg--bot typing';
    typing.innerHTML = '<div class="chat-msg__bubble">...</div>';
    list.appendChild(typing);
    list.scrollTop = list.scrollHeight;

    // helper fetch dengan fallback ke localhost
    async function sendToAPI(url) {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg })
      });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res.json();
    }

    try {
      // coba ke Railway dulu
      let data;
      try {
        data = await sendToAPI(API_BASE + '/chat');
      } catch (err) {
        // kalau gagal (misal kamu lagi develop lokal), coba ke localhost
        data = await sendToAPI('http://localhost:8080/chat');
      }

      typing.remove();
      render('bot', data.reply);
      history.push({ role:'bot', text: data.reply });
      saveHistory(history);
    } catch (err) {
      typing.remove();
      render('bot', '⚠️ Gagal terhubung ke server. Cek URL API atau redeploy Railway.');
    }
  });
})();
