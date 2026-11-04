/**
 * EPS — Unified Authentication & Registration Interactive System
 * Features:
 * - Dynamic Role Selection (Student vs Teacher)
 * - Filtered, searchable Roll Number lookup from institutional enrollment records
 * - Real-time debounced Username availability validation
 * - Real-time debounced Email availability validation
 * - Real-time Password requirement checklist & strength meter
 * - Real-time Confirm Password match validation
 * - Show/Hide password toggle
 */

document.addEventListener('DOMContentLoaded', () => {

    // -------------------------------------------------------------
    // 1. Password Visibility Toggle
    // -------------------------------------------------------------
    document.querySelectorAll('.password-toggle-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('data-target');
            const input = document.getElementById(targetId);
            if (!input) return;

            const isPassword = input.type === 'password';
            input.type = isPassword ? 'text' : 'password';

            const icon = this.querySelector('i');
            if (icon) {
                icon.setAttribute('data-lucide', isPassword ? 'eye-off' : 'eye');
                if (window.lucide) window.lucide.createIcons();
            }
        });
    });

    // -------------------------------------------------------------
    // 2. Role Selection (Student vs Teacher)
    // -------------------------------------------------------------
    const roleCardStudent = document.getElementById('role-card-student');
    const roleCardTeacher = document.getElementById('role-card-teacher');
    const roleSelectionScreen = document.getElementById('role-selection-screen');
    const studentFormContainer = document.getElementById('student-form-container');
    const teacherFormContainer = document.getElementById('teacher-form-container');
    const activeRoleBar = document.getElementById('active-role-bar');
    const activeRoleLabel = document.getElementById('active-role-label');
    const changeRoleBtn = document.getElementById('change-role-btn');
    const roleInputHidden = document.getElementById('selected-role-input');

    function selectRole(role) {
        if (!studentFormContainer || !teacherFormContainer) return;

        if (roleInputHidden) roleInputHidden.value = role;

        if (role === 'student') {
            if (roleCardStudent) roleCardStudent.classList.add('is-selected');
            if (roleCardTeacher) roleCardTeacher.classList.remove('is-selected');
            studentFormContainer.style.display = 'block';
            teacherFormContainer.style.display = 'none';
            if (activeRoleLabel) activeRoleLabel.textContent = 'Student Account';
        } else if (role === 'teacher') {
            if (roleCardTeacher) roleCardTeacher.classList.add('is-selected');
            if (roleCardStudent) roleCardStudent.classList.remove('is-selected');
            studentFormContainer.style.display = 'none';
            teacherFormContainer.style.display = 'block';
            if (activeRoleLabel) activeRoleLabel.textContent = 'Teacher / Examiner Account';
        }

        // Show active role bar, collapse role cards if needed
        if (activeRoleBar) activeRoleBar.style.display = 'flex';
        if (roleSelectionScreen) roleSelectionScreen.style.display = 'none';

        if (window.lucide) window.lucide.createIcons();
    }

    if (roleCardStudent) {
        roleCardStudent.addEventListener('click', () => selectRole('student'));
    }
    if (roleCardTeacher) {
        roleCardTeacher.addEventListener('click', () => selectRole('teacher'));
    }
    if (changeRoleBtn) {
        changeRoleBtn.addEventListener('click', () => {
            if (roleSelectionScreen) roleSelectionScreen.style.display = 'grid';
            if (activeRoleBar) activeRoleBar.style.display = 'none';
            if (studentFormContainer) studentFormContainer.style.display = 'none';
            if (teacherFormContainer) teacherFormContainer.style.display = 'none';
        });
    }

    // Auto-select role only if explicit in URL query or if server returned form errors
    const urlParams = new URLSearchParams(window.location.search);
    const hasFormErrors = document.querySelector('.auth-alert--danger') !== null;
    const preRole = urlParams.get('role') || (hasFormErrors && roleInputHidden ? roleInputHidden.value : null);
    if (preRole === 'teacher') {
        selectRole('teacher');
    } else if (preRole === 'student') {
        selectRole('student');
    }

    // -------------------------------------------------------------
    // 3. Academic Batch & Course Synchronization
    // -------------------------------------------------------------
    const batchSelect = document.getElementById('student-batch-select');
    const courseSelect = document.getElementById('student-course-select');
    const semSelect = document.getElementById('student-semester-select');

    if (batchSelect) {
        batchSelect.addEventListener('change', function() {
            const selectedOpt = this.options[this.selectedIndex];
            if (selectedOpt && selectedOpt.value) {
                const courseId = selectedOpt.getAttribute('data-course-id');
                const sem = selectedOpt.getAttribute('data-sem');
                if (courseSelect && courseId) courseSelect.value = courseId;
                if (semSelect && sem) semSelect.value = sem;
            }
        });

        // Sync on initial load if batch pre-selected
        if (batchSelect.value && batchSelect.selectedIndex >= 0) {
            const selectedOpt = batchSelect.options[batchSelect.selectedIndex];
            if (selectedOpt) {
                const courseId = selectedOpt.getAttribute('data-course-id');
                const sem = selectedOpt.getAttribute('data-sem');
                if (courseSelect && courseId && !courseSelect.value) courseSelect.value = courseId;
                if (semSelect && sem && !semSelect.value) semSelect.value = sem;
            }
        }
    }

    // -------------------------------------------------------------
    // 4. Live Debounced Username Validation (Section 4E)
    // -------------------------------------------------------------
    function setupUsernameValidation(inputId, statusId) {
        const input = document.getElementById(inputId);
        const status = document.getElementById(statusId);
        if (!input || !status) return;

        let debounceTimer = null;

        input.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            const val = this.value.trim();

            if (!val) {
                status.innerHTML = '';
                return;
            }

            status.innerHTML = '<span class="auth-field-status is-checking"><i data-lucide="loader-2" class="lucide-icon icon-xs"></i> Checking availability...</span>';
            if (window.lucide) window.lucide.createIcons();

            debounceTimer = setTimeout(async () => {
                try {
                    const resp = await fetch(`/accounts/api/check-username/?username=${encodeURIComponent(val)}`);
                    const data = await resp.json();

                    if (data.available) {
                        status.innerHTML = `<span class="auth-field-status is-available"><i data-lucide="check" class="lucide-icon icon-xs"></i> ${data.message}</span>`;
                    } else {
                        status.innerHTML = `<span class="auth-field-status is-taken"><i data-lucide="x" class="lucide-icon icon-xs"></i> ${data.message}</span>`;
                    }
                    if (window.lucide) window.lucide.createIcons();
                } catch (err) {
                    status.innerHTML = '<span class="auth-field-status is-error">Network error checking username.</span>';
                }
            }, 300);
        });
    }

    setupUsernameValidation('student-username-input', 'student-username-status');
    setupUsernameValidation('teacher-username-input', 'teacher-username-status');

    // -------------------------------------------------------------
    // 5. Live Debounced Email Validation (Section 4F)
    // -------------------------------------------------------------
    function setupEmailValidation(inputId, statusId) {
        const input = document.getElementById(inputId);
        const status = document.getElementById(statusId);
        if (!input || !status) return;

        let debounceTimer = null;

        input.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            const val = this.value.trim();

            if (!val) {
                status.innerHTML = '';
                return;
            }

            debounceTimer = setTimeout(async () => {
                try {
                    const resp = await fetch(`/accounts/api/check-email/?email=${encodeURIComponent(val)}`);
                    const data = await resp.json();

                    if (data.available) {
                        status.innerHTML = `<span class="auth-field-status is-available"><i data-lucide="check" class="lucide-icon icon-xs"></i> ${data.message}</span>`;
                    } else {
                        status.innerHTML = `<span class="auth-field-status is-taken"><i data-lucide="x" class="lucide-icon icon-xs"></i> ${data.message}</span>`;
                    }
                    if (window.lucide) window.lucide.createIcons();
                } catch (err) {
                    status.innerHTML = '';
                }
            }, 350);
        });
    }

    setupEmailValidation('student-email-input', 'student-email-status');
    setupEmailValidation('teacher-email-input', 'teacher-email-status');

    // -------------------------------------------------------------
    // 6. Live Password Checklist & Strength Meter (Section 4G)
    // -------------------------------------------------------------
    function setupPasswordLiveValidation(passInputId, checklistPrefix, meterId, strengthTextId) {
        const passInput = document.getElementById(passInputId);
        if (!passInput) return;

        const meter = document.getElementById(meterId);
        const strengthText = document.getElementById(strengthTextId);

        passInput.addEventListener('input', function() {
            const val = this.value;

            // 5 rules
            const hasLen = val.length >= 8;
            const hasUpper = /[A-Z]/.test(val);
            const hasLower = /[a-z]/.test(val);
            const hasNumber = /[0-9]/.test(val);
            const hasSpecial = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(val);

            function updateRule(elemId, isValid) {
                const el = document.getElementById(elemId);
                if (!el) return;
                if (isValid) {
                    el.classList.add('is-valid');
                    el.innerHTML = '<i data-lucide="check" class="lucide-icon icon-xs" style="color:#10B981;"></i> ' + el.getAttribute('data-label');
                } else {
                    el.classList.remove('is-valid');
                    el.innerHTML = '<i data-lucide="circle" class="lucide-icon icon-xs" style="color:var(--auth-text-muted);"></i> ' + el.getAttribute('data-label');
                }
            }

            updateRule(`${checklistPrefix}-rule-len`, hasLen);
            updateRule(`${checklistPrefix}-rule-upper`, hasUpper);
            updateRule(`${checklistPrefix}-rule-lower`, hasLower);
            updateRule(`${checklistPrefix}-rule-num`, hasNumber);
            updateRule(`${checklistPrefix}-rule-special`, hasSpecial);

            if (window.lucide) window.lucide.createIcons();

            // Calculate strength
            const passedCount = [hasLen, hasUpper, hasLower, hasNumber, hasSpecial].filter(Boolean).length;

            if (meter && strengthText) {
                meter.className = 'password-strength-bar';
                if (val.length === 0) {
                    strengthText.textContent = '';
                } else if (passedCount <= 2) {
                    meter.classList.add('is-weak');
                    strengthText.textContent = 'Weak';
                    strengthText.style.color = '#DC2626';
                } else if (passedCount <= 4) {
                    meter.classList.add('is-fair');
                    strengthText.textContent = 'Fair';
                    strengthText.style.color = '#EA580C';
                } else {
                    meter.classList.add('is-strong');
                    strengthText.textContent = 'Strong';
                    strengthText.style.color = '#10B981';
                }
            }
        });
    }

    setupPasswordLiveValidation('student-password1-input', 'student', 'student-pass-meter', 'student-pass-strength-text');
    setupPasswordLiveValidation('teacher-password1-input', 'teacher', 'teacher-pass-meter', 'teacher-pass-strength-text');

    // -------------------------------------------------------------
    // 7. Live Confirm Password Matching (Section 4H)
    // -------------------------------------------------------------
    function setupConfirmPasswordMatch(p1Id, p2Id, statusId) {
        const p1 = document.getElementById(p1Id);
        const p2 = document.getElementById(p2Id);
        const status = document.getElementById(statusId);
        if (!p1 || !p2 || !status) return;

        function checkMatch() {
            const v1 = p1.value;
            const v2 = p2.value;

            if (!v2) {
                status.innerHTML = '';
                return;
            }

            if (v1 === v2) {
                status.innerHTML = '<span class="auth-field-status is-available"><i data-lucide="check" class="lucide-icon icon-xs"></i> Passwords match.</span>';
            } else {
                status.innerHTML = '<span class="auth-field-status is-error"><i data-lucide="x" class="lucide-icon icon-xs"></i> Passwords do not match.</span>';
            }
            if (window.lucide) window.lucide.createIcons();
        }

        p1.addEventListener('input', checkMatch);
        p2.addEventListener('input', checkMatch);
    }

    setupConfirmPasswordMatch('student-password1-input', 'student-password2-input', 'student-confirm-status');
    setupConfirmPasswordMatch('teacher-password1-input', 'teacher-password2-input', 'teacher-confirm-status');

    // -------------------------------------------------------------
    // 8. Form Submission Loading State
    // -------------------------------------------------------------
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function() {
            if (this.checkValidity && !this.checkValidity()) {
                return;
            }
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                // Use a short delay so standard browser form submission dispatches without cancellation
                setTimeout(() => {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<i data-lucide="loader-2" class="lucide-icon icon-sm spin-animate"></i> <span>Processing...</span>';
                    if (window.lucide) window.lucide.createIcons();
                }, 50);
            }
        });
    });

    // Reset button states on pageshow (e.g. Back button or bfcache restoration)
    window.addEventListener('pageshow', function() {
        document.querySelectorAll('button[type="submit"]').forEach(btn => {
            btn.disabled = false;
        });
    });

    // Initial Lucide Icons initialization
    if (window.lucide) {
        window.lucide.createIcons();
    }
});
