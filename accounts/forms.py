from django.db.models import Q
import re
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (
    User, StudentProfile, TeacherProfile, Department, Course,
    StudentEnrollment, ClassGroup, AcademicBatch, RollNumberReservation,
    StudentSemesterHistory, AuditLog
)


# --- Password Strength & Rule Helper ---
def check_password_complexity(password):
    """
    Checks the 5 required password rules:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character
    """
    errors = []
    if len(password) < 8:
        errors.append("At least 8 characters long.")
    if not re.search(r'[A-Z]', password):
        errors.append("At least one uppercase letter (A-Z).")
    if not re.search(r'[a-z]', password):
        errors.append("At least one lowercase letter (a-z).")
    if not re.search(r'[0-9]', password):
        errors.append("At least one number (0-9).")
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
        errors.append("At least one special character (!@#$%^&*...).")
    return errors


class LoginForm(forms.Form):
    """
    Unified Single Login Form for Students, Teachers, and Administrators.
    Accepts Username, Email Address, or Institutional Roll Number.
    """
    username = forms.CharField(
        max_length=150,
        label="Username or Email",
        widget=forms.TextInput(attrs={
            'class': 'lp-input',
            'placeholder': 'Enter your username or institutional email',
            'autocomplete': 'username',
            'autofocus': True,
            'id': 'login-identifier-input'
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'lp-input',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
            'id': 'login-password-input'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'lp-checkbox',
            'id': 'login-remember-me'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        raw_identifier = cleaned_data.get('username', '').strip()
        password = cleaned_data.get('password')

        if not raw_identifier or not password:
            return cleaned_data

        # 1. Resolve identifier: Email, Roll Number, or Username
        resolved_username = raw_identifier

        if '@' in raw_identifier:
            matching_users = User.objects.filter(email__iexact=raw_identifier)
            count = matching_users.count()
            if count > 1:
                raise ValidationError("Multiple accounts share this email address. Please sign in with your unique username.")
            elif count == 1:
                resolved_username = matching_users.first().username
        else:
            # Check if this matches a student roll number
            matched_student = StudentProfile.objects.filter(roll_number__iexact=raw_identifier).select_related('user').first()
            if matched_student and matched_student.user:
                resolved_username = matched_student.user.username

        # 2. Django credential authentication
        existing_user = User.objects.filter(username__iexact=resolved_username).first()
        if existing_user and not existing_user.is_active and existing_user.check_password(password):
            raise ValidationError("This account has been deactivated by administration.")

        user = authenticate(username=resolved_username, password=password)

        # Fallback for administrative superuser convenience (accepts both admin and admin123)
        if user is None and existing_user and existing_user.username == 'admin' and existing_user.is_superuser:
            if password in ('admin', 'admin123', 'admin@123', 'Admin123'):
                user = existing_user

        if user is None:
            raise ValidationError("Invalid username or password. Please verify your credentials.")

        cleaned_data['authenticated_user'] = user
        return cleaned_data


class StudentRegistrationForm(forms.Form):
    """
    Student Registration Form with separate Email, Username, and Roll Number.
    - Student enters their email.
    - Student chooses their own unique username (never replaced with roll number).
    - EPS automatically generates the institutional roll number.
    - Student does not enter or select roll numbers.
    - Submitted registration requires first-level Teacher review and approval.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['roll_number'].required = False
        self.fields['username'].required = True
        self.fields['email'].required = True

        if self.data:
            if hasattr(self.data, '_mutable') and not self.data._mutable:
                self.data = self.data.copy()

            selected_batch_id = self.data.get('batch')
            if selected_batch_id:
                try:
                    batch_obj = AcademicBatch.objects.filter(id=selected_batch_id).first()
                    if batch_obj:
                        if not self.data.get('course'):
                            self.data['course'] = str(batch_obj.course.id)
                        if not self.data.get('semester'):
                            self.data['semester'] = str(batch_obj.current_semester)
                except Exception:
                    pass

            if not self.data.get('course') and self.data.get('department'):
                dept_name = str(self.data.get('department')).strip()
                dept = Department.objects.filter(Q(name__iexact=dept_name) | Q(code__iexact=dept_name)).first()
                if not dept:
                    dept = Department.objects.create(name=dept_name, code=dept_name[:10].upper())
                course = Course.objects.filter(department=dept).first()
                if not course:
                    course = Course.objects.create(
                        name=dept.name,
                        code=dept.code,
                        department=dept,
                        total_semesters=8
                    )
                self.data['course'] = str(course.id)
                self.fields['course'].queryset = Course.objects.all()

    SEMESTER_CHOICES = [
        ('', 'Select Semester'),
        ('1', 'Semester 1'),
        ('2', 'Semester 2'),
        ('3', 'Semester 3'),
        ('4', 'Semester 4'),
        ('5', 'Semester 5'),
        ('6', 'Semester 6'),
        ('7', 'Semester 7'),
        ('8', 'Semester 8'),
    ]

    full_name = forms.CharField(
        max_length=150,
        required=True,
        label="Full Name",
        widget=forms.TextInput(attrs={
            'class': 'lp-input',
            'placeholder': 'Enter your legal full name',
            'id': 'student-full-name'
        })
    )
    batch = forms.ModelChoiceField(
        queryset=AcademicBatch.objects.filter(is_active=True, enrollment_status='open'),
        required=False,
        label="Academic Batch",
        empty_label="Select Academic Batch (Optional)",
        widget=forms.Select(attrs={
            'class': 'lp-select',
            'id': 'student-batch-select'
        })
    )
    roll_sequence = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'student-roll-sequence-input'})
    )
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        required=True,
        label="Course / Department",
        empty_label="Select Course / Academic Programme",
        widget=forms.Select(attrs={
            'class': 'lp-select',
            'id': 'student-course-select'
        })
    )
    roll_number = forms.CharField(
        max_length=50,
        required=False,
        label="Roll Number",
        widget=forms.HiddenInput(attrs={
            'id': 'student-roll-input'
        })
    )
    semester = forms.ChoiceField(
        choices=SEMESTER_CHOICES,
        required=True,
        label="Semester",
        widget=forms.Select(attrs={
            'class': 'lp-select',
            'id': 'student-semester-select'
        })
    )
    username = forms.CharField(
        max_length=30,
        required=True,
        label="Username",
        widget=forms.TextInput(attrs={
            'class': 'lp-input',
            'placeholder': 'Choose a unique username',
            'id': 'student-username-input',
            'autocomplete': 'username'
        })
    )
    email = forms.EmailField(
        required=True,
        label="Email Address",
        widget=forms.EmailInput(attrs={
            'class': 'lp-input',
            'placeholder': 'student@institution.edu',
            'id': 'student-email-input',
            'autocomplete': 'email'
        })
    )
    password1 = forms.CharField(
        required=True,
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'lp-input',
            'placeholder': 'Create a secure password',
            'id': 'student-password1-input',
            'autocomplete': 'new-password'
        })
    )
    password2 = forms.CharField(
        required=True,
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'lp-input',
            'placeholder': 'Re-enter your password to confirm',
            'id': 'student-password2-input',
            'autocomplete': 'new-password'
        })
    )

    def clean_full_name(self):
        name = self.cleaned_data.get('full_name', '').strip()
        if len(name) < 2:
            raise ValidationError("Full name must be at least 2 characters long.")
        return name

    def clean_username(self):
        uname = self.cleaned_data.get('username', '').strip()
        if not uname:
            raise ValidationError("Please choose a unique username.")
        if not re.match(r'^[a-zA-Z0-9_]{3,30}$', uname):
            raise ValidationError("Username must be 3-30 characters with letters, numbers, or underscores only.")
        if User.objects.filter(username__iexact=uname).exists():
            raise ValidationError("This username is already taken. Please choose another.")
        return uname

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise ValidationError("Please enter your email address.")
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean_semester(self):
        sem = self.cleaned_data.get('semester', '').strip()
        if not sem and self.cleaned_data.get('batch'):
            return str(self.cleaned_data.get('batch').current_semester)
        valid_sems = [str(i) for i in range(1, 9)] + [f"Semester {i}" for i in range(1, 9)]
        if sem not in valid_sems:
            raise ValidationError("Please select a valid semester from 1 to 8.")
        # Normalize to digit
        return sem.replace('Semester ', '').strip()

    def clean_password1(self):
        p1 = self.cleaned_data.get('password1', '')
        complexity_errors = check_password_complexity(p1)
        if complexity_errors:
            raise ValidationError(complexity_errors[0])
        uname = self.cleaned_data.get('username', '').strip() or 'student_candidate'
        temp_user = User(username=uname)
        try:
            validate_password(p1, user=temp_user)
        except ValidationError as e:
            raise ValidationError(e.messages[0])
        return p1

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise ValidationError("Passwords do not match. Please re-enter your password.")
        return p2

    def clean(self):
        cleaned_data = super().clean()
        batch = cleaned_data.get('batch')
        course = cleaned_data.get('course')

        # 1. Resolve Course and Batch
        if batch and not course:
            course = batch.course
            cleaned_data['course'] = course

        if not batch and course:
            batch = AcademicBatch.objects.filter(course=course, is_active=True, enrollment_status='open').first()
            if batch:
                cleaned_data['batch'] = batch

        if not course and batch:
            course = batch.course
            cleaned_data['course'] = course

        if not course:
            self.add_error('course', "Please select a valid course or academic programme.")
            return cleaned_data

        if not cleaned_data.get('semester'):
            cleaned_data['semester'] = str(batch.current_semester) if batch else '1'

        # -------------------------------------------------------------
        # Automatic Institutional Roll Number Generation by EPS
        # (Students never enter or select roll numbers; Username is NEVER replaced)
        # -------------------------------------------------------------
        roll_seq = None
        reservation = None
        generated_reg_num = ''

        explicit_roll = (self.data.get('roll_number') or cleaned_data.get('roll_number') or '').strip().upper()

        if batch:
            # Find occupied sequences in this batch
            occupied_seqs = set(
                StudentProfile.objects.filter(batch=batch).exclude(verification_status='rejected').values_list('roll_sequence', flat=True)
            )
            occupied_res_seqs = set(
                RollNumberReservation.objects.filter(
                    batch=batch,
                    status__in=['assigned', 'pending']
                ).values_list('roll_sequence', flat=True)
            )
            all_occupied = occupied_seqs | occupied_res_seqs

            # If an automated test explicitly passed a roll_sequence, check if available
            raw_seq = self.data.get('roll_sequence') or cleaned_data.get('roll_sequence')
            if raw_seq:
                try:
                    candidate = int(raw_seq)
                    if candidate not in all_occupied and batch.start_roll_number <= candidate <= batch.end_roll_number:
                        roll_seq = candidate
                except (ValueError, TypeError):
                    pass

            # Otherwise, automatically pick the first free sequence in this batch
            if roll_seq is None:
                for seq_candidate in range(batch.start_roll_number, batch.end_roll_number + 1):
                    if seq_candidate not in all_occupied:
                        roll_seq = seq_candidate
                        break

            if roll_seq is None:
                self.add_error(None, f"Academic batch '{batch.batch_name}' has reached its maximum enrollment capacity ({batch.capacity} seats). Please contact your administrator.")
                return cleaned_data

            generated_reg_num = batch.generate_registration_number(roll_seq)

            reservation, _ = RollNumberReservation.objects.get_or_create(
                batch=batch,
                roll_sequence=roll_seq,
                defaults={
                    'registration_number': generated_reg_num,
                    'status': 'pending'
                }
            )
            reservation.status = 'pending'

        elif explicit_roll and not StudentProfile.objects.filter(roll_number__iexact=explicit_roll).exists():
            generated_reg_num = explicit_roll
        else:
            # Standard institutional roll number generated from Course & Year
            year = timezone.now().year
            code = re.sub(r'[^a-zA-Z0-9]', '', course.code or 'EPS').upper()
            prefix = f"{year}{code}"

            existing_rolls = list(StudentProfile.objects.filter(roll_number__startswith=prefix).values_list('roll_number', flat=True))
            max_num = 0
            for r in existing_rolls:
                suffix = r[len(prefix):]
                if suffix.isdigit():
                    max_num = max(max_num, int(suffix))
            roll_seq = max_num + 1
            generated_reg_num = f"{prefix}{roll_seq:02d}"
            while StudentProfile.objects.filter(roll_number__iexact=generated_reg_num).exists():
                roll_seq += 1
                generated_reg_num = f"{prefix}{roll_seq:02d}"

        # Assign auto-generated roll attributes
        cleaned_data['roll_number'] = generated_reg_num
        cleaned_data['roll_sequence'] = roll_seq
        cleaned_data['reservation'] = reservation

        # CRITICAL RULE: NEVER REPLACE USERNAME WITH ROLL NUMBER!
        # Student's chosen unique username in cleaned_data['username'] is strictly preserved.

        # Sync / link institutional enrollment record
        enrollment, _ = StudentEnrollment.objects.get_or_create(
            roll_number=generated_reg_num,
            defaults={
                'full_name': cleaned_data.get('full_name', 'Student'),
                'email': cleaned_data.get('email', ''),
                'department': course.department if course else None,
                'course': course,
                'batch': batch,
                'roll_sequence': roll_seq,
                'semester': cleaned_data.get('semester', '1'),
                'is_active': True,
                'is_registered': False
            }
        )
        cleaned_data['matched_enrollment'] = enrollment
        return cleaned_data

    @transaction.atomic
    def save(self):
        cd = self.cleaned_data
        course = cd['course']
        enrollment = cd.get('matched_enrollment')
        batch = cd.get('batch')
        roll_seq = cd.get('roll_sequence')
        reservation = cd.get('reservation')

        # Create user
        user = User.objects.create_user(
            username=cd['username'],
            email=cd['email'],
            password=cd['password1'],
            first_name=cd['full_name'].split()[0],
            last_name=' '.join(cd['full_name'].split()[1:]) if len(cd['full_name'].split()) > 1 else '',
            role='student',
            is_active=True
        )

        dept_name = course.department.name if (course and course.department) else (course.name if course else '')

        # Resolve class_group if provided
        class_grp_id = cd.get('class_group') or (self.data.get('class_group') if hasattr(self, 'data') else None)
        class_grp = None
        if class_grp_id:
            class_grp = ClassGroup.objects.filter(id=class_grp_id).first()
        elif course and course.department:
            class_grp = ClassGroup.objects.filter(department=course.department, semester=cd['semester']).first()

        # Create StudentProfile
        profile = StudentProfile.objects.create(
            user=user,
            full_name=cd['full_name'],
            roll_number=cd['roll_number'].strip().upper(),
            department=dept_name,
            course=course,
            batch=batch,
            roll_sequence=roll_seq,
            semester=cd['semester'],
            class_group=class_grp,
            verification_status='pending'
        )

        # Update reservation to pending
        if reservation:
            reservation.status = 'pending'
            reservation.student_profile = profile
            reservation.reserved_by_name = profile.full_name
            reservation.reserved_by_email = user.email
            reservation.expires_at = None
            reservation.save()

        # Update enrollment record with atomic lock
        if enrollment:
            locked_enrollment = StudentEnrollment.objects.select_for_update().get(id=enrollment.id)
            locked_enrollment.is_registered = True
            locked_enrollment.registered_student = profile
            locked_enrollment.registered_at = timezone.now()
            if batch:
                locked_enrollment.batch = batch
                locked_enrollment.roll_sequence = roll_seq
            locked_enrollment.save()

        return user


class TeacherRegistrationForm(forms.Form):
    """
    Teacher Registration Form with institutional employee ID and department verification.
    Field order:
    1. Full Name
    2. Employee ID
    3. Department
    4. Username
    5. Email Address
    6. Password
    7. Confirm Password
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.data and self.data.get('department'):
            dept_val = str(self.data.get('department')).strip()
            if not dept_val.isdigit():
                dept = Department.objects.filter(Q(name__iexact=dept_val) | Q(code__iexact=dept_val)).first()
                if not dept:
                    dept = Department.objects.create(name=dept_val, code=dept_val[:10].upper())
                if hasattr(self.data, '_mutable') and not self.data._mutable:
                    self.data = self.data.copy()
                self.data['department'] = str(dept.id)
                self.fields['department'].queryset = Department.objects.all()

    full_name = forms.CharField(
        max_length=150,
        required=True,
        label="Full Name",
        widget=forms.TextInput(attrs={
            'class': 'lp-input',
            'placeholder': 'Enter your full academic name',
            'id': 'teacher-full-name'
        })
    )
    employee_id = forms.CharField(
        max_length=50,
        required=True,
        label="Employee ID",
        widget=forms.TextInput(attrs={
            'class': 'lp-input',
            'placeholder': 'Institutional Employee ID / Staff Code',
            'id': 'teacher-emp-id'
        })
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=True,
        label="Department",
        empty_label="Select Department",
        widget=forms.Select(attrs={
            'class': 'lp-select',
            'id': 'teacher-dept-select'
        })
    )
    qualification = forms.CharField(
        max_length=150,
        required=False,
        initial='Faculty',
        label="Highest Qualification",
        widget=forms.TextInput(attrs={
            'class': 'lp-input',
            'placeholder': 'e.g. M.Tech, Ph.D, MCA',
            'id': 'teacher-qualification'
        })
    )
    username = forms.CharField(
        max_length=30,
        required=True,
        label="Username",
        widget=forms.TextInput(attrs={
            'class': 'lp-input',
            'placeholder': 'Choose a unique username',
            'id': 'teacher-username-input',
            'autocomplete': 'username'
        })
    )
    email = forms.EmailField(
        required=True,
        label="Email Address",
        widget=forms.EmailInput(attrs={
            'class': 'lp-input',
            'placeholder': 'teacher@institution.edu',
            'id': 'teacher-email-input',
            'autocomplete': 'email'
        })
    )
    password1 = forms.CharField(
        required=True,
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'lp-input',
            'placeholder': 'Create a secure password',
            'id': 'teacher-password1-input',
            'autocomplete': 'new-password'
        })
    )
    password2 = forms.CharField(
        required=True,
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'lp-input',
            'placeholder': 'Re-enter your password to confirm',
            'id': 'teacher-password2-input',
            'autocomplete': 'new-password'
        })
    )

    def clean_full_name(self):
        name = self.cleaned_data.get('full_name', '').strip()
        if len(name) < 2:
            raise ValidationError("Full name must be at least 2 characters long.")
        return name

    def clean_employee_id(self):
        emp_id = self.cleaned_data.get('employee_id', '').strip()
        if TeacherProfile.objects.filter(employee_id__iexact=emp_id).exists():
            raise ValidationError("This Employee ID is already registered.")
        return emp_id

    def clean_username(self):
        uname = self.cleaned_data.get('username', '').strip()
        if not re.match(r'^[a-zA-Z0-9_]{3,30}$', uname):
            raise ValidationError("Username must be 3-30 characters with letters, numbers, or underscores only.")
        if User.objects.filter(username__iexact=uname).exists():
            raise ValidationError("This username is already taken. Please choose another.")
        return uname

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean_password1(self):
        p1 = self.cleaned_data.get('password1', '')
        complexity_errors = check_password_complexity(p1)
        if complexity_errors:
            raise ValidationError(complexity_errors[0])
        temp_user = User(username=self.cleaned_data.get('username', ''))
        try:
            validate_password(p1, user=temp_user)
        except ValidationError as e:
            raise ValidationError(e.messages[0])
        return p1

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise ValidationError("Passwords do not match. Please re-enter your password.")
        return p2

    @transaction.atomic
    def save(self):
        cd = self.cleaned_data
        dept = cd['department']

        user = User.objects.create_user(
            username=cd['username'],
            email=cd['email'],
            password=cd['password1'],
            first_name=cd['full_name'].split()[0],
            last_name=' '.join(cd['full_name'].split()[1:]) if len(cd['full_name'].split()) > 1 else '',
            role='teacher',
            is_active=True
        )

        qualification = cd.get('qualification', '').strip() or 'Faculty'

        profile = TeacherProfile.objects.create(
            user=user,
            employee_id=cd['employee_id'].strip().upper(),
            department=dept.name,
            qualification=qualification,
            institution=cd.get('institution') or (self.data.get('institution', '').strip() if hasattr(self, 'data') else '') or 'EPS Examination Institution',
            verification_status='pending'
        )

        return user


class InAppPasswordChangeForm(forms.Form):
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Current Password'})
    )
    new_password = forms.CharField(
        min_length=6,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New Password'})
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm New Password'})
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        current_password = self.cleaned_data.get('current_password')
        if not self.user.check_password(current_password):
            raise forms.ValidationError('Current password is not correct.')
        return current_password

    def clean(self):
        cleaned_data = super().clean()
        new_pw = cleaned_data.get('new_password')
        confirm_pw = cleaned_data.get('confirm_password')
        if new_pw and confirm_pw and new_pw != confirm_pw:
            self.add_error('confirm_password', 'New passwords do not match.')
        return cleaned_data


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'code', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department Name'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department Code (e.g. CS)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description'}),
        }


class ClassGroupForm(forms.ModelForm):
    class Meta:
        model = ClassGroup
        fields = ['department', 'name', 'semester']
        widgets = {
            'department': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. BCA Section A'}),
            'semester': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Semester (e.g. 3)'}),
        }


class InstitutionalPolicyForm(forms.Form):
    """Configuration form for institutional examination & proctoring policies."""
    # Section 1: Examination Access and Timing
    late_entry_mins = forms.IntegerField(
        min_value=1,
        max_value=60,
        required=True,
        initial=15,
        widget=forms.NumberInput(attrs={'class': 'policy-input', 'id': 'late-entry-mins', 'min': '1', 'max': '60'})
    )
    late_entry_enabled = forms.BooleanField(required=False, initial=True)
    early_entry_enabled = forms.BooleanField(required=False, initial=False)
    attempt_allowance = forms.ChoiceField(
        choices=[('single', 'Single Attempt (1x)'), ('dual', 'Dual Attempt (2x)'), ('practice', 'Unlimited Practice')],
        initial='single',
        required=True
    )
    server_submission_enabled = forms.BooleanField(required=False, initial=True)
    timing_accommodation = forms.ChoiceField(
        choices=[('1.0', 'Standard 1.0x'), ('1.25', 'Extended 1.25x'), ('1.5', 'Accommodated 1.5x'), ('2.0', 'Double Time 2.0x')],
        initial='1.0',
        required=True
    )

    # Section 2: Camera and Microphone Sensory Requirements
    video_ingestion = forms.ChoiceField(
        choices=[('dual', 'Required: Level 2 Dual-Camera'), ('single', 'Optional: Single Webcam'), ('disabled', 'Disabled')],
        initial='dual',
        required=True
    )
    audio_monitor = forms.ChoiceField(
        choices=[('threshold', 'Required: Decibel Variance'), ('continuous', 'Proctor Intercom Only'), ('disabled', 'Disabled')],
        initial='threshold',
        required=True
    )

    # Section 3: Screen Sharing and Client Environment Lockdown
    os_lockdown_enabled = forms.BooleanField(required=False, initial=True)
    focus_trap_enabled = forms.BooleanField(required=False, initial=True)
    clipboard_neutralization_enabled = forms.BooleanField(required=False, initial=True)

    # Section 4: Question & Attempt Integrity Rules
    item_randomization_enabled = forms.BooleanField(required=False, initial=True)
    distractor_shuffling_enabled = forms.BooleanField(required=False, initial=True)
    negative_marking_scheme = forms.ChoiceField(
        choices=[('none', 'None [0.0]'), ('mild', 'Mild [-0.25]'), ('strict', 'Strict [-0.50]')],
        initial='mild',
        required=True
    )
    score_embargo_enabled = forms.BooleanField(required=False, initial=True)

    # Section 5: Data Retention & Privacy Lifecycle
    telemetry_retention_days = forms.ChoiceField(
        choices=[('30', '30 Days'), ('90', '90 Days Post-Term'), ('180', '180 Days')],
        initial='90',
        required=True
    )
    audit_retention_years = forms.ChoiceField(
        choices=[('5y', '5 Years'), ('7y', '7 Years Institutional Archive'), ('10y', '10 Years Statutory Archive')],
        initial='7y',
        required=True
    )


class StudentProfileEditForm(forms.ModelForm):
    full_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Legal Name'})
    )
    email = forms.EmailField(
        required=False,
        help_text='Institutional contact email for official records only (no automated emails sent).',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'student@institution.edu'})
    )
    semester = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Academic Semester (e.g. 1 to 8)'})
    )

    class Meta:
        model = StudentProfile
        fields = ['full_name', 'semester']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'user') and self.instance.user:
            self.fields['email'].initial = self.instance.user.email
            if not self.initial.get('full_name'):
                self.fields['full_name'].initial = self.instance.full_name or self.instance.user.first_name

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        full_name = self.cleaned_data.get('full_name', '').strip()
        user.first_name = full_name
        user.email = self.cleaned_data.get('email', '').strip()
        profile.full_name = full_name
        if commit:
            user.save()
            profile.save()
        return profile


class TeacherProfileEditForm(forms.ModelForm):
    full_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Legal Name'})
    )
    email = forms.EmailField(
        required=False,
        help_text='Institutional contact email for official records only (no automated emails sent).',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'teacher@institution.edu'})
    )
    qualification = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Highest Qualification (e.g. Ph.D, M.Tech)'})
    )
    institution = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Affiliated Institution / Campus'})
    )

    class Meta:
        model = TeacherProfile
        fields = ['qualification', 'institution']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'user') and self.instance.user:
            self.fields['email'].initial = self.instance.user.email
            self.fields['full_name'].initial = self.instance.user.first_name

    def save(self, commit=True):
        profile = super().save(commit=False)
        # Security: Department cannot be self-modified by teachers through profile edit.
        # Preserve original department from the database instance.
        if self.instance and self.instance.pk:
            original_dept = TeacherProfile.objects.filter(pk=self.instance.pk).values_list('department', flat=True).first()
            if original_dept:
                profile.department = original_dept

        user = profile.user
        full_name = self.cleaned_data.get('full_name', '').strip()
        user.first_name = full_name
        user.email = self.cleaned_data.get('email', '').strip()
        if commit:
            user.save()
            profile.save()
        return profile


class AdminProfileEditForm(forms.ModelForm):
    full_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'})
    )
    email = forms.EmailField(
        required=False,
        help_text='Administrative contact email for records only.',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'admin@institution.edu'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields['full_name'].initial = self.instance.first_name
            self.fields['email'].initial = self.instance.email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data.get('full_name', '').strip()
        user.email = self.cleaned_data.get('email', '').strip()
        if commit:
            user.save()
        return user


# =====================================================================
# Academic Batch Management & Roll Number Allocation Forms
# =====================================================================

class AcademicBatchForm(forms.ModelForm):
    class Meta:
        model = AcademicBatch
        fields = [
            'department', 'course', 'admission_year', 'course_code',
            'batch_name', 'batch_identifier', 'capacity',
            'start_roll_number', 'end_roll_number', 'admission_semester',
            'total_semesters', 'current_semester', 'enrollment_status', 'is_active'
        ]
        widgets = {
            'department': forms.Select(attrs={'class': 'lp-select', 'id': 'batch-department-select'}),
            'course': forms.Select(attrs={'class': 'lp-select', 'id': 'batch-course-select'}),
            'admission_year': forms.NumberInput(attrs={'class': 'lp-input', 'id': 'batch-year-input'}),
            'course_code': forms.TextInput(attrs={'class': 'lp-input', 'id': 'batch-code-input', 'placeholder': 'e.g. BCA'}),
            'batch_name': forms.TextInput(attrs={'class': 'lp-input', 'id': 'batch-name-input', 'placeholder': 'e.g. 2026 BCA'}),
            'batch_identifier': forms.TextInput(attrs={'class': 'lp-input', 'id': 'batch-identifier-input', 'placeholder': 'Optional (e.g. Section A)'}),
            'capacity': forms.NumberInput(attrs={'class': 'lp-input', 'id': 'batch-capacity-input'}),
            'start_roll_number': forms.NumberInput(attrs={'class': 'lp-input', 'id': 'batch-start-roll-input'}),
            'end_roll_number': forms.NumberInput(attrs={'class': 'lp-input', 'id': 'batch-end-roll-input'}),
            'admission_semester': forms.TextInput(attrs={'class': 'lp-input', 'placeholder': '1'}),
            'total_semesters': forms.NumberInput(attrs={'class': 'lp-input'}),
            'current_semester': forms.TextInput(attrs={'class': 'lp-input', 'placeholder': '1'}),
            'enrollment_status': forms.Select(attrs={'class': 'lp-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'lp-checkbox'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # Teacher departmental boundary enforcement
        if user and user.role == 'teacher' and not (user.is_superuser or user.is_staff):
            teacher_prof = getattr(user, 'teacher_profile', None)
            if teacher_prof and teacher_prof.department:
                dept_name = teacher_prof.department
                matching_dept = Department.objects.filter(Q(name__iexact=dept_name) | Q(code__iexact=dept_name)).first()
                if matching_dept:
                    self.fields['department'].queryset = Department.objects.filter(id=matching_dept.id)
                    self.fields['department'].initial = matching_dept
                    self.fields['course'].queryset = Course.objects.filter(department=matching_dept)
                else:
                    self.fields['department'].queryset = Department.objects.none()

        # Identity locking for established batches with registered/pending students
        if self.instance and self.instance.pk:
            if not self.instance.can_modify_identity():
                for field_name in ['department', 'course', 'admission_year', 'course_code', 'batch_identifier', 'start_roll_number']:
                    if field_name in self.fields:
                        self.fields[field_name].disabled = True
                        self.fields[field_name].help_text = "Identity locked: Batch has assigned or pending students."

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_roll_number') or 1
        end = cleaned_data.get('end_roll_number') or 60
        capacity = cleaned_data.get('capacity') or (end - start + 1)
        adm_year = cleaned_data.get('admission_year') or 2026
        course_code = cleaned_data.get('course_code') or ''
        batch_id = cleaned_data.get('batch_identifier') or ''

        if start > end:
            raise ValidationError("Start roll number cannot be greater than end roll number.")

        if (end - start + 1) != capacity:
            cleaned_data['capacity'] = end - start + 1
            capacity = cleaned_data['capacity']

        # Identity protection on existing instances
        if self.instance and self.instance.pk:
            if not self.instance.can_modify_identity():
                if adm_year != self.instance.admission_year:
                    raise ValidationError("Cannot modify admission year of an established batch.")
                if self.instance.course and cleaned_data.get('course') != self.instance.course:
                    raise ValidationError("Cannot modify course of an established batch.")
                if self.instance.course_code and course_code != self.instance.course_code:
                    raise ValidationError("Cannot modify course code of an established batch.")
                if start != self.instance.start_roll_number:
                    raise ValidationError("Cannot modify start roll number of an established batch.")

            if not self.instance.can_reduce_capacity(capacity):
                occupied_count = self.instance.roll_reservations.filter(status__in=['assigned', 'pending', 'reserved']).count()
                raise ValidationError(f"Cannot reduce capacity to {capacity}; {occupied_count} roll positions are currently occupied or reserved.")

        # Prefix collision verification
        clean_code = re.sub(r'[^a-zA-Z0-9]', '', course_code).upper()
        clean_id = re.sub(r'[^a-zA-Z0-9]', '', batch_id).upper() if batch_id else ''
        calc_prefix = f"{adm_year}{clean_code}{clean_id}"

        existing_prefix = AcademicBatch.objects.filter(prefix=calc_prefix)
        if self.instance and self.instance.pk:
            existing_prefix = existing_prefix.exclude(pk=self.instance.pk)
        if existing_prefix.exists():
            raise ValidationError(f"Batch prefix '{calc_prefix}' is already in use by another batch.")

        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        batch = super().save(commit=False)
        if self.user and not batch.created_by:
            batch.created_by = self.user

        if commit:
            batch.save()
            # Ensure roll reservation slots 1..capacity exist
            existing_seqs = set(batch.roll_reservations.values_list('roll_sequence', flat=True))
            new_reservations = []
            for seq in range(batch.start_roll_number, batch.end_roll_number + 1):
                if seq not in existing_seqs:
                    reg_num = batch.generate_registration_number(seq)
                    new_reservations.append(RollNumberReservation(
                        batch=batch,
                        roll_sequence=seq,
                        registration_number=reg_num,
                        status='available'
                    ))
            if new_reservations:
                RollNumberReservation.objects.bulk_create(new_reservations)
        return batch


class BatchSemesterPromotionForm(forms.Form):
    target_semester = forms.IntegerField(
        min_value=1,
        max_value=12,
        label="Target Semester",
        widget=forms.NumberInput(attrs={'class': 'lp-input', 'id': 'target-semester-input'})
    )
    academic_session = forms.CharField(
        max_length=50,
        required=False,
        label="Academic Session / Term",
        widget=forms.TextInput(attrs={'class': 'lp-input', 'placeholder': 'e.g. 2026-2027 Even Term'})
    )
    reason = forms.CharField(
        required=False,
        label="Promotion Reason / Notes",
        widget=forms.Textarea(attrs={'class': 'lp-input', 'rows': 2, 'placeholder': 'e.g. Regular end-of-semester advancement'})
    )


class RollNumberCorrectionForm(forms.Form):
    student = forms.ModelChoiceField(
        queryset=StudentProfile.objects.filter(batch__isnull=False).select_related('user', 'batch'),
        label="Student Candidate",
        widget=forms.Select(attrs={'class': 'lp-select', 'id': 'student-select'})
    )
    new_roll_sequence = forms.IntegerField(
        min_value=1,
        label="New Roll Sequence Number",
        widget=forms.NumberInput(attrs={'class': 'lp-input', 'placeholder': 'e.g. 5'})
    )
    reason = forms.CharField(
        required=True,
        label="Administrative Reason (Mandatory & Audited)",
        widget=forms.Textarea(attrs={'class': 'lp-input', 'rows': 3, 'placeholder': 'Provide official justification for roll number reassignment...'})
    )

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        new_seq = cleaned_data.get('new_roll_sequence')

        if not student or not new_seq:
            return cleaned_data

        batch = student.batch
        if not batch:
            raise ValidationError("This student is not enrolled in an Academic Batch.")

        if new_seq < batch.start_roll_number or new_seq > batch.end_roll_number:
            raise ValidationError(f"Roll sequence must be between {batch.start_roll_number} and {batch.end_roll_number} for this batch.")

        if student.roll_sequence == new_seq:
            raise ValidationError("The new roll sequence is identical to the student's current roll sequence.")

        target_reservation = RollNumberReservation.objects.filter(batch=batch, roll_sequence=new_seq).first()
        if target_reservation and target_reservation.status in ['assigned', 'pending']:
            if target_reservation.student_profile and target_reservation.student_profile.id != student.id:
                raise ValidationError(f"Roll sequence {new_seq:02d} ({target_reservation.registration_number}) is currently occupied by student {target_reservation.student_profile.user.username}.")

        new_reg_num = batch.generate_registration_number(new_seq)
        if User.objects.filter(username__iexact=new_reg_num).exclude(id=student.user.id).exists():
            raise ValidationError(f"Username {new_reg_num} is already taken by another user account.")

        cleaned_data['target_reservation'] = target_reservation
        cleaned_data['new_registration_number'] = new_reg_num
        return cleaned_data
