from django.db import models
from django.utils import timezone
from decimal import Decimal
from accounts.models import User
from exams.models import Exam, ExamAttempt, StudentAnswer


class Result(models.Model):
    GRADING_STATUS = (
        ('auto_graded', 'Objective Auto-Graded'),
        ('pending_manual', 'Pending Manual Evaluation'),
        ('fully_graded', 'Fully Evaluated'),
    )

    attempt = models.OneToOneField(
        ExamAttempt,
        on_delete=models.CASCADE,
        related_name='result'
    )
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='results'
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='results'
    )

    total_marks_obtained = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    maximum_marks = models.DecimalField(max_digits=6, decimal_places=2, default=100.0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    is_passed = models.BooleanField(default=False)

    # Publication gate (Master rule: unpublished results protected from students)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='published_results'
    )

    grading_status = models.CharField(
        max_length=20,
        choices=GRADING_STATUS,
        default='auto_graded'
    )
    teacher_remarks = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-total_marks_obtained']
        unique_together = ('exam', 'student')

    def recalculate(self):
        """Calculates total marks, percentage, pass/fail status, and evaluation completeness."""
        answers = self.attempt.answers.all()
        unevaluated_count = answers.filter(is_evaluated=False).count()

        evaluated_score = sum(
            ans.marks_awarded for ans in answers if ans.is_evaluated and ans.marks_awarded is not None
        )

        self.total_marks_obtained = max(Decimal('0.0'), Decimal(str(evaluated_score)))
        self.maximum_marks = self.exam.total_marks

        if self.maximum_marks > 0:
            pct = (self.total_marks_obtained / self.maximum_marks) * 100
            self.percentage = round(min(Decimal('100.0'), pct), 2)
        else:
            self.percentage = Decimal('0.0')

        self.is_passed = (self.total_marks_obtained >= self.exam.passing_marks)

        if unevaluated_count > 0:
            self.grading_status = 'pending_manual'
        else:
            self.grading_status = 'fully_graded'

        self.save()
        return self

    def __str__(self):
        return f"{self.student.username} - {self.exam.title}: {self.total_marks_obtained}/{self.maximum_marks} ({'PASS' if self.is_passed else 'FAIL'})"
