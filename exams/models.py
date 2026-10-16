from django.db import models
from django.utils import timezone
from accounts.models import User, Department, ClassGroup


class Subject(models.Model):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='subjects'
    )
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_subjects'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class Question(models.Model):
    QUESTION_TYPES = (
        ('mcq', 'Multiple Choice (Single Answer)'),
        ('true_false', 'True / False'),
        ('short_answer', 'Short Answer'),
        ('descriptive', 'Descriptive / Essay'),
    )

    DIFFICULTY_LEVELS = (
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_questions'
    )
    question_text = models.TextField()
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPES,
        default='mcq'
    )
    difficulty = models.CharField(
        max_length=10,
        choices=DIFFICULTY_LEVELS,
        default='medium'
    )
    topic = models.CharField(max_length=100, blank=True, default='')
    marks = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    negative_marks = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    explanation = models.TextField(blank=True, default='')
    correct_text_answer = models.TextField(
        blank=True,
        default='',
        help_text="Reference answer key for short-answer or descriptive evaluation."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_question_type_display()}] {self.question_text[:60]} ({self.marks}m)"


class AnswerOption(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='options'
    )
    option_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{'✓' if self.is_correct else '✗'} {self.option_text[:40]}"


class Exam(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('closed', 'Closed'),
    )

    PROCTOR_REQUIREMENT = (
        ('required', 'Required'),
        ('optional', 'Optional'),
        ('disabled', 'Disabled'),
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    instructions = models.TextField(
        blank=True,
        default="1. Ensure steady webcam and microphone functionality.\n2. Do not switch tabs or exit fullscreen.\n3. Submission locks automatically when timer expires."
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='exams'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_exams'
    )

    # Schedule & Timing
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)

    # Scoring & Rules
    total_marks = models.DecimalField(max_digits=6, decimal_places=2, default=100.0)
    passing_marks = models.DecimalField(max_digits=6, decimal_places=2, default=40.0)
    negative_marking = models.BooleanField(default=False)
    default_negative_mark = models.DecimalField(max_digits=4, decimal_places=2, default=0.25)
    attempt_limit = models.PositiveIntegerField(default=1)

    # Question delivery options
    shuffle_questions = models.BooleanField(default=True)
    shuffle_options = models.BooleanField(default=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='draft')

    # Proctoring Configuration (Part G, 22)
    camera_required = models.CharField(max_length=10, choices=PROCTOR_REQUIREMENT, default='required')
    microphone_required = models.CharField(max_length=10, choices=PROCTOR_REQUIREMENT, default='optional')
    fullscreen_required = models.BooleanField(default=True)
    block_tab_switch = models.BooleanField(default=True)
    block_copy_paste = models.BooleanField(default=True)
    screen_sharing_required = models.CharField(max_length=10, choices=PROCTOR_REQUIREMENT, default='disabled')
    face_detection_enabled = models.BooleanField(default=True)
    max_warning_count = models.PositiveIntegerField(default=3)

    # Assignments
    assigned_classes = models.ManyToManyField(
        ClassGroup,
        blank=True,
        related_name='assigned_exams'
    )
    assigned_students = models.ManyToManyField(
        User,
        blank=True,
        related_name='individual_assigned_exams'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_time']

    @property
    def can_modify(self):
        return self.status == 'draft'

    def is_accessible_by_teacher(self, user):
        """
        Check if teacher or admin user has permission to manage/grade this exam.
        - Admin or superuser has full access.
        - The creator of the exam has full access.
        - A teacher in the same department as the exam's subject has access.
        """
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser or user.role == 'admin':
            return True
        if user.role != 'teacher':
            return False
        if self.created_by_id == user.id:
            return True
        if hasattr(user, 'teacher_profile') and self.subject and self.subject.department:
            teacher_dept = (user.teacher_profile.department or '').strip().lower()
            dept_name = self.subject.department.name.strip().lower()
            dept_code = self.subject.department.code.strip().lower()
            if teacher_dept and (teacher_dept == dept_name or teacher_dept == dept_code):
                return True
        return False

    def get_live_status(self):
        now = timezone.now()
        if self.status == 'draft':
            return 'draft'
        if self.status == 'closed':
            return 'closed'
        if now < self.start_time:
            return 'scheduled'
        elif self.start_time <= now <= self.end_time:
            return 'active'
        else:
            return 'closed'

    def is_eligible(self, user):
        """Check if student is enrolled/assigned and approved."""
        if user.role != 'student':
            return False
        if not hasattr(user, 'student_profile') or user.student_profile.verification_status != 'approved':
            return False

        # Check direct assignment or class assignment
        if self.assigned_students.filter(id=user.id).exists():
            return True

        if user.student_profile.class_group and self.assigned_classes.filter(id=user.student_profile.class_group.id).exists():
            return True

        # Check department match if no specific class assigned
        if not self.assigned_classes.exists() and not self.assigned_students.exists():
            if user.student_profile.department.lower() == self.subject.department.name.lower():
                return True

        return False

    def __str__(self):
        return f"{self.title} ({self.subject.code}) - {self.status}"


class ExamQuestion(models.Model):
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='exam_questions'
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='question_exams'
    )
    order = models.PositiveIntegerField(default=1)
    marks = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    negative_marks = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['order', 'id']
        unique_together = ('exam', 'question')

    def effective_marks(self):
        return self.marks if self.marks is not None else self.question.marks

    def effective_negative_marks(self):
        return self.negative_marks if self.negative_marks is not None else self.question.negative_marks

    def __str__(self):
        return f"{self.exam.title} - Q{self.order}: {self.question.question_text[:30]}"


class ExamAttempt(models.Model):
    STATUS_CHOICES = (
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted by Student'),
        ('auto_submitted', 'Auto-Submitted at Deadline'),
        ('cancelled', 'Cancelled'),
    )

    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='attempts'
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='exam_attempts'
    )
    attempt_number = models.PositiveIntegerField(default=1)
    started_at = models.DateTimeField(default=timezone.now)
    server_deadline = models.DateTimeField(help_text="Strict server-enforced deadline.")
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    total_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # Proctoring metrics
    warning_count = models.PositiveIntegerField(default=0)
    proctoring_flagged = models.BooleanField(default=False)
    proctoring_notes = models.TextField(blank=True, default='')

    # Shuffled question sequence for deterministic session consistency
    shuffled_question_ids = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-started_at']
        unique_together = ('exam', 'student', 'attempt_number')

    @property
    def is_active(self):
        return self.status == 'in_progress' and timezone.now() <= self.server_deadline

    def time_remaining_seconds(self):
        if self.status != 'in_progress':
            return 0
        diff = (self.server_deadline - timezone.now()).total_seconds()
        return max(0, int(diff))

    def __str__(self):
        return f"{self.student.username} - {self.exam.title} (Attempt #{self.attempt_number}) [{self.status}]"


class StudentAnswer(models.Model):
    attempt = models.ForeignKey(
        ExamAttempt,
        on_delete=models.CASCADE,
        related_name='answers'
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='student_answers'
    )
    selected_option = models.ForeignKey(
        AnswerOption,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='student_selections'
    )
    text_answer = models.TextField(blank=True, default='')
    is_marked_for_review = models.BooleanField(default=False)

    marks_awarded = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_evaluated = models.BooleanField(default=False)
    evaluator_feedback = models.TextField(blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('attempt', 'question')

    def __str__(self):
        return f"Ans: {self.attempt.student.username} -> Q{self.question.id}"


class ProctoringIncident(models.Model):
    EVENT_TYPES = (
        ('camera_interrupted', 'Camera Stream Interrupted / Denied'),
        ('camera_restored', 'Camera Stream Restored'),
        ('face_not_detected', 'Face Missing from Video Frame'),
        ('multiple_faces', 'Multiple Faces Detected'),
        ('audio_spike', 'High Sustained Audio Noise Detected'),
        ('tab_switch', 'Exam Tab Visibility Changed (Tab Switch)'),
        ('fullscreen_exit', 'Fullscreen Mode Exited'),
        ('window_blur', 'Window Focus Lost'),
        ('copy_paste_attempt', 'Prohibited Clipboard Event (Copy/Paste)'),
        ('key_violation', 'Restricted Key Shortcut Pressed'),
        ('network_disconnect', 'Network Offline Detected'),
        ('network_restored', 'Network Restored'),
        ('screen_share_stopped', 'Screen Share Interrupted'),
    )

    SEVERITY_LEVELS = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    )

    REVIEW_STATUS = (
        ('unreviewed', 'Unreviewed'),
        ('reviewed', 'Reviewed - Cleared'),
        ('inconclusive', 'Inconclusive'),
        ('action_required', 'Requires Action / Follow-up'),
    )

    attempt = models.ForeignKey(
        ExamAttempt,
        on_delete=models.CASCADE,
        related_name='proctoring_incidents'
    )
    event_type = models.CharField(max_length=40, choices=EVENT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS, default='medium')
    timestamp = models.DateTimeField(default=timezone.now)
    details = models.TextField(blank=True, default='')

    review_status = models.CharField(max_length=20, choices=REVIEW_STATUS, default='unreviewed')
    reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_incidents'
    )
    review_notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.severity.upper()}] {self.get_event_type_display()} - {self.attempt.student.username} at {self.timestamp.strftime('%H:%M:%S')}"

