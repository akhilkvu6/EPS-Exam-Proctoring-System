/**
 * EPS (Exam Proctoring System) — Main Interactive Script
 * Handles application shell controls, sidebar collapse, mobile navigation drawer,
 * alert dismissal, and password field toggles.
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Sidebar Collapse State Management (Desktop)
    const sidebar = document.getElementById('app-sidebar');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
    const sidebarOverlay = document.getElementById('sidebar-overlay');

    if (sidebar && sidebarToggle) {
        // Restore saved preference
        const isCollapsed = localStorage.getItem('eps_sidebar_collapsed') === 'true';
        if (isCollapsed && window.innerWidth > 1024) {
            sidebar.classList.add('is-collapsed');
        }

        sidebarToggle.addEventListener('click', function () {
            sidebar.classList.toggle('is-collapsed');
            localStorage.setItem('eps_sidebar_collapsed', sidebar.classList.contains('is-collapsed'));
        });
    }

    // 2. Mobile Off-Canvas Navigation Drawer
    if (sidebar && mobileMenuToggle) {
        mobileMenuToggle.addEventListener('click', function () {
            sidebar.classList.toggle('is-mobile-open');
            if (sidebarOverlay) {
                sidebarOverlay.style.display = sidebar.classList.contains('is-mobile-open') ? 'block' : 'none';
            }
        });

        if (sidebarOverlay) {
            sidebarOverlay.addEventListener('click', function () {
                sidebar.classList.remove('is-mobile-open');
                sidebarOverlay.style.display = 'none';
            });
        }
    }

    // 3. Global Alert Auto-Dismissal and Close Triggers
    const alertCloseBtns = document.querySelectorAll('.alert-close-btn');
    alertCloseBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            const alertBox = this.closest('.bento-alert, .alert');
            if (alertBox) {
                alertBox.style.opacity = '0';
                alertBox.style.transform = 'translateY(-6px)';
                alertBox.style.transition = 'all 0.2s ease-out';
                setTimeout(function () { alertBox.remove(); }, 200);
            }
        });
    });

    // 4. Password Visibility Toggle Utility
    window.togglePasswordVisibility = function (inputId, btnEl) {
        const input = document.getElementById(inputId);
        if (!input) return;
        if (input.type === 'password') {
            input.type = 'text';
            btnEl.textContent = '🙈';
            btnEl.setAttribute('aria-label', 'Hide password');
        } else {
            input.type = 'password';
            btnEl.textContent = '👁️';
            btnEl.setAttribute('aria-label', 'Show password');
        }
    };
});
