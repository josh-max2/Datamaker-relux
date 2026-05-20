/* FranchiseDepth motion choreography — Phase 2 luxury overhaul.
   - Count-up animations on hero stat tiles (first paint).
   - Chart-bar reveal-on-scroll via IntersectionObserver (fires once).
   - Threshold-tier coloring for closure / growth indicators (data-tier attr).
   Respects prefers-reduced-motion via the global CSS guard. */
(function () {
    'use strict';

    var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    /* ---------- count-up ---------- */
    // Tween a single numeric value over `duration` ms using ease-spring approximation.
    function spring(t) { return 1 - Math.pow(1 - t, 3); }

    function animateNumber(el, finalNum, formatter, duration) {
        if (reduced) { el.textContent = formatter(finalNum); return; }
        var start = performance.now();
        function frame(now) {
            var t = Math.min(1, (now - start) / duration);
            var v = finalNum * spring(t);
            el.textContent = formatter(v);
            if (t < 1) requestAnimationFrame(frame);
        }
        requestAnimationFrame(frame);
    }

    // Detect what kind of value the text contains. Returns null if too complex (ranges, etc.).
    function parseStat(text) {
        var raw = text.trim();
        if (raw.indexOf('–') !== -1 || raw.indexOf('—') !== -1) return null;     // range — skip
        if (/[a-zA-Z]/.test(raw.replace(/[a-zA-Z]?%/, ''))) return null;          // contains letters (other than trailing %) — skip
        var isCurrency = raw.indexOf('$') !== -1;
        var isPercent  = raw.indexOf('%') !== -1;
        var num = parseFloat(raw.replace(/[$,%\s]/g, ''));
        if (isNaN(num) || num === 0) return null;
        var decimals = (raw.split('.')[1] || '').replace(/[^0-9]/g, '').length;
        return {
            value: num,
            decimals: decimals,
            format: function (n) {
                var str;
                if (decimals > 0) {
                    str = n.toFixed(decimals);
                } else {
                    str = Math.round(n).toLocaleString('en-US');
                }
                if (decimals > 0) {
                    // re-add thousand separators on the integer part
                    var parts = str.split('.');
                    parts[0] = Number(parts[0]).toLocaleString('en-US');
                    str = parts.join('.');
                }
                if (isCurrency) str = '$' + str;
                if (isPercent)  str = str + '%';
                return str;
            }
        };
    }

    function bootCountUps() {
        var selectors = [
            '.featured-stat-val',
            '.fact-hero .value',
            '.fact-grid .fact .value',
            '.stat-tile-value',
            '.aggregates .value'
        ];
        var nodes = document.querySelectorAll(selectors.join(','));
        var idx = 0;
        nodes.forEach(function (el) {
            // Skip if already animated, has child elements (e.g. emoji icons), or is empty
            if (el.dataset.cuDone) return;
            if (el.children.length > 0) return;
            var parsed = parseStat(el.textContent);
            if (!parsed) return;
            el.dataset.cuDone = '1';
            var delay = idx++ * 80;
            setTimeout(function () {
                animateNumber(el, parsed.value, parsed.format, 800);
            }, delay);
        });
    }

    /* ---------- chart reveal on scroll ---------- */
    function bootChartReveal() {
        if (!('IntersectionObserver' in window)) {
            // fallback — reveal everything immediately
            document.querySelectorAll('.fd-chart-reveal').forEach(function (n) { n.classList.add('fd-revealed'); });
            return;
        }
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (e) {
                if (e.isIntersecting) {
                    e.target.classList.add('fd-revealed');
                    io.unobserve(e.target);
                }
            });
        }, { threshold: 0.3 });
        document.querySelectorAll('.fd-chart-reveal').forEach(function (n) { io.observe(n); });
        // Auto-tag any .chart-wrap that hasn't been opted out
        document.querySelectorAll('.chart-wrap:not(.fd-chart-reveal):not(.fd-no-reveal)').forEach(function (n) {
            n.classList.add('fd-chart-reveal');
            io.observe(n);
        });
    }

    /* ---------- threshold tiers (closure rate, growth) ---------- */
    // Look for elements with class .auto-tier and a data-metric (closure | growth) and a numeric text.
    // Apply data-tier=positive|warning|negative based on thresholds from spec.
    function bootAutoTier() {
        document.querySelectorAll('.auto-tier').forEach(function (el) {
            var metric = el.dataset.metric;
            var n = parseFloat((el.dataset.value || el.textContent || '').replace(/[^0-9.\-]/g, ''));
            if (isNaN(n)) return;
            var tier;
            if (metric === 'closure') {
                tier = n >= 5 ? 'negative' : (n >= 3 ? 'warning' : 'positive');
            } else if (metric === 'growth') {
                tier = n < 0 ? 'negative' : (n < 5 ? 'warning' : 'positive');
            }
            if (tier) el.setAttribute('data-tier', tier);
        });
    }

    /* ---------- dark/light theme toggle ---------- */
    function bootThemeToggle() {
        var html = document.documentElement;
        // The <head> boot script may have already set data-theme; if not, set it now.
        if (!html.hasAttribute('data-theme')) {
            var stored = null;
            try { stored = localStorage.getItem('fd-theme'); } catch (e) {}
            if (!stored) {
                stored = (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) ? 'light' : 'dark';
            }
            html.setAttribute('data-theme', stored);
        }
        document.querySelectorAll('.theme-toggle').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var current = html.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
                var next = current === 'light' ? 'dark' : 'light';
                html.setAttribute('data-theme', next);
                btn.setAttribute('aria-pressed', next === 'light' ? 'true' : 'false');
                try { localStorage.setItem('fd-theme', next); } catch (e) {}
            });
            btn.setAttribute('aria-pressed', html.getAttribute('data-theme') === 'light' ? 'true' : 'false');
        });
    }

    /* ---------- freshness tier on .brand-meta badges ---------- */
    // Parse "X mo old" / "X yr old" / "X year(s) old" from a meta-badge's text
    // and apply data-tier="positive|warning|negative" per spec thresholds:
    //   ≤6 mo positive · 6–12 mo warning · >12 mo negative
    function bootFreshnessTier() {
        document.querySelectorAll('.brand-meta .meta-badge').forEach(function (el) {
            if (el.dataset.tierBooted) return;
            var t = el.textContent || '';
            var months = null;
            var m;
            if ((m = t.match(/(\d+)\s*mo(?:s|nths?)?\s*(?:old|ago)/i))) {
                months = parseInt(m[1], 10);
            } else if ((m = t.match(/(\d+)\s*(?:yr|years?)\s*(?:old|ago)/i))) {
                months = parseInt(m[1], 10) * 12;
            }
            if (months == null) return;
            var tier;
            if (months <= 6) tier = 'positive';
            else if (months <= 12) tier = 'warning';
            else tier = 'negative';
            el.setAttribute('data-tier', tier);
            el.dataset.tierBooted = '1';
        });
    }

    /* ---------- slash-to-focus search keyboard shortcut ---------- */
    function bootSearchHotkey() {
        var input = document.getElementById('header-search-input');
        if (!input) return;
        document.addEventListener('keydown', function (e) {
            if (e.key !== '/') return;
            var t = e.target;
            // Don't hijack when user is typing in an input/textarea/contenteditable
            if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
            e.preventDefault();
            input.focus();
            input.select();
        });
    }

    /* ---------- compare-page outlet growth coloring ---------- */
    // The compare page renders growth values like "▲ +4.3%" / "▼ -10.6%" inside <td>s
    // built by the compare JS. We post-process to add data-tier so existing CSS hooks fire.
    function bootCompareGrowthColor() {
        var rows = document.querySelectorAll('#cmp-rows tr, .compare-table tbody tr');
        rows.forEach(function (row) {
            // Identify the outlet-growth row by its row label text
            var labelCell = row.querySelector('th[scope="row"], td:first-child');
            if (!labelCell) return;
            var label = (labelCell.textContent || '').toLowerCase();
            if (label.indexOf('outlet growth') === -1 && label.indexOf('growth') === -1) return;
            row.querySelectorAll('td').forEach(function (td) {
                if (td === labelCell) return;
                var txt = (td.textContent || '').trim();
                if (!txt || txt === '—') return;
                var tier = null;
                if (txt.indexOf('▲') !== -1 || /\+\d/.test(txt))       tier = 'positive';
                else if (txt.indexOf('▼') !== -1 || /^[-−]\d/.test(txt)) tier = 'negative';
                if (tier) td.setAttribute('data-tier', tier);
            });
        });
        // Tag the derived "all-in" row for editorial emphasis (NEW 3)
        rows.forEach(function (row) {
            var labelCell = row.querySelector('th[scope="row"], td:first-child');
            if (!labelCell) return;
            var label = (labelCell.textContent || '').toLowerCase();
            if (label.indexOf('all-in') !== -1 || label.indexOf('all in %') !== -1) {
                row.classList.add('row--derived');
            }
        });
    }

    /* ---------- 5-yr net info tooltip wiring ---------- */
    // Pages inject .info-icon-5yr; this just wires the existing .info[data-tip] popover handler.
    // The popover JS for .info already exists in the page footer; nothing extra needed here.

    function init() {
        bootCountUps();
        bootChartReveal();
        bootAutoTier();
        bootThemeToggle();
        bootFreshnessTier();
        bootSearchHotkey();
        bootCompareGrowthColor();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
