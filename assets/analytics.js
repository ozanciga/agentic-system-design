// Only the published guides send aggregate page views to the owner's dashboard.
(() => {
  const endpoint = document.querySelector('meta[name="goatcounter-endpoint"]')?.content;
  const script = document.currentScript;
  if (!endpoint || !/^https:\/\/[a-z0-9-]+\.goatcounter\.com\/count$/.test(endpoint) || !script) return;
  const root = new URL('../', script.src);
  if (location.hostname !== 'ozanciga.github.io' || location.origin !== root.origin || !location.pathname.startsWith(root.pathname)) return;
  if (navigator.doNotTrack === '1' || navigator.globalPrivacyControl === true) return;
  if (typeof window.fetch !== 'function') return;

  const workshop = root.pathname === '/agentic-system-design-for-beginners/';
  let lastPath;
  let referrer = '';
  try {
    const source = new URL(document.referrer);
    if (source.origin !== location.origin) referrer = source.origin;
  } catch { /* Direct visits have no referrer. */ }

  function page() {
    if (workshop) {
      const route = location.hash.slice(1) || 'intro';
      const names = { intro: 'Introduction', overview: 'Course index', lab: 'Research lab', runs: 'Run archive', reviews: 'Reviews', glossary: 'Glossary', setup: 'Local setup' };
      if (Object.hasOwn(names, route)) return { path: root.pathname + '#' + route, title: names[route] + ' · Company research workshop' };
      if (/^lesson\/(0[1-9]|1[0-8])$/.test(route)) return { path: root.pathname + '#' + route, title: 'Lesson ' + route.slice(7) + ' · Company research workshop' };
      // Group saved results and source views; never send run IDs or custom input.
      for (const kind of ['run', 'review', 'source']) {
        if (route.startsWith(kind + '/')) return { path: root.pathname + '#' + kind, title: kind + ' · Company research workshop' };
      }
      return null;
    }
    const relative = location.pathname.slice(root.pathname.length);
    if (!relative || relative === 'index.html') return { path: root.pathname, title: document.title };
    if (relative === 'glossary.html' || /^lessons\/[a-z0-9-]+\.html$/.test(relative)) return { path: location.pathname, title: document.title };
    return null;
  }

  function count() {
    const current = page();
    if (!current || current.path === lastPath) return;
    lastPath = current.path;
    // GoatCounter's documented browser endpoint; never include location.search.
    const url = new URL(endpoint);
    url.search = new URLSearchParams({
      p: current.path, t: current.title, r: referrer,
      s: String(window.screen.width), b: navigator.webdriver ? '153' : '0',
      rnd: Math.random().toString(36).slice(2, 7),
    });
    window.fetch(url.href, {
      mode: 'no-cors', credentials: 'omit', referrerPolicy: 'no-referrer',
      cache: 'no-store', keepalive: true,
    }).catch(() => { /* Blocked analytics must not affect the guide. */ });
  }

  // No remote JavaScript, tracking cookies, or persistent visitor identifiers.
  count();
  if (workshop) window.addEventListener('hashchange', count);
})();
