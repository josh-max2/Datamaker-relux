/* §1 SimilarWeb/Koyfin-pattern header behavior — rebuild spec §1.4 / §1.5.
   Mega-menu hover (200ms open delay, 100ms close, cancels on re-enter),
   click/keyboard toggle, outside-click + Escape close, mobile drawer
   accordion, active-route highlight, and Cmd/Ctrl-K search focus.
   The header scroll-state (data-scrolled) + drawer open/close + body
   scroll-lock are handled by motion.js; this file only adds the new bits. */
(function () {
    'use strict';

    /* ---------- Desktop mega-menus ---------- */
    var groups = Array.prototype.slice.call(document.querySelectorAll('.has-megamenu'));
    var OPEN_DELAY = 200, CLOSE_DELAY = 100;

    function closeAll(except) {
        groups.forEach(function (g) {
            if (g === except) return;
            g.classList.remove('open');
            var t = g.querySelector('.megamenu-trigger');
            if (t) t.setAttribute('aria-expanded', 'false');
        });
    }

    groups.forEach(function (group) {
        var trigger = group.querySelector('.megamenu-trigger');
        if (!trigger) return;
        var openTimer = null, closeTimer = null;

        function open() {
            clearTimeout(closeTimer); closeTimer = null;
            closeAll(group);
            group.classList.add('open');
            trigger.setAttribute('aria-expanded', 'true');
        }
        function close() {
            group.classList.remove('open');
            trigger.setAttribute('aria-expanded', 'false');
        }

        // Hover: 200ms open delay (prevents accidental trigger on horizontal pass)
        group.addEventListener('mouseenter', function () {
            clearTimeout(closeTimer); closeTimer = null;
            openTimer = setTimeout(open, OPEN_DELAY);
        });
        // Leave: 100ms close, cancelled if the pointer re-enters
        group.addEventListener('mouseleave', function () {
            clearTimeout(openTimer); openTimer = null;
            closeTimer = setTimeout(close, CLOSE_DELAY);
        });
        // Click/tap + keyboard: immediate toggle
        trigger.addEventListener('click', function (e) {
            e.preventDefault();
            clearTimeout(openTimer); clearTimeout(closeTimer);
            if (group.classList.contains('open')) { close(); }
            else { open(); }
        });
    });

    // Outside click closes everything
    document.addEventListener('click', function (e) {
        if (!e.target.closest('.has-megamenu')) closeAll(null);
    });
    // Escape closes + returns focus to the open trigger
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            var open = document.querySelector('.has-megamenu.open');
            if (open) {
                var t = open.querySelector('.megamenu-trigger');
                closeAll(null);
                if (t) t.focus();
            }
        }
    });

    /* ---------- Active-route highlight ---------- */
    try {
        var path = window.location.pathname.replace(/\/+$/, '/') || '/';
        var marked = false;
        document.querySelectorAll('.megamenu .mm-link').forEach(function (a) {
            var href = a.getAttribute('href');
            if (!marked && href && href !== '/' && path.indexOf(href) === 0) {
                var trig = a.closest('.has-megamenu').querySelector('.megamenu-trigger');
                if (trig) { trig.classList.add('is-active'); marked = true; }
            }
        });
        document.querySelectorAll('.primary-nav .nav-item > a.nav-link').forEach(function (a) {
            var href = a.getAttribute('href');
            if (href && href !== '/' && path.indexOf(href) === 0) a.classList.add('is-active');
        });
    } catch (e) { /* non-fatal */ }

    /* ---------- Mobile drawer accordion ---------- */
    document.querySelectorAll('.drawer-acc-trigger').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var grp = btn.closest('.drawer-acc-group');
            var isOpen = grp.classList.toggle('open');
            btn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        });
    });

    /* ---------- Cmd/Ctrl-K focuses search ---------- */
    document.addEventListener('keydown', function (e) {
        if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
            var input = document.getElementById('header-search-input');
            if (input) { e.preventDefault(); input.focus(); }
        }
    });
})();
