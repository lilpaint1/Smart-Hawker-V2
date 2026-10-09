/**
 * theme.js — โหลดก่อน CSS render เพื่อกัน FOUC (Flash of Unstyled Content)
 * อ่าน cookie/localStorage → ตั้ง data-theme + --brand-h + data-senior บน <html>
 * เร็วที่สุดเท่าที่เป็นไปได้ — ไม่มี import, ไม่มี async
 */
(function () {
  var THEMES  = ['light', 'dark'];
  var ACCENTS = {
    blossom: { h: 340, s: '85%', label: 'ชมพูสด (ค่าเริ่มต้น)' },
    amber:   { h: 36,  s: '82%', label: 'อำพัน' },
    teal:    { h: 168, s: '76%', label: 'เขียวมรกต' },
    indigo:  { h: 235, s: '78%', label: 'คราม' },
    rose:    { h: 345, s: '78%', label: 'กุหลาบ' },
    violet:  { h: 262, s: '70%', label: 'ม่วง' },
    emerald: { h: 142, s: '72%', label: 'เขียวมรกตเข้ม' },
  };
  var DEFAULT_ACCENT = 'blossom';
  var html = document.documentElement;

  function getCookie(name) {
    var m = document.cookie.match('(?:^|;)\\s*' + name + '=([^;]*)');
    return m ? decodeURIComponent(m[1]) : null;
  }
  function setCookie(name, val) {
    document.cookie = name + '=' + encodeURIComponent(val) +
      ';path=/;max-age=31536000;samesite=lax';
  }

  // ---- Theme (light/dark) ----
  var theme = getCookie('sh_theme') || localStorage.getItem('sh_theme');
  if (!theme || THEMES.indexOf(theme) === -1) {
    theme = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)
      ? 'dark' : 'light';
  }
  html.setAttribute('data-theme', theme);

  // ---- Accent colour ----
  var accent = getCookie('sh_accent') || localStorage.getItem('sh_accent') || DEFAULT_ACCENT;
  if (!ACCENTS[accent]) accent = DEFAULT_ACCENT;
  var a = ACCENTS[accent];
  html.style.setProperty('--brand-h', a.h);
  html.style.setProperty('--brand-s', a.s);
  html.setAttribute('data-accent', accent);

  // ---- Senior / density mode ----
  var senior = getCookie('sh_senior') || localStorage.getItem('sh_senior');
  if (senior === '1') html.setAttribute('data-senior', '1');

  // ---- Language ----
  var lang = getCookie('sh_lang') || localStorage.getItem('sh_lang') || 'th';
  html.setAttribute('lang', lang);

  // ---- Public API (ใช้ใน app.js / templates) ----
  window.THEME = {
    set: function (t) {
      if (THEMES.indexOf(t) === -1) return;
      html.setAttribute('data-theme', t);
      localStorage.setItem('sh_theme', t);
      setCookie('sh_theme', t);
    },
    setAccent: function (key) {
      var ac = ACCENTS[key];
      if (!ac) return;
      html.style.setProperty('--brand-h', ac.h);
      html.style.setProperty('--brand-s', ac.s);
      html.setAttribute('data-accent', key);
      localStorage.setItem('sh_accent', key);
      setCookie('sh_accent', key);
    },
    setSenior: function (on) {
      if (on) { html.setAttribute('data-senior', '1'); }
      else     { html.removeAttribute('data-senior'); }
      var v = on ? '1' : '0';
      localStorage.setItem('sh_senior', v);
      setCookie('sh_senior', v);
    },
    setLang: function (l) {
      html.setAttribute('lang', l);
      localStorage.setItem('sh_lang', l);
      setCookie('sh_lang', l);
    },
    toggle: function () {
      this.set(html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
    },
    current:       function () { return html.getAttribute('data-theme'); },
    currentAccent: function () { return html.getAttribute('data-accent'); },
    currentLang:   function () { return html.getAttribute('lang') || 'th'; },
    isSenior:      function () { return html.hasAttribute('data-senior'); },
    accents:       Object.keys(ACCENTS),
    accentList:    ACCENTS,
  };
})();
