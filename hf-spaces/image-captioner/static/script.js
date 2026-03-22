const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const previewImg = document.getElementById('previewImg');
const uploadPrompt = document.getElementById('uploadPrompt');
const captionBtn = document.getElementById('captionBtn');
let currentFile = null;
let currentMode = 'detailed';

function setMode(mode) {
    currentMode = mode;
    document.querySelectorAll('.mode-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.mode === mode);
    });
}

fileInput.addEventListener('change', (e) => handleFile(e.target.files[0]));

dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.style.borderColor = 'var(--accent)'; });
dropZone.addEventListener('dragleave', () => { dropZone.style.borderColor = ''; });
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = '';
    if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});

function handleFile(file) {
    if (!file || !file.type.startsWith('image/')) return;
    currentFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
        previewImg.src = e.target.result;
        previewImg.classList.remove('hidden');
        uploadPrompt.style.display = 'none';
        dropZone.classList.add('has-image');
        captionBtn.disabled = false;

        // Show image meta
        const img = new window.Image();
        img.onload = () => {
            const meta = document.getElementById('imageMeta');
            meta.classList.remove('hidden');
            meta.textContent = `${img.width} x ${img.height} | ${file.name} | ${(file.size / 1024).toFixed(1)} KB`;
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

async function loadDemoImage(url, name) {
    captionBtn.disabled = true;
    captionBtn.textContent = 'Loading image...';

    try {
        const res = await fetch(url);
        const blob = await res.blob();
        currentFile = new File([blob], name + '.jpg', { type: blob.type });

        const reader = new FileReader();
        reader.onload = (e) => {
            previewImg.src = e.target.result;
            previewImg.classList.remove('hidden');
            uploadPrompt.style.display = 'none';
            dropZone.classList.add('has-image');

            const meta = document.getElementById('imageMeta');
            meta.classList.remove('hidden');
            meta.textContent = `${name} | ${(blob.size / 1024).toFixed(1)} KB`;

            captionBtn.disabled = false;
            captionBtn.textContent = 'Generate Captions';
        };
        reader.readAsDataURL(currentFile);
    } catch (err) {
        captionBtn.textContent = 'Failed to load demo image';
        setTimeout(() => { captionBtn.textContent = 'Generate Captions'; }, 2000);
    }
}

async function generateCaption() {
    if (!currentFile) return;
    captionBtn.disabled = true;
    captionBtn.textContent = 'Generating...';

    const formData = new FormData();
    formData.append('file', currentFile);
    formData.append('mode', currentMode);

    try {
        const res = await fetch('/api/caption', { method: 'POST', body: formData });
        const data = await res.json();

        const el = document.getElementById('result');
        el.classList.remove('hidden');

        const modeLabels = { quick: 'Quick', detailed: 'Detailed', creative: 'Creative' };
        document.getElementById('modeTag').textContent = modeLabels[data.mode] + ' | ' + data.size[0] + 'x' + data.size[1];
        document.getElementById('timeTag').textContent = data.ms + 'ms | ' + data.beams + ' beams';

        document.getElementById('captionList').innerHTML = data.captions.map((c, i) => `
            <div class="caption-item ${i === 0 ? 'best' : ''}">
                <span class="caption-num">${i + 1}.</span>
                <span>${escapeHtml(c)}${i === 0 ? '<span class="caption-badge">BEST</span>' : ''}</span>
            </div>
        `).join('');
    } catch (err) {
        alert('Error: ' + err.message);
    } finally {
        captionBtn.disabled = false;
        captionBtn.textContent = 'Generate Captions';
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
