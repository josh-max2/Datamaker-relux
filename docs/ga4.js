/* GA4 wrapper that respects consent.
   Only loads gtag.js if the user has accepted analytics in the consent banner.
   Listens for consent updates (re-load on change).
   Emits custom events: scroll_75, cta_click, outbound_click, lead_form_submit. */
(function() {
  var MEASUREMENT_ID = document.currentScript.dataset.ga4Id;
  if (!MEASUREMENT_ID) return;

  var loaded = false;
  function loadGA4() {
    if (loaded) return;
    loaded = true;
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + MEASUREMENT_ID;
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function() { window.dataLayer.push(arguments); };
    gtag('js', new Date());
    gtag('config', MEASUREMENT_ID, { anonymize_ip: true });
    // Custom events setup
    bindScroll();
    bindClicks();
    bindFormSubmit();
  }

  function maybeLoad() {
    var consent = window.fdConsent ? window.fdConsent() : { analytics: false };
    if (consent.analytics) loadGA4();
  }

  // Initial check + listen for updates
  maybeLoad();
  window.addEventListener('fd-consent-update', function(e) {
    if (e.detail && e.detail.analytics) loadGA4();
  });

  // --- Custom event bindings ---
  var scrollFired = false;
  function bindScroll() {
    window.addEventListener('scroll', function() {
      if (scrollFired) return;
      var dh = document.documentElement;
      var pct = (dh.scrollTop + dh.clientHeight) / dh.scrollHeight * 100;
      if (pct >= 75) {
        scrollFired = true;
        gtag('event', 'scroll_75', { page_path: location.pathname });
      }
    }, { passive: true });
  }

  function bindClicks() {
    document.addEventListener('click', function(e) {
      var a = e.target.closest('a');
      if (!a) return;
      // CTA click — affiliate buttons have data-cta attribute
      var cta = a.dataset.cta || a.closest('[data-cta]')?.dataset.cta;
      if (cta) {
        gtag('event', 'cta_click', { cta_id: cta, page_path: location.pathname });
      }
      // §19.14 dashboard funnel click — links with data-funnel-source attribute
      // (added on /reports/ pages, category pages, brand pages, etc. that
      // funnel readers into /dashboard/). source = where they clicked from;
      // target = which preset/sort lands. Lets us measure CTR per surface.
      var src = a.dataset.funnelSource || a.closest('[data-funnel-source]')?.dataset.funnelSource;
      if (src) {
        var tgt = a.dataset.funnelTarget || a.closest('[data-funnel-target]')?.dataset.funnelTarget || '';
        gtag('event', 'dashboard_funnel_click', {
          source_surface: src, source_target: tgt, page_path: location.pathname,
        });
      }
      // Outbound click — different origin from current
      try {
        var u = new URL(a.href, location.href);
        if (u.origin !== location.origin) {
          gtag('event', 'outbound_click', { destination: u.hostname, page_path: location.pathname });
        }
      } catch (_) {}
    });
  }

  function bindFormSubmit() {
    document.addEventListener('submit', function(e) {
      var f = e.target;
      if (!f.classList || !f.classList.contains('lead-form')) return;
      var src = f.querySelector('input[name="source"]')?.value || 'unknown';
      var brand = f.querySelector('input[name="brand"]')?.value || '';
      gtag('event', 'lead_form_submit', { source: src, brand: brand, page_path: location.pathname });
    });
  }
})();
