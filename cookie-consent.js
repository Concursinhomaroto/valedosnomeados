/**
 * Aviso de cookies + carregamento do Google Analytics e do Microsoft Clarity
 * condicionados ao aceite (LGPD). O gtag() fica sempre definido (só empilha em
 * dataLayer) pra qualquer evento customizado da página não quebrar — mas os
 * scripts reais (GA4 + Clarity) só disparam depois que a pessoa aceita os cookies.
 */
(function () {
  window.dataLayer = window.dataLayer || [];
  function gtag() { dataLayer.push(arguments); }
  window.gtag = gtag;
  gtag('js', new Date());

  var GA_ID = 'G-LQJ00HV771';
  var CLARITY_ID = 'xz9vo1frqs';
  var CONSENT_KEY = 'vdn_cookie_consent';

  function loadGA() {
    if (window.__gaLoaded) return;
    window.__gaLoaded = true;
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
    document.head.appendChild(s);
    gtag('config', GA_ID);
  }

  function loadClarity() {
    if (window.__clarityLoaded) return;
    window.__clarityLoaded = true;
    (function (c, l, a, r, i, t, y) {
      c[a] = c[a] || function () { (c[a].q = c[a].q || []).push(arguments); };
      t = l.createElement(r); t.async = 1; t.src = 'https://www.clarity.ms/tag/' + i;
      y = l.getElementsByTagName(r)[0]; y.parentNode.insertBefore(t, y);
    })(window, document, 'clarity', 'script', CLARITY_ID);
  }

  function loadAnalytics() {
    loadGA();
    loadClarity();
  }

  function showBanner() {
    if (document.getElementById('cookie-banner')) return;
    var el = document.createElement('div');
    el.id = 'cookie-banner';
    el.style.cssText = 'position:fixed;left:0;right:0;bottom:0;z-index:999;background:#1a1830;border-top:1px solid #332f54;padding:16px 20px;display:flex;align-items:center;justify-content:center;gap:16px;flex-wrap:wrap;font-family:Inter,system-ui,-apple-system,sans-serif;box-shadow:0 -8px 24px rgba(0,0,0,.4);';
    el.innerHTML =
      '<span style="font-size:13px;color:#c4b5fd;max-width:640px;line-height:1.5">🍪 Usamos cookies pra entender como você usa o site e melhorar sua experiência. <a href="privacidade.html" style="color:#a78bfa;text-decoration:underline">Saiba mais</a>.</span>' +
      '<span style="display:flex;gap:8px;flex-shrink:0">' +
      '<button id="cookie-decline" style="padding:9px 16px;border-radius:10px;border:1.5px solid #332f54;background:#201d38;color:#ede9fe;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;">Recusar</button>' +
      '<button id="cookie-accept" style="padding:9px 18px;border-radius:10px;border:none;background:linear-gradient(135deg,#a78bfa,#8b5cf6);color:#fff;font-weight:800;font-size:13px;cursor:pointer;font-family:inherit;">Aceitar</button>' +
      '</span>';
    document.body.appendChild(el);
    document.getElementById('cookie-accept').onclick = function () {
      localStorage.setItem(CONSENT_KEY, 'accepted');
      el.remove();
      loadAnalytics();
    };
    document.getElementById('cookie-decline').onclick = function () {
      localStorage.setItem(CONSENT_KEY, 'declined');
      el.remove();
    };
  }

  var consent = localStorage.getItem(CONSENT_KEY);
  if (consent === 'accepted') {
    loadAnalytics();
  } else if (consent !== 'declined') {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', showBanner);
    } else {
      showBanner();
    }
  }
})();
