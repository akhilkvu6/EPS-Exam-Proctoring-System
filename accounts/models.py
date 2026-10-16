from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Administrator'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='student'
    )

    @property
    def is_student(self):
        return self.role == 'student'

    @property
    def is_teacher(self):
        return self.role == 'teacher'

    @property
    def is_admin_user(self):
        return self.role == 'admin' or self.is_superuser or self.is_staff

    def get_status(self):
        if self.is_admin_user:
            return 'approved'
        if self.role == 'teacher' and hasattr(self, 'teacher_profile'):
            return self.teacher_profile.verification_status
        if self.role == 'student' and hasattr(self, 'student_profile'):
            return self.student_profile.verification_status
        return 'pending'

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class ClassGroup(models.Model):
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='classes'
    )
    name = models.CharField(max_length=100)
    semester = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('department', 'name', 'semester')

    def __str__(self):
        return f"{self.name} - Sem {self.semester} ({self.department.code})"


class TeacherProfile(models.Model):
    VERIFICATION_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='teacher_profile'
    )
    employee_id = models.CharField(max_length=50)
    department = models.CharField(max_length=100)
    qualification = models.CharField(max_length=150)
    institution = models.CharField(max_length=150, blank=True, default='')

    verification_status = models.CharField(
        max_length=15,
        choices=VERIFICATION_STATUS,
        default='pending'
    )
    reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_teachers'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default='')

    assigned_classes = models.ManyToManyField(
        ClassGroup,
        blank=True,
        related_name='assigned_teachers'
    )

    def __str__(self):
        return f"{self.user.username} - {self.department} ({self.verification_status})"


class StudentProfile(models.Model):
    VERIFICATION_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile'
    )
    full_name = models.CharField(max_length=150, blank=True, default='')
    roll_number = models.CharField(max_length=50)
    department = models.CharField(max_length=100)
    semester = models.CharField(max_length=20)

    class_group = models.ForeignKey(
        ClassGroup,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='students'
    )

    verification_status = models.CharField(
        max_length=15,
        choices=VERIFICATION_STATUS,
        default='pending'
    )
    reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_students'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default='')

    def __str__(self):
        return f"{self.user.username} ({self.roll_number}) - {self.verification_status}"


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('registration', 'Registration'),
        ('approval', 'Approval / Status'),
        ('exam', 'Examination'),
        ('result', 'Result'),
        ('security', 'Security Alert'),
        ('system', 'System Notice'),
    )

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES,
        default='system'
    )
    link = models.CharField(max_length=255, blank=True, default='')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"To {self.recipient.username}: {self.title}"


class ApprovalRecord(models.Model):
    applicant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='approval_records'
    )
    reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='decisions_made'
    )
    role = models.CharField(max_length=20)
    decision = models.CharField(max_length=20)
    reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.applicant.username} - {self.decision} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class AuditLog(models.Model):
    actor = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=100)
    target_user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_targets'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    details = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        actor_name = self.actor.username if self.actor else "System"
        return f"[{self.created_at.strftime('%Y-%m-%d %H:%M')}] {actor_name}: {self.action}"