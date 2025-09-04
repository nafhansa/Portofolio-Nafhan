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


// === Entrance & Scroll Reveal (added by assistant) =======================
(function(){
  function setupReveal(){
    try{
      var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      if(reduceMotion) return; // users asked to reduce motion

      // Groups of selectors to reveal with stagger
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

      // Tag targets with .reveal and set a CSS var for stagger delay
      groups.forEach(function(sel, gi){
        document.querySelectorAll(sel).forEach(function(el, i){
          el.classList.add('reveal');
          el.style.setProperty('--stagger', (i * 70 + gi * 40) + 'ms');
        });
      });

      if(!('IntersectionObserver' in window)){
        // Fallback: just show everything
        document.querySelectorAll('.reveal').forEach(function(el){ el.classList.add('reveal--visible'); });
        return;
      }

      // IntersectionObserver to toggle visibility once
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
      // Fail-safe: if anything goes wrong, just show everything
      document.querySelectorAll('.reveal').forEach(function(el){
        el.classList.add('reveal--visible');
      });
    }
  }

  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', setupReveal, { once: true });
    window.addEventListener('load', setupReveal, { once: true });
  } else {
    setupReveal();
  }
})();
// =========================================================================


// === Page Intro (first-load entrance) — added by assistant ================
(function(){
  var reduceMotion = false;
  try{
    reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }catch(_){}

  function runIntro(){
    if(reduceMotion) return;

    // Build overlay
    var intro = document.createElement('div');
    intro.className = 'intro';
    intro.setAttribute('aria-hidden', 'true');
    intro.innerHTML = '<div class="intro__brand"><span class="brand__top">NAFHAN</span><span class="brand__sub">PORTFOLIO</span></div>';

    document.body.appendChild(intro);
    document.body.classList.add('is-intro');

    // Start: next frame
    requestAnimationFrame(function(){
      intro.classList.add('intro--enter');
    });

    // Exit after a short beat
    var exitDelay = 980; // ms — tweak if you want it shorter/longer
    setTimeout(function(){
      intro.classList.add('intro--exit');
      document.body.classList.remove('is-intro');

      // Clean up after transition
      setTimeout(function(){
        if(intro && intro.parentNode){ intro.parentNode.removeChild(intro); }
      }, 520);
    }, exitDelay);
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', runIntro);
  }else{
    runIntro();
  }
})();
// ========================================================================
