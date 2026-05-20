/* Microsoft Clarity wrapper that respects consent.
   Loads Clarity tag only if the user has accepted analytics in the consent banner.
   Listens for consent updates (re-load on change).
   Falls under "analytics" consent since Clarity records sessions + heatmaps. */
(function() {
  var PROJECT_ID = document.currentScript.dataset.clarityId;
  if (!PROJECT_ID) return;

  var loaded = false;
  function loadClarity() {
    if (loaded) return;
    loaded = true;
    (function(c, l, a, r, i, t, y) {
      c[a] = c[a] || function() { (c[a].q = c[a].q || []).push(arguments); };
      t = l.createElement(r);
      t.async = 1;
      t.src = "https://www.clarity.ms/tag/" + i;
      y = l.getElementsByTagName(r)[0];
      y.parentNode.insertBefore(t, y);
    })(window, document, "clarity", "script", PROJECT_ID);
  }

  function maybeLoad() {
    var consent = window.fdConsent ? window.fdConsent() : { analytics: false };
    if (consent.analytics) loadClarity();
  }

  maybeLoad();
  window.addEventListener('fd-consent-update', function(e) {
    if (e.detail && e.detail.analytics) loadClarity();
  });
})();
