// Tab switching
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
    });
});

// ── Text file upload zone ──
const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');
let selectedFile = null;

uploadZone.addEventListener('click', () => fileInput.click());
uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('dragover'); });
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
uploadZone.addEventListener('drop', e => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
        selectedFile = e.dataTransfer.files[0];
        uploadZone.innerHTML = `<p class="file-name">${selectedFile.name}</p><p class="hint">${(selectedFile.size / 1024).toFixed(1)} KB</p>`;
    }
});
fileInput.addEventListener('change', () => {
    if (fileInput.files.length) {
        selectedFile = fileInput.files[0];
        uploadZone.innerHTML = `<p class="file-name">${selectedFile.name}</p><p class="hint">${(selectedFile.size / 1024).toFixed(1)} KB</p>`;
    }
});

// ── CSV upload zone ──
const csvUploadZone = document.getElementById('csvUploadZone');
const csvFileInput = document.getElementById('csvFileInput');
let csvFile = null;
let csvHeaders = [];

csvUploadZone.addEventListener('click', () => csvFileInput.click());
csvUploadZone.addEventListener('dragover', e => { e.preventDefault(); csvUploadZone.classList.add('dragover'); });
csvUploadZone.addEventListener('dragleave', () => csvUploadZone.classList.remove('dragover'));
csvUploadZone.addEventListener('drop', e => {
    e.preventDefault();
    csvUploadZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) handleCSVFile(e.dataTransfer.files[0]);
});
csvFileInput.addEventListener('change', () => {
    if (csvFileInput.files.length) handleCSVFile(csvFileInput.files[0]);
});

async function handleCSVFile(file) {
    csvFile = file;
    csvUploadZone.innerHTML = `<p class="file-name">${file.name}</p><p class="hint">${(file.size / 1024).toFixed(1)} KB -- previewing...</p>`;

    const form = new FormData();
    form.append('file', file);

    try {
        const res = await fetch('/api/csv/preview', { method: 'POST', body: form });
        const data = await res.json();
        if (data.error) { csvUploadZone.innerHTML = `<p>${data.error}</p>`; return; }

        csvHeaders = data.headers;
        document.getElementById('csvFileName').textContent = data.filename;
        document.getElementById('csvMeta').textContent = `${data.total_rows} rows | ${data.columns} columns`;

        // Render table
        document.getElementById('csvThead').innerHTML = '<tr>' + data.headers.map(h => `<th>${escapeHtml(h)}</th>`).join('') + '</tr>';
        document.getElementById('csvTbody').innerHTML = data.preview.map(row =>
            '<tr>' + row.map(cell => `<td>${escapeHtml(cell)}</td>`).join('') + '</tr>'
        ).join('');

        // Render column picker
        document.getElementById('columnPicker').innerHTML = data.headers.map(h =>
            `<label class="col-toggle selected" onclick="this.classList.toggle('selected')">
                <input type="checkbox" value="${escapeHtml(h)}" checked> ${escapeHtml(h)}
            </label>`
        ).join('');

        document.getElementById('csvPreview').classList.remove('hidden');
    } catch (err) {
        csvUploadZone.innerHTML = `<p>Error: ${err.message}</p>`;
    }
}

async function ingestCSV() {
    if (!csvFile) return;
    const checkboxes = document.querySelectorAll('#columnPicker input:checked');
    const cols = Array.from(checkboxes).map(c => c.value).join(',');

    const form = new FormData();
    form.append('file', csvFile);
    form.append('columns', cols);

    const el = document.getElementById('csvResult');
    el.classList.remove('hidden');
    el.innerHTML = '<p class="meta">Ingesting CSV...</p>';

    try {
        const res = await fetch('/api/csv/ingest', { method: 'POST', body: form });
        const data = await res.json();
        if (data.error) { el.innerHTML = `<p class="meta">${data.error}</p>`; return; }

        el.innerHTML = `
            <p class="meta">${data.ms}ms</p>
            <p>Ingested <strong>"${escapeHtml(data.title)}"</strong></p>
            <p>Rows indexed: ${data.rows_indexed} | Chunks: ${data.chunks} | Columns: ${data.columns_used.join(', ')}</p>
            <p>Total in store: ${data.total_docs}</p>
        `;
    } catch (err) {
        el.innerHTML = `<p class="meta">Error: ${err.message}</p>`;
    }
}

// ── PDF upload zone ──
const pdfUploadZone = document.getElementById('pdfUploadZone');
const pdfFileInput = document.getElementById('pdfFileInput');
let pdfFile = null;

pdfUploadZone.addEventListener('click', () => pdfFileInput.click());
pdfUploadZone.addEventListener('dragover', e => { e.preventDefault(); pdfUploadZone.classList.add('dragover'); });
pdfUploadZone.addEventListener('dragleave', () => pdfUploadZone.classList.remove('dragover'));
pdfUploadZone.addEventListener('drop', e => {
    e.preventDefault();
    pdfUploadZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) handlePDFFile(e.dataTransfer.files[0]);
});
pdfFileInput.addEventListener('change', () => {
    if (pdfFileInput.files.length) handlePDFFile(pdfFileInput.files[0]);
});

async function handlePDFFile(file) {
    pdfFile = file;
    pdfUploadZone.innerHTML = `<p class="file-name">${file.name}</p><p class="hint">${(file.size / 1024).toFixed(1)} KB -- extracting pages...</p>`;

    const form = new FormData();
    form.append('file', file);

    try {
        const res = await fetch('/api/pdf/preview', { method: 'POST', body: form });
        const data = await res.json();
        if (data.error) { pdfUploadZone.innerHTML = `<p>${data.error}</p>`; return; }

        document.getElementById('pdfFileName').textContent = data.filename;
        document.getElementById('pdfMeta').textContent = `${data.total_pages} pages | ${data.total_chars.toLocaleString()} characters`;

        // Set page range defaults
        document.getElementById('pdfPageStart').value = 1;
        document.getElementById('pdfPageStart').max = data.total_pages;
        document.getElementById('pdfPageEnd').value = data.total_pages;
        document.getElementById('pdfPageEnd').max = data.total_pages;

        // Render page previews
        const pagesEl = document.getElementById('pdfPages');
        pagesEl.innerHTML = data.pages.map(p => `
            <div class="pdf-page ${p.chars === 0 ? 'empty' : ''}">
                <div class="pdf-page-header">
                    <span class="pdf-page-num">Page ${p.page}</span>
                    <span class="pdf-page-chars">${p.chars.toLocaleString()} chars</span>
                </div>
                <div class="pdf-page-text">${p.chars === 0 ? 'No extractable text (likely a scanned image)' : escapeHtml(p.preview)}</div>
            </div>
        `).join('');

        document.getElementById('pdfPreview').classList.remove('hidden');
        pdfUploadZone.innerHTML = `<p class="file-name">${file.name}</p><p class="hint">${data.total_pages} pages extracted</p>`;
    } catch (err) {
        pdfUploadZone.innerHTML = `<p>Error: ${err.message}</p>`;
    }
}

async function ingestPDF() {
    if (!pdfFile) return;

    const pageStart = parseInt(document.getElementById('pdfPageStart').value) || 1;
    const pageEnd = parseInt(document.getElementById('pdfPageEnd').value) || 0;

    const form = new FormData();
    form.append('file', pdfFile);
    form.append('page_start', pageStart);
    form.append('page_end', pageEnd);

    const el = document.getElementById('pdfResult');
    el.classList.remove('hidden');
    el.innerHTML = '<p class="meta">Extracting text & embedding pages...</p>';

    try {
        const res = await fetch('/api/pdf/ingest', { method: 'POST', body: form });
        const data = await res.json();
        if (data.error) { el.innerHTML = `<p class="meta">${data.error}</p>`; return; }

        el.innerHTML = `
            <p class="meta">${data.ms}ms</p>
            <p>Ingested <strong>"${escapeHtml(data.title)}"</strong></p>
            <div class="pdf-stats">
                <div class="pdf-stat"><div class="val">${data.pages_processed}</div><div class="key">Pages</div></div>
                <div class="pdf-stat"><div class="val">${data.chunks}</div><div class="key">Chunks</div></div>
                <div class="pdf-stat"><div class="val">${data.characters.toLocaleString()}</div><div class="key">Characters</div></div>
            </div>
            <p style="margin-top:10px">Page range: ${data.page_range} of ${data.total_pages} | Total in store: ${data.total_docs}</p>
        `;
    } catch (err) {
        el.innerHTML = `<p class="meta">Error: ${err.message}</p>`;
    }
}

// ── Ask (chatbot) ──
let chatHistory = [];

async function askQuestion() {
    const input = document.getElementById('askInput');
    const question = input.value.trim();
    if (!question) return;

    const btn = document.getElementById('askBtn');
    btn.disabled = true;
    input.value = '';

    const messages = document.getElementById('chatMessages');

    // Remove welcome message if present
    const welcome = messages.querySelector('.chat-welcome');
    if (welcome) welcome.remove();

    // Add user bubble
    const userBubble = document.createElement('div');
    userBubble.className = 'chat-bubble user';
    userBubble.textContent = question;
    messages.appendChild(userBubble);

    // Add thinking bubble
    const thinkBubble = document.createElement('div');
    thinkBubble.className = 'chat-bubble thinking';
    thinkBubble.innerHTML = 'Reading your documents<span class="thinking-dots"></span>';
    messages.appendChild(thinkBubble);
    messages.scrollTop = messages.scrollHeight;

    try {
        const res = await fetch('/api/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, top_k: 3, max_tokens: 300 }),
        });
        const data = await res.json();

        // Remove thinking bubble
        thinkBubble.remove();

        if (data.error) {
            const errBubble = document.createElement('div');
            errBubble.className = 'chat-bubble bot';
            errBubble.textContent = data.error;
            messages.appendChild(errBubble);
        } else {
            // Add bot answer bubble
            const botBubble = document.createElement('div');
            botBubble.className = 'chat-bubble bot';

            let sourcesHtml = '';
            if (data.sources && data.sources.length > 0) {
                sourcesHtml = '<div class="chat-sources">Sources: ' +
                    data.sources.map(s =>
                        `<span class="chat-source">${escapeHtml(s.source)} <span class="sim">${(s.similarity * 100).toFixed(0)}%</span></span>`
                    ).join('') + '</div>';
            }

            botBubble.innerHTML = `
                <div class="answer-text">${escapeHtml(data.answer)}</div>
                ${sourcesHtml}
                <div class="chat-timing">Retrieve: ${data.retrieve_ms}ms | Generate: ${data.generate_ms}ms | ${data.tokens} tokens</div>
            `;
            messages.appendChild(botBubble);
        }
    } catch (err) {
        thinkBubble.remove();
        const errBubble = document.createElement('div');
        errBubble.className = 'chat-bubble bot';
        errBubble.textContent = 'Error: ' + err.message;
        messages.appendChild(errBubble);
    }

    messages.scrollTop = messages.scrollHeight;
    btn.disabled = false;
    input.focus();
}

// ── Text ingest ──
async function ingestText() {
    const text = document.getElementById('docText').value.trim();
    const title = document.getElementById('docTitle').value.trim();
    if (!text) return;

    const el = document.getElementById('ingestResult');
    el.classList.remove('hidden');
    el.innerHTML = '<p class="meta">Ingesting...</p>';

    try {
        const res = await fetch('/api/ingest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, title }),
        });
        const data = await res.json();
        if (data.error) { el.innerHTML = `<p class="meta">${data.error}</p>`; return; }

        el.innerHTML = `
            <p class="meta">${data.ms}ms</p>
            <p>Ingested "<strong>${escapeHtml(data.title)}</strong>"</p>
            <p>Chunks: ${data.chunks} | Characters: ${data.characters.toLocaleString()} | Total in store: ${data.total_docs}</p>
        `;
    } catch (err) {
        el.innerHTML = `<p class="meta">Error: ${err.message}</p>`;
    }
}

async function ingestFile() {
    if (!selectedFile) return;
    const el = document.getElementById('ingestResult');
    el.classList.remove('hidden');
    el.innerHTML = '<p class="meta">Uploading & ingesting...</p>';

    try {
        const form = new FormData();
        form.append('file', selectedFile);
        const res = await fetch('/api/upload', { method: 'POST', body: form });
        const data = await res.json();
        if (data.error) { el.innerHTML = `<p class="meta">${data.error}</p>`; return; }

        el.innerHTML = `
            <p class="meta">${data.ms}ms</p>
            <p>Ingested "<strong>${escapeHtml(data.title)}</strong>"</p>
            <p>Chunks: ${data.chunks} | Characters: ${data.characters.toLocaleString()} | Total in store: ${data.total_docs}</p>
        `;
    } catch (err) {
        el.innerHTML = `<p class="meta">Error: ${err.message}</p>`;
    }
}

// ── Query with similarity bars ──
async function queryDocs() {
    const question = document.getElementById('queryInput').value.trim();
    const topK = parseInt(document.getElementById('topK').value) || 5;
    if (!question) return;

    const el = document.getElementById('queryResult');
    el.classList.remove('hidden');
    el.innerHTML = '<p class="meta">Searching...</p>';

    try {
        const res = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, top_k: topK }),
        });
        const data = await res.json();
        if (data.error) { el.innerHTML = `<p class="meta">${data.error}</p>`; return; }

        let html = `<p class="meta">${data.ms}ms | ${data.results.length} results</p>`;
        for (const m of data.results) {
            const simPct = (m.similarity * 100).toFixed(1);
            const barColor = m.similarity > 0.7 ? '#34d399' : m.similarity > 0.4 ? '#fbbf24' : '#f87171';
            html += `
                <div class="match">
                    <div class="match-header">
                        <span class="match-rank">#${m.rank}</span>
                        <span class="match-source">${escapeHtml(m.source)}</span>
                        <div class="match-sim-wrap">
                            <div class="sim-bar-wrap">
                                <div class="sim-bar" style="width:${simPct}%;background:${barColor}"></div>
                            </div>
                            <span class="match-sim" style="color:${barColor}">${simPct}%</span>
                        </div>
                    </div>
                    <div class="match-text">${escapeHtml(m.preview)}</div>
                </div>
            `;
        }
        el.innerHTML = html;
    } catch (err) {
        el.innerHTML = `<p class="meta">Error: ${err.message}</p>`;
    }
}

// ── Status + Word Cloud ──
async function getStatus() {
    const el = document.getElementById('statusResult');
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        if (data.total_chunks === 0) {
            el.textContent = 'Store is empty. No documents ingested.';
            document.getElementById('wordCloudWrap').classList.add('hidden');
        } else {
            el.textContent = `Documents: ${data.documents.join(', ')}\nTotal chunks: ${data.total_chunks}\nModel: ${data.model} (384 dimensions)`;

            if (data.top_words && data.top_words.length > 0) {
                document.getElementById('wordCloudWrap').classList.remove('hidden');
                drawWordCloud(data.top_words);
            }
        }
    } catch (err) {
        el.textContent = 'Error: ' + err.message;
    }
}

function drawWordCloud(words) {
    const canvas = document.getElementById('wordCloud');
    const ctx = canvas.getContext('2d');
    const W = canvas.width;
    const H = canvas.height;

    ctx.clearRect(0, 0, W, H);

    const maxCount = words[0].count;
    const colors = ['#6e8efb', '#34d399', '#e879f9', '#fbbf24', '#f87171', '#60a5fa', '#a78bfa'];

    // Simple scatter layout
    const positions = [];
    words.forEach((w, i) => {
        const size = Math.max(12, Math.min(36, (w.count / maxCount) * 36));
        ctx.font = `${Math.round(size * 0.8) >= 14 ? 600 : 400} ${size}px Inter, sans-serif`;

        let x, y, attempts = 0;
        const metrics = ctx.measureText(w.word);
        const tw = metrics.width;

        do {
            x = 20 + Math.random() * (W - tw - 40);
            y = size + Math.random() * (H - size - 10);
            attempts++;
        } while (attempts < 50 && positions.some(p =>
            Math.abs(p.x - x) < (tw + p.w) / 2 + 4 &&
            Math.abs(p.y - y) < size * 0.8
        ));

        positions.push({ x, y, w: tw });
        ctx.fillStyle = colors[i % colors.length];
        ctx.globalAlpha = 0.7 + (w.count / maxCount) * 0.3;
        ctx.fillText(w.word, x, y);
    });
    ctx.globalAlpha = 1;
}

async function clearAll() {
    if (!confirm('Clear all documents?')) return;
    try {
        await fetch('/api/clear', { method: 'POST' });
        document.getElementById('statusResult').textContent = 'All documents cleared.';
        document.getElementById('wordCloudWrap').classList.add('hidden');
    } catch (err) {
        document.getElementById('statusResult').textContent = 'Error: ' + err.message;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
