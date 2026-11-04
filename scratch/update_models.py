with open('accounts/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Insert Course right after Department
course_model_code = """

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
"""

enrollment_model_code = """

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
"""

# Add course to StudentProfile
student_profile_needle = "class_group = models.ForeignKey("
student_profile_addition = """    course = models.ForeignKey(
        'Course',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='enrolled_profiles'
    )
    class_group = models.ForeignKey("""

if "class Course(models.Model):" not in content:
    # insert Course after Department
    dept_end_marker = "    def __str__(self):\n        return f\"{self.name} ({self.code})\"\n"
    assert dept_end_marker in content, "Department end marker not found"
    content = content.replace(dept_end_marker, dept_end_marker + course_model_code)

    # insert StudentEnrollment after StudentProfile
    profile_end_marker = "    def __str__(self):\n        return f\"{self.user.username} ({self.roll_number}) - {self.verification_status}\"\n"
    assert profile_end_marker in content, "StudentProfile end marker not found"
    content = content.replace(profile_end_marker, profile_end_marker + enrollment_model_code)

    # add course field to StudentProfile
    assert student_profile_needle in content, "student_profile_needle not found"
    content = content.replace(student_profile_needle, student_profile_addition, 1)

    with open('accounts/models.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("accounts/models.py updated successfully!")
else:
    print("Course and StudentEnrollment already present in accounts/models.py.")
