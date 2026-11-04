/**
 * EPS (Exam Proctoring System) — Minimalist Landing Page Interactions
 * Handles:
 * 1. Mobile navigation menu drawer toggle
 * 2. Smooth anchor scrolling with sticky header offset
 * 3. Hero interface mockup live simulation (timer countdown, candidate streaming indicator)
 * 4. Theme synchronization
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Mobile Menu Drawer Toggle
    const mobileToggleBtn = document.getElementById('lp-mobile-menu-toggle');
    const mobileDrawer = document.getElementById('lp-mobile-drawer');

    if (mobileToggleBtn && mobileDrawer) {
        mobileToggleBtn.addEventListener('click', () => {
            const isOpen = mobileDrawer.classList.toggle('is-open');
            mobileToggleBtn.setAttribute('aria-expanded', isOpen);
            const icon = mobileToggleBtn.querySelector('i');
            if (icon && window.lucide) {
                if (isOpen) {
                    mobileToggleBtn.innerHTML = '<i data-lucide="x" class="lucide-icon icon-sm"></i>';
                } else {
                    mobileToggleBtn.innerHTML = '<i data-lucide="menu" class="lucide-icon icon-sm"></i>';
                }
                window.lucide.createIcons();
            }
        });

        // Close drawer when clicking any link
        mobileDrawer.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                mobileDrawer.classList.remove('is-open');
                mobileToggleBtn.setAttribute('aria-expanded', 'false');
                mobileToggleBtn.innerHTML = '<i data-lucide="menu" class="lucide-icon icon-sm"></i>';
                if (window.lucide) window.lucide.createIcons();
            });
        });
    }

    // 2. Realistic Countdown Timer in Hero / Exam Interface Mockup
    const timerEls = document.querySelectorAll('.lp-mockup-timer');
    if (timerEls.length > 0) {
        let totalSeconds = 6138; // 01:42:18
        setInterval(() => {
            if (totalSeconds > 0) {
                totalSeconds--;
                const h = String(Math.floor(totalSeconds / 3600)).padStart(2, '0');
                const m = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, '0');
                const s = String(totalSeconds % 60).padStart(2, '0');
                timerEls.forEach(el => {
                    el.textContent = `${h}:${m}:${s}`;
                });
            }
        }, 1000);
    }

    // 3. Smooth Anchor Scrolling Offset Handling
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            const targetEl = document.querySelector(targetId);
            if (targetEl) {
                e.preventDefault();
                const navHeight = 64;
                const elementPosition = targetEl.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - navHeight;

                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });

    // 4. Ensure Lucide Icons Render
    if (window.lucide) {
        window.lucide.createIcons();
    }
});
