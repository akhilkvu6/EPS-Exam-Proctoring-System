/**
 * EPS Design Foundation (EDF) — Interactive Component Engine & Live Playground
 * Powers:
 * 1. Interactive component states (Modals, Toasts, Dropdowns, Tabs, Form validation)
 * 2. Real-time Live Design Playground & Token Customization Engine (Workbench + Drawer)
 * 3. Export to CSS / JSON with one-click clipboard copying
 * 4. Light/Dark theme switching & default reset
 */

(function () {
    'use strict';

    // Global EPSDesign Namespace
    window.EPSDesign = {
        toast: showToast,
        openModal: openModal,
        closeModal: closeModal,
        resetPlayground: resetPlayground,
        openDrawer: openPlaygroundDrawer,
        closeDrawer: closePlaygroundDrawer,
        exportTokensCSS: exportTokensCSS,
        exportTokensJSON: exportTokensJSON
    };

    document.addEventListener('DOMContentLoaded', function () {
        initLucideIcons();
        initDropdowns();
        initTabs();
        initModals();
        initPlayground();
        initTableSorting();
        initFormValidationDemo();
        initButtonInteractiveDemo();
    });

    /* ==========================================================================
       1. LUCIDE ICON REFRESH HELPER
       ========================================================================== */
    function initLucideIcons() {
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
            window.lucide.createIcons();
        }
    }

    /* ==========================================================================
       2. DROPDOWN COMPONENT CONTROLLER
       ========================================================================== */
    function initDropdowns() {
        document.addEventListener('click', function (e) {
            const toggle = e.target.closest('[data-dropdown-toggle]');
            const allDropdowns = document.querySelectorAll('.dropdown-menu');

            if (toggle) {
                e.preventDefault();
                e.stopPropagation();
                const parent = toggle.closest('.dropdown');
                const menu = parent ? parent.querySelector('.dropdown-menu') : null;

                allDropdowns.forEach(m => {
                    if (m !== menu) m.classList.remove('is-active');
                });

                if (menu) {
                    menu.classList.toggle('is-active');
                }
            } else {
                if (!e.target.closest('.dropdown-menu')) {
                    allDropdowns.forEach(m => m.classList.remove('is-active'));
                }
            }
        });
    }

    /* ==========================================================================
       3. TABS CONTROLLER
       ========================================================================== */
    function initTabs() {
        document.querySelectorAll('.tabs-nav').forEach(nav => {
            nav.addEventListener('click', function (e) {
                const link = e.target.closest('.tab-link');
                if (!link) return;
                e.preventDefault();

                const targetId = link.getAttribute('data-tab-target');
                if (!targetId) return;

                nav.querySelectorAll('.tab-link').forEach(l => l.classList.remove('is-active'));
                link.classList.add('is-active');

                const container = nav.closest('[data-tabs-container]') || document;
                const panes = container.querySelectorAll('.tab-content');
                panes.forEach(pane => {
                    if (pane.id === targetId) {
                        pane.classList.add('is-active');
                    } else if (pane.getAttribute('data-tab-group') === link.getAttribute('data-tab-group')) {
                        pane.classList.remove('is-active');
                    }
                });

                initLucideIcons();
            });
        });
    }

    /* ==========================================================================
       4. MODAL & CONFIRMATION CONTROLLER
       ========================================================================== */
    function initModals() {
        document.addEventListener('click', function (e) {
            const trigger = e.target.closest('[data-modal-target]');
            if (trigger) {
                e.preventDefault();
                const modalId = trigger.getAttribute('data-modal-target');
                openModal(modalId);
            }

            const closeBtn = e.target.closest('[data-modal-close]');
            if (closeBtn) {
                e.preventDefault();
                const modal = closeBtn.closest('.modal-backdrop');
                if (modal) closeModal(modal.id);
            }

            if (e.target.classList.contains('modal-backdrop')) {
                closeModal(e.target.id);
            }
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                const activeModal = document.querySelector('.modal-backdrop.is-active');
                if (activeModal) closeModal(activeModal.id);

                const drawer = document.getElementById('edf-playground-drawer');
                if (drawer && drawer.classList.contains('is-active')) {
                    closePlaygroundDrawer();
                }
            }
        });
    }

    function openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('is-active');
            document.body.style.overflow = 'hidden';
            initLucideIcons();
        }
    }

    function closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('is-active');
            document.body.style.overflow = '';
        }
    }

    /* ==========================================================================
       5. TOAST NOTIFICATION DISPATCHER
       ========================================================================== */
    function showToast(options) {
        let container = document.getElementById('edf-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'edf-toast-container';
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        const type = options.type || 'info';
        const title = options.title || (type.charAt(0).toUpperCase() + type.slice(1));
        const message = options.message || '';
        const duration = options.duration || 4000;

        let iconName = 'info';
        if (type === 'success') iconName = 'check-circle';
        if (type === 'danger') iconName = 'alert-octagon';
        if (type === 'warning') iconName = 'alert-triangle';

        const toastEl = document.createElement('div');
        toastEl.className = `toast toast--${type}`;
        toastEl.innerHTML = `
            <div class="toast-icon">
                <i data-lucide="${iconName}" class="lucide-icon icon-sm"></i>
            </div>
            <div class="toast-content">
                <div class="toast-title">${escapeHTML(title)}</div>
                <div class="toast-msg">${escapeHTML(message)}</div>
            </div>
            <button type="button" class="toast-close" aria-label="Dismiss toast">
                <i data-lucide="x" class="lucide-icon icon-xs"></i>
            </button>
        `;

        container.appendChild(toastEl);
        initLucideIcons();

        const closeBtn = toastEl.querySelector('.toast-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => removeToast(toastEl));
        }

        const timer = setTimeout(() => {
            removeToast(toastEl);
        }, duration);

        function removeToast(el) {
            clearTimeout(timer);
            el.style.opacity = '0';
            el.style.transform = 'translateX(20px)';
            setTimeout(() => {
                if (el.parentNode) el.parentNode.removeChild(el);
            }, 180);
        }
    }

    function escapeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    /* ==========================================================================
       6. TABLE SORTING INTERACTION DEMO
       ========================================================================== */
    function initTableSorting() {
        document.querySelectorAll('.th-sortable').forEach(th => {
            th.addEventListener('click', function () {
                const currentOrder = this.getAttribute('data-sort-order') || 'none';
                const nextOrder = (currentOrder === 'asc') ? 'desc' : 'asc';
                
                this.closest('tr').querySelectorAll('.th-sortable').forEach(header => {
                    header.removeAttribute('data-sort-order');
                    const icon = header.querySelector('.sort-indicator');
                    if (icon) icon.innerHTML = '<i data-lucide="chevrons-up-down" class="lucide-icon icon-xs"></i>';
                });

                this.setAttribute('data-sort-order', nextOrder);
                const icon = this.querySelector('.sort-indicator');
                if (icon) {
                    icon.innerHTML = (nextOrder === 'asc') ? 
                        '<i data-lucide="chevron-up" class="lucide-icon icon-xs" style="color:var(--color-primary);"></i>' : 
                        '<i data-lucide="chevron-down" class="lucide-icon icon-xs" style="color:var(--color-primary);"></i>';
                }
                initLucideIcons();
            });
        });
    }

    /* ==========================================================================
       7. FORM VALIDATION INTERACTIVE DEMO
       ========================================================================== */
    function initFormValidationDemo() {
        const trigger = document.getElementById('demo-toggle-validation-btn');
        if (trigger) {
            let isValid = false;
            trigger.addEventListener('click', function () {
                isValid = !isValid;
                const demoInput = document.getElementById('demo-validation-input');
                const feedbackMsg = document.getElementById('demo-validation-feedback');

                if (demoInput && feedbackMsg) {
                    if (isValid) {
                        demoInput.classList.remove('is-invalid');
                        demoInput.classList.add('is-valid');
                        feedbackMsg.className = 'form-success-msg';
                        feedbackMsg.innerHTML = '<i data-lucide="check" class="lucide-icon icon-xs"></i> Examination candidate code verified.';
                    } else {
                        demoInput.classList.remove('is-valid');
                        demoInput.classList.add('is-invalid');
                        feedbackMsg.className = 'form-error-msg';
                        feedbackMsg.innerHTML = '<i data-lucide="alert-circle" class="lucide-icon icon-xs"></i> Invalid registration format (e.g. EPS-2026-X).';
                    }
                    initLucideIcons();
                }
            });
        }
    }

    /* ==========================================================================
       7B. BUTTON INTERACTIVE STATES DEMO (Loading & Disabled Toggles)
       ========================================================================== */
    function initButtonInteractiveDemo() {
        const toggleLoadingBtn = document.getElementById('demo-toggle-btn-loading');
        if (toggleLoadingBtn) {
            let isLoading = false;
            toggleLoadingBtn.addEventListener('click', function () {
                isLoading = !isLoading;
                document.querySelectorAll('.demo-interactive-btn').forEach(btn => {
                    if (isLoading) {
                        btn.classList.add('is-loading');
                    } else {
                        btn.classList.remove('is-loading');
                    }
                });
                toggleLoadingBtn.innerHTML = isLoading ? 
                    '<i data-lucide="stop-circle" class="lucide-icon icon-xs"></i> <span>Stop Loading Spinners</span>' : 
                    '<i data-lucide="loader" class="lucide-icon icon-xs"></i> <span>Test Loading Spinners</span>';
                initLucideIcons();
            });
        }

        const toggleDisabledBtn = document.getElementById('demo-toggle-btn-disabled');
        if (toggleDisabledBtn) {
            let isDisabled = false;
            toggleDisabledBtn.addEventListener('click', function () {
                isDisabled = !isDisabled;
                document.querySelectorAll('.demo-interactive-btn').forEach(btn => {
                    btn.disabled = isDisabled;
                });
                toggleDisabledBtn.innerHTML = isDisabled ? 
                    '<i data-lucide="unlock" class="lucide-icon icon-xs"></i> <span>Enable Buttons</span>' : 
                    '<i data-lucide="lock" class="lucide-icon icon-xs"></i> <span>Test Disabled State</span>';
                initLucideIcons();
            });
        }
    }

    /* ==========================================================================
       8. LIVE DESIGN PLAYGROUND ENGINE (WORKBENCH + DRAWER)
       ========================================================================== */
    const PLAYGROUND_TOKENS = [
        // Palette & Surfaces
        { key: '--color-primary', type: 'color', default: '#2563EB', label: 'Primary Blue (Main Action)', group: 'palette' },
        { key: '--color-secondary', type: 'color', default: '#57534E', label: 'Secondary Grey', group: 'palette' },
        { key: '--bg-app', type: 'color', default: '#FAFAF8', label: 'Canvas Background', group: 'palette' },
        { key: '--bg-surface', type: 'color', default: '#FFFFFF', label: 'Card Surface', group: 'palette' },
        { key: '--text-primary', type: 'color', default: '#1C1917', label: 'Text Primary', group: 'palette' },

        // Typography & Layout Dimensions
        { key: '--font-family', type: 'select', default: "'Inter', sans-serif", label: 'Font Family', group: 'typography' },
        { key: '--font-size-base', type: 'slider', unit: 'px', min: 12, max: 18, default: 14, label: 'Base Font Size', group: 'typography' },
        { key: '--sidebar-width', type: 'slider', unit: 'px', min: 200, max: 320, default: 240, label: 'Sidebar Width', group: 'typography' },
        { key: '--header-height', type: 'slider', unit: 'px', min: 48, max: 80, default: 64, label: 'Header Height', group: 'typography' },

        // Geometry & Motion
        { key: '--radius-control', type: 'slider', unit: 'px', min: 0, max: 20, default: 8, label: 'Control Radius', group: 'geometry' },
        { key: '--radius-card', type: 'slider', unit: 'px', min: 0, max: 28, default: 16, label: 'Card Radius', group: 'geometry' },
        { key: '--anim-duration', type: 'slider', unit: 'ms', min: 0, max: 600, default: 200, label: 'Animation Speed', group: 'geometry' }
    ];

    const customizedValues = {};

    function initPlayground() {
        // Render in-page workbench groups if present
        const paletteContainer = document.getElementById('workbench-controls-palette');
        const typographyContainer = document.getElementById('workbench-controls-typography');
        const geometryContainer = document.getElementById('workbench-controls-geometry');

        if (paletteContainer) {
            renderTokenList(paletteContainer, PLAYGROUND_TOKENS.filter(t => t.group === 'palette'), 'wb');
        }
        if (typographyContainer) {
            renderTokenList(typographyContainer, PLAYGROUND_TOKENS.filter(t => t.group === 'typography'), 'wb');
        }
        if (geometryContainer) {
            renderTokenList(geometryContainer, PLAYGROUND_TOKENS.filter(t => t.group === 'geometry'), 'wb');
        }

        // Render slide-out drawer controls if present
        const drawerContainer = document.getElementById('drawer-playground-controls');
        if (drawerContainer) {
            renderTokenList(drawerContainer, PLAYGROUND_TOKENS, 'dr');
        }

        // Fallback container if present
        const fallbackContainer = document.getElementById('edf-playground-controls');
        if (fallbackContainer && !paletteContainer) {
            renderTokenList(fallbackContainer, PLAYGROUND_TOKENS, 'fb');
        }

        // Bind Theme Switchers
        const themeButtons = document.querySelectorAll('#playground-theme-toggle, #workbench-theme-toggle, #drawer-theme-toggle');
        themeButtons.forEach(btn => {
            btn.addEventListener('click', toggleTheme);
        });

        // Bind Reset Buttons
        const resetButtons = document.querySelectorAll('#playground-reset-btn, #workbench-reset-btn, #drawer-reset-btn');
        resetButtons.forEach(btn => {
            btn.addEventListener('click', resetPlayground);
        });

        // Bind Export Buttons
        const exportCSSButtons = document.querySelectorAll('#playground-export-css-btn, #workbench-export-css-btn, #drawer-export-css-btn');
        exportCSSButtons.forEach(btn => {
            btn.addEventListener('click', exportTokensCSS);
        });

        const exportJSONButtons = document.querySelectorAll('#playground-export-json-btn, #workbench-export-json-btn, #drawer-export-json-btn');
        exportJSONButtons.forEach(btn => {
            btn.addEventListener('click', exportTokensJSON);
        });

        // Bind Drawer Controls
        const drawerToggle = document.getElementById('edf-drawer-toggle');
        if (drawerToggle) {
            drawerToggle.addEventListener('click', openPlaygroundDrawer);
        }

        const openDrawerBtn = document.getElementById('btn-open-drawer');
        if (openDrawerBtn) {
            openDrawerBtn.addEventListener('click', openPlaygroundDrawer);
        }

        const drawerClose = document.getElementById('edf-drawer-close');
        if (drawerClose) {
            drawerClose.addEventListener('click', closePlaygroundDrawer);
        }

        const drawerBackdrop = document.getElementById('edf-drawer-backdrop');
        if (drawerBackdrop) {
            drawerBackdrop.addEventListener('click', closePlaygroundDrawer);
        }
    }

    function openPlaygroundDrawer() {
        const drawer = document.getElementById('edf-playground-drawer');
        const backdrop = document.getElementById('edf-drawer-backdrop');
        if (drawer) drawer.classList.add('is-active');
        if (backdrop) backdrop.classList.add('is-active');
        initLucideIcons();
    }

    function closePlaygroundDrawer() {
        const drawer = document.getElementById('edf-playground-drawer');
        const backdrop = document.getElementById('edf-drawer-backdrop');
        if (drawer) drawer.classList.remove('is-active');
        if (backdrop) backdrop.classList.remove('is-active');
    }

    function toggleTheme() {
        const current = document.documentElement.getAttribute('data-theme') || 'light';
        const next = (current === 'dark') ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('eps-theme', next);

        // Update button labels/icons
        const themeButtons = document.querySelectorAll('#playground-theme-toggle, #workbench-theme-toggle, #drawer-theme-toggle');
        themeButtons.forEach(btn => {
            btn.innerHTML = (next === 'dark') ? 
                '<i data-lucide="sun" class="lucide-icon icon-xs"></i> <span>Light Mode</span>' : 
                '<i data-lucide="moon" class="lucide-icon icon-xs"></i> <span>Dark Mode</span>';
        });

        initLucideIcons();
        showToast({
            type: 'info',
            title: 'Theme Toggled',
            message: `Switched active preview to ${next.toUpperCase()} theme.`
        });
    }

    function renderTokenList(container, tokens, prefix) {
        container.innerHTML = '';

        tokens.forEach(token => {
            const row = document.createElement('div');
            row.className = 'token-row';
            row.setAttribute('data-token-row', token.key);

            let controlHTML = '';

            if (token.type === 'color') {
                controlHTML = `
                    <div class="token-control">
                        <input type="color" class="token-color-picker" data-token="${token.key}" data-role="picker" value="${token.default}" aria-label="${token.label} color picker">
                        <input type="text" class="token-text-input" data-token="${token.key}" data-role="text" value="${token.default}" maxlength="7" spellcheck="false" aria-label="${token.label} hex code">
                    </div>
                `;
            } else if (token.type === 'slider') {
                controlHTML = `
                    <div class="token-control">
                        <input type="range" class="token-slider" data-token="${token.key}" data-role="slider" data-unit="${token.unit}" min="${token.min}" max="${token.max}" value="${token.default}">
                        <span class="text-mono token-val-display" data-token="${token.key}" style="font-size:11px; min-width:44px; text-align:right;">${token.default}${token.unit}</span>
                    </div>
                `;
            } else if (token.type === 'select') {
                controlHTML = `
                    <div class="token-control">
                        <select class="form-select" data-token="${token.key}" data-role="select" style="min-height:28px; padding:2px 20px 2px 6px; font-size:11px;">
                            <option value="'Inter', sans-serif">Inter (Default)</option>
                            <option value="system-ui, -apple-system, sans-serif">System UI</option>
                            <option value="'JetBrains Mono', monospace">JetBrains Mono</option>
                            <option value="Georgia, serif">Georgia Serif</option>
                        </select>
                    </div>
                `;
            }

            row.innerHTML = `
                <div class="token-meta">
                    <div style="display:flex; align-items:center; gap:6px;">
                        <span class="token-name">${token.key}</span>
                        <span class="badge-modified">Modified</span>
                    </div>
                    <span class="token-desc">${token.label}</span>
                </div>
                ${controlHTML}
            `;

            container.appendChild(row);

            // Bind Event Listeners
            if (token.type === 'color') {
                const picker = row.querySelector('[data-role="picker"]');
                const text = row.querySelector('[data-role="text"]');

                picker.addEventListener('input', function () {
                    syncAndApplyToken(token.key, picker.value.toUpperCase());
                });

                text.addEventListener('input', function () {
                    if (/^#[0-9A-F]{6}$/i.test(text.value)) {
                        syncAndApplyToken(token.key, text.value.toUpperCase());
                    }
                });
            } else if (token.type === 'slider') {
                const slider = row.querySelector('[data-role="slider"]');
                slider.addEventListener('input', function () {
                    const formatted = `${slider.value}${token.unit}`;
                    syncAndApplyToken(token.key, formatted, slider.value);
                });
            } else if (token.type === 'select') {
                const select = row.querySelector('[data-role="select"]');
                select.addEventListener('change', function () {
                    syncAndApplyToken(token.key, select.value);
                });
            }
        });
    }

    function syncAndApplyToken(key, value, numericPart) {
        document.documentElement.style.setProperty(key, value);
        customizedValues[key] = value;

        // Specific sub-tokens propagation
        if (key === '--color-primary') {
            document.documentElement.style.setProperty('--border-focus', value);
        }
        if (key === '--bg-surface') {
            document.documentElement.style.setProperty('--header-bg', value);
        }

        // Synchronize all matching inputs across page & drawer
        document.querySelectorAll(`[data-token="${key}"]`).forEach(el => {
            const role = el.getAttribute('data-role');
            if (role === 'picker' || role === 'text') {
                el.value = value;
            } else if (role === 'slider') {
                if (numericPart !== undefined) el.value = numericPart;
                else el.value = parseInt(value, 10);
            } else if (role === 'select') {
                el.value = value;
            } else if (el.classList.contains('token-val-display')) {
                el.textContent = value;
            }
        });

        // Mark matching rows as modified
        document.querySelectorAll(`[data-token-row="${key}"]`).forEach(row => {
            row.classList.add('is-modified');
        });

        updateModifiedBadge();
    }

    function updateModifiedBadge() {
        const count = Object.keys(customizedValues).length;
        const text = `${count} token${count === 1 ? '' : 's'} customized`;
        document.querySelectorAll('.workbench-modified-badge').forEach(b => {
            b.textContent = text;
            if (count > 0) {
                b.className = 'badge badge--warning workbench-modified-badge';
            } else {
                b.className = 'badge badge--neutral workbench-modified-badge';
            }
        });
    }

    function resetPlayground() {
        // Clear all inline overrides
        Object.keys(customizedValues).forEach(key => {
            document.documentElement.style.removeProperty(key);
            delete customizedValues[key];
        });
        document.documentElement.style.removeProperty('--border-focus');
        document.documentElement.style.removeProperty('--header-bg');

        // Reset all inputs to factory defaults
        PLAYGROUND_TOKENS.forEach(token => {
            document.querySelectorAll(`[data-token="${token.key}"]`).forEach(el => {
                const role = el.getAttribute('data-role');
                if (role === 'picker' || role === 'text') {
                    el.value = token.default;
                } else if (role === 'slider') {
                    el.value = token.default;
                } else if (role === 'select') {
                    el.value = token.default;
                } else if (el.classList.contains('token-val-display')) {
                    el.textContent = `${token.default}${token.unit || ''}`;
                }
            });

            document.querySelectorAll(`[data-token-row="${token.key}"]`).forEach(row => {
                row.classList.remove('is-modified');
            });
        });

        updateModifiedBadge();

        showToast({
            type: 'success',
            title: 'Tokens Reset',
            message: 'All live playground overrides cleared. Restored factory design tokens.'
        });
    }

    /* ==========================================================================
       9. EXPORT MODAL IMPLEMENTATIONS (CSS & JSON)
       ========================================================================== */
    function exportTokensCSS() {
        const count = Object.keys(customizedValues).length;
        let cssBody = '';
        if (count === 0) {
            cssBody = '/* No custom overrides applied. All tokens currently match default design-tokens.css */\n';
        } else {
            cssBody = '/* EPS Custom Tokens Generated from EDF Playground */\n:root {\n';
            for (const [k, v] of Object.entries(customizedValues)) {
                cssBody += `  ${k}: ${v};\n`;
            }
            cssBody += '}\n';
        }

        showExportDialog('Export Design Tokens (CSS)', cssBody, 'css');
    }

    function exportTokensJSON() {
        const count = Object.keys(customizedValues).length;
        let jsonStr = '';
        if (count === 0) {
            jsonStr = JSON.stringify({ message: 'No custom overrides applied. All default tokens in effect.' }, null, 2);
        } else {
            jsonStr = JSON.stringify({ epsDesignTokens: customizedValues }, null, 2);
        }

        showExportDialog('Export Design Tokens (JSON)', jsonStr, 'json');
    }

    function showExportDialog(title, content, mode) {
        let modal = document.getElementById('edf-export-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'edf-export-modal';
            modal.className = 'modal-backdrop';
            modal.innerHTML = `
                <div class="modal-dialog">
                    <div class="modal-header">
                        <h3 class="modal-title" id="edf-export-modal-title">Export Tokens</h3>
                        <button type="button" class="btn btn-ghost btn-xs" data-modal-close aria-label="Close modal">
                            <i data-lucide="x" class="lucide-icon icon-sm"></i>
                        </button>
                    </div>
                    <div class="modal-body">
                        <p class="text-caption" style="margin-bottom:var(--space-3);">
                            Copy the generated configuration to persist approved changes into <code class="text-mono">static/css/design-tokens.css</code>.
                        </p>
                        <textarea id="edf-export-textarea" class="form-textarea text-mono" style="min-height:200px; font-size:12px; line-height:1.45;" readonly></textarea>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary btn-sm" data-modal-close>Close</button>
                        <button type="button" class="btn btn-primary btn-sm" id="edf-copy-export-btn">
                            <i data-lucide="copy" class="lucide-icon icon-xs"></i>
                            <span>Copy to Clipboard</span>
                        </button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        const titleEl = modal.querySelector('#edf-export-modal-title');
        const textarea = modal.querySelector('#edf-export-textarea');
        const copyBtn = modal.querySelector('#edf-copy-export-btn');

        if (titleEl) titleEl.textContent = title;
        if (textarea) textarea.value = content;

        copyBtn.onclick = function () {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(content).then(() => {
                    showToast({
                        type: 'success',
                        title: 'Copied',
                        message: 'Token configuration copied to clipboard.'
                    });
                }).catch(() => fallbackCopy(textarea));
            } else {
                fallbackCopy(textarea);
            }
        };

        function fallbackCopy(inputEl) {
            inputEl.select();
            document.execCommand('copy');
            showToast({
                type: 'success',
                title: 'Copied',
                message: 'Token configuration copied via fallback.'
            });
        }

        openModal('edf-export-modal');
    }

})();
