// Tab switching
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById(tab.dataset.tab).classList.add('active');
    });
});

function setExample(text) {
    document.getElementById('singleText').value = text;
    triggerLiveAnalysis(text);
}

async function post(url, body) {
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    return res.json();
}

// ── History tracking ──
let history = [];

function addToHistory(text, label, score) {
    history.unshift({ text: text.substring(0, 100), label, score, time: new Date() });
    if (history.length > 30) history.pop();
    renderHistory();
    updateHistoryChart();
}

function clearHistory() {
    history = [];
    renderHistory();
    updateHistoryChart();
}

function renderHistory() {
    const el = document.getElementById('historyList');
    if (history.length === 0) {
        el.innerHTML = '<p class="text-dim">No analyses yet. Go to Analyze tab and run some.</p>';
        return;
    }
    el.innerHTML = history.map(h => `
        <div class="history-item">
            <span class="history-text">${escapeHtml(h.text)}</span>
            <div class="history-meta">
                <span class="history-label ${h.label}">${h.label}</span>
                <span class="history-score">${(h.score * 100).toFixed(1)}%</span>
            </div>
        </div>
    `).join('');
}

// ── History trend chart ──
let historyChart = null;

function updateHistoryChart() {
    const ctx = document.getElementById('historyChart');
    if (!ctx) return;

    const labels = history.slice().reverse().map((_, i) => '#' + (i + 1));
    const data = history.slice().reverse().map(h =>
        h.label === 'POSITIVE' ? h.score : -h.score
    );

    if (historyChart) historyChart.destroy();

    historyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Sentiment',
                data,
                borderColor: '#6e8efb',
                backgroundColor: 'rgba(110, 142, 251, 0.1)',
                fill: true,
                tension: 0.4,
                pointBackgroundColor: data.map(v => v >= 0 ? '#34d399' : '#f87171'),
                pointBorderColor: data.map(v => v >= 0 ? '#34d399' : '#f87171'),
                pointRadius: 5,
            }],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
            },
            scales: {
                y: {
                    min: -1, max: 1,
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#5a6080', callback: v => v === 0 ? 'Neutral' : v > 0 ? 'Pos' : 'Neg' },
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#5a6080' },
                },
            },
        },
    });
}

// ── Confidence ring animation ──
function drawConfidenceRing(score, label) {
    const canvas = document.getElementById('confidenceRing');
    const ctx = canvas.getContext('2d');
    const size = 140;
    const center = size / 2;
    const radius = 55;
    const lineWidth = 10;

    ctx.clearRect(0, 0, size, size);

    // Background ring
    ctx.beginPath();
    ctx.arc(center, center, radius, 0, Math.PI * 2);
    ctx.strokeStyle = '#252a3a';
    ctx.lineWidth = lineWidth;
    ctx.stroke();

    // Animated fill
    const color = label === 'POSITIVE' ? '#34d399' : '#f87171';
    const endAngle = -Math.PI / 2 + (Math.PI * 2 * score);

    ctx.beginPath();
    ctx.arc(center, center, radius, -Math.PI / 2, endAngle);
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Glow
    ctx.shadowColor = color;
    ctx.shadowBlur = 15;
    ctx.beginPath();
    ctx.arc(center, center, radius, endAngle - 0.1, endAngle);
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth;
    ctx.stroke();
    ctx.shadowBlur = 0;

    document.getElementById('ringPercent').textContent = (score * 100).toFixed(1) + '%';
}

// ── Emotion radar chart ──
let radarChart = null;

function drawEmotionRadar(emotions) {
    const ctx = document.getElementById('emotionRadar');

    const labels = Object.keys(emotions).map(e => e.charAt(0).toUpperCase() + e.slice(1));
    const data = Object.values(emotions);

    if (radarChart) radarChart.destroy();

    radarChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels,
            datasets: [{
                label: 'Emotion',
                data,
                backgroundColor: 'rgba(110, 142, 251, 0.2)',
                borderColor: '#6e8efb',
                borderWidth: 2,
                pointBackgroundColor: '#6e8efb',
                pointBorderColor: '#fff',
                pointRadius: 4,
            }],
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                r: {
                    beginAtZero: true,
                    max: 1,
                    grid: { color: 'rgba(255,255,255,0.08)' },
                    angleLines: { color: 'rgba(255,255,255,0.08)' },
                    pointLabels: { color: '#c8cde0', font: { size: 12, family: 'Inter' } },
                    ticks: { display: false },
                },
            },
        },
    });
}

// ── Live typing analysis ──
let liveTimer = null;

document.getElementById('singleText').addEventListener('input', (e) => {
    clearTimeout(liveTimer);
    const text = e.target.value.trim();
    if (text.length < 3) {
        document.getElementById('liveIndicator').classList.add('hidden');
        return;
    }
    liveTimer = setTimeout(() => triggerLiveAnalysis(text), 400);
});

async function triggerLiveAnalysis(text) {
    if (text.length < 3) return;
    document.getElementById('liveIndicator').classList.remove('hidden');

    try {
        const data = await post('/api/live', { text });
        const el = document.getElementById('liveLabel');
        el.textContent = data.label;
        el.className = 'live-label ' + (data.label === 'POSITIVE' ? 'pos' : 'neg');

        const meter = document.getElementById('liveMeter');
        const pct = data.score * 100;
        meter.style.width = pct + '%';
        meter.style.background = data.label === 'POSITIVE' ? '#34d399' : '#f87171';

        document.getElementById('liveScore').textContent = pct.toFixed(0) + '%';
    } catch (_) {}
}

// ── Main analyze ──
async function analyzeSingle() {
    const text = document.getElementById('singleText').value.trim();
    if (!text) return;

    const btn = document.querySelector('#single .btn-primary');
    btn.disabled = true;
    btn.textContent = 'Analyzing...';

    try {
        const data = await post('/api/analyze', { text });
        const el = document.getElementById('singleResult');
        el.classList.remove('hidden');

        const labelEl = document.getElementById('singleLabel');
        labelEl.textContent = data.label;
        labelEl.className = 'label-tag ' + data.label;

        document.getElementById('singleTime').textContent = data.ms + 'ms';

        const bar = document.getElementById('singleBar');
        bar.style.width = (data.score * 100) + '%';
        bar.style.background = data.label === 'POSITIVE' ? 'var(--positive)' : 'var(--negative)';

        document.getElementById('singleScore').textContent = 'Confidence: ' + (data.score * 100).toFixed(2) + '%';

        drawConfidenceRing(data.score, data.label);
        drawEmotionRadar(data.emotions);
        addToHistory(text, data.label, data.score);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Analyze Sentiment';
    }
}

// ── Batch with chart ──
let batchChart = null;

async function analyzeBatch() {
    const raw = document.getElementById('batchText').value.trim();
    if (!raw) return;

    const texts = raw.split('\n').filter(l => l.trim());
    const btn = document.querySelector('#batch .btn-primary');
    btn.disabled = true;
    btn.textContent = 'Analyzing ' + texts.length + ' texts...';

    try {
        const data = await post('/api/batch', { texts });
        const el = document.getElementById('batchResult');
        el.classList.remove('hidden');

        const s = data.stats;
        document.getElementById('batchStats').innerHTML = `
            <div class="stat-card"><div class="val">${s.total}</div><div class="key">Total</div></div>
            <div class="stat-card"><div class="val" style="color:var(--positive)">${s.positive}</div><div class="key">Positive</div></div>
            <div class="stat-card"><div class="val" style="color:var(--negative)">${s.negative}</div><div class="key">Negative</div></div>
            <div class="stat-card"><div class="val">${s.throughput}</div><div class="key">Texts/sec</div></div>
        `;

        // Bar chart
        const ctx = document.getElementById('batchChart');
        if (batchChart) batchChart.destroy();

        batchChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.results.map((_, i) => '#' + (i + 1)),
                datasets: [{
                    label: 'Score',
                    data: data.results.map(r => r.label === 'POSITIVE' ? r.score : -r.score),
                    backgroundColor: data.results.map(r => r.label === 'POSITIVE' ? 'rgba(52,211,153,0.7)' : 'rgba(248,113,113,0.7)'),
                    borderRadius: 4,
                }],
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    y: {
                        min: -1, max: 1,
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#5a6080' },
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#5a6080' },
                    },
                },
            },
        });

        document.getElementById('batchItems').innerHTML = data.results.map(r => `
            <div class="batch-item">
                <span class="batch-text">${escapeHtml(r.text)}</span>
                <span class="batch-label ${r.label}">${r.label} ${r.score.toFixed(3)}</span>
            </div>
        `).join('');

        data.results.forEach(r => addToHistory(r.text, r.label, r.score));
    } finally {
        btn.disabled = false;
        btn.textContent = 'Analyze Batch';
    }
}

// ── Compare ──
async function analyzeCompare() {
    const a = document.getElementById('compareA').value.trim();
    const b = document.getElementById('compareB').value.trim();
    if (!a || !b) return;

    const btn = document.querySelector('#compare .btn-primary');
    btn.disabled = true;
    btn.textContent = 'Comparing...';

    try {
        const data = await post('/api/compare', { text_a: a, text_b: b });
        const el = document.getElementById('compareResult');
        el.classList.remove('hidden');

        const colorA = data.a.label === 'POSITIVE' ? 'var(--positive)' : 'var(--negative)';
        const colorB = data.b.label === 'POSITIVE' ? 'var(--positive)' : 'var(--negative)';

        el.innerHTML = `
            <div class="compare-result-grid">
                <div class="compare-card">
                    <h3>Text A</h3>
                    <div class="compare-label" style="color:${colorA}">${data.a.label}</div>
                    <div class="compare-score">${(data.a.score * 100).toFixed(2)}%</div>
                </div>
                <div class="compare-card">
                    <h3>Text B</h3>
                    <div class="compare-label" style="color:${colorB}">${data.b.label}</div>
                    <div class="compare-score">${(data.b.score * 100).toFixed(2)}%</div>
                </div>
            </div>
            <div class="compare-verdict">
                Text ${data.winner} is more positive &middot; Gap: ${data.gap.toFixed(4)} &middot; ${data.ms}ms
            </div>
        `;

        addToHistory(a, data.a.label, data.a.score);
        addToHistory(b, data.b.label, data.b.score);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Compare';
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
