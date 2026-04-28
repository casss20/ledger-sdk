/**
 * Citadel Motion System
 * Scroll-reveal engine + shared animation utilities.
 * Import at end of <body> on every surface.
 */
(function () {
  'use strict';

  const STAGGER   = 70;   // ms between staggered children
  const THRESHOLD = 0.10; // % of element visible before triggering
  const ROOT_MARGIN = '0px 0px -48px 0px';

  // ── IntersectionObserver ──────────────────────────────────────────────────
  const io = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-visible');
      io.unobserve(entry.target);
    });
  }, { threshold: THRESHOLD, rootMargin: ROOT_MARGIN });

  function watch(el) { io.observe(el); }

  // ── Register [data-reveal] elements ──────────────────────────────────────
  function registerReveals() {
    document.querySelectorAll('[data-reveal]').forEach(el => {
      if (!el.classList.contains('is-visible')) watch(el);
    });
  }

  // ── Register [data-stagger] containers ───────────────────────────────────
  function registerStagger() {
    document.querySelectorAll('[data-stagger]').forEach(container => {
      const children = Array.from(container.children);
      children.forEach((child, i) => {
        child.style.setProperty('--reveal-delay', `${i * STAGGER}ms`);
      });
      // Observe the container itself — when it's visible, trigger children
      const cio = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (!entry.isIntersecting) return;
          Array.from(entry.target.children).forEach(child => {
            child.classList.add('is-visible');
          });
          cio.unobserve(entry.target);
        });
      }, { threshold: 0.05, rootMargin: ROOT_MARGIN });
      cio.observe(container);
    });
  }

  // ── Animate a number counting up ─────────────────────────────────────────
  window.CMotion = {
    countUp(el, target, duration = 1600, suffix = '') {
      const start   = performance.now();
      const initial = 0;
      function step(now) {
        const p   = Math.min((now - start) / duration, 1);
        const val = Math.floor(easeOut(p) * target);
        el.textContent = val.toLocaleString() + suffix;
        if (p < 1) requestAnimationFrame(step);
        else el.textContent = target.toLocaleString() + suffix;
      }
      requestAnimationFrame(step);
    },

    // Animate a bar width (CSS width property)
    fillBar(el, targetPct, duration = 900, delay = 0) {
      setTimeout(() => {
        el.style.transition = `width ${duration}ms cubic-bezier(0.22,1,0.36,1)`;
        el.style.width = targetPct + '%';
      }, delay);
    },

    // Typewriter effect on a code block
    typewrite(el, text, speed = 18) {
      el.textContent = '';
      let i = 0;
      function tick() {
        if (i < text.length) {
          el.textContent += text[i++];
          setTimeout(tick, speed + Math.random() * 8);
        }
      }
      tick();
    },

    // Stagger-reveal a set of elements immediately (for above-fold)
    revealNow(selector, baseDelay = 0) {
      document.querySelectorAll(selector).forEach((el, i) => {
        el.setAttribute('data-reveal', el.getAttribute('data-reveal') || '');
        setTimeout(() => el.classList.add('is-visible'), baseDelay + i * STAGGER);
      });
    },
  };

  function easeOut(t) { return 1 - Math.pow(1 - t, 3); }

  // ── Init ──────────────────────────────────────────────────────────────────
  function init() {
    registerReveals();
    registerStagger();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
