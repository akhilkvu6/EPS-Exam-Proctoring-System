from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    ROLE_CHOICES = (
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='student'
    )


class TeacherProfile(models.Model):

    VERIFICATION_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='teacher_profile'
    )

    employee_id = models.CharField(max_length=50)
    department = models.CharField(max_length=100)
    qualification = models.CharField(max_length=150)

    verification_status = models.CharField(
        max_length=10,
        choices=VERIFICATION_STATUS,
        default='pending'
    )

    def __str__(self):
        return self.user.username