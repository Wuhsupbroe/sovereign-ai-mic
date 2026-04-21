// ── Sovereign AI — Web UI Logic ───────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {

    // ── Equalizer visualizer ──────────────────────────────────────────────────
    const eqContainer = document.getElementById('eq-bars');
    const NUM_BARS = 24;

    for (let i = 0; i < NUM_BARS; i++) {
        const bar = document.createElement('div');
        bar.className = 'eq-bar';
        bar.style.height = '3px';
        eqContainer.appendChild(bar);
    }
    const bars = eqContainer.querySelectorAll('.eq-bar');

    eel.expose(update_equalizer);
    function update_equalizer(amplitudes) {
        if (!amplitudes) return;
        for (let i = 0; i < NUM_BARS; i++) {
            if (amplitudes[i] !== undefined) {
                const h = Math.max(3, Math.min(28, amplitudes[i] * 1.4));
                bars[i].style.height = h + 'px';
            }
        }
    }

    // ── Page navigation ───────────────────────────────────────────────────────
    const navItems  = document.querySelectorAll('.nav-item');
    const pages     = document.querySelectorAll('.page');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const target = item.dataset.page;
            navItems.forEach(n => {
                n.classList.remove('active');
                const ind = n.querySelector('.active-indicator');
                if (ind) ind.remove();
            });
            item.classList.add('active');
            const ind = document.createElement('div');
            ind.className = 'active-indicator';
            item.prepend(ind);

            pages.forEach(p => p.classList.remove('active'));
            const tp = document.getElementById('page-' + target);
            if (tp) tp.classList.add('active');
        });
    });

    // ── Live state polling ────────────────────────────────────────────────────
    const pillTitle       = document.getElementById('pill-title');
    const pillSub         = document.getElementById('pill-sub');
    const apiBadge        = document.getElementById('api-badge');
    const geminiChip      = document.getElementById('gemini-chip');
    const modelBadge      = document.getElementById('model-badge');
    const statusDot       = document.getElementById('status-dot');
    const sidebarStatus   = document.getElementById('sidebar-status');

    // Dashboard stats
    const statWordsToday  = document.getElementById('stat-words-today');
    const statWordsTotal  = document.getElementById('stat-words-total');
    const statSessions    = document.getElementById('stat-sessions');
    const statMacros      = document.getElementById('stat-macros');

    // Voice commands page
    const wakeWordDisplay  = document.getElementById('wake-word-display');
    const writePhraseDisp  = document.getElementById('write-phrase-display');

    let lastLogLength = 0;

    function fmtNum(n) {
        if (n >= 1000) return (n / 1000).toFixed(1) + 'k';
        return String(n);
    }

    async function pollState() {
        try {
            const state = await eel.get_state()();
            if (!state || state.error) {
                setTimeout(pollState, 2000);
                return;
            }

            // ── Recording / transcribing status ──
            if (state.is_recording) {
                pillTitle.textContent   = 'LISTENING…';
                pillTitle.className     = 'pill-title recording';
                pillSub.textContent     = 'Recording your voice';
                statusDot.className     = 'status-dot active';
                sidebarStatus.textContent = 'Recording';
            } else if (state.is_transcribing) {
                pillTitle.textContent   = 'TRANSCRIBING…';
                pillTitle.className     = 'pill-title transcribing';
                pillSub.textContent     = 'Processing audio…';
                statusDot.className     = 'status-dot busy';
                sidebarStatus.textContent = 'Processing';
            } else {
                pillTitle.textContent   = 'AWAITING COMMAND';
                pillTitle.className     = 'pill-title';
                pillSub.textContent     = 'Hold Right Alt anywhere to dictate';
                statusDot.className     = 'status-dot ready';
                sidebarStatus.textContent = 'Ready';
            }

            // ── Stats ──
            if (state.stats) {
                statWordsToday.textContent  = fmtNum(state.stats.words_today  || 0);
                statWordsTotal.textContent  = fmtNum(state.stats.words_total  || 0);
                statSessions.textContent    = fmtNum(state.stats.sessions_total || 0);
            }

            // ── Config ──
            if (state.config) {
                const cfg = state.config;

                // API badge
                if (cfg.gemini_api_key_set) {
                    apiBadge.textContent = '✓ API Key Set';
                    apiBadge.className   = 'api-badge ok';
                } else {
                    apiBadge.textContent = '⚠ No API Key';
                    apiBadge.className   = 'api-badge';
                }

                // Gemini model chip + selector
                geminiChip.textContent = cfg.gemini_model || 'gemini-2.0-flash';
                syncSelector('#model-selector', '[data-model]', 'data-model', cfg.gemini_model);

                // Whisper model badge + selector
                modelBadge.textContent = 'whisper / ' + (cfg.whisper_model || 'small');
                syncSelector('#whisper-selector', '[data-wmodel]', 'data-wmodel', cfg.whisper_model);

                // Wake word display
                wakeWordDisplay.textContent = '"' + (cfg.ai_wake_word || 'assistant') + '"';

                // Write prompt display
                writePhraseDisp.textContent = '"' + (cfg.write_prompt_phrase || 'write a prompt') + ', ..."';

                // Settings fields (only update if not focused)
                setFieldIfNotFocused('wake-word-input', cfg.ai_wake_word || 'assistant');
                setFieldIfNotFocused('wp-phrase-input', cfg.write_prompt_phrase || 'write a prompt');

                // Mic selection sync (once mics are loaded)
                if (micLoaded && cfg.selected_mic && micSelect) {
                    // Only update if not actively being changed
                    if (document.activeElement !== micSelect) {
                        micSelect.value = cfg.selected_mic;
                    }
                }

                // Auto-punctuate toggle
                const apt = document.getElementById('auto-punct-toggle');
                const aptTxt = document.getElementById('auto-punct-text');
                if (apt) {
                    apt.checked = !!cfg.auto_punctuate;
                    aptTxt.textContent = cfg.auto_punctuate
                        ? 'On — first letter capitalised, period added if missing'
                        : 'Off — text pasted exactly as spoken';
                }

                // Macros
                statMacros.textContent = Object.keys(cfg.voice_macros || {}).length;
                renderMacroList(cfg.voice_macros || {});
            }

            // ── Dictation log ──
            if (state.log && state.log.length !== lastLogLength) {
                lastLogLength = state.log.length;
                renderLog(state.log);
            }

        } catch (e) {
            // eel might not be ready yet — retry silently
        }
        setTimeout(pollState, 800);
    }

    function setFieldIfNotFocused(id, value) {
        const el = document.getElementById(id);
        if (el && document.activeElement !== el) el.value = value;
    }

    function syncSelector(containerSel, itemSel, attr, currentVal) {
        const container = document.querySelector(containerSel);
        if (!container) return;
        container.querySelectorAll(itemSel).forEach(opt => {
            opt.classList.toggle('active', opt.getAttribute(attr) === currentVal);
        });
    }

    function renderLog(log) {
        const list = document.getElementById('intercept-list');
        const full = document.getElementById('full-log');

        // Dashboard: last 5
        const recent = log.slice(-5).reverse();
        list.innerHTML = recent.length
            ? recent.map((e, i) => `
                <div class="intercept-item">
                    <div class="item-left">
                        <div class="dot ${i === 0 ? 'active' : 'inactive'}"></div>
                        <span>${esc(e.text.length > 60 ? e.text.substring(0,60) + '…' : e.text)}</span>
                    </div>
                    <div class="item-right">${esc(e.time)}</div>
                </div>`).join('')
            : '<div class="empty-state">No dictations yet</div>';

        // History page: all (most recent first)
        const allReversed = log.slice().reverse();
        full.innerHTML = allReversed.length
            ? allReversed.map(e => `
                <div class="intercept-item">
                    <div class="item-left">
                        <div class="dot active"></div>
                        <span>${esc(e.text.length > 120 ? e.text.substring(0,120) + '…' : e.text)}</span>
                    </div>
                    <div class="item-right">${esc(e.time)}</div>
                </div>`).join('')
            : '<div class="empty-state">No dictations yet</div>';
    }

    function renderMacroList(macros) {
        const list = document.getElementById('macro-list');
        const entries = Object.entries(macros);
        list.innerHTML = entries.length
            ? entries.map(([t, e]) => `
                <div class="macro-item">
                    <span class="macro-trigger">🎙 "${esc(t)}"</span>
                    <span class="macro-arrow">→</span>
                    <span class="macro-exp">${esc(e)}</span>
                    <span class="macro-del" data-trigger="${esc(t)}" title="Delete">✕</span>
                </div>`).join('')
            : '<div class="empty-state">No macros yet</div>';

        list.querySelectorAll('.macro-del').forEach(btn => {
            btn.addEventListener('click', async () => {
                const trig = btn.dataset.trigger;
                await eel.delete_voice_macro(trig)();
            });
        });
    }

    function esc(s) {
        return String(s)
            .replace(/&/g,'&amp;').replace(/</g,'&lt;')
            .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    // ── Gemini model selector ─────────────────────────────────────────────────
    document.querySelectorAll('#model-selector .sel-option').forEach(opt => {
        opt.addEventListener('click', async () => {
            const model = opt.dataset.model;
            await eel.update_setting('gemini_model', model)();
        });
    });

    // ── Whisper model selector ────────────────────────────────────────────────
    document.querySelectorAll('#whisper-selector .sel-option').forEach(opt => {
        opt.addEventListener('click', async () => {
            const model = opt.dataset.wmodel;
            await eel.update_setting('whisper_model', model)();
        });
    });

    // ── Microphone selector ───────────────────────────────────────────────────
    const micSelect = document.getElementById('mic-select');
    let micLoaded = false;

    async function loadMics() {
        try {
            const mics = await eel.get_mics()();
            if (!mics || !mics.length) return;
            micSelect.innerHTML = mics.map(m =>
                `<option value="${esc(m)}">${esc(m)}</option>`
            ).join('');
            micLoaded = true;
        } catch (e) {}
    }
    loadMics();

    document.getElementById('save-mic-btn').addEventListener('click', async () => {
        const name = micSelect.value;
        if (!name) return;
        const r = await eel.set_mic(name)();
        if (r && r.ok) {
            feedback('mic-feedback', '✅ Microphone set', true);
        } else {
            feedback('mic-feedback', r ? '❌ ' + r.error : '❌ Error', false);
        }
    });

    // ── Save API key ──────────────────────────────────────────────────────────
    document.getElementById('save-key-btn').addEventListener('click', async () => {
        const val = document.getElementById('api-key-input').value.trim();
        if (!val) return feedback('key-feedback', 'Please enter a key', false);
        const r = await eel.update_setting('gemini_api_key', val)();
        if (r && r.ok) {
            feedback('key-feedback', '✅ Saved', true);
            document.getElementById('api-key-input').value = '';
        } else {
            feedback('key-feedback', '❌ Error saving', false);
        }
    });

    // ── Save wake word ────────────────────────────────────────────────────────
    document.getElementById('save-ww-btn').addEventListener('click', async () => {
        const val = document.getElementById('wake-word-input').value.trim();
        if (!val) return;
        await eel.update_setting('ai_wake_word', val)();
        feedback('ww-feedback', '✅ Saved', true);
    });

    // ── Save write-prompt phrase ──────────────────────────────────────────────
    document.getElementById('save-wp-btn').addEventListener('click', async () => {
        const val = document.getElementById('wp-phrase-input').value.trim();
        if (!val) return;
        await eel.update_setting('write_prompt_phrase', val)();
        feedback('wp-feedback', '✅ Saved', true);
    });

    // ── Auto-punctuate toggle ─────────────────────────────────────────────────
    document.getElementById('auto-punct-toggle').addEventListener('change', async (e) => {
        await eel.update_setting('auto_punctuate', e.target.checked)();
    });

    // ── Add macro ─────────────────────────────────────────────────────────────
    document.getElementById('add-macro-btn').addEventListener('click', async () => {
        const trig = document.getElementById('mac-trigger').value.trim();
        const exp  = document.getElementById('mac-expansion').value.trim();
        if (!trig || !exp) return feedback('macro-feedback', 'Both fields required', false);
        const r = await eel.add_voice_macro(trig, exp)();
        if (r && r.ok) {
            feedback('macro-feedback', '✅ Macro added', true);
            document.getElementById('mac-trigger').value    = '';
            document.getElementById('mac-expansion').value = '';
        } else {
            feedback('macro-feedback', r ? r.error : 'Error', false);
        }
    });

    // Enter key on macro fields
    document.getElementById('mac-trigger').addEventListener('keydown', e => {
        if (e.key === 'Enter') document.getElementById('mac-expansion').focus();
    });
    document.getElementById('mac-expansion').addEventListener('keydown', e => {
        if (e.key === 'Enter') document.getElementById('add-macro-btn').click();
    });

    // ── Feedback helper ───────────────────────────────────────────────────────
    function feedback(id, msg, ok) {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent  = msg;
        el.className    = 'save-feedback ' + (ok ? 'ok' : 'err');
        el.style.opacity = '1';
        setTimeout(() => { el.style.opacity = '0'; }, 2500);
    }

    // ── Start polling ─────────────────────────────────────────────────────────
    pollState();
});
