/**
 * EPS School Management Platform — Main Script
 * Manages:
 * 1. Warm Off-White Sidebar collapse (expanded 240px <-> collapsed 72px) & mobile drawer
 * 2. Theme toggle (Light / Dark)
 * 3. School Calendar widget with month navigation, date selection, and event rendering
 * 4. Alert auto-dismissals & notifications
 * 5. Form password visibility toggles
 * 6. Lucide icons initialization
 */

// 1. Prevent Theme Flash
(function () {
    const savedTheme = localStorage.getItem('eps-theme') || 
        (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', savedTheme);
})();

document.addEventListener('DOMContentLoaded', function () {
    // 2. Initialize Lucide Icons
    function refreshIcons() {
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
            window.lucide.createIcons();
        }
    }
    refreshIcons();

    // 3. Theme Toggle Controller
    const themeToggleBtns = document.querySelectorAll('.theme-toggle-btn');
    themeToggleBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
            const nextTheme = (currentTheme === 'dark') ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', nextTheme);
            localStorage.setItem('eps-theme', nextTheme);
            refreshIcons();
        });
    });

    // 4. Desktop Collapsible Sidebar
    const sidebar = document.getElementById('app-sidebar');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
    const sidebarOverlay = document.getElementById('sidebar-overlay');

    if (sidebar && sidebarToggle) {
        // Restore saved preference on desktop
        const isCollapsed = localStorage.getItem('eps_sidebar_collapsed') === 'true';
        if (isCollapsed && window.innerWidth > 1024) {
            sidebar.classList.add('is-collapsed');
            updateToggleIcon(true);
        }

        sidebarToggle.addEventListener('click', function () {
            const collapsed = sidebar.classList.toggle('is-collapsed');
            localStorage.setItem('eps_sidebar_collapsed', collapsed);
            updateToggleIcon(collapsed);
            refreshIcons();
        });

        function updateToggleIcon(collapsed) {
            const icon = sidebarToggle.querySelector('.lucide-icon, svg');
            if (icon) {
                sidebarToggle.setAttribute('title', collapsed ? 'Expand Sidebar' : 'Collapse Sidebar');
                sidebarToggle.setAttribute('aria-label', collapsed ? 'Expand Sidebar' : 'Collapse Sidebar');
                sidebarToggle.innerHTML = collapsed ? 
                    '<i data-lucide="chevrons-right" class="lucide-icon"></i>' : 
                    '<i data-lucide="chevrons-left" class="lucide-icon"></i>';
                refreshIcons();
            }
        }
    }

    // 5. Mobile Navigation Drawer
    if (sidebar && mobileMenuToggle) {
        mobileMenuToggle.addEventListener('click', function () {
            sidebar.classList.toggle('is-mobile-open');
            if (sidebarOverlay) {
                sidebarOverlay.style.display = sidebar.classList.contains('is-mobile-open') ? 'block' : 'none';
            }
            refreshIcons();
        });

        if (sidebarOverlay) {
            sidebarOverlay.addEventListener('click', function () {
                sidebar.classList.remove('is-mobile-open');
                sidebarOverlay.style.display = 'none';
            });
        }

        // Close on Escape key
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && sidebar.classList.contains('is-mobile-open')) {
                sidebar.classList.remove('is-mobile-open');
                if (sidebarOverlay) sidebarOverlay.style.display = 'none';
            }
        });
    }

    // 6. Interactive School Monthly Calendar
    initSchoolCalendar();

    function initSchoolCalendar() {
        const calendarContainer = document.querySelector('[data-school-calendar]');
        if (!calendarContainer) return;

        let currentDate = new Date();
        let selectedDate = new Date();

        function renderCalendar() {
            const year = currentDate.getFullYear();
            const month = currentDate.getMonth();

            const titleEl = calendarContainer.querySelector('.calendar-month-title');
            const gridEl = calendarContainer.querySelector('.calendar-days-grid');
            if (!titleEl || !gridEl) return;

            const monthNames = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ];
            titleEl.textContent = `${monthNames[month]} ${year}`;

            // Parse real events from data attribute if provided
            let eventDates = [];
            try {
                const eventsRaw = calendarContainer.getAttribute('data-event-dates');
                if (eventsRaw) eventDates = JSON.parse(eventsRaw);
            } catch (e) {
                eventDates = [];
            }

            gridEl.innerHTML = '';

            const firstDayIndex = new Date(year, month, 1).getDay(); // 0 is Sun
            // Shift so Monday is index 0
            const startOffset = (firstDayIndex === 0) ? 6 : firstDayIndex - 1;

            const daysInMonth = new Date(year, month + 1, 0).getDate();
            const daysInPrevMonth = new Date(year, month, 0).getDate();

            // Previous month's trailing days
            for (let i = startOffset; i > 0; i--) {
                const d = daysInPrevMonth - i + 1;
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'calendar-day is-other-month';
                btn.textContent = d;
                btn.disabled = true;
                gridEl.appendChild(btn);
            }

            // Current month days
            const today = new Date();
            for (let day = 1; day <= daysInMonth; day++) {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'calendar-day';
                btn.textContent = day;

                const isToday = (today.getFullYear() === year && today.getMonth() === month && today.getDate() === day);
                if (isToday) btn.classList.add('is-today');

                const isSelected = (selectedDate.getFullYear() === year && selectedDate.getMonth() === month && selectedDate.getDate() === day);
                if (isSelected) btn.classList.add('is-selected');

                // Check for event match
                const dateKey = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                if (eventDates.includes(dateKey)) {
                    btn.classList.add('has-event');
                    btn.setAttribute('title', 'Scheduled event / exam');
                }

                btn.addEventListener('click', function () {
                    calendarContainer.querySelectorAll('.calendar-day').forEach(b => b.classList.remove('is-selected'));
                    btn.classList.add('is-selected');
                    selectedDate = new Date(year, month, day);

                    // Trigger event date selection callback
                    const selectedDisplay = document.querySelector('[data-selected-date-display]');
                    if (selectedDisplay) {
                        selectedDisplay.textContent = selectedDate.toLocaleDateString('en-US', {
                            weekday: 'short',
                            month: 'short',
                            day: 'numeric'
                        });
                    }
                });

                gridEl.appendChild(btn);
            }
        }

        const prevBtn = calendarContainer.querySelector('.calendar-prev-btn');
        const nextBtn = calendarContainer.querySelector('.calendar-next-btn');

        if (prevBtn) {
            prevBtn.addEventListener('click', function () {
                currentDate.setMonth(currentDate.getMonth() - 1);
                renderCalendar();
            });
        }
        if (nextBtn) {
            nextBtn.addEventListener('click', function () {
                currentDate.setMonth(currentDate.getMonth() + 1);
                renderCalendar();
            });
        }

        renderCalendar();
    }

    // 7. Alert Auto-Dismissal
    document.querySelectorAll('.alert-close-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const alertBox = this.closest('.alert, .bento-alert');
            if (alertBox) {
                alertBox.style.opacity = '0';
                alertBox.style.transform = 'translateY(-4px)';
                alertBox.style.transition = 'all 150ms ease-out';
                setTimeout(() => alertBox.remove(), 160);
            }
        });
    });

    // 8. Password Visibility Toggle
    window.togglePasswordVisibility = function (inputId, btnEl) {
        const input = document.getElementById(inputId);
        if (!input) return;
        if (input.type === 'password') {
            input.type = 'text';
            btnEl.innerHTML = '<i data-lucide="eye-off" class="lucide-icon"></i>';
        } else {
            input.type = 'password';
            btnEl.innerHTML = '<i data-lucide="eye" class="lucide-icon"></i>';
        }
        refreshIcons();
    };
});
