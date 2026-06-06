// Hamburger menu
(function() {
  var hamburger = document.getElementById('hamburger');
  var mobileMenu = document.getElementById('mobile-menu');
  if (!hamburger || !mobileMenu) return;

  // Set all styles directly via JS to avoid CSS conflicts
  function openMenu() {
    mobileMenu.style.cssText = 'display:flex !important;position:fixed !important;top:0 !important;left:0 !important;width:100% !important;height:100% !important;background:#111 !important;z-index:9998 !important;flex-direction:column !important;align-items:center !important;justify-content:flex-start !important;padding:100px 20px 30px !important;gap:6px !important;overflow-y:auto !important;box-sizing:border-box !important;';
    document.body.style.overflow = 'hidden';
    // Style each link
    var links = mobileMenu.querySelectorAll('.nav-link');
    for (var i = 0; i < links.length; i++) {
      links[i].style.cssText = 'font-size:20px !important;font-weight:600 !important;color:#fff !important;padding:12px 36px !important;text-decoration:none !important;border-radius:10px !important;width:100% !important;max-width:280px !important;text-align:center !important;display:block !important;';
    }
    // Style close button
    var closeBtn = document.getElementById('menu-close');
    if (closeBtn) {
      closeBtn.style.cssText = 'position:absolute !important;top:12px !important;right:16px !important;background:none !important;border:none !important;font-size:40px !important;color:#999 !important;cursor:pointer !important;width:48px !important;height:48px !important;display:flex !important;align-items:center !important;justify-content:center !important;';
    }
  }

  function closeMenu() {
    mobileMenu.style.display = 'none';
    document.body.style.overflow = '';
  }

  hamburger.addEventListener('click', function() {
    if (mobileMenu.style.display === 'flex') {
      closeMenu();
    } else {
      openMenu();
    }
    hamburger.classList.toggle('open');
  });

  var closeBtn = document.getElementById('menu-close');
  if (closeBtn) {
    closeBtn.addEventListener('click', function() {
      closeMenu();
      hamburger.classList.remove('open');
    });
  }

  var links = mobileMenu.querySelectorAll('.nav-link');
  for (var j = 0; j < links.length; j++) {
    links[j].addEventListener('click', function() {
      closeMenu();
      hamburger.classList.remove('open');
    });
  }
})();

// Header scroll effect
(function() {
  var header = document.querySelector('.header');
  if (!header) return;
  var ticking = false;
  function updateHeader() {
    header.classList.toggle('scrolled', window.scrollY > 80);
    ticking = false;
  }
  window.addEventListener('scroll', function() {
    if (!ticking) {
      requestAnimationFrame(updateHeader);
      ticking = true;
    }
  });
  updateHeader();
})();

// Scroll reveal animations
(function() {
  var reveals = document.querySelectorAll('.reveal, .reveal-left, .reveal-right, .reveal-scale');
  if (!reveals.length) return;
  var observer = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });
  reveals.forEach(function(el) { observer.observe(el); });
})();

// Counter animation for stats
(function() {
  var counters = document.querySelectorAll('.stat-number');
  if (!counters.length) return;
  var observer = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
      if (entry.isIntersecting) {
        var el = entry.target;
        var target = parseInt(el.getAttribute('data-target') || el.textContent.replace(/[^0-9]/g, ''), 10);
        if (!target) return;
        var duration = 1500;
        var start = performance.now();
        function update(now) {
          var progress = Math.min((now - start) / duration, 1);
          var eased = 1 - Math.pow(1 - progress, 3);
          el.textContent = Math.round(target * eased).toLocaleString();
          if (progress < 1) requestAnimationFrame(update);
        }
        requestAnimationFrame(update);
        observer.unobserve(el);
      }
    });
  }, { threshold: 0.5 });
  counters.forEach(function(el) { observer.observe(el); });
})();



// Active nav link
(function() {
  var currentPath = window.location.pathname;
  document.querySelectorAll('.nav-link').forEach(function(link) {
    var href = link.getAttribute('href');
    if (href === currentPath || (href !== '/' && currentPath.startsWith(href))) {
      link.classList.add('active');
    }
  });
})();

// Carousel
(function() {
  var container = document.getElementById('aboutCarousel');
  if (!container) return;
  var track = container.querySelector('.carousel-track');
  var slides = track.querySelectorAll('.carousel-slide');
  var dotsContainer = document.getElementById('carouselDots');
  var current = 0;

  // Create dots
  slides.forEach(function(_, i) {
    var dot = document.createElement('span');
    dot.addEventListener('click', function() { goTo(i); });
    dotsContainer.appendChild(dot);
  });
  var dots = dotsContainer.querySelectorAll('span');

  function goTo(idx) {
    current = Math.max(0, Math.min(idx, slides.length - 1));
    track.scrollTo({ left: track.clientWidth * current, behavior: 'smooth' });
    dots.forEach(function(d, i) { d.classList.toggle('active', i === current); });
  }

  window.moveCarousel = function(dir) { goTo(current + dir); };

  // Sync dots on scroll
  track.addEventListener('scroll', function() {
    var idx = Math.round(track.scrollLeft / track.clientWidth);
    if (idx !== current) { current = idx; dots.forEach(function(d, i) { d.classList.toggle('active', i === current); }); }
  });

  goTo(0);

  // Auto-play
  var interval = setInterval(function() { goTo((current + 1) % slides.length); }, 4000);
  container.addEventListener('mouseenter', function() { clearInterval(interval); });
  container.addEventListener('mouseleave', function() {
    clearInterval(interval);
    interval = setInterval(function() { goTo((current + 1) % slides.length); }, 4000);
  });
})();

// Chatbot
(function() {
  var btn = document.getElementById('chatBtn');
  var widget = document.getElementById('chatWidget');
  var form = document.getElementById('chatForm');
  var input = document.getElementById('chatInput');
  var messages = document.getElementById('chatMessages');
  if (!btn || !widget || !form) return;

  btn.addEventListener('click', function() { widget.classList.toggle('open'); });

  form.addEventListener('submit', function(e) {
    e.preventDefault();
    var msg = input.value.trim();
    if (!msg) return;
    input.value = '';

    // Add user message
    var userMsg = document.createElement('div');
    userMsg.className = 'chat-msg user';
    userMsg.textContent = msg;
    messages.appendChild(userMsg);
    messages.scrollTop = messages.scrollHeight;

    // Bot thinking
    var botMsg = document.createElement('div');
    botMsg.className = 'chat-msg bot';
    botMsg.textContent = '...';
    messages.appendChild(botMsg);

    var formData = new FormData();
    formData.append('message', msg);

    fetch('/api/chat', { method: 'POST', body: formData })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        botMsg.innerHTML = data.reply.replace(/\n/g, '<br>');
        messages.scrollTop = messages.scrollHeight;
      })
      .catch(function() {
        botMsg.textContent = 'Lo siento, hubo un error. Intenta de nuevo.';
      });
  });
})();

// Cookie consent
(function() {
  var banner = document.getElementById('cookieBanner');
  if (!banner) return;
  if (document.cookie.split(';').some(function(c) { return c.trim().startsWith('cookie_consent='); })) return;
  banner.classList.add('show');
  window.cookieConsent = function(level) {
    var expiry = new Date();
    expiry.setFullYear(expiry.getFullYear() + 1);
    document.cookie = 'cookie_consent=' + level + ';expires=' + expiry.toUTCString() + ';path=/';
    banner.classList.remove('show');
  };
})();
