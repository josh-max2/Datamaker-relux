/* Lightweight self-hosted consent manager.
   GDPR + CCPA compliant baseline: gates "Analytics" category until explicit consent.
   No third-party dependencies; ~3 KB minified.
   Persists choice in localStorage under "fd_consent_v1". */
(function() {
  var KEY = 'fd_consent_v1';
  var saved = null;
  try { saved = JSON.parse(localStorage.getItem(KEY)); } catch (_) {}

  function setConsent(state) {
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (_) {}
    // Tell any listening tag (e.g., GA4 wrapper) about the update
    window.dispatchEvent(new CustomEvent('fd-consent-update', { detail: state }));
    var b = document.getElementById('fd-consent-banner');
    var m = document.getElementById('fd-consent-modal');
    if (b) b.style.display = 'none';
    if (m) m.style.display = 'none';
  }

  function build() {
    if (saved) {
      // Already chose — still tell listeners on load so GA4 etc. activates
      window.dispatchEvent(new CustomEvent('fd-consent-update', { detail: saved }));
      return;
    }
    var banner = document.createElement('div');
    banner.id = 'fd-consent-banner';
    banner.setAttribute('role', 'dialog');
    banner.setAttribute('aria-label', 'Cookie consent');
    banner.innerHTML =
      '<div class="fd-consent-text">' +
        // #43 + #36 — Compressed copy. Kept just GDPR-required disclosures:
        // purpose ("cookies + analytics"), tool names by category (GA4,
        // Clarity), opt-out via Privacy link. Originally 3 sentences (~280
        // chars / 5 mobile lines) → #43 cut to 1 sentence (~73 chars /
        // 2 mobile lines) → #36 trims to ~45 chars / 1 mobile line at 414px.
        // Cannot go shorter without dropping the GDPR-named tools (GA4 +
        // Clarity), which would weaken transparency. The audit's "1-line
        // bar with [Customize] [Accept] only" would also violate GDPR
        // fairness (Reject must be visually equal to Accept) — declined.
        'Cookies + analytics (GA4 + Clarity). ' +
        '<a href="/privacy/" aria-label="Privacy policy">Privacy</a>.' +
      '</div>' +
      '<div class="fd-consent-actions">' +
        '<button type="button" class="fd-btn-tertiary" id="fd-c-customize">Customize</button>' +
        '<button type="button" class="fd-btn-sec" id="fd-c-reject">Reject all</button>' +
        '<button type="button" class="fd-btn-pri" id="fd-c-accept">Accept all</button>' +
      '</div>';
    document.body.appendChild(banner);

    var modal = document.createElement('div');
    modal.id = 'fd-consent-modal';
    modal.style.display = 'none';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-label', 'Customize cookie settings');
    modal.innerHTML =
      '<div class="fd-consent-modal-inner">' +
        '<h3>Customize cookie settings</h3>' +
        '<div class="fd-consent-cat">' +
          '<label><input type="checkbox" checked disabled> ' +
          '<strong>Necessary</strong> — required for the site to function (e.g., remembering your consent choice). Always on.</label>' +
        '</div>' +
        '<div class="fd-consent-cat">' +
          '<label><input type="checkbox" id="fd-c-analytics"> ' +
          '<strong>Analytics</strong> — anonymous page view + interaction tracking via Google Analytics 4, plus heatmap + session-replay via Microsoft Clarity (with text inputs auto-masked). Helps us improve the site.</label>' +
        '</div>' +
        '<div class="fd-consent-actions">' +
          '<button type="button" class="fd-btn-sec" id="fd-c-save">Save preferences</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(modal);

    document.getElementById('fd-c-accept').onclick = function() {
      setConsent({ necessary: true, analytics: true, ts: Date.now() });
    };
    document.getElementById('fd-c-reject').onclick = function() {
      setConsent({ necessary: true, analytics: false, ts: Date.now() });
    };
    document.getElementById('fd-c-customize').onclick = function() {
      modal.style.display = 'flex';
    };
    document.getElementById('fd-c-save').onclick = function() {
      var a = document.getElementById('fd-c-analytics').checked;
      setConsent({ necessary: true, analytics: a, ts: Date.now() });
    };
  }

  // Expose a function for the footer link to re-open the customize modal
  window.fdOpenConsent = function() {
    try { localStorage.removeItem(KEY); } catch (_) {}
    saved = null;
    document.getElementById('fd-consent-banner')?.remove();
    document.getElementById('fd-consent-modal')?.remove();
    build();
  };

  // Tiny public API for other scripts (GA4)
  window.fdConsent = function() {
    if (!saved) {
      try { saved = JSON.parse(localStorage.getItem(KEY)); } catch (_) {}
    }
    return saved || { necessary: true, analytics: false };
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', build);
  } else {
    build();
  }
})();
