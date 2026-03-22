let currentFocus = 'general';

document.querySelectorAll('.focus-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.focus-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentFocus = btn.dataset.focus;
    });
});

const EXAMPLES = {
    sql: `def login(username, password):\n    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"\n    cursor.execute(query)\n    user = cursor.fetchone()\n    if user:\n        session['user'] = username\n        return True\n    return False`,
    perf: `function fetchData() {\n  let data = [];\n  for (let i = 0; i < 10000; i++) {\n    data.push(fetch('/api/item/' + i).then(r => r.json()));\n  }\n  return Promise.all(data);\n}`,
    fib: `def fibonacci(n):\n    if n <= 0:\n        return 0\n    elif n == 1:\n        return 1\n    else:\n        return fibonacci(n-1) + fibonacci(n-2)\n\nfor i in range(100):\n    print(fibonacci(i))`,
};

function loadExample(key) {
    document.getElementById('codeInput').value = EXAMPLES[key];
    if (key === 'sql') currentFocus = 'security';
    else if (key === 'perf' || key === 'fib') currentFocus = 'performance';
    document.querySelectorAll('.focus-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.focus === currentFocus);
    });
}

function drawScoreRing(score) {
    const canvas = document.getElementById('scoreRing');
    const ctx = canvas.getContext('2d');
    const size = 120;
    const center = size / 2;
    const radius = 46;
    const lineWidth = 10;

    ctx.clearRect(0, 0, size, size);

    // Background ring
    ctx.beginPath();
    ctx.arc(center, center, radius, 0, Math.PI * 2);
    ctx.strokeStyle = '#252a3a';
    ctx.lineWidth = lineWidth;
    ctx.stroke();

    // Score color
    let color;
    if (score >= 80) color = '#34d399';
    else if (score >= 50) color = '#fbbf24';
    else color = '#f87171';

    // Animated fill
    const pct = score / 100;
    const endAngle = -Math.PI / 2 + (Math.PI * 2 * pct);

    ctx.beginPath();
    ctx.arc(center, center, radius, -Math.PI / 2, endAngle);
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Glow
    ctx.shadowColor = color;
    ctx.shadowBlur = 12;
    ctx.beginPath();
    ctx.arc(center, center, radius, endAngle - 0.1, endAngle);
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth;
    ctx.stroke();
    ctx.shadowBlur = 0;

    document.getElementById('scoreNum').textContent = score;
}

function toggleRaw() {
    const el = document.getElementById('rawOutput');
    el.classList.toggle('hidden');
    const btn = el.previousElementSibling;
    btn.textContent = el.classList.contains('hidden') ? 'Show Raw Output' : 'Hide Raw Output';
}

async function runReview() {
    const code = document.getElementById('codeInput').value.trim();
    if (!code) return;

    const btn = document.getElementById('reviewBtn');
    btn.disabled = true;
    btn.textContent = 'Reviewing...';

    try {
        const res = await fetch('/api/review', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                code,
                language: document.getElementById('language').value,
                focus: currentFocus,
                max_tokens: 384,
            }),
        });
        const data = await res.json();

        const el = document.getElementById('result');
        el.classList.remove('hidden');

        // Score ring
        drawScoreRing(data.score);

        // Verdict
        const vt = document.getElementById('verdictTag');
        vt.textContent = data.verdict.replace(/_/g, ' ');
        vt.className = 'verdict-tag ' + data.verdict;

        // Meta
        document.getElementById('metaTag').textContent =
            `${data.tokens} tokens | ${data.ms}ms | ${data.tps} tok/s`;

        // Summary bar
        const sb = document.getElementById('summaryBar');
        let chips = '';

        // Severity chips
        const sevColors = { CRITICAL: 'critical', WARNING: 'warning', INFO: 'info' };
        for (const [sev, count] of Object.entries(data.severity_counts)) {
            if (count > 0) {
                chips += `<div class="summary-chip">
                    <div class="chip-dot ${sevColors[sev]}"></div>
                    <span class="chip-count">${count}</span>
                    <span class="chip-label">${sev.toLowerCase()}</span>
                </div>`;
            }
        }

        // Category chips
        const catColors = { BUG: 'bug', SECURITY: 'security', PERFORMANCE: 'performance', STYLE: 'style' };
        for (const [cat, count] of Object.entries(data.counts)) {
            if (count > 0) {
                chips += `<div class="summary-chip">
                    <div class="chip-dot ${catColors[cat] || 'info'}"></div>
                    <span class="chip-count">${count}</span>
                    <span class="chip-label">${cat.toLowerCase()}</span>
                </div>`;
            }
        }
        sb.innerHTML = chips;

        // Issue cards
        const ic = document.getElementById('issueCards');
        ic.innerHTML = data.issues.map(iss => `
            <div class="issue-card ${iss.severity}">
                <div class="issue-header">
                    <span class="severity-badge ${iss.severity}">${iss.severity}</span>
                    <span class="category-badge">${iss.category}</span>
                </div>
                <div class="issue-message">${escapeHtml(iss.message)}</div>
            </div>
        `).join('');

        // Raw output
        document.getElementById('rawOutput').textContent = data.raw;
        document.getElementById('rawOutput').classList.add('hidden');

    } catch (err) {
        alert('Error: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Review Code';
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
