"""
Academic Management Models for EPS Phoenix.
Compliant with Section 9 (Academic Structure: Dept -> Course -> Batch -> Semester -> Subject -> Enrollment -> Scoping).
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.student.models import StudentProfile


class Department(models.Model):
    """
    Academic Department (e.g. Department of Computer Science & Engineering).
    """
    code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text=_("Unique departmental shortcode (e.g. CSE, ECE, ME)."),
    )
    name = models.CharField(
        max_length=150,
        help_text=_("Official department legal title."),
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Department")
        verbose_name_plural = _("Departments")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Course(models.Model):
    """
    Academic Program / Degree (e.g. Bachelor of Technology in Computer Science).
    """
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="courses",
        help_text=_("Parent academic department."),
    )
    code = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
        help_text=_("Unique degree program code (e.g. BT-CSE, MS-DS)."),
    )
    name = models.CharField(
        max_length=150,
        help_text=_("Full academic program title."),
    )
    duration_years = models.PositiveIntegerField(
        default=4,
        help_text=_("Program length in calendar years."),
    )
    total_semesters = models.PositiveIntegerField(
        default=8,
        help_text=_("Total number of academic semesters in curriculum."),
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Course")
        verbose_name_plural = _("Courses")
        ordering = ["department", "name"]

    def __str__(self):
        return f"{self.name} [{self.code}]"


class AcademicBatch(models.Model):
    """
    Academic cohort / graduating class (e.g. Batch 2024-2028).
    """
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="batches",
        help_text=_("Enrolled degree program."),
    )
    name = models.CharField(
        max_length=100,
        help_text=_("Batch label (e.g. 2024-2028)."),
    )
    start_year = models.PositiveIntegerField()
    end_year = models.PositiveIntegerField()
    current_semester = models.PositiveIntegerField(
        default=1,
        help_text=_("Current operational semester for this cohort."),
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Academic Batch")
        verbose_name_plural = _("Academic Batches")
        ordering = ["-start_year", "course"]
        unique_together = ("course", "name")

    def __str__(self):
        return f"{self.course.code} - Batch {self.name} (Sem {self.current_semester})"


class Semester(models.Model):
    """
    Semester instance within a specific batch.
    """
    batch = models.ForeignKey(
        AcademicBatch,
        on_delete=models.CASCADE,
        related_name="semesters",
    )
    semester_number = models.PositiveIntegerField(
        help_text=_("Semester ordinal number (1-8)."),
    )
    is_current = models.BooleanField(
        default=False,
        help_text=_("True if this semester is currently active for examination scheduling."),
    )

    class Meta:
        verbose_name = _("Semester")
        verbose_name_plural = _("Semesters")
        unique_together = ("batch", "semester_number")
        ordering = ["batch", "semester_number"]

    def __str__(self):
        return f"{self.batch.name} - Semester {self.semester_number}"


class Subject(models.Model):
    """
    Course module / paper (e.g. CS301 - Data Structures & Algorithms).
    """
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="subjects",
    )
    code = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
        help_text=_("Unique subject code (e.g. CS201, MATH101)."),
    )
    name = models.CharField(
        max_length=150,
        help_text=_("Official subject course title."),
    )
    semester_number = models.PositiveIntegerField(
        default=1,
        help_text=_("Standard semester level where this subject is taught."),
    )
    credits = models.PositiveIntegerField(
        default=3,
        help_text=_("Academic credit weight."),
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Subject")
        verbose_name_plural = _("Subjects")
        ordering = ["course", "semester_number", "code"]

    def __str__(self):
        return f"[{self.code}] {self.name} (Sem {self.semester_number})"


class TeacherAssignment(models.Model):
    """
    Teacher Scoping Entity (Section 9):
    Links a faculty member to a specific Subject and Academic Batch.
    Enforces that faculty can only author questions, schedule exams, and invigilate
    candidates within their explicitly assigned academic scope.
    """
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="academic_assignments",
        help_text=_("Faculty member assigned to instruct or invigilate."),
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="teacher_assignments",
    )
    batch = models.ForeignKey(
        AcademicBatch,
        on_delete=models.CASCADE,
        related_name="teacher_assignments",
    )
    academic_year = models.PositiveIntegerField(
        default=2026,
        help_text=_("Calendar year for assignment validity."),
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Teacher Academic Assignment")
        verbose_name_plural = _("Teacher Academic Assignments")
        unique_together = ("teacher", "subject", "batch")
        ordering = ["-academic_year", "subject"]

    def __str__(self):
        return f"@{self.teacher.username} -> {self.subject.code} for {self.batch.name}"


class StudentEnrollment(models.Model):
    """
    Official candidate enrollment in an academic batch cohort.
    """
    class EnrollmentStatus(models.TextChoices):
        ENROLLED = "ENROLLED", _("Currently Enrolled & Active")
        PROMOTED = "PROMOTED", _("Promoted to Next Semester")
        GRADUATED = "GRADUATED", _("Successfully Graduated")
        SUSPENDED = "SUSPENDED", _("Academically Suspended")
        DROPPED = "DROPPED", _("Discontinued")

    student = models.OneToOneField(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="academic_enrollment",
    )
    batch = models.ForeignKey(
        AcademicBatch,
        on_delete=models.CASCADE,
        related_name="student_enrollments",
    )
    current_semester = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=30,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ENROLLED,
        db_index=True,
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Student Enrollment")
        verbose_name_plural = _("Student Enrollments")
        ordering = ["batch", "student__roll_number"]

    def __str__(self):
        roll = self.student.roll_number or self.student.registration_number
        return f"{roll} in {self.batch.name} (Sem {self.current_semester})"
