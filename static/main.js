document.addEventListener('DOMContentLoaded', () => {

    // =================================================================
    // TOAST NOTIFICATION SYSTEM (replaces alert())
    // =================================================================
    function showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `<span class="toast-icon">${icons[type] || icons.info}</span><span class="toast-msg">${message}</span>`;
        toast.addEventListener('click', () => { toast.classList.add('removing'); setTimeout(() => toast.remove(), 300); });
        container.appendChild(toast);
        setTimeout(() => { toast.classList.add('removing'); setTimeout(() => toast.remove(), 300); }, 4000);
    }
    window.showToast = showToast; // Global access

    // =================================================================
    // THEME TOGGLE
    // =================================================================
    const themeToggle = document.getElementById('themeToggle');
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    themeToggle.textContent = savedTheme === 'dark' ? '🌙 Tema Oscuro' : '☀️ Tema Claro';
    themeToggle.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        themeToggle.textContent = next === 'dark' ? '🌙 Tema Oscuro' : '☀️ Tema Claro';
        showToast(`Tema cambiado a ${next === 'dark' ? 'oscuro' : 'claro'}`, 'info');
    });

    // ===== DOM Elements =====
    const navBtns = document.querySelectorAll('.nav-btn');
    const mainTitle = document.getElementById('mainTitle');
    const mainSubtitle = document.getElementById('mainSubtitle');

    // Extractor Form
    const form = document.getElementById('extractorForm');
    const platformRadios = document.querySelectorAll('input[name="platform"]');
    const btnStart = document.getElementById('btnStart');
    const seleniumActions = document.getElementById('seleniumActions');
    const btnScan = document.getElementById('btnScan');

    // Progress Panel
    const progressPanel = document.getElementById('progressPanel');
    const statusText = document.getElementById('statusText');
    const countValue = document.getElementById('countValue');
    const terminal = document.getElementById('terminal');
    const resultActions = document.getElementById('resultActions');
    const btnDownload = document.getElementById('btnDownload');
    const btnNew = document.getElementById('btnNew');

    // OSINT Panel
    const osintForm = document.getElementById('osintForm');
    const osintResultsArea = document.getElementById('osintResultsArea');
    const osintTerminal = document.getElementById('osintTerminal');
    const osintCards = document.getElementById('osintCards');
    const osintActions = document.getElementById('osintActions');
    const btnOsintSearch = document.getElementById('btnOsintSearch');
    const btnOsintDownload = document.getElementById('btnOsintDownload');
    const btnOsintNew = document.getElementById('btnOsintNew');

    let currentTaskId = null;
    let pollInterval = null;

    // Load Settings + Dashboard on Start
    loadSettings();
    loadDashboard();

    // ===== Navigation Logic =====
    const panelTitles = {
        dashboardPanel: { title: 'Dashboard', sub: 'Resumen general de actividad e investigaciones.' },
        osintPanel: { title: 'Buscador OSINT Multi-Plataforma', sub: 'Busque un usuario en todas las redes sociales simultáneamente.' },
        formPanel: { title: 'Extractor de Datos', sub: 'Seleccione la plataforma, método y objetivo para iniciar la extracción.' },
        analysisPanel: { title: 'Análisis y Dashboard', sub: 'Análisis cruzado multi-plataforma y visualización de datos.' },
        toolsPanel: { title: 'Herramientas', sub: 'Extracción programada, búsqueda inversa, Sherlock y búsqueda en lote.' },
        historyPanel: { title: 'Historial de Tareas', sub: 'Revise sus extracciones anteriores y descargue los resultados.' },
        settingsPanel: { title: 'Ajustes del Sistema', sub: 'Configure credenciales, proxies, Telegram y autenticación.' },
        mapPanel: { title: 'Avanzado', sub: 'Mapa de geolocalización, grafo de relaciones, detector de cambios y análisis de bots.' },
    };

    navBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            navBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const target = btn.getAttribute('data-target');
            document.querySelectorAll('.panel').forEach(p => p.style.display = 'none');
            document.getElementById(target).style.display = 'block';

            const info = panelTitles[target];
            if (info) {
                mainTitle.textContent = info.title;
                mainSubtitle.textContent = info.sub;
            }

            if (target === 'historyPanel') loadHistory();
        });
    });

    // ===== Platform Selection (Extractor) =====
    platformRadios.forEach(radio => {
        radio.addEventListener('change', () => {
            document.querySelectorAll('.radio-card-platform .cbox-content').forEach(el => el.classList.remove('selected'));
            radio.closest('.radio-card-platform').querySelector('.cbox-content').classList.add('selected');
        });
    });

    // ===== OSINT Search =====
    osintForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('osintUsername').value.trim();
        const checkboxes = document.querySelectorAll('input[name="osintPlatform"]:checked');
        const platforms = Array.from(checkboxes).map(cb => cb.value);

        if (!username) return;
        if (platforms.length === 0) {
            showToast('Seleccione al menos una red social.', 'warning');
            return;
        }

        btnOsintSearch.disabled = true;
        btnOsintSearch.textContent = '🔄 Buscando...';
        osintResultsArea.style.display = 'block';
        osintTerminal.innerHTML = '';
        osintCards.innerHTML = '';
        osintActions.style.display = 'none';

        try {
            const response = await fetch('/osint/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, platforms })
            });

            const data = await response.json();
            currentTaskId = data.task_id;
            startOsintPolling();

        } catch (error) {
            showToast('Error al iniciar la búsqueda.', 'error');
            btnOsintSearch.disabled = false;
            btnOsintSearch.textContent = '🔍 Buscar en Todas las Redes';
        }
    });

    function startOsintPolling() {
        if (pollInterval) clearInterval(pollInterval);
        pollInterval = setInterval(async () => {
            if (!currentTaskId) return;
            try {
                const response = await fetch(`/status/${currentTaskId}`);
                const data = await response.json();

                if (data.logs && data.logs.length > 0) {
                    data.logs.forEach(msg => {
                        const p = document.createElement('p');
                        p.textContent = msg;
                        // Color code by platform
                        if (msg.includes('[Instagram]')) p.style.color = '#E1306C';
                        else if (msg.includes('[TikTok]')) p.style.color = '#00f2ea';
                        else if (msg.includes('[X]')) p.style.color = '#1DA1F2';
                        else if (msg.includes('[Facebook]')) p.style.color = '#4267B2';
                        else if (msg.includes('✓')) p.style.color = '#10b981';
                        else if (msg.includes('✗')) p.style.color = '#ef4444';
                        osintTerminal.appendChild(p);
                        osintTerminal.scrollTop = osintTerminal.scrollHeight;
                    });
                }

                if (data.status === 'completed') {
                    clearInterval(pollInterval);
                    btnOsintSearch.disabled = false;
                    btnOsintSearch.textContent = '🔍 Buscar en Todas las Redes';
                    osintActions.style.display = 'flex';
                    loadOsintResults();
                } else if (data.status === 'error') {
                    clearInterval(pollInterval);
                    btnOsintSearch.disabled = false;
                    btnOsintSearch.textContent = '🔍 Buscar en Todas las Redes';
                }

            } catch (error) { console.error("Error polling OSINT:", error); }
        }, 1000);
    }

    async function loadOsintResults() {
        if (!currentTaskId) return;
        try {
            const response = await fetch(`/osint/results/${currentTaskId}`);
            const data = await response.json();

            osintCards.innerHTML = '';

            const platformColors = {
                instagram: { bg: 'rgba(225, 48, 108, 0.1)', border: '#E1306C', icon: 'IG', baseUrl: 'https://www.instagram.com/' },
                tiktok: { bg: 'rgba(0, 242, 234, 0.1)', border: '#00f2ea', icon: 'TT', baseUrl: 'https://www.tiktok.com/@' },
                x: { bg: 'rgba(29, 161, 242, 0.1)', border: '#1DA1F2', icon: 'X', baseUrl: 'https://x.com/' },
                facebook: { bg: 'rgba(66, 103, 178, 0.1)', border: '#4267B2', icon: 'FB', baseUrl: 'https://www.facebook.com/' },
            };

            // Get the searched username from the form
            const searchedUsername = document.getElementById('osintUsername').value.trim();

            for (const [platform, info] of Object.entries(data.found || {})) {
                const colors = platformColors[platform] || { bg: 'rgba(255,255,255,0.05)', border: '#666', icon: '?', baseUrl: '' };
                const card = document.createElement('div');
                card.className = 'osint-card';
                card.style.borderColor = colors.border;

                // Always build a profile URL - use the one from data, or construct one as fallback
                const profileUser = info.username || searchedUsername;
                const profileUrl = info.profile_url || (colors.baseUrl + profileUser);

                let fieldsHtml = '';
                const skipFields = ['platform', 'profile_pic', 'profile_url'];
                for (const [key, value] of Object.entries(info)) {
                    if (skipFields.includes(key)) continue;
                    const displayKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    let displayVal = value;
                    if (typeof value === 'number') displayVal = value.toLocaleString();
                    if (typeof value === 'boolean') displayVal = value ? '✓ Sí' : '✗ No';
                    fieldsHtml += `<div class="osint-field"><span class="field-key">${displayKey}</span><span class="field-val">${displayVal || '-'}</span></div>`;
                }
                // Add profile link as a field too
                fieldsHtml += `<div class="osint-field"><span class="field-key">Perfil</span><span class="field-val"><a href="${profileUrl}" target="_blank" rel="noopener noreferrer" style="color:${colors.border}; text-decoration:none;">${profileUrl}</a></span></div>`;

                card.innerHTML = `
                    <div class="osint-card-header" style="background:${colors.bg};">
                        <span class="plat-icon" style="background:${colors.border};">${colors.icon}</span>
                        <span class="osint-platform-name">${info.platform || platform.toUpperCase()}</span>
                        <a href="${profileUrl}" target="_blank" rel="noopener noreferrer" class="osint-link">Abrir ↗</a>
                    </div>
                    <div class="osint-card-body">${fieldsHtml}</div>
                `;
                osintCards.appendChild(card);
            }

            // Show errors
            for (const [platform, error] of Object.entries(data.errors || {})) {
                const colors = platformColors[platform] || { border: '#666', icon: '?', baseUrl: '' };
                const fallbackUrl = colors.baseUrl ? (colors.baseUrl + searchedUsername) : '#';
                const card = document.createElement('div');
                card.className = 'osint-card osint-card-error';
                card.innerHTML = `
                    <div class="osint-card-header" style="background:rgba(239,68,68,0.1);">
                        <span class="plat-icon" style="background:#666;">${colors.icon}</span>
                        <span class="osint-platform-name">${platform.toUpperCase()}</span>
                        <a href="${fallbackUrl}" target="_blank" rel="noopener noreferrer" style="color:#ef4444; font-size:0.8rem; text-decoration:none;">Buscar manualmente ↗</a>
                    </div>
                `;
                osintCards.appendChild(card);
            }
        } catch (error) {
            console.error("Error loading OSINT results:", error);
        }
    }

    btnOsintDownload.addEventListener('click', () => {
        if (currentTaskId) window.location.href = `/download/${currentTaskId}`;
    });

    btnOsintNew.addEventListener('click', () => {
        osintResultsArea.style.display = 'none';
        osintCards.innerHTML = '';
        osintTerminal.innerHTML = '';
        document.getElementById('osintUsername').value = '';
        currentTaskId = null;
    });

    // ===== Extractor Form Submission =====
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const platform = document.querySelector('input[name="platform"]:checked').value;
        const extractType = document.querySelector('input[name="extractType"]:checked').value;
        const depth = document.querySelector('input[name="depth"]:checked').value;
        const target = document.getElementById('target').value.trim();

        if (!target) { showToast('Introduce un nombre de usuario.', 'warning'); return; }

        const requestData = {
            method: 'Selenium_Prepare',
            platform,
            target,
            extract_type: extractType,
            depth
        };

        try {
            btnStart.disabled = true;
            btnStart.textContent = '⏳ Abriendo navegador...';

            const response = await fetch('/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestData)
            });

            const data = await response.json();
            if (data.error) {
                showToast(data.error, 'error');
                btnStart.disabled = false;
                btnStart.textContent = '🚀 Abrir Navegador e Iniciar';
                return;
            }

            currentTaskId = data.task_id;
            seleniumActions.style.display = 'block';
            btnScan.disabled = false;
            btnStart.textContent = '✅ Navegador Abierto';
            startPolling(true);

        } catch (error) {
            showToast('Error al iniciar el proceso.', 'error');
            btnStart.disabled = false;
            btnStart.textContent = '🚀 Abrir Navegador e Iniciar';
        }
    });

    btnScan.addEventListener('click', async () => {
        btnScan.disabled = true;
        btnScan.textContent = '⏳ Extrayendo...';
        const target = document.getElementById('target').value.trim();
        const platform = document.querySelector('input[name="platform"]:checked').value;
        const extractType = document.querySelector('input[name="extractType"]:checked').value;
        const depth = document.querySelector('input[name="depth"]:checked').value;

        try {
            await fetch('/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    method: 'Selenium_Scan',
                    target,
                    task_id: currentTaskId,
                    platform,
                    extract_type: extractType,
                    depth
                })
            });
            showProgressPanel();
        } catch (error) {
            showToast('Error al iniciar el escaneo.', 'error');
            btnScan.disabled = false;
            btnScan.textContent = '▶ Comenzar Extracción Automática';
        }
    });

    // ===== Progress Panel =====
    function showProgressPanel() {
        document.querySelectorAll('.panel').forEach(p => p.style.display = 'none');
        progressPanel.style.display = 'block';
        terminal.innerHTML = '';
        countValue.textContent = '0';
        resultActions.style.display = 'none';
        statusText.innerHTML = '<div class="spinner"></div> Procesando';
        statusText.style.color = 'var(--text-primary)';
    }

    function addLog(msg) {
        const p = document.createElement('p');
        p.textContent = msg;
        terminal.appendChild(p);
        terminal.scrollTop = terminal.scrollHeight;
    }

    function startPolling(isSeleniumPrepare = false) {
        if (pollInterval) clearInterval(pollInterval);
        pollInterval = setInterval(async () => {
            if (!currentTaskId) return;
            try {
                const response = await fetch(`/status/${currentTaskId}`);
                const data = await response.json();

                if (data.status === 'not_found') { clearInterval(pollInterval); return; }

                if (data.logs && data.logs.length > 0) data.logs.forEach(addLog);
                if (data.progress !== undefined) countValue.textContent = data.progress;

                if (data.status === 'completed') {
                    clearInterval(pollInterval);
                    statusText.innerHTML = '¡Completado!';
                    statusText.style.color = 'var(--success)';
                    resultActions.style.display = 'flex';
                } else if (data.status === 'error') {
                    clearInterval(pollInterval);
                    statusText.innerHTML = 'Ocurrió un error';
                    statusText.style.color = 'var(--danger)';
                    resultActions.style.display = 'flex';
                    btnDownload.style.display = 'none';
                } else if (data.status === 'browser_ready') {
                    statusText.innerHTML = 'Esperando a que presiones Capturar Datos...';
                }
            } catch (error) { console.error("Error polling:", error); }
        }, 1000);
    }

    btnDownload.addEventListener('click', () => {
        if (currentTaskId) window.location.href = `/download/${currentTaskId}`;
    });

    document.getElementById('btnDownloadExcel').addEventListener('click', () => {
        if (currentTaskId) window.location.href = `/download/${currentTaskId}?format=excel`;
    });

    document.getElementById('btnDownloadJson').addEventListener('click', () => {
        if (currentTaskId) window.location.href = `/download/${currentTaskId}?format=json`;
    });

    document.getElementById('btnDownloadPdf').addEventListener('click', () => {
        if (currentTaskId) window.location.href = `/api/report/${currentTaskId}`;
    });

    btnNew.addEventListener('click', () => {
        progressPanel.style.display = 'none';
        document.getElementById('formPanel').style.display = 'block';
        btnStart.disabled = false;
        btnStart.textContent = '🚀 Abrir Navegador e Iniciar';
        btnScan.disabled = true;
        btnScan.textContent = '▶ Comenzar Extracción Automática';
        seleniumActions.style.display = 'none';
        currentTaskId = null;
        if (pollInterval) clearInterval(pollInterval);
    });

    // ===== Settings =====
    const settingsForm = document.getElementById('settingsForm');
    settingsForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const ig_user = document.getElementById('ig_user').value;
        const ig_pass = document.getElementById('ig_pass').value;
        const proxyList = document.getElementById('proxyList').value;
        const tgBotToken = document.getElementById('tgBotToken').value.trim();
        const tgChatId = document.getElementById('tgChatId').value.trim();

        await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ig_user, ig_pass,
                defaultUser: ig_user, defaultPassword: ig_pass,
                proxy_list: proxyList,
                telegram_bot_token: tgBotToken,
                telegram_chat_id: tgChatId,
                telegram_auto: document.getElementById('tgAutoNotify').checked
            })
        });
        showToast('Ajustes guardados correctamente.', 'success');
    });

    async function loadSettings() {
        const res = await fetch('/api/settings');
        const data = await res.json();
        // Instagram
        if (data.ig_user || data.defaultUser) {
            document.getElementById('ig_user').value = data.ig_user || data.defaultUser || '';
            if (data.ig_pass || data.defaultPassword) {
                document.getElementById('ig_pass').value = data.ig_pass || data.defaultPassword || '';
            }
        }
        // Proxies
        if (data.proxy_list) {
            document.getElementById('proxyList').value = data.proxy_list;
        }
        // Telegram
        if (data.telegram_bot_token) {
            document.getElementById('tgBotToken').value = data.telegram_bot_token;
        }
        if (data.telegram_chat_id) {
            document.getElementById('tgChatId').value = data.telegram_chat_id;
        }
        if (data.telegram_auto) {
            document.getElementById('tgAutoNotify').checked = true;
        }
        // Auth status
        try {
            const authRes = await fetch('/api/auth/status');
            const auth = await authRes.json();
            const authSection = document.querySelector('#settingsPanel .auth-status');
            if (authSection) authSection.remove();
            if (auth.authenticated) {
                const div = document.createElement('div');
                div.className = 'auth-status';
                div.style.cssText = 'display:flex;align-items:center;gap:12px;margin-top:10px;';
                div.innerHTML = `
                    <span style="color:var(--success);font-weight:600;">✓ Sesión activa como @${auth.username}</span>
                    <button class="btn" style="background:var(--danger);padding:8px 16px;font-size:0.8rem;" id="btnLogout">Cerrar Sesión</button>
                `;
                const authInfo = document.querySelectorAll('#settingsPanel .alert.alert-info');
                // Insert after the auth alert (4th alert)
                if (authInfo.length >= 4) authInfo[3].after(div);
                document.getElementById('btnLogout')?.addEventListener('click', async () => {
                    await fetch('/api/auth/logout', { method: 'POST' });
                    location.reload();
                });
            }
        } catch(e) {}
    }

    // ===== History =====
    async function loadHistory() {
        const res = await fetch('/api/history');
        const data = await res.json();
        const tbody = document.getElementById('historyTableBody');
        tbody.innerHTML = '';
        // Load tags
        let allTags = {};
        try { const tRes = await fetch('/api/tags'); allTags = await tRes.json(); } catch(e) {}
        data.reverse().forEach(item => {
            const userTags = allTags[item.target] || [];
            const tagHtml = userTags.map(t => `<span class="tag tag-${t.color}">${t.label}</span>`).join('');
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="padding:12px; border-bottom:1px solid var(--border-color);"><input type="checkbox" class="compare-check" data-id="${item.id}" data-target="${item.target}" data-platform="${item.platform || 'Instagram'}" data-count="${item.count}" data-date="${item.date}"></td>
                <td style="padding:12px; border-bottom:1px solid var(--border-color);">${item.date}</td>
                <td style="padding:12px; border-bottom:1px solid var(--border-color);"><span class="badge badge-secondary">${item.platform || 'Instagram'}</span></td>
                <td style="padding:12px; border-bottom:1px solid var(--border-color); font-weight:600;">${item.target} ${tagHtml}</td>
                <td style="padding:12px; border-bottom:1px solid var(--border-color);"><span class="badge badge-secondary">${item.method}</span></td>
                <td style="padding:12px; border-bottom:1px solid var(--border-color);">${item.count}</td>
                <td style="padding:12px; border-bottom:1px solid var(--border-color);">
                    <div style="display:flex;gap:4px;flex-wrap:wrap;">
                        <a href="/download/${item.id}" class="btn btn-primary" style="padding:4px 8px; font-size:0.75rem; text-decoration:none;">CSV</a>
                        <a href="/download/${item.id}?format=excel" class="btn btn-primary" style="padding:4px 8px; font-size:0.75rem; text-decoration:none;background:#217346;">Excel</a>
                        <a href="/download/${item.id}?format=json" class="btn btn-primary" style="padding:4px 8px; font-size:0.75rem; text-decoration:none;background:#f59e0b;color:#000;">JSON</a>
                        <a href="/api/report/${item.id}" class="btn btn-primary" style="padding:4px 8px; font-size:0.75rem; text-decoration:none;background:#dc2626;">PDF</a>
                        <a href="/api/report/${item.id}?format=docx" class="btn btn-primary" style="padding:4px 8px; font-size:0.75rem; text-decoration:none;background:#2b579a;">Word</a>
                        <button class="btn-delete" onclick="deleteHistoryItem('${item.id}')">&#x2715;</button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    // Delete single history item
    window.deleteHistoryItem = async function(id) {
        if (!confirm('¿Eliminar este registro del historial?')) return;
        const res = await fetch(`/api/history/${id}`, { method: 'DELETE' });
        if (res.ok) {
            showToast('Registro eliminado', 'success');
            loadHistory();
        } else {
            showToast('Error al eliminar', 'error');
        }
    };

    // Clear all history
    window.clearAllHistory = async function() {
        if (!confirm('¿Eliminar TODO el historial? Esta acción no se puede deshacer.')) return;
        const res = await fetch('/api/history', { method: 'DELETE' });
        if (res.ok) {
            showToast('Historial borrado', 'success');
            loadHistory();
        } else {
            showToast('Error al borrar', 'error');
        }
    };

    // ===== Cross-Analysis =====
    document.getElementById('btnCrossAnalysis').addEventListener('click', async () => {
        const fileInput = document.getElementById('crossFiles');
        const files = fileInput.files;
        if (files.length < 2) {
            showToast('Seleccione al menos 2 archivos CSV.', 'warning');
            return;
        }

        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }

        const btn = document.getElementById('btnCrossAnalysis');
        btn.disabled = true;
        btn.textContent = '⏳ Analizando...';

        try {
            const res = await fetch('/api/cross-analysis', { method: 'POST', body: formData });
            const data = await res.json();

            if (data.error) {
                showToast(data.error, 'error');
                btn.disabled = false;
                btn.textContent = '🔎 Analizar Coincidencias';
                return;
            }

            document.getElementById('crossResults').style.display = 'block';

            // Stats
            const statsDiv = document.getElementById('crossStats');
            let statsHtml = '';
            for (const [name, count] of Object.entries(data.platforms)) {
                statsHtml += `<div class="stat-card"><span class="stat-title">${name}</span><span class="stat-value">${count}</span></div>`;
            }
            statsHtml += `<div class="stat-card" style="border-color:var(--success);"><span class="stat-title">Comunes (todos)</span><span class="stat-value" style="color:var(--success);">${data.common_all_count}</span></div>`;
            statsDiv.innerHTML = statsHtml;

            // Common users list
            const terminal = document.getElementById('crossTerminal');
            terminal.innerHTML = '';
            for (const [pair, info] of Object.entries(data.pairwise)) {
                const p = document.createElement('p');
                p.innerHTML = `<strong>${pair}</strong>: ${info.count} usuarios comunes`;
                p.style.color = 'var(--accent-primary)';
                terminal.appendChild(p);
                info.users.forEach(u => {
                    const line = document.createElement('p');
                    line.textContent = `  → @${u}`;
                    terminal.appendChild(line);
                });
            }

            if (data.common_all.length > 0) {
                const header = document.createElement('p');
                header.innerHTML = `<strong>⭐ En TODAS las plataformas (${data.common_all.length}):</strong>`;
                header.style.color = '#10b981';
                terminal.appendChild(header);
                data.common_all.forEach(u => {
                    const line = document.createElement('p');
                    line.textContent = `  ⭐ @${u}`;
                    terminal.appendChild(line);
                });
            }

        } catch (error) {
            showToast('Error al analizar archivos.', 'error');
        }
        btn.disabled = false;
        btn.textContent = '🔎 Analizar Coincidencias';
    });

    // ===== Dashboard Charts =====
    let chartTypeInstance = null;
    let chartTopInstance = null;

    function loadDashboard(taskId) {
        if (!taskId) return;

        fetch(`/download/${taskId}?format=json`)
            .then(r => r.json())
            .then(data => {
                if (!data.data || data.data.length === 0) return;

                const rows = data.data;

                // Stats
                const dashStats = document.getElementById('dashStats');
                const followers = rows.filter(r => r.source === 'followers').length;
                const following = rows.filter(r => r.source === 'following').length;
                dashStats.innerHTML = `
                    <div class="stat-card"><span class="stat-title">Total Extraidos</span><span class="stat-value">${rows.length}</span></div>
                    <div class="stat-card"><span class="stat-title">Seguidores</span><span class="stat-value">${followers}</span></div>
                    <div class="stat-card"><span class="stat-title">Seguidos</span><span class="stat-value">${following}</span></div>
                `;

                // Chart: distribution by type
                if (chartTypeInstance) chartTypeInstance.destroy();
                const ctxType = document.getElementById('chartType').getContext('2d');
                chartTypeInstance = new Chart(ctxType, {
                    type: 'doughnut',
                    data: {
                        labels: ['Seguidores', 'Seguidos'],
                        datasets: [{
                            data: [followers, following],
                            backgroundColor: ['#6366f1', '#f59e0b'],
                            borderWidth: 0
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: { legend: { labels: { color: '#e2e8f0' } } }
                    }
                });

                // Chart: top 10 by followers
                if (chartTopInstance) chartTopInstance.destroy();
                const withFollowers = rows.filter(r => r.followers).sort((a, b) =>
                    parseInt(String(b.followers).replace(/[^0-9]/g, '')) - parseInt(String(a.followers).replace(/[^0-9]/g, ''))
                ).slice(0, 10);

                if (withFollowers.length > 0) {
                    const ctxTop = document.getElementById('chartTop').getContext('2d');
                    chartTopInstance = new Chart(ctxTop, {
                        type: 'bar',
                        data: {
                            labels: withFollowers.map(r => '@' + r.username),
                            datasets: [{
                                label: 'Seguidores',
                                data: withFollowers.map(r => parseInt(String(r.followers).replace(/[^0-9]/g, '')) || 0),
                                backgroundColor: '#6366f1',
                                borderRadius: 6
                            }]
                        },
                        options: {
                            responsive: true,
                            indexAxis: 'y',
                            plugins: { legend: { display: false } },
                            scales: {
                                x: { ticks: { color: '#94a3b8' }, grid: { color: '#1e293b' } },
                                y: { ticks: { color: '#e2e8f0' }, grid: { display: false } }
                            }
                        }
                    });
                }
            })
            .catch(() => {});
    }
    // ===== Scheduled Extractions =====
    async function loadScheduled() {
        try {
            const res = await fetch('/api/scheduled');
            const jobs = await res.json();
            const container = document.getElementById('scheduledList');

            if (!jobs || jobs.length === 0) {
                container.innerHTML = '<p style="color:var(--text-secondary);text-align:center;padding:20px;">No hay tareas programadas. Cree una arriba.</p>';
                return;
            }

            let html = '<table style="width:100%;border-collapse:collapse;text-align:left;">';
            html += '<thead><tr style="border-bottom:1px solid var(--border-color);">';
            html += '<th style="padding:10px;color:var(--text-secondary);font-size:0.85rem;">Plataforma</th>';
            html += '<th style="padding:10px;color:var(--text-secondary);font-size:0.85rem;">Objetivo</th>';
            html += '<th style="padding:10px;color:var(--text-secondary);font-size:0.85rem;">Cada</th>';
            html += '<th style="padding:10px;color:var(--text-secondary);font-size:0.85rem;">Estado</th>';
            html += '<th style="padding:10px;color:var(--text-secondary);font-size:0.85rem;">Acción</th>';
            html += '</tr></thead><tbody>';

            jobs.forEach(job => {
                const status = job.active
                    ? '<span style="color:var(--success);">\u2705 Activa</span>'
                    : '<span style="color:var(--text-secondary);">\u23f8 Parada</span>';
                html += `<tr style="border-bottom:1px solid var(--border-color);">`;
                html += `<td style="padding:10px;"><span class="badge badge-secondary">${job.platform.toUpperCase()}</span></td>`;
                html += `<td style="padding:10px;font-weight:600;">@${job.target}</td>`;
                html += `<td style="padding:10px;">${job.interval_days} d\u00edas</td>`;
                html += `<td style="padding:10px;">${status}</td>`;
                html += `<td style="padding:10px;"><button class="btn btn-outline" style="padding:4px 12px;font-size:0.8rem;color:var(--danger);border-color:var(--danger);" onclick="deleteScheduled('${job.job_id}')">❌ Eliminar</button></td>`;
                html += `</tr>`;
            });

            html += '</tbody></table>';
            container.innerHTML = html;
        } catch (e) {
            document.getElementById('scheduledList').innerHTML = '<p style="color:var(--text-secondary);text-align:center;">Error al cargar tareas.</p>';
        }
    }

    // Make deleteScheduled globally accessible
    window.deleteScheduled = async function(jobId) {
        if (!confirm('\u00bfEliminar esta tarea programada?')) return;
        await fetch(`/api/scheduled/${jobId}`, { method: 'DELETE' });
        loadScheduled();
    };

    document.getElementById('btnCreateScheduled').addEventListener('click', async () => {
        const platform = document.getElementById('schedPlatform').value;
        const target = document.getElementById('schedTarget').value.trim();
        const extract_type = document.getElementById('schedExtractType').value;
        const depth = document.getElementById('schedDepth').value;
        const interval_days = document.getElementById('schedInterval').value;

        if (!target) {
            showToast('Ingrese un usuario objetivo.', 'warning');
            return;
        }

        const btn = document.getElementById('btnCreateScheduled');
        btn.disabled = true;
        btn.textContent = '\u23f3 Creando...';

        try {
            const res = await fetch('/api/scheduled', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ platform, target, extract_type, depth, interval_days })
            });
            const data = await res.json();
            if (data.success) {
                showToast(`✅ Tarea programada creada. Se ejecutará cada ${interval_days} días.`, 'success');
                document.getElementById('schedTarget').value = '';
                loadScheduled();
            } else {
                showToast('Error al crear la tarea.', 'error');
            }
        } catch (e) {
            showToast('Error de conexión.', 'error');
        }
        btn.disabled = false;
        btn.textContent = '\ud83d\udcc5 Programar Extracci\u00f3n';
    });

    // ===== Reverse Search =====
    document.getElementById('btnReverseSearch').addEventListener('click', async () => {
        const query = document.getElementById('reverseQuery').value.trim();
        if (!query) {
            showToast('Ingrese un email o teléfono.', 'warning');
            return;
        }

        const btn = document.getElementById('btnReverseSearch');
        btn.disabled = true;
        btn.textContent = '\u23f3 Buscando...';

        try {
            const res = await fetch('/api/reverse-search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });
            const data = await res.json();

            document.getElementById('reverseResults').style.display = 'block';

            // Stats
            const statsDiv = document.getElementById('reverseStats');
            statsDiv.innerHTML = `
                <div class="stat-card"><span class="stat-title">Consulta</span><span class="stat-value" style="font-size:0.9rem;">${data.query}</span></div>
                <div class="stat-card"><span class="stat-title">Tipo</span><span class="stat-value">${data.type === 'email' ? '\ud83d\udce7 Email' : '\ud83d\udcf1 Tel\u00e9fono'}</span></div>
                <div class="stat-card"><span class="stat-title">Plataformas Buscadas</span><span class="stat-value">${data.platforms_checked.length}</span></div>
                <div class="stat-card" style="border-color:${data.total_found > 0 ? 'var(--success)' : 'var(--border-color)'};"><span class="stat-title">Cuentas Encontradas</span><span class="stat-value" style="color:${data.total_found > 0 ? 'var(--success)' : 'var(--text-secondary)'}">${data.total_found}</span></div>
            `;

            // Results
            const terminal = document.getElementById('reverseTerminal');
            terminal.innerHTML = '';

            if (data.results.length === 0) {
                const p = document.createElement('p');
                p.textContent = 'No se encontraron cuentas asociadas a esta consulta.';
                p.style.color = 'var(--text-secondary)';
                terminal.appendChild(p);
            } else {
                data.results.forEach(r => {
                    const p = document.createElement('p');
                    p.innerHTML = `<span style="color:var(--success);">\u2705</span> <strong>${r.platform}</strong>: ${r.detail}`;
                    terminal.appendChild(p);
                });
            }

            // Show checked platforms without results
            const foundPlatforms = data.results.map(r => r.platform);
            data.platforms_checked.forEach(plat => {
                if (!foundPlatforms.includes(plat)) {
                    const p = document.createElement('p');
                    p.innerHTML = `<span style="color:var(--text-secondary);">\u274c</span> <strong>${plat}</strong>: No encontrado`;
                    p.style.color = 'var(--text-secondary)';
                    terminal.appendChild(p);
                }
            });

        } catch (e) {
            showToast('Error al realizar la búsqueda.', 'error');
        }
        btn.disabled = false;
        btn.textContent = '\ud83d\udd0e Buscar Cuentas Asociadas';
    });

    // Load scheduled tasks when panel opens
    const origNavHandler = navBtns[0].onclick;
    navBtns.forEach(btn => {
        const origListener = btn._clickHandler;
        btn.addEventListener('click', () => {
            const target = btn.getAttribute('data-target');
            if (target === 'toolsPanel') loadScheduled();
            if (target === 'mapPanel') loadHistorySelects();
        });
    });


    // =================================================================
    // SHERLOCK MODE
    // =================================================================
    const btnSherlock = document.getElementById('btnSherlock');
    if (btnSherlock) {
        btnSherlock.addEventListener('click', async () => {
            const username = document.getElementById('sherlockUsername').value.trim();
            if (!username) { showToast('Introduce un username', 'warning'); return; };

            btnSherlock.disabled = true;
            btnSherlock.textContent = 'Buscando...';
            document.getElementById('sherlockProgress').style.display = 'block';
            document.getElementById('sherlockResults').style.display = 'none';
            document.getElementById('sherlockBar').style.width = '0%';

            try {
                const res = await fetch('/api/sherlock', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username })
                });
                const data = await res.json();
                const taskId = data.task_id;
                const total = data.total;

                // Poll progress
                const sherlockPoll = setInterval(async () => {
                    const sRes = await fetch(`/api/sherlock/${taskId}`);
                    const sData = await sRes.json();
                    const pct = Math.round((sData.progress / total) * 100);
                    document.getElementById('sherlockBar').style.width = pct + '%';
                    document.getElementById('sherlockProgressText').textContent = `${sData.progress} / ${total}`;

                    if (sData.status === 'completed') {
                        clearInterval(sherlockPoll);
                        btnSherlock.disabled = false;
                        btnSherlock.textContent = '🔍 Buscar en 120+ Plataformas';
                        document.getElementById('sherlockProgress').style.display = 'none';
                        displaySherlockResults(sData.results);
                    }
                }, 1500);

            } catch (err) {
                showToast('Error: ' + err.message, 'error');
                btnSherlock.disabled = false;
                btnSherlock.textContent = '🔍 Buscar en 120+ Plataformas';
            }
        });
    }

    function displaySherlockResults(data) {
        if (!data) return;
        document.getElementById('sherlockResults').style.display = 'block';

        document.getElementById('sherlockStats').innerHTML = `
            <div class="stat-card"><div class="stat-number">${data.total_found}</div><div class="stat-label">Encontradas</div></div>
            <div class="stat-card"><div class="stat-number">${data.total_checked}</div><div class="stat-label">Comprobadas</div></div>
            <div class="stat-card"><div class="stat-number">${Math.round(data.total_found / data.total_checked * 100)}%</div><div class="stat-label">Presencia</div></div>
        `;

        const term = document.getElementById('sherlockTerminal');
        term.innerHTML = '';
        data.results.forEach(r => {
            const line = document.createElement('div');
            line.style.padding = '4px 0';
            line.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
            if (r.found) {
                line.innerHTML = `<span style="color:#22c55e;">✓</span> <strong>${r.platform}</strong> → <a href="${r.url}" target="_blank" style="color:var(--accent);">${r.url}</a> <span style="color:var(--text-secondary);font-size:0.8rem;">(${r.response_time}ms)</span>`;
            } else {
                line.innerHTML = `<span style="color:#555;">✗</span> <span style="color:#666;">${r.platform}</span>`;
            }
            term.appendChild(line);
        });
    }


    // =================================================================
    // BULK SEARCH
    // =================================================================
    const btnBulk = document.getElementById('btnBulkSearch');
    if (btnBulk) {
        btnBulk.addEventListener('click', async () => {
            const text = document.getElementById('bulkUsernames').value.trim();
            if (!text) { showToast('Introduce al menos un username', 'warning'); return; };

            const usernames = text.split('\n').map(u => u.trim()).filter(u => u.length > 0);
            if (usernames.length === 0) { showToast('No hay usernames válidos', 'warning'); return; }
            btnBulk.disabled = true;
            btnBulk.textContent = `Buscando ${usernames.length} usuarios...`;

            try {
                const res = await fetch('/api/bulk-search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ usernames })
                });
                const data = await res.json();
                const taskId = data.task_id;

                const bulkPoll = setInterval(async () => {
                    const bRes = await fetch(`/api/bulk-search/${taskId}`);
                    const bData = await bRes.json();
                    btnBulk.textContent = `Buscando... ${bData.progress}/${bData.total}`;

                    if (bData.status === 'completed') {
                        clearInterval(bulkPoll);
                        btnBulk.disabled = false;
                        btnBulk.textContent = '🔎 Buscar Todos';
                        displayBulkResults(bData.results);
                    }
                }, 2000);

            } catch (err) {
                showToast('Error: ' + err.message, 'error');
                btnBulk.disabled = false;
                btnBulk.textContent = '🔎 Buscar Todos';
            }
        });
    }

    function displayBulkResults(results) {
        if (!results) return;
        document.getElementById('bulkResults').style.display = 'block';
        const usernames = Object.keys(results);
        let totalFound = 0;

        const term = document.getElementById('bulkTerminal');
        term.innerHTML = '';

        usernames.forEach(username => {
            const platforms = results[username] || {};
            const found = Object.values(platforms).filter(p => p && p.found).length;
            totalFound += found;

            const header = document.createElement('div');
            header.style.padding = '8px 0';
            header.style.borderBottom = '1px solid rgba(255,255,255,0.1)';
            header.innerHTML = `<strong style="color:var(--accent);">@${username}</strong> → ${found} plataformas encontradas`;
            term.appendChild(header);

            Object.entries(platforms).forEach(([plat, info]) => {
                if (info && info.found) {
                    const line = document.createElement('div');
                    line.style.paddingLeft = '16px';
                    line.style.color = '#22c55e';
                    line.innerHTML = `✓ ${plat}: <a href="${info.profile_url || '#'}" target="_blank" style="color:var(--accent);">${info.username || ''}</a>`;
                    term.appendChild(line);
                }
            });
        });

        document.getElementById('bulkStats').innerHTML = `
            <div class="stat-card"><div class="stat-number">${usernames.length}</div><div class="stat-label">Usuarios</div></div>
            <div class="stat-card"><div class="stat-number">${totalFound}</div><div class="stat-label">Cuentas Encontradas</div></div>
        `;
    }


    // =================================================================
    // TELEGRAM TEST
    // =================================================================
    const btnTg = document.getElementById('btnTestTelegram');
    if (btnTg) {
        btnTg.addEventListener('click', async () => {
            const token = document.getElementById('tgBotToken').value.trim();
            const chatId = document.getElementById('tgChatId').value.trim();
            if (!token || !chatId) { showToast('Rellena Bot Token y Chat ID', 'warning'); return; };

            btnTg.disabled = true;
            btnTg.textContent = 'Enviando...';

            try {
                const res = await fetch('/api/telegram/test', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ bot_token: token, chat_id: chatId })
                });
                const data = await res.json();
                if (data.success) {
                    showToast('Mensaje enviado a Telegram correctamente!', 'success');
                } else {
                    showToast('Error: ' + (data.error || 'Desconocido'), 'error');
                }
            } catch (err) {
                showToast('Error: ' + err.message, 'error');
            }
            btnTg.disabled = false;
            btnTg.textContent = '📨 Probar Conexión Telegram';
        });
    }


    // =================================================================
    // ADVANCED PANEL: History selects loader
    // =================================================================
    function loadHistorySelects() {
        fetch('/api/history').then(r => r.json()).then(history => {
            const selects = ['mapTaskSelect', 'diffOld', 'diffNew', 'botTaskSelect'];
            selects.forEach(id => {
                const sel = document.getElementById(id);
                if (!sel) return;
                const current = sel.value;
                sel.innerHTML = '<option value="">Seleccionar del historial...</option>';
                history.forEach(h => {
                    const opt = document.createElement('option');
                    opt.value = h.id || h.task_id;
                    opt.textContent = `${h.date} - ${h.target} (${h.platform || 'IG'}) - ${h.count || '?'} registros`;
                    sel.appendChild(opt);
                });
                if (current) sel.value = current;
            });
        }).catch(() => {});
    }


    // =================================================================
    // GEOLOCATION MAP
    // =================================================================
    let leafletMap = null;
    const btnMap = document.getElementById('btnLoadMap');
    if (btnMap) {
        btnMap.addEventListener('click', async () => {
            const taskId = document.getElementById('mapTaskSelect').value;
            if (!taskId) { showToast('Selecciona una extracción', 'warning'); return; }

            btnMap.disabled = true;
            btnMap.textContent = 'Geocodificando...';

            try {
                const res = await fetch(`/api/geodata/${taskId}`);
                const data = await res.json();

                if (data.error) {
                    showToast(data.error, 'error');
                    btnMap.disabled = false;
                    btnMap.textContent = '🌍 Cargar Mapa';
                    return;
                }

                const container = document.getElementById('mapContainer');
                container.style.display = 'block';

                if (leafletMap) {
                    leafletMap.remove();
                }

                leafletMap = L.map(container).setView([40.4168, -3.7038], 3);
                L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                    attribution: '&copy; OSM &amp; CARTO',
                    maxZoom: 18,
                }).addTo(leafletMap);

                data.markers.forEach(m => {
                    L.marker([m.lat, m.lng])
                        .addTo(leafletMap)
                        .bindPopup(`<strong>@${m.username}</strong><br>${m.location}`);
                });

                if (data.markers.length > 0) {
                    const group = L.featureGroup(data.markers.map(m => L.marker([m.lat, m.lng])));
                    leafletMap.fitBounds(group.getBounds().pad(0.3));
                }

                showToast(`${data.total} ubicaciones mapeadas`, 'success');
            } catch (err) {
                showToast('Error: ' + err.message, 'error');
            }
            btnMap.disabled = false;
            btnMap.textContent = '🌍 Cargar Mapa';
        });
    }


    // =================================================================
    // RELATIONSHIP GRAPH (D3.js)
    // =================================================================
    const btnGraph = document.getElementById('btnLoadGraph');
    if (btnGraph) {
        btnGraph.addEventListener('click', () => {
            const container = document.getElementById('graphContainer');
            container.style.display = 'block';
            container.innerHTML = '';

            // Build graph from history
            fetch('/api/history').then(r => r.json()).then(history => {
                if (!history || history.length === 0) { showToast('No hay datos en el historial', 'warning'); return; }

                const nodes = [];
                const links = [];
                const nodeSet = new Set();

                history.forEach(h => {
                    const target = h.target;
                    if (!nodeSet.has(target)) {
                        nodeSet.add(target);
                        nodes.push({ id: target, group: h.platform || 'IG', radius: 12 });
                    }
                });

                // Create connections between targets that share a platform
                const byPlatform = {};
                history.forEach(h => {
                    const p = h.platform || 'IG';
                    if (!byPlatform[p]) byPlatform[p] = [];
                    byPlatform[p].push(h.target);
                });

                Object.values(byPlatform).forEach(targets => {
                    for (let i = 0; i < targets.length; i++) {
                        for (let j = i + 1; j < targets.length; j++) {
                            links.push({ source: targets[i], target: targets[j] });
                        }
                    }
                });

                if (nodes.length === 0) { showToast('No hay datos suficientes', 'warning'); return; }

                const width = container.clientWidth;
                const height = container.clientHeight || 500;

                const colorScale = d3.scaleOrdinal(d3.schemeSet2);

                const svg = d3.select(container)
                    .append('svg')
                    .attr('width', width)
                    .attr('height', height);

                const simulation = d3.forceSimulation(nodes)
                    .force('link', d3.forceLink(links).id(d => d.id).distance(100))
                    .force('charge', d3.forceManyBody().strength(-200))
                    .force('center', d3.forceCenter(width / 2, height / 2));

                const link = svg.append('g')
                    .selectAll('line')
                    .data(links)
                    .join('line')
                    .attr('stroke', '#334')
                    .attr('stroke-width', 1.5);

                const node = svg.append('g')
                    .selectAll('circle')
                    .data(nodes)
                    .join('circle')
                    .attr('r', d => d.radius)
                    .attr('fill', d => colorScale(d.group))
                    .attr('stroke', '#fff')
                    .attr('stroke-width', 1.5)
                    .call(d3.drag()
                        .on('start', (e, d) => { if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
                        .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
                        .on('end', (e, d) => { if (!e.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; })
                    );

                const label = svg.append('g')
                    .selectAll('text')
                    .data(nodes)
                    .join('text')
                    .attr('font-size', '11px')
                    .attr('fill', '#ccc')
                    .attr('dx', 15)
                    .attr('dy', 4)
                    .text(d => '@' + d.id);

                node.append('title').text(d => `@${d.id} (${d.group})`);

                simulation.on('tick', () => {
                    link
                        .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
                        .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
                    node
                        .attr('cx', d => d.x).attr('cy', d => d.y);
                    label
                        .attr('x', d => d.x).attr('y', d => d.y);
                });
            });
        });
    }


    // =================================================================
    // DIFF / CHANGE DETECTION
    // =================================================================
    const btnDiff = document.getElementById('btnDiff');
    if (btnDiff) {
        btnDiff.addEventListener('click', async () => {
            const oldId = document.getElementById('diffOld').value;
            const newId = document.getElementById('diffNew').value;
            if (!oldId || !newId) { showToast('Selecciona ambas extracciones', 'warning'); return; }
            if (oldId === newId) { showToast('Selecciona dos extracciones diferentes', 'warning'); return; }

            btnDiff.disabled = true;
            btnDiff.textContent = 'Comparando...';

            try {
                const res = await fetch('/api/diff', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ task_id_old: oldId, task_id_new: newId })
                });
                const data = await res.json();

                if (data.error) {
                    showToast(data.error, 'error');
                } else {
                    document.getElementById('diffResults').style.display = 'block';

                    document.getElementById('diffStats').innerHTML = `
                        <div class="stat-card"><div class="stat-number" style="color:#22c55e;">+${data.gained_count}</div><div class="stat-label">Nuevos</div></div>
                        <div class="stat-card"><div class="stat-number" style="color:#ef4444;">-${data.lost_count}</div><div class="stat-label">Perdidos</div></div>
                        <div class="stat-card"><div class="stat-number">${data.maintained}</div><div class="stat-label">Mantenidos</div></div>
                        <div class="stat-card"><div class="stat-number">${data.changes_count}</div><div class="stat-label">Con Cambios</div></div>
                    `;

                    const gained = document.getElementById('diffGained');
                    gained.innerHTML = data.gained.length ? data.gained.map(u => `<div style="color:#22c55e;padding:3px 0;">+ @${u}</div>`).join('') : '<div style="color:#666;">Sin nuevos</div>';

                    const lost = document.getElementById('diffLost');
                    lost.innerHTML = data.lost.length ? data.lost.map(u => `<div style="color:#ef4444;padding:3px 0;">- @${u}</div>`).join('') : '<div style="color:#666;">Sin perdidos</div>';
                }
            } catch (err) {
                showToast('Error: ' + err.message, 'error');
            }
            btnDiff.disabled = false;
            btnDiff.textContent = '🔍 Comparar Extracciones';
        });
    }


    // =================================================================
    // BOT DETECTION
    // =================================================================
    const btnBot = document.getElementById('btnBotAnalysis');
    if (btnBot) {
        btnBot.addEventListener('click', async () => {
            const taskId = document.getElementById('botTaskSelect').value;
            if (!taskId) { showToast('Selecciona una extracción', 'warning'); return; }

            btnBot.disabled = true;
            btnBot.textContent = 'Analizando...';

            try {
                const res = await fetch(`/api/bot-analysis/${taskId}`);
                const data = await res.json();

                if (data.error) {
                    showToast(data.error, 'error');
                } else {
                    document.getElementById('botResults').style.display = 'block';

                    const riskColor = data.estimated_bot_pct > 30 ? '#ef4444' : data.estimated_bot_pct > 15 ? '#f59e0b' : '#22c55e';

                    document.getElementById('botStats').innerHTML = `
                        <div class="stat-card"><div class="stat-number">${data.total_analyzed}</div><div class="stat-label">Analizados</div></div>
                        <div class="stat-card"><div class="stat-number" style="color:${riskColor};">${data.estimated_bot_pct}%</div><div class="stat-label">Est. Bots</div></div>
                        <div class="stat-card"><div class="stat-number">${data.average_score}</div><div class="stat-label">Score Medio</div></div>
                        <div class="stat-card"><div class="stat-number" style="color:#ef4444;">${data.risk_distribution.high}</div><div class="stat-label">Riesgo Alto</div></div>
                    `;

                    const term = document.getElementById('botTerminal');
                    term.innerHTML = '';
                    data.results.slice(0, 50).forEach(r => {
                        const color = r.risk_level === 'Alto' ? '#ef4444' : r.risk_level === 'Medio' ? '#f59e0b' : '#22c55e';
                        const line = document.createElement('div');
                        line.style.padding = '4px 0';
                        line.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
                        line.innerHTML = `<span style="color:${color};font-weight:bold;">[${r.bot_score}]</span> @${r.username} <span style="color:${color};">(${r.risk_level})</span>`;
                        term.appendChild(line);
                    });
                }
            } catch (err) {
                showToast('Error: ' + err.message, 'error');
            }
            btnBot.disabled = false;
            btnBot.textContent = '🤖 Analizar Bots';
        });
    }


    // =================================================================
    // EXPORT / IMPORT DATA
    // =================================================================
    const btnExport = document.getElementById('btnExportData');
    if (btnExport) {
        btnExport.addEventListener('click', async () => {
            try {
                const res = await fetch('/api/export');
                const data = await res.json();
                const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `dataextractor_backup_${new Date().toISOString().slice(0,10)}.json`;
                a.click();
                URL.revokeObjectURL(url);
            } catch (err) {
                showToast('Error al exportar: ' + err.message, 'error');
            }
        });
    }

    const btnImport = document.getElementById('btnImportData');
    if (btnImport) {
        btnImport.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            try {
                const text = await file.text();
                const data = JSON.parse(text);
                if (!data.version) {
                    showToast('El archivo no parece ser un backup válido de DataExtractor.', 'warning');
                    return;
                }
                if (!confirm(`¿Importar backup del ${data.export_date || 'desconocido'}? Esto sobrescribirá los datos actuales.`)) return;

                const res = await fetch('/api/import', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: text
                });
                const result = await res.json();
                if (result.success) {
                    showToast('Datos importados correctamente. Recargando...', 'success');
                    location.reload();
                } else {
                    showToast('Error: ' + (result.error || 'Desconocido'), 'error');
                }
            } catch (err) {
                showToast('Error al importar: ' + err.message, 'error');
            }
            e.target.value = '';
        });
    }

    // =================================================================
    // DASHBOARD
    // =================================================================
    let activityChart = null;
    async function loadDashboard() {
        try {
            const res = await fetch('/api/dashboard-stats');
            const stats = await res.json();
            document.getElementById('statTotal').textContent = stats.total || 0;
            document.getElementById('statUsers').textContent = stats.unique_users || 0;
            document.getElementById('statPlatforms').textContent = stats.platforms || 0;
            document.getElementById('statRecords').textContent = stats.total_records || 0;

            // Activity chart
            const ctx = document.getElementById('chartActivity');
            if (ctx && stats.monthly_activity) {
                if (activityChart) activityChart.destroy();
                activityChart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: stats.monthly_activity.map(m => m.month),
                        datasets: [{
                            label: 'Investigaciones',
                            data: stats.monthly_activity.map(m => m.count),
                            backgroundColor: 'rgba(59, 130, 246, 0.5)',
                            borderColor: '#3b82f6',
                            borderWidth: 1,
                            borderRadius: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            y: { beginAtZero: true, ticks: { color: '#a1a1aa' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                            x: { ticks: { color: '#a1a1aa' }, grid: { display: false } }
                        }
                    }
                });
            }

            // Recent items
            const recentList = document.getElementById('recentList');
            if (stats.recent && stats.recent.length > 0) {
                recentList.innerHTML = stats.recent.map(item => `
                    <div class="recent-item">
                        <span><strong>${item.target || 'N/A'}</strong> — ${item.platform || 'osint'}</span>
                        <span class="recent-meta">${item.date || ''}</span>
                    </div>
                `).join('');
            }
        } catch(e) { console.log('Dashboard load error:', e); }
    }

    // Nav shortcuts (Dashboard quick actions)
    document.querySelectorAll('.nav-shortcut').forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.getAttribute('data-target');
            document.querySelectorAll('.panel').forEach(p => p.style.display = 'none');
            document.getElementById(target).style.display = 'block';
            navBtns.forEach(b => b.classList.remove('active'));
            const navBtn = document.querySelector(`.nav-btn[data-target="${target}"]`);
            if (navBtn) navBtn.classList.add('active');
            const info = panelTitles[target];
            if (info) { mainTitle.textContent = info.title; mainSubtitle.textContent = info.sub; }
        });
    });

    // =================================================================
    // HISTORY SEARCH & FILTER
    // =================================================================
    const historySearch = document.getElementById('historySearch');
    const historyFilterPlatform = document.getElementById('historyFilterPlatform');

    function filterHistory() {
        const query = (historySearch?.value || '').toLowerCase();
        const platform = historyFilterPlatform?.value || '';
        const rows = document.querySelectorAll('#historyTableBody tr');
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            const matchQuery = !query || text.includes(query);
            const matchPlatform = !platform || text.includes(platform);
            row.style.display = (matchQuery && matchPlatform) ? '' : 'none';
        });
    }
    historySearch?.addEventListener('input', filterHistory);
    historyFilterPlatform?.addEventListener('change', filterHistory);

    // =================================================================
    // TIMELINE VIEW
    // =================================================================
    const btnTimeline = document.getElementById('btnTimelineView');
    let timelineVisible = false;
    if (btnTimeline) {
        btnTimeline.addEventListener('click', async () => {
            timelineVisible = !timelineVisible;
            const tc = document.getElementById('timelineContainer');
            const tbl = document.getElementById('tableContainer');
            if (timelineVisible) {
                tc.style.display = 'block';
                tbl.style.display = 'none';
                btnTimeline.textContent = '📋 Vista Tabla';
                // Build timeline
                try {
                    const res = await fetch('/api/history');
                    const data = await res.json();
                    const tv = document.getElementById('timelineView');
                    tv.innerHTML = data.reverse().slice(0, 50).map(item => `
                        <div class="timeline-item">
                            <div class="timeline-date">${item.date || ''}</div>
                            <div class="timeline-title">${item.target || 'N/A'} — ${(item.platform || 'osint').toUpperCase()}</div>
                            <div class="timeline-sub">${item.method || ''} · ${item.count || 0} registros</div>
                        </div>
                    `).join('');
                } catch(e) {}
            } else {
                tc.style.display = 'none';
                tbl.style.display = 'block';
                btnTimeline.textContent = '⏱️ Vista Timeline';
            }
        });
    }

    // =================================================================
    // NOTES PER USER
    // =================================================================
    window.openNoteModal = async function(username) {
        // Load existing note
        let existingNote = '';
        try {
            const res = await fetch(`/api/notes/${encodeURIComponent(username)}`);
            const data = await res.json();
            existingNote = data.note || '';
        } catch(e) {}

        const note = prompt(`📝 Nota para @${username}:`, existingNote);
        if (note === null) return; // cancelled
        try {
            await fetch('/api/notes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, note })
            });
            showToast(`Nota guardada para @${username}`, 'success');
        } catch(e) {
            showToast('Error al guardar nota', 'error');
        }
    };

    // =================================================================
    // LOGIN PROMPT (show on first visit if not logged in)
    // =================================================================
    window.dismissLoginPrompt = function() {
        document.getElementById('loginPrompt').style.display = 'none';
        // Remember dismiss for 24 hours
        localStorage.setItem('loginDismissedAt', Date.now().toString());
    };
    (async function checkLoginPrompt() {
        // Check if dismissed within the last 24 hours
        const dismissedAt = localStorage.getItem('loginDismissedAt');
        if (dismissedAt && (Date.now() - parseInt(dismissedAt)) < 24 * 60 * 60 * 1000) return;
        try {
            const res = await fetch('/api/auth/status');
            const data = await res.json();
            if (!data.authenticated) {
                document.getElementById('loginPrompt').style.display = 'flex';
            }
        } catch(e) {}
    })();

    // =================================================================
    // HAMBURGER MENU (responsive)
    // =================================================================
    const hamburger = document.getElementById('hamburgerBtn');
    const sidebar = document.querySelector('.sidebar');
    if (hamburger) {
        hamburger.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                if (window.innerWidth <= 900) sidebar.classList.remove('open');
            });
        });
    }

    // =================================================================
    // SELECT ALL CHECKBOX
    // =================================================================
    const checkAll = document.getElementById('checkAll');
    if (checkAll) {
        checkAll.addEventListener('change', function() {
            document.querySelectorAll('.compare-check').forEach(cb => cb.checked = this.checked);
        });
    }

    // =================================================================
    // COMPARATOR
    // =================================================================
    window.compareSelected = function() {
        const checked = document.querySelectorAll('.compare-check:checked');
        if (checked.length < 2) {
            showToast('Selecciona al menos 2 registros para comparar', 'warning');
            return;
        }
        const items = Array.from(checked).map(cb => ({
            id: cb.dataset.id,
            target: cb.dataset.target,
            platform: cb.dataset.platform,
            count: parseInt(cb.dataset.count) || 0,
            date: cb.dataset.date
        }));

        const grid = document.getElementById('compareGrid');
        grid.innerHTML = items.map(item => `
            <div class="compare-card">
                <h3>${item.target}</h3>
                <div class="compare-metric"><span>Plataforma</span><span class="badge badge-secondary">${item.platform}</span></div>
                <div class="compare-metric"><span>Registros</span><span style="font-weight:700;color:var(--brand-primary);">${item.count}</span></div>
                <div class="compare-metric"><span>Fecha</span><span>${item.date}</span></div>
            </div>
        `).join('');

        const ctx = document.getElementById('compareChart').getContext('2d');
        if (window._compareChart) window._compareChart.destroy();
        window._compareChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: items.map(i => `${i.target} (${i.platform})`),
                datasets: [{
                    label: 'Registros',
                    data: items.map(i => i.count),
                    backgroundColor: ['#3b82f6', '#a855f7', '#ec4899', '#10b981', '#f59e0b', '#ef4444']
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true } }
            }
        });

        document.getElementById('compareResults').style.display = 'block';
        showToast(`Comparando ${items.length} perfiles`, 'info');
    };

    // =================================================================
    // ANALYSIS CHARTS (Platform pie + Timeline line)
    // =================================================================
    async function loadAnalysisCharts() {
        try {
            const res = await fetch('/api/history');
            const history = await res.json();
            if (!history.length) return;

            const platCounts = {};
            history.forEach(h => {
                const p = h.platform || 'Instagram';
                platCounts[p] = (platCounts[p] || 0) + 1;
            });

            const platCanvas = document.getElementById('platDistChart');
            if (platCanvas && !platCanvas.dataset.loaded) {
                platCanvas.dataset.loaded = '1';
                new Chart(platCanvas.getContext('2d'), {
                    type: 'doughnut',
                    data: {
                        labels: Object.keys(platCounts),
                        datasets: [{
                            data: Object.values(platCounts),
                            backgroundColor: ['#e1306c', '#ff0050', '#1DA1F2', '#1877f2', '#0a66c2', '#ff0000']
                        }]
                    },
                    options: { responsive: true, plugins: { legend: { position: 'right' } } }
                });
            }

            const dateCounts = {};
            history.forEach(h => {
                const d = h.date ? h.date.split(' ')[0] : 'N/A';
                dateCounts[d] = (dateCounts[d] || 0) + 1;
            });
            const sortedDates = Object.keys(dateCounts).sort();

            const timeCanvas = document.getElementById('timelineChart');
            if (timeCanvas && !timeCanvas.dataset.loaded) {
                timeCanvas.dataset.loaded = '1';
                new Chart(timeCanvas.getContext('2d'), {
                    type: 'line',
                    data: {
                        labels: sortedDates.slice(-15),
                        datasets: [{
                            label: 'Investigaciones',
                            data: sortedDates.slice(-15).map(d => dateCounts[d]),
                            borderColor: '#3b82f6',
                            backgroundColor: 'rgba(59,130,246,0.1)',
                            fill: true,
                            tension: 0.3
                        }]
                    },
                    options: { responsive: true, scales: { y: { beginAtZero: true } } }
                });
            }
        } catch(e) {}
    }

    // =================================================================
    // MEDIA EXTRACTOR
    // =================================================================
    const btnMediaExtract = document.getElementById('btnMediaExtract');
    if (btnMediaExtract) {
        btnMediaExtract.addEventListener('click', async () => {
            const platform = document.getElementById('mediaExPlatform').value;
            const username = document.getElementById('mediaExUsername').value.trim().replace('@', '');
            const maxPosts = document.getElementById('mediaExMax').value;
            const includeLikes = document.getElementById('mediaExLikes').checked;

            if (!username) { showToast('Introduce un username', 'warning'); return; }

            btnMediaExtract.disabled = true;
            btnMediaExtract.textContent = 'Extrayendo...';
            document.getElementById('mediaExTerminal').style.display = 'block';
            const logEl = document.getElementById('mediaExLog');
            logEl.textContent = `Iniciando extraccion de media de @${username} (${platform})...\n`;

            try {
                const res = await fetch('/api/media-extract', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ platform, username, max_posts: maxPosts, include_likes: includeLikes })
                });
                const data = await res.json();
                const taskId = data.task_id;

                const poll = setInterval(async () => {
                    const sRes = await fetch(`/api/media-extract/${taskId}`);
                    const sData = await sRes.json();
                    logEl.textContent = sData.logs.join('\n');
                    logEl.scrollTop = logEl.scrollHeight;
                    btnMediaExtract.textContent = `Extrayendo... ${sData.progress}/${sData.total}`;

                    if (sData.status === 'completed' || sData.status === 'error') {
                        clearInterval(poll);
                        btnMediaExtract.disabled = false;
                        btnMediaExtract.textContent = '\uD83D\uDCE5 Extraer Media';

                        if (sData.results && sData.results.posts && sData.results.posts.length > 0) {
                            const gallery = document.getElementById('mediaExGallery');
                            gallery.style.display = 'grid';
                            gallery.innerHTML = sData.results.posts.map(p => {
                                if (p.type === 'video') {
                                    const thumb = p.thumbnail || '';
                                    return `<div class="media-thumb" onclick="window.open('${p.url}','_blank')">
                                        ${thumb ? `<img src="${thumb}" alt="video">` : '<div style="display:flex;align-items:center;justify-content:center;height:100%;background:var(--bg-card);font-size:2rem;">\uD83C\uDFAC</div>'}
                                        <span class="media-type">VIDEO</span>
                                    </div>`;
                                } else {
                                    return `<div class="media-thumb" onclick="window.open('${p.url}','_blank')">
                                        <div style="display:flex;align-items:center;justify-content:center;height:100%;background:var(--bg-card);font-size:2rem;">\uD83D\uDCF7</div>
                                        <span class="media-type">FOTO</span>
                                    </div>`;
                                }
                            }).join('');
                            showToast(`${sData.results.posts.length} elementos encontrados`, 'success');
                        } else {
                            showToast('No se encontraron elementos', 'warning');
                        }
                    }
                }, 2000);
            } catch(err) {
                showToast('Error: ' + err.message, 'error');
                btnMediaExtract.disabled = false;
                btnMediaExtract.textContent = '\uD83D\uDCE5 Extraer Media';
            }
        });
    }

    // Trigger analysis charts when panel opens
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.dataset.target === 'analysisPanel') {
                setTimeout(loadAnalysisCharts, 300);
            }
        });
    });

});
