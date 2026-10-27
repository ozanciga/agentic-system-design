"use strict";

const body = document.body;
const total = Number(body.dataset.guideCount);
const links = [...document.querySelectorAll('.lesson-link')];
const sidebarSearch = document.getElementById('sidebar-search');
const normalize = text => text.normalize('NFKD').toLocaleLowerCase()
  .replace(/[^\p{L}\p{N}]+/gu, ' ').trim();

function matches(item, rawTerm) {
  const raw = rawTerm.trim().toLowerCase();
  const source = raw.match(/^q\s*0*(\d+)$/);
  if (source) return item.dataset.sources.split(' ').includes(String(Number(source[1])));
  const number = raw.match(/^(?:l\s*|lesson\s*)?0*(\d+)$/);
  if (number) return Number(item.dataset.number) === Number(number[1]);
  const terms = normalize(raw).split(/\s+/).filter(Boolean);
  const haystack = normalize(item.dataset.search);
  return terms.every(term => haystack.includes(term));
}

sidebarSearch.addEventListener('input', () => {
  let count = 0;
  for (const link of links) {
    link.hidden = !matches(link, sidebarSearch.value);
    if (!link.hidden) count += 1;
  }
  for (const group of document.querySelectorAll('.nav-chapter')) {
    group.hidden = !group.querySelector('.lesson-link:not([hidden])');
  }
  document.getElementById('sidebar-count').textContent = `${count} / ${total}`;
  document.getElementById('sidebar-empty').hidden = count !== 0;
});

const directorySearch = document.getElementById('directory-search');
if (directorySearch) {
  directorySearch.addEventListener('input', () => {
    let count = 0, chapters = 0;
    for (const section of document.querySelectorAll('.topic-section')) {
      let visible = 0;
      for (const item of section.querySelectorAll('.directory-item')) {
        item.hidden = !matches(item, directorySearch.value);
        if (!item.hidden) visible += 1;
      }
      section.hidden = visible === 0;
      count += visible;
      if (visible) chapters += 1;
    }
    document.getElementById('directory-count').textContent = `${count} lesson${count === 1 ? '' : 's'} · ${chapters} chapter${chapters === 1 ? '' : 's'}`;
    document.getElementById('directory-empty').hidden = count !== 0;
  });
}

try {
  if (body.dataset.lessonSlug) {
    localStorage.setItem('agentic-design-last-lesson', body.dataset.lessonSlug);
  }
  const resume = document.getElementById('resume-link');
  if (resume) {
    const last = localStorage.getItem('agentic-design-last-lesson');
    let saved = links.find(link => new URL(link.href).pathname.endsWith('/' + last + '.html'));
    if (!saved) {
      const old = localStorage.getItem('agentic-design-last-question');
      if (old) saved = links.find(link => link.dataset.sources.split(' ').includes(String(Number(old))));
    }
    if (saved) {
      resume.href = saved.href;
      resume.textContent = `Continue reading · ${saved.dataset.number} →`;
    }
  }
} catch { /* Local file origins and private browsing can restrict storage. */ }

const sidebar = document.getElementById('sidebar');
const main = document.getElementById('main');
const menu = document.getElementById('menu-button');
const backdrop = document.querySelector('.sidebar-backdrop');
const mobile = matchMedia('(max-width: 760px)');

function setMenu(open) {
  const visible = open && mobile.matches;
  body.classList.toggle('menu-open', visible);
  menu.setAttribute('aria-expanded', String(visible));
  menu.setAttribute('aria-label', visible ? 'Close contents' : 'Open contents');
  backdrop.hidden = !visible;
  sidebar.inert = mobile.matches && !visible;
  main.inert = visible;
  if (visible) sidebarSearch.focus();
}
menu.addEventListener('click', () => setMenu(!body.classList.contains('menu-open')));
backdrop.addEventListener('click', () => { setMenu(false); menu.focus(); });
mobile.addEventListener('change', () => setMenu(false));
setMenu(false);

document.addEventListener('keydown', event => {
  if (body.classList.contains('menu-open')) {
    if (event.key === 'Escape') { setMenu(false); menu.focus(); event.preventDefault(); }
    if (event.key === 'Tab') {
      const focusable = [...sidebar.querySelectorAll('input, a')].filter(item => item.getClientRects().length);
      const first = focusable[0], last = focusable.at(-1);
      if (event.shiftKey && document.activeElement === first) { last.focus(); event.preventDefault(); }
      if (!event.shiftKey && document.activeElement === last) { first.focus(); event.preventDefault(); }
    }
    return;
  }
  if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
  if (event.target.closest('input, textarea, button, [contenteditable], .diagram-scroll, .table-scroll, pre')) return;
  const direction = event.key === 'ArrowLeft' ? 'prev' : event.key === 'ArrowRight' ? 'next' : '';
  if (!direction) return;
  const link = document.querySelector(`.adjacent-navigation a[rel="${direction}"]`);
  if (link) { event.preventDefault(); location.href = link.href; }
});

const active = document.querySelector('.lesson-link[aria-current="page"]');
if (active && !mobile.matches) {
  const list = active.closest('.lesson-list');
  list.scrollTop = active.offsetTop - list.offsetTop - list.clientHeight / 3;
}

for (const button of document.querySelectorAll('.copy-button')) {
  button.addEventListener('click', async () => {
    const code = button.closest('.code-example').querySelector('code');
    let copied = false;
    try {
      if (navigator.clipboard?.writeText) { await navigator.clipboard.writeText(code.textContent); copied = true; }
    } catch { /* The fallback keeps offline local-file use possible. */ }
    if (!copied) {
      const selection = getSelection(), range = document.createRange();
      range.selectNodeContents(code); selection.removeAllRanges(); selection.addRange(range);
      try { copied = document.execCommand('copy'); } catch { /* Leave text selected. */ }
      if (copied) selection.removeAllRanges();
    }
    button.textContent = copied ? 'Copied' : 'Text selected';
    setTimeout(() => { button.textContent = 'Copy'; }, 1800);
  });
}

// Glossary terms: one floating tooltip on the body, so table scroll areas can't clip it.
const tip = document.createElement('div');
tip.className = 'term-tip';
tip.setAttribute('role', 'tooltip');
tip.hidden = true;
document.body.append(tip);
function showTip(term) {
  tip.textContent = term.dataset.def;
  tip.hidden = false;
  const box = term.getBoundingClientRect(), width = tip.offsetWidth;
  const left = Math.max(8, Math.min(box.left, innerWidth - width - 8));
  const below = box.bottom + 6 + tip.offsetHeight < innerHeight;
  tip.style.left = `${left + scrollX}px`;
  tip.style.top = `${(below ? box.bottom + 6 : box.top - tip.offsetHeight - 6) + scrollY}px`;
}
for (const term of document.querySelectorAll('.term[data-def]')) {
  term.addEventListener('mouseenter', () => showTip(term));
  term.addEventListener('focus', () => showTip(term));
  term.addEventListener('mouseleave', () => { tip.hidden = true; });
  term.addEventListener('blur', () => { tip.hidden = true; });
}
