// Tab switching
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
    });
});

const EXAMPLES = {
    prime: 'Write a Python function to find prime numbers and analyze its time complexity',
    api: 'Design a REST API for a todo app with authentication',
    sort: 'Compare bubble sort vs quicksort and write both implementations',
};

const AGENT_ICONS = {
    planner: '\u{1F4CB}',
    coder: '\u{1F4BB}',
    researcher: '\u{1F50D}',
    analyst: '\u{1F4CA}',
    synthesizer: '\u{1F9E9}',
};

function loadExample(key) {
    document.getElementById('taskInput').value = EXAMPLES[key];
    if (key === 'sort') document.getElementById('useAnalyst').checked = true;
}

let lastOrchResult = null;
let lastTask = '';
let tokenChart = null;

function buildFlowchart(agents, activeIdx) {
    const nodes = document.getElementById('flowNodes');
    let html = '';
    agents.forEach((agent, i) => {
        let cls = '';
        if (i < activeIdx) cls = 'done';
        else if (i === activeIdx) cls = 'active';

        html += `<div class="flow-node ${cls}">
            <span class="flow-icon">${AGENT_ICONS[agent] || '\u{2699}'}</span>
            <span class="flow-label">${agent}</span>
            <span class="flow-ms" id="flow-ms-${i}"></span>
        </div>`;

        if (i < agents.length - 1) {
            html += `<span class="flow-arrow ${i < activeIdx ? 'done' : ''}">\u{2192}</span>`;
        }
    });
    nodes.innerHTML = html;
}

async function runOrchestrate() {
    const task = document.getElementById('taskInput').value.trim();
    if (!task) return;
    lastTask = task;

    const agents = ['planner'];
    if (document.getElementById('useCoder').checked) agents.push('coder');
    if (document.getElementById('useResearcher').checked) agents.push('researcher');
    if (document.getElementById('useAnalyst').checked) agents.push('analyst');
    agents.push('synthesizer');

    const maxTokens = parseInt(document.getElementById('maxTokens').value) || 300;

    const btn = document.getElementById('orchBtn');
    btn.disabled = true;
    btn.textContent = 'Running pipeline...';

    // Show flowchart
    const flowEl = document.getElementById('flowchart');
    flowEl.classList.remove('hidden');
    buildFlowchart(agents, 0);

    const el = document.getElementById('orchResult');
    el.classList.remove('hidden');
    el.innerHTML = '<div class="phase"><p class="phase-output">Starting pipeline...</p></div>';

    try {
        const res = await fetch('/api/orchestrate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task, agents: agents.filter(a => a !== 'planner' && a !== 'synthesizer'), max_tokens: maxTokens }),
        });
        const data = await res.json();
        lastOrchResult = data;

        if (data.error) {
            el.innerHTML = `<div class="phase"><p class="phase-output">${data.error}</p></div>`;
            return;
        }

        // Update flowchart - all done
        buildFlowchart(agents, agents.length);
        data.phases.forEach((phase, i) => {
            const msEl = document.getElementById('flow-ms-' + i);
            if (msEl) msEl.textContent = phase.ms + 'ms';
        });

        // Render phase cards
        let html = '';
        data.phases.forEach(phase => {
            html += `
                <div class="phase">
                    <div class="phase-header">
                        <div>
                            <span class="phase-agent">${AGENT_ICONS[phase.agent] || ''} ${phase.agent}</span>
                            <span class="phase-label"> -- ${phase.label}</span>
                        </div>
                        <span class="phase-meta">${phase.tokens} tok | ${phase.ms}ms</span>
                    </div>
                    <div class="phase-output">${escapeHtml(phase.output)}</div>
                </div>
            `;
        });

        html += `
            <div class="total-bar">
                <span>Agents: ${data.agent_count}</span>
                <span>Total: ${data.total_ms}ms</span>
            </div>
        `;
        el.innerHTML = html;

        // Token usage bar chart
        drawTokenChart(data.phases);

        // Show follow-up
        document.getElementById('followUpWrap').classList.remove('hidden');

    } catch (err) {
        el.innerHTML = `<div class="phase"><p class="phase-output">Error: ${err.message}</p></div>`;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Run Pipeline';
    }
}

function drawTokenChart(phases) {
    const wrap = document.getElementById('tokenChartWrap');
    wrap.classList.remove('hidden');

    const ctx = document.getElementById('tokenChart');
    if (tokenChart) tokenChart.destroy();

    const colors = {
        planner: '#6e8efb',
        coder: '#34d399',
        researcher: '#fbbf24',
        analyst: '#e879f9',
        synthesizer: '#f87171',
    };

    tokenChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: phases.map(p => p.agent.charAt(0).toUpperCase() + p.agent.slice(1)),
            datasets: [
                {
                    label: 'Tokens',
                    data: phases.map(p => p.tokens),
                    backgroundColor: phases.map(p => colors[p.agent] || '#6e8efb'),
                    borderRadius: 6,
                },
                {
                    label: 'Time (ms)',
                    data: phases.map(p => p.ms),
                    backgroundColor: phases.map(p => (colors[p.agent] || '#6e8efb') + '44'),
                    borderRadius: 6,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { labels: { color: '#5a6080', font: { family: 'Inter' } } },
            },
            scales: {
                y: {
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
}

async function runFollowUp() {
    const followUp = document.getElementById('followUpInput').value.trim();
    if (!followUp || !lastOrchResult) return;

    const btn = document.getElementById('followUpBtn');
    btn.disabled = true;
    btn.textContent = 'Processing...';

    // Build context from previous results
    const priorContext = lastOrchResult.phases.map(p => `[${p.agent.toUpperCase()}]: ${p.output}`).join('\n\n');
    const task = `Previous task: ${lastTask}\n\nPrevious agent outputs:\n${priorContext}\n\nFollow-up question: ${followUp}`;

    const el = document.getElementById('followUpResult');
    el.classList.remove('hidden');
    el.innerHTML = '<div class="phase"><p class="phase-output">Thinking...</p></div>';

    try {
        const res = await fetch('/api/single', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ agent: 'synthesizer', task, max_tokens: 300 }),
        });
        const data = await res.json();

        el.innerHTML = `
            <div class="phase">
                <div class="phase-header">
                    <span class="phase-agent">${AGENT_ICONS.synthesizer} Synthesizer (follow-up)</span>
                    <span class="phase-meta">${data.tokens} tok | ${data.ms}ms</span>
                </div>
                <div class="phase-output">${escapeHtml(data.output)}</div>
            </div>
        `;
    } catch (err) {
        el.innerHTML = `<div class="phase"><p class="phase-output">Error: ${err.message}</p></div>`;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Send Follow-up';
    }
}

async function runSingle() {
    const agent = document.getElementById('agentSelect').value;
    const task = document.getElementById('singleTask').value.trim();
    const maxTokens = parseInt(document.getElementById('singleMaxTok').value) || 300;
    if (!task) return;

    const btn = document.getElementById('singleBtn');
    btn.disabled = true;
    btn.textContent = 'Running...';

    const el = document.getElementById('singleResult');
    el.classList.remove('hidden');
    el.innerHTML = '<div class="phase"><p class="phase-output">Running agent...</p></div>';

    try {
        const res = await fetch('/api/single', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ agent, task, max_tokens: maxTokens }),
        });
        const data = await res.json();
        if (data.error) { el.innerHTML = `<div class="phase"><p class="phase-output">${data.error}</p></div>`; return; }

        el.innerHTML = `
            <div class="phase">
                <div class="phase-header">
                    <span class="phase-agent">${AGENT_ICONS[data.agent] || ''} ${data.agent}</span>
                    <span class="phase-meta">${data.tokens} tok | ${data.ms}ms</span>
                </div>
                <div class="phase-output">${escapeHtml(data.output)}</div>
            </div>
        `;
    } catch (err) {
        el.innerHTML = `<div class="phase"><p class="phase-output">Error: ${err.message}</p></div>`;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Run Agent';
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
