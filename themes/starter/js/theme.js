/* © 2025 Spwig. All rights reserved. */

/**
 * Starter Theme - Minimal JavaScript
 * Target: < 5KB minified
 */

(function() {
  'use strict';

  // ========================================================================
  // Mobile Menu Toggle
  // ========================================================================

  function initMobileMenu() {
    const toggle = document.querySelector('[data-menu-toggle]');
    const menu = document.querySelector('[data-mobile-menu]');
    const body = document.body;

    if (!toggle || !menu) return;

    toggle.addEventListener('click', function() {
      const isOpen = menu.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', isOpen);
      body.classList.toggle('menu-open', isOpen);
    });

    // Close menu on escape key
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && menu.classList.contains('is-open')) {
        menu.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
        body.classList.remove('menu-open');
      }
    });
  }

  // ========================================================================
  // Quantity Selector
  // ========================================================================

  function initQuantitySelectors() {
    document.addEventListener('click', function(e) {
      const btn = e.target.closest('[data-quantity-btn]');
      if (!btn) return;

      const action = btn.dataset.quantityBtn;
      const wrapper = btn.closest('[data-quantity]');
      const input = wrapper.querySelector('[data-quantity-input]');

      if (!input) return;

      let value = parseInt(input.value, 10) || 1;
      const min = parseInt(input.min, 10) || 1;
      const max = parseInt(input.max, 10) || 999;

      if (action === 'decrease') {
        value = Math.max(min, value - 1);
      } else if (action === 'increase') {
        value = Math.min(max, value + 1);
      }

      input.value = value;
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });
  }

  // ========================================================================
  // Product Gallery
  // ========================================================================

  function initProductGallery() {
    const galleries = document.querySelectorAll('[data-product-gallery]');

    galleries.forEach(function(gallery) {
      const main = gallery.querySelector('[data-gallery-main]');
      const thumbs = gallery.querySelectorAll('[data-gallery-thumb]');

      if (!main || thumbs.length === 0) return;

      thumbs.forEach(function(thumb) {
        thumb.addEventListener('click', function() {
          const src = this.dataset.galleryThumb;
          const alt = this.querySelector('img')?.alt || '';

          // Update main image
          const mainImg = main.querySelector('img');
          if (mainImg) {
            mainImg.src = src;
            mainImg.alt = alt;
          }

          // Update active state
          thumbs.forEach(t => t.classList.remove('product-gallery__thumb--active'));
          this.classList.add('product-gallery__thumb--active');
        });
      });
    });
  }

  // ========================================================================
  // Add to Cart Animation
  // ========================================================================

  function initAddToCart() {
    document.addEventListener('submit', function(e) {
      const form = e.target.closest('[data-add-to-cart-form]');
      if (!form) return;

      const btn = form.querySelector('[data-add-to-cart-btn]');
      if (!btn) return;

      // Add loading state
      btn.classList.add('is-loading');
      btn.disabled = true;

      // Reset after animation (actual cart update should be handled by backend)
      setTimeout(function() {
        btn.classList.remove('is-loading');
        btn.classList.add('is-added');
        btn.disabled = false;

        setTimeout(function() {
          btn.classList.remove('is-added');
        }, 2000);
      }, 500);
    });
  }

  // ========================================================================
  // Accordion (FAQ)
  // ========================================================================

  function initAccordions() {
    document.addEventListener('click', function(e) {
      const trigger = e.target.closest('[data-accordion-trigger]');
      if (!trigger) return;

      const item = trigger.closest('[data-accordion-item]');
      const content = item.querySelector('[data-accordion-content]');

      if (!content) return;

      const isOpen = item.classList.toggle('is-open');
      trigger.setAttribute('aria-expanded', isOpen);
      content.hidden = !isOpen;
    });
  }

  // ========================================================================
  // Smooth Scroll
  // ========================================================================

  function initSmoothScroll() {
    document.addEventListener('click', function(e) {
      const link = e.target.closest('a[href^="#"]');
      if (!link) return;

      const targetId = link.getAttribute('href').slice(1);
      const target = document.getElementById(targetId);

      if (!target) return;

      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  // ========================================================================
  // Newsletter Form
  // ========================================================================

  function initNewsletterForm() {
    const forms = document.querySelectorAll('[data-newsletter-form]');

    forms.forEach(function(form) {
      form.addEventListener('submit', function(e) {
        // Let the form submit naturally, but show feedback
        const btn = form.querySelector('button[type="submit"]');
        if (btn) {
          btn.classList.add('is-loading');
        }
      });
    });
  }

  // ========================================================================
  // Lazy Load Images
  // ========================================================================

  function initLazyLoad() {
    if ('loading' in HTMLImageElement.prototype) {
      // Native lazy loading supported
      const images = document.querySelectorAll('img[loading="lazy"]');
      images.forEach(function(img) {
        if (img.dataset.src) {
          img.src = img.dataset.src;
        }
      });
    } else {
      // Fallback for older browsers
      const observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
          if (entry.isIntersecting) {
            const img = entry.target;
            if (img.dataset.src) {
              img.src = img.dataset.src;
            }
            observer.unobserve(img);
          }
        });
      });

      document.querySelectorAll('img[data-src]').forEach(function(img) {
        observer.observe(img);
      });
    }
  }

  // ========================================================================
  // Initialize
  // ========================================================================

  function init() {
    initMobileMenu();
    initQuantitySelectors();
    initProductGallery();
    initAddToCart();
    initAccordions();
    initSmoothScroll();
    initNewsletterForm();
    initLazyLoad();
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
