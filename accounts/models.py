import re
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone


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
        if self.role == 'teacher' and hasattr(self, 'teacher_profile'):
            return self.teacher_profile.verification_status
        if self.role == 'student' and hasattr(self, 'student_profile'):
            return self.student_profile.verification_status
        return 'approved' if (self.is_superuser or self.is_staff) else 'pending'

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class Course(models.Model):
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='courses',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, default='')
    total_semesters = models.PositiveSmallIntegerField(default=8)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class AcademicBatch(models.Model):
    ENROLLMENT_STATUS = (
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('archived', 'Archived'),
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='batches'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='batches'
    )
    admission_year = models.PositiveIntegerField(default=2026, db_index=True)
    course_code = models.CharField(max_length=20)
    batch_name = models.CharField(max_length=100)
    batch_identifier = models.CharField(max_length=50, blank=True, default='')
    prefix = models.CharField(max_length=30, db_index=True)
    capacity = models.PositiveIntegerField(default=60)
    start_roll_number = models.PositiveIntegerField(default=1)
    end_roll_number = models.PositiveIntegerField(default=60)
    admission_semester = models.CharField(max_length=20, default='1')
    total_semesters = models.PositiveSmallIntegerField(default=6)
    current_semester = models.CharField(max_length=20, default='1')
    enrollment_status = models.CharField(max_length=20, choices=ENROLLMENT_STATUS, default='open')
    is_active = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_batches'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-admission_year', 'course_code', 'batch_name']
        unique_together = ('admission_year', 'course', 'batch_identifier')

    def __str__(self):
        suffix = f" ({self.batch_identifier})" if self.batch_identifier else ""
        return f"{self.batch_name}{suffix} - Sem {self.current_semester}"

    def save(self, *args, **kwargs):
        if not self.course_code and self.course:
            self.course_code = self.course.code
        clean_code = re.sub(r'[^a-zA-Z0-9]', '', self.course_code).upper()
        if self.batch_identifier:
            clean_id = re.sub(r'[^a-zA-Z0-9]', '', self.batch_identifier).upper()
            self.prefix = f"{self.admission_year}{clean_code}{clean_id}"
        else:
            self.prefix = f"{self.admission_year}{clean_code}"
        if not self.batch_name:
            self.batch_name = f"{self.admission_year} {self.course.code}"
        super().save(*args, **kwargs)

    def generate_registration_number(self, roll_sequence):
        pad_width = 3 if self.capacity > 99 else 2
        return f"{self.prefix}{roll_sequence:0{pad_width}d}"

    def get_positions_summary(self):
        now = timezone.now()
        self.roll_reservations.filter(status='reserved', expires_at__lt=now).update(
            status='available', session_key='', reserved_by_email='', reserved_by_name='', expires_at=None
        )
        counts = self.roll_reservations.aggregate(
            total=Count('id'),
            assigned=Count('id', filter=Q(status='assigned')),
            pending=Count('id', filter=Q(status='pending')),
            reserved=Count('id', filter=Q(status='reserved')),
            available=Count('id', filter=Q(status='available')),
            released=Count('id', filter=Q(status='released')),
        )
        return counts

    def can_modify_identity(self):
        """Returns False if there are permanently assigned students or pending registrations."""
        return not self.roll_reservations.filter(status__in=['assigned', 'pending']).exists()

    def can_reduce_capacity(self, new_capacity):
        occupied_count = self.roll_reservations.filter(status__in=['assigned', 'pending', 'reserved']).count()
        return new_capacity >= occupied_count


class RollNumberReservation(models.Model):
    STATUS_CHOICES = (
        ('available', 'Available'),
        ('reserved', 'Temporarily Reserved'),
        ('pending', 'Pending Approval'),
        ('assigned', 'Permanently Assigned'),
        ('released', 'Released'),
    )

    batch = models.ForeignKey(
        AcademicBatch,
        on_delete=models.CASCADE,
        related_name='roll_reservations'
    )
    roll_sequence = models.PositiveIntegerField()
    registration_number = models.CharField(max_length=50, unique=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available', db_index=True)
    session_key = models.CharField(max_length=100, blank=True, default='')
    reserved_by_email = models.EmailField(blank=True, default='')
    reserved_by_name = models.CharField(max_length=150, blank=True, default='')
    reserved_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    student_profile = models.ForeignKey(
        'StudentProfile',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='roll_allocations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['batch', 'roll_sequence']
        unique_together = ('batch', 'roll_sequence')

    def __str__(self):
        return f"{self.registration_number} ({self.get_status_display()})"

    def is_expired(self):
        if self.status == 'reserved' and self.expires_at:
            return timezone.now() > self.expires_at
        return False


class StudentSemesterHistory(models.Model):
    student = models.ForeignKey(
        'StudentProfile',
        on_delete=models.CASCADE,
        related_name='semester_history'
    )
    batch = models.ForeignKey(
        AcademicBatch,
        on_delete=models.CASCADE,
        related_name='semester_promotions',
        null=True,
        blank=True
    )
    previous_semester = models.CharField(max_length=20)
    new_semester = models.CharField(max_length=20)
    academic_session = models.CharField(max_length=50, blank=True, default='')
    changed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='promoted_students'
    )
    reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.roll_number}: Sem {self.previous_semester} -> Sem {self.new_semester}"


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
    employee_id = models.CharField(max_length=50, unique=True)
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
    roll_number = models.CharField(max_length=50, unique=True)
    department = models.CharField(max_length=100)
    semester = models.CharField(max_length=20)

    course = models.ForeignKey(
        Course,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='enrolled_profiles'
    )
    batch = models.ForeignKey(
        AcademicBatch,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='enrolled_students'
    )
    roll_sequence = models.PositiveIntegerField(null=True, blank=True)
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


class StudentEnrollment(models.Model):
    roll_number = models.CharField(max_length=50, unique=True, db_index=True)
    full_name = models.CharField(max_length=150)
    email = models.EmailField(blank=True, default='')
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='enrolled_students',
        null=True,
        blank=True
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        related_name='enrolled_students',
        null=True,
        blank=True
    )
    course_name = models.CharField(max_length=100, blank=True, default='')
    batch = models.ForeignKey(
        AcademicBatch,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='enrolled_records'
    )
    roll_sequence = models.PositiveIntegerField(null=True, blank=True)
    semester = models.CharField(max_length=20, default='1')
    is_active = models.BooleanField(default=True, db_index=True)
    is_registered = models.BooleanField(default=False, db_index=True)
    registered_student = models.OneToOneField(
        'StudentProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='enrollment_record'
    )
    registered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['roll_number']

    def __str__(self):
        c_code = self.course.code if self.course else (self.department.code if self.department else 'N/A')
        return f"{self.roll_number} - {self.full_name} ({c_code})"


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
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='system'
    )
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.username} - {self.title}"


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
