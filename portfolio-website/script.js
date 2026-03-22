/* ============================================
   PORTFOLIO v3 — Lightweight scroll animations
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
    initNav();
    initScrollAnimations();
    initCounters();
    initSmoothScroll();
    initActiveNav();
    initCategoryFilter();
});

/* ---- NAV ---- */
function initNav() {
    const nav = document.getElementById('nav');
    const toggle = document.getElementById('navToggle');
    const links = document.getElementById('navLinks');

    window.addEventListener('scroll', () => {
        nav.classList.toggle('scrolled', window.scrollY > 50);
    }, { passive: true });

    if (toggle && links) {
        toggle.addEventListener('click', () => {
            links.classList.toggle('open');
        });

        links.querySelectorAll('a').forEach(a => {
            a.addEventListener('click', () => links.classList.remove('open'));
        });

        // close menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!links.contains(e.target) && !toggle.contains(e.target)) {
                links.classList.remove('open');
            }
        });
    }
}

/* ---- SCROLL ANIMATIONS ---- */
function initScrollAnimations() {
    const items = document.querySelectorAll('.anim-fade, .anim-slide');

    // hero elements animate immediately based on their data-delay
    const heroItems = document.querySelectorAll('.hero .anim-fade, .hero .anim-slide');
    heroItems.forEach(el => {
        const delay = parseInt(el.dataset.delay || '0');
        setTimeout(() => el.classList.add('visible'), delay + 200);
    });

    // everything else uses intersection observer
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry, i) => {
            if (entry.isIntersecting) {
                // skip hero items, they're handled above
                if (entry.target.closest('.hero')) return;

                const delay = parseInt(entry.target.dataset.delay || '0') + i * 50;
                setTimeout(() => entry.target.classList.add('visible'), delay);
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.08,
        rootMargin: '0px 0px -30px 0px'
    });

    items.forEach(el => {
        if (!el.closest('.hero')) {
            observer.observe(el);
        }
    });
}

/* ---- COUNTERS ---- */
function initCounters() {
    const nums = document.querySelectorAll('.stat-num[data-target]');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                countUp(entry.target);
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });
    nums.forEach(el => observer.observe(el));
}

function countUp(el) {
    const target = parseInt(el.dataset.target);
    const duration = 1400;
    const start = performance.now();

    function tick(now) {
        const progress = Math.min((now - start) / duration, 1);
        const ease = 1 - Math.pow(1 - progress, 4);
        el.textContent = Math.floor(ease * target);
        if (progress < 1) requestAnimationFrame(tick);
        else el.textContent = target;
    }
    requestAnimationFrame(tick);
}

/* ---- SMOOTH SCROLL ---- */
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href === '#') {
                e.preventDefault();
                window.scrollTo({ top: 0, behavior: 'smooth' });
                return;
            }
            const target = document.querySelector(href);
            if (target) {
                e.preventDefault();
                const offset = 80;
                const top = target.getBoundingClientRect().top + window.pageYOffset - offset;
                window.scrollTo({ top, behavior: 'smooth' });
                history.pushState(null, '', href);
            }
        });
    });
}

/* ---- CATEGORY FILTER ---- */
function initCategoryFilter() {
    const tabs = document.querySelectorAll('.cat-tab');
    const cards = document.querySelectorAll('.project-card[data-cat]');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            const cat = tab.dataset.cat;
            cards.forEach(card => {
                if (cat === 'all' || card.dataset.cat === cat) {
                    card.classList.remove('hidden');
                } else {
                    card.classList.add('hidden');
                }
            });
        });
    });
}

/* ---- ACTIVE NAV TRACKING ---- */
function initActiveNav() {
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav-links a');

    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const id = entry.target.id;
                navLinks.forEach(link => {
                    link.classList.toggle('active', link.getAttribute('data-section') === id);
                });
            }
        });
    }, { threshold: 0.15, rootMargin: '-80px 0px -40% 0px' });

    sections.forEach(s => observer.observe(s));
}
