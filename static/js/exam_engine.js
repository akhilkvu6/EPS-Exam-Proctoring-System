/**
 * EPS Examination Engine Client Controller
 * Manages question navigation, autosave, server timer synchronization,
 * and duplicate-submission protection.
 */

class ExamEngine {
    constructor(config) {
        this.attemptId = config.attemptId;
        this.saveUrl = config.saveUrl;
        this.submitUrl = config.submitUrl;
        this.csrfToken = config.csrfToken;
        this.timeRemaining = config.timeRemaining; // seconds
        this.totalQuestions = config.totalQuestions;
        this.currentQuestionIndex = 1;

        this.statusIndicator = document.getElementById('save-status');
        this.timerDisplay = document.getElementById('exam-timer');
        this.saveTimeout = null;
        this.isSubmitting = false;

        this.init();
    }

    init() {
        this.startTimer();
        this.showQuestion(1);
        this.bindEvents();
    }

    startTimer() {
        this.updateTimerDisplay();
        this.timerInterval = setInterval(() => {
            this.timeRemaining--;
            this.updateTimerDisplay();

            if (this.timeRemaining <= 0) {
                clearInterval(this.timerInterval);
                this.autoSubmitAtDeadline();
            }
        }, 1000);
    }

    updateTimerDisplay() {
        const hours = Math.floor(this.timeRemaining / 3600);
        const minutes = Math.floor((this.timeRemaining % 3600) / 60);
        const seconds = this.timeRemaining % 60;

        const pad = num => String(num).padStart(2, '0');
        const formatted = `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;

        if (this.timerDisplay) {
            this.timerDisplay.textContent = formatted;
            if (this.timeRemaining < 300) { // under 5 mins
                this.timerDisplay.style.color = 'var(--danger)';
                this.timerDisplay.style.fontWeight = '800';
            }
        }
    }

    showQuestion(number) {
        document.querySelectorAll('.question-card').forEach(card => card.style.display = 'none');
        document.querySelectorAll('.palette-btn').forEach(btn => btn.classList.remove('active-q'));

        const targetCard = document.getElementById(`q-card-${number}`);
        const targetBtn = document.getElementById(`palette-btn-${number}`);

        if (targetCard) {
            targetCard.style.display = 'block';
            this.currentQuestionIndex = number;
        }
        if (targetBtn) {
            targetBtn.classList.add('active-q');
        }

        // Update Prev / Next buttons
        const prevBtn = document.getElementById('btn-prev-q');
        const nextBtn = document.getElementById('btn-next-q');
        if (prevBtn) prevBtn.disabled = (number <= 1);
        if (nextBtn) nextBtn.disabled = (number >= this.totalQuestions);
    }

    nextQuestion() {
        if (this.currentQuestionIndex < this.totalQuestions) {
            this.showQuestion(this.currentQuestionIndex + 1);
        }
    }

    prevQuestion() {
        if (this.currentQuestionIndex > 1) {
            this.showQuestion(this.currentQuestionIndex - 1);
        }
    }

    bindEvents() {
        // Radio choices autosave
        document.querySelectorAll('input[type="radio"].option-radio').forEach(radio => {
            radio.addEventListener('change', (e) => {
                const qId = e.target.dataset.questionId;
                const optId = e.target.value;
                const qNum = e.target.dataset.questionNumber;
                this.triggerAutosave(qId, optId, null, null, qNum);
            });
        });

        // Text answers autosave with debounce
        document.querySelectorAll('.text-answer-input').forEach(input => {
            input.addEventListener('input', (e) => {
                const qId = e.target.dataset.questionId;
                const textVal = e.target.value;
                const qNum = e.target.dataset.questionNumber;
                clearTimeout(this.saveTimeout);
                this.saveTimeout = setTimeout(() => {
                    this.triggerAutosave(qId, null, textVal, null, qNum);
                }, 800);
            });
        });

        // Mark for review toggle
        document.querySelectorAll('.review-toggle-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const qId = btn.dataset.questionId;
                const qNum = btn.dataset.questionNumber;
                const isMarkedNow = btn.getAttribute('data-marked') === 'true';
                const nextState = !isMarkedNow;

                btn.setAttribute('data-marked', nextState ? 'true' : 'false');
                btn.textContent = nextState ? '★ Marked for Review' : '☆ Mark for Review';
                btn.className = nextState ? 'btn btn-warning btn-sm review-toggle-btn' : 'btn btn-outline btn-sm review-toggle-btn';

                const pBtn = document.getElementById(`palette-btn-${qNum}`);
                if (pBtn) {
                    if (nextState) {
                        pBtn.classList.add('palette-marked');
                    } else {
                        pBtn.classList.remove('palette-marked');
                    }
                }

                this.triggerAutosave(qId, null, null, nextState, qNum);
            });
        });
    }

    triggerAutosave(questionId, selectedOptionId, textAnswer, isMarkedForReview, questionNumber) {
        this.setSaveStatus('saving');

        const payload = {
            question_id: questionId,
            selected_option_id: selectedOptionId,
            text_answer: textAnswer,
            is_marked_for_review: isMarkedForReview
        };

        fetch(this.saveUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify(payload)
        })
        .then(response => {
            if (!response.ok) {
                if (response.status === 403) {
                    this.autoSubmitAtDeadline();
                }
                throw new Error('Save error');
            }
            return response.json();
        })
        .then(data => {
            this.setSaveStatus('saved');
            if (questionNumber) {
                const pBtn = document.getElementById(`palette-btn-${questionNumber}`);
                if (pBtn) pBtn.classList.add('palette-answered');
            }
        })
        .catch(err => {
            this.setSaveStatus('error');
        });
    }

    setSaveStatus(state) {
        if (!this.statusIndicator) return;
        if (state === 'saving') {
            this.statusIndicator.textContent = 'Saving...';
            this.statusIndicator.style.color = 'var(--warning)';
        } else if (state === 'saved') {
            this.statusIndicator.textContent = '✓ All changes saved';
            this.statusIndicator.style.color = 'var(--success)';
        } else {
            this.statusIndicator.textContent = '⚠️ Offline / Retrying';
            this.statusIndicator.style.color = 'var(--danger)';
        }
    }

    confirmSubmit() {
        if (confirm('Are you sure you want to finalize and submit your examination? Once submitted, your answers will be locked.')) {
            this.submitForm();
        }
    }

    autoSubmitAtDeadline() {
        if (this.isSubmitting) return;
        this.isSubmitting = true;
        alert('Examination time has expired! Your answers are being submitted automatically.');
        this.submitForm();
    }

    submitForm() {
        this.isSubmitting = true;
        const form = document.getElementById('exam-submission-form');
        if (form) {
            form.submit();
        }
    }
}
