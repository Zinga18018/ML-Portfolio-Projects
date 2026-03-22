/* ============================================
   PORTFOLIO v2 — Neural Network BG + Interactions
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
    initNeuralNetwork();
    initNav();
    initCounters();
    initScrollReveal();
    initSmoothScroll();
    initActiveNav();
});

/* ---- NEURAL NETWORK BACKGROUND ---- */
function initNeuralNetwork() {
    const canvas = document.getElementById('particleBg');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let w, h;
    let mouse = { x: -9999, y: -9999 };

    // Neural network layers repeated down the page
    const LAYER_CONFIGS = [
        { neurons: [3, 5, 8, 6, 4, 2], label: 'Encoder' },
        { neurons: [2, 6, 10, 8, 5, 3], label: 'Transformer' },
        { neurons: [4, 7, 5, 8, 6, 3], label: 'Decoder' },
        { neurons: [3, 6, 9, 7, 4, 2], label: 'Attention' },
        { neurons: [2, 5, 8, 10, 6, 3], label: 'MLP' },
    ];

    const COLORS = [
        { r: 124, g: 91, b: 245 },  // purple
        { r: 0, g: 194, b: 203 },    // cyan
        { r: 233, g: 64, b: 144 },   // pink
        { r: 40, g: 200, b: 64 },    // green
        { r: 251, g: 191, b: 36 },   // gold
    ];

    let networks = [];
    let pulses = [];

    function resize() {
        w = canvas.width = window.innerWidth;
        h = canvas.height = document.documentElement.scrollHeight;
        buildNetworks();
    }

    function buildNetworks() {
        networks = [];
        const sectionHeight = h / LAYER_CONFIGS.length;

        LAYER_CONFIGS.forEach((config, ni) => {
            const baseY = ni * sectionHeight + sectionHeight * 0.5;
            const color = COLORS[ni % COLORS.length];
            const layers = [];
            const layerCount = config.neurons.length;
            const totalWidth = Math.min(w * 0.7, 700);
            const startX = (w - totalWidth) / 2;
            const layerSpacing = totalWidth / (layerCount - 1);

            config.neurons.forEach((count, li) => {
                const neurons = [];
                const layerHeight = Math.min(count * 50, 300);
                const spacing = layerHeight / (count + 1);
                const x = startX + li * layerSpacing;

                for (let i = 0; i < count; i++) {
                    const y = baseY - layerHeight / 2 + spacing * (i + 1);
                    neurons.push({
                        x, y,
                        baseX: x, baseY: y,
                        r: li === 0 || li === layerCount - 1 ? 4 : 3,
                        phase: Math.random() * Math.PI * 2,
                        speed: 0.001 + Math.random() * 0.002,
                    });
                }
                layers.push(neurons);
            });

            networks.push({ layers, color, label: config.label, baseY });
        });
    }

    function spawnPulse() {
        if (networks.length === 0) return;
        const ni = Math.floor(Math.random() * networks.length);
        const net = networks[ni];
        if (net.layers.length < 2) return;

        const startLayer = 0;
        const startNeuron = Math.floor(Math.random() * net.layers[0].length);
        const n = net.layers[0][startNeuron];

        pulses.push({
            x: n.x, y: n.y,
            networkIdx: ni,
            layerIdx: 0,
            neuronIdx: startNeuron,
            targetLayer: 1,
            targetNeuron: Math.floor(Math.random() * net.layers[1].length),
            progress: 0,
            speed: 0.015 + Math.random() * 0.01,
            color: net.color,
        });
    }

    function draw(time) {
        ctx.clearRect(0, 0, w, h);
        const scrollY = window.scrollY;
        const viewTop = scrollY - 300;
        const viewBottom = scrollY + window.innerHeight + 300;

        // Spawn pulses periodically
        if (Math.random() < 0.08) spawnPulse();

        // Draw each network
        networks.forEach((net, ni) => {
            const { layers, color } = net;

            // Skip if not in view
            if (net.baseY < viewTop - 200 || net.baseY > viewBottom + 200) return;

            // Animate neuron positions (gentle float)
            layers.forEach(layer => {
                layer.forEach(n => {
                    n.x = n.baseX + Math.sin(time * n.speed + n.phase) * 3;
                    n.y = n.baseY + Math.cos(time * n.speed * 0.7 + n.phase) * 3;
                });
            });

            // Draw connections between layers
            for (let li = 0; li < layers.length - 1; li++) {
                const curr = layers[li];
                const next = layers[li + 1];

                curr.forEach(a => {
                    next.forEach(b => {
                        const sy1 = a.y - scrollY;
                        const sy2 = b.y - scrollY;

                        // Mouse proximity brightens connections
                        const midX = (a.x + b.x) / 2;
                        const midY = (a.y + b.y) / 2;
                        const dx = mouse.x - midX;
                        const dy = (mouse.y + scrollY) - midY;
                        const dist = Math.sqrt(dx * dx + dy * dy);
                        const proximity = dist < 200 ? (200 - dist) / 200 : 0;

                        const alpha = 0.03 + proximity * 0.08;
                        ctx.beginPath();
                        ctx.strokeStyle = `rgba(${color.r}, ${color.g}, ${color.b}, ${alpha})`;
                        ctx.lineWidth = 0.4 + proximity * 0.8;
                        ctx.moveTo(a.x, sy1);
                        ctx.lineTo(b.x, sy2);
                        ctx.stroke();
                    });
                });
            }

            // Draw neurons
            layers.forEach((layer, li) => {
                layer.forEach(n => {
                    const sy = n.y - scrollY;
                    const dx = mouse.x - n.x;
                    const dy = (mouse.y + scrollY) - n.y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    const hover = dist < 80 ? (80 - dist) / 80 : 0;

                    const pulse = Math.sin(time * 0.003 + n.phase) * 0.15 + 0.85;
                    const nodeAlpha = (0.3 + hover * 0.5) * pulse;
                    const r = n.r + hover * 3;

                    // Outer glow
                    const glow = ctx.createRadialGradient(n.x, sy, 0, n.x, sy, r * 5);
                    glow.addColorStop(0, `rgba(${color.r}, ${color.g}, ${color.b}, ${nodeAlpha * 0.3})`);
                    glow.addColorStop(1, 'transparent');
                    ctx.beginPath();
                    ctx.fillStyle = glow;
                    ctx.arc(n.x, sy, r * 5, 0, Math.PI * 2);
                    ctx.fill();

                    // Core
                    ctx.beginPath();
                    ctx.fillStyle = `rgba(${color.r}, ${color.g}, ${color.b}, ${nodeAlpha + 0.15})`;
                    ctx.arc(n.x, sy, r, 0, Math.PI * 2);
                    ctx.fill();

                    // Bright center
                    ctx.beginPath();
                    ctx.fillStyle = `rgba(255, 255, 255, ${nodeAlpha * 0.4})`;
                    ctx.arc(n.x, sy, r * 0.4, 0, Math.PI * 2);
                    ctx.fill();
                });
            });
        });

        // Draw and update pulses (data flowing through network)
        pulses.forEach(p => {
            const net = networks[p.networkIdx];
            if (!net) return;

            const fromLayer = net.layers[p.layerIdx];
            const toLayer = net.layers[p.targetLayer];
            if (!fromLayer || !toLayer) return;

            const from = fromLayer[p.neuronIdx];
            const to = toLayer[p.targetNeuron];
            if (!from || !to) return;

            p.progress += p.speed;
            const t = p.progress;
            const px = from.x + (to.x - from.x) * t;
            const py = from.y + (to.y - from.y) * t;
            const sy = py - scrollY;

            // Pulse glow
            const glow = ctx.createRadialGradient(px, sy, 0, px, sy, 8);
            glow.addColorStop(0, `rgba(${p.color.r}, ${p.color.g}, ${p.color.b}, 0.8)`);
            glow.addColorStop(0.5, `rgba(${p.color.r}, ${p.color.g}, ${p.color.b}, 0.2)`);
            glow.addColorStop(1, 'transparent');
            ctx.beginPath();
            ctx.fillStyle = glow;
            ctx.arc(px, sy, 8, 0, Math.PI * 2);
            ctx.fill();

            // Bright core
            ctx.beginPath();
            ctx.fillStyle = `rgba(255, 255, 255, 0.9)`;
            ctx.arc(px, sy, 2, 0, Math.PI * 2);
            ctx.fill();

            // Move to next layer when arrived
            if (p.progress >= 1) {
                p.layerIdx = p.targetLayer;
                p.neuronIdx = p.targetNeuron;
                p.targetLayer++;
                p.progress = 0;
                if (p.targetLayer < net.layers.length) {
                    p.targetNeuron = Math.floor(Math.random() * net.layers[p.targetLayer].length);
                }
            }
        });

        // Remove finished pulses
        pulses = pulses.filter(p => {
            const net = networks[p.networkIdx];
            return net && p.targetLayer < net.layers.length;
        });

        // Cap pulse count
        if (pulses.length > 30) pulses = pulses.slice(-30);

        requestAnimationFrame(draw);
    }

    window.addEventListener('resize', () => { resize(); });
    document.addEventListener('mousemove', e => {
        mouse.x = e.clientX;
        mouse.y = e.clientY;
    });

    resize();
    requestAnimationFrame(draw);
}

/* ---- NAV ---- */
function initNav() {
    const nav = document.getElementById('nav');
    const toggle = document.getElementById('navToggle');
    const links = document.getElementById('navLinks');

    window.addEventListener('scroll', () => {
        nav.classList.toggle('scrolled', window.scrollY > 50);
    });

    if (toggle && links) {
        toggle.addEventListener('click', () => {
            links.classList.toggle('open');
        });

        links.querySelectorAll('a').forEach(a => {
            a.addEventListener('click', () => {
                links.classList.remove('open');
            });
        });
    }
}

/* ---- ACTIVE NAV SECTION TRACKING ---- */
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

/* ---- COUNTERS ---- */
function initCounters() {
    const els = document.querySelectorAll('.metric-val[data-target]');
    const observer = new IntersectionObserver(entries => {
        entries.forEach(e => {
            if (e.isIntersecting) {
                animateNum(e.target);
                observer.unobserve(e.target);
            }
        });
    }, { threshold: 0.5 });
    els.forEach(el => observer.observe(el));
}

function animateNum(el) {
    const target = parseInt(el.dataset.target);
    const dur = 1600;
    const start = performance.now();
    function tick(now) {
        const p = Math.min((now - start) / dur, 1);
        const ease = 1 - Math.pow(1 - p, 4);
        el.textContent = Math.floor(ease * target);
        if (p < 1) requestAnimationFrame(tick);
        else el.textContent = target;
    }
    requestAnimationFrame(tick);
}

/* ---- SCROLL REVEAL ---- */
function initScrollReveal() {
    const items = document.querySelectorAll('.reveal-item');
    const observer = new IntersectionObserver(entries => {
        entries.forEach((e, i) => {
            if (e.isIntersecting) {
                const delay = parseInt(e.target.dataset.delay || '0') + i * 60;
                setTimeout(() => e.target.classList.add('visible'), delay);
                observer.unobserve(e.target);
            }
        });
    }, { threshold: 0.05, rootMargin: '0px 0px -40px 0px' });
    items.forEach(el => observer.observe(el));
}

/* ---- SMOOTH SCROLL (fixed) ---- */
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            // Skip bare "#" links
            if (href === '#') {
                e.preventDefault();
                window.scrollTo({ top: 0, behavior: 'smooth' });
                return;
            }
            const target = document.querySelector(href);
            if (target) {
                e.preventDefault();
                const offset = 90;
                const top = target.getBoundingClientRect().top + window.pageYOffset - offset;
                window.scrollTo({ top, behavior: 'smooth' });
                // Update URL hash without jumping
                history.pushState(null, '', href);
            }
        });
    });
}
