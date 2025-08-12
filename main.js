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
