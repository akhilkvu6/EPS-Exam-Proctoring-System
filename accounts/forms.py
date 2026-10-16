from django import forms
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm
from django.contrib.auth import authenticate
from .models import User, TeacherProfile, StudentProfile, Department, ClassGroup


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username or ID',
            'autocomplete': 'username',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password'
        })
    )


class StudentRegistrationForm(UserCreationForm):
    full_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'})
    )
    email = forms.EmailField(
        required=False,
        help_text='Institutional email for records only (no automated emails will be sent).',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'student@institution.edu'})
    )
    roll_number = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Register / Roll Number'})
    )
    department = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department (e.g. Computer Science)'})
    )
    semester = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Semester (e.g. 1 to 8)'})
    )

    class Meta:
        model = User
        fields = [
            'username',
            'full_name',
            'email',
            'password1',
            'password2',
            'roll_number',
            'department',
            'semester',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ['username', 'password1', 'password2']:
            if field in self.fields:
                self.fields[field].widget.attrs['class'] = 'form-control'

    def clean_roll_number(self):
        roll_number = self.cleaned_data.get('roll_number', '').strip()
        if StudentProfile.objects.filter(roll_number__iexact=roll_number).exists():
            raise forms.ValidationError('A student with this roll/register number is already registered.')
        return roll_number

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data.get('full_name', '')
        user.email = self.cleaned_data.get('email', '')
        user.role = 'student'

        if commit:
            user.save()
            # Try to associate with matching Department & ClassGroup if existing
            dept_name = self.cleaned_data['department'].strip()
            dept = Department.objects.filter(name__iexact=dept_name).first()
            class_grp = None
            if dept:
                class_grp = ClassGroup.objects.filter(
                    department=dept,
                    semester=self.cleaned_data['semester'].strip()
                ).first()

            StudentProfile.objects.create(
                user=user,
                full_name=self.cleaned_data['full_name'],
                roll_number=self.cleaned_data['roll_number'],
                department=self.cleaned_data['department'],
                semester=self.cleaned_data['semester'],
                class_group=class_grp,
                verification_status='pending'
            )

        return user


class TeacherRegistrationForm(UserCreationForm):
    full_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'})
    )
    email = forms.EmailField(
        required=False,
        help_text='Institutional email for records only (no automated emails will be sent).',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'teacher@institution.edu'})
    )
    employee_id = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Employee ID / Staff Code'})
    )
    department = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department'})
    )
    qualification = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Highest Qualification (e.g. MCA, M.Tech, Ph.D)'})
    )
    institution = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Institution / College Name'})
    )

    class Meta:
        model = User
        fields = [
            'username',
            'full_name',
            'email',
            'password1',
            'password2',
            'employee_id',
            'department',
            'qualification',
            'institution',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ['username', 'password1', 'password2']:
            if field in self.fields:
                self.fields[field].widget.attrs['class'] = 'form-control'

    def clean_employee_id(self):
        emp_id = self.cleaned_data.get('employee_id', '').strip()
        if TeacherProfile.objects.filter(employee_id__iexact=emp_id).exists():
            raise forms.ValidationError('A teacher with this employee ID is already registered.')
        return emp_id

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data.get('full_name', '')
        user.email = self.cleaned_data.get('email', '')
        user.role = 'teacher'

        if commit:
            user.save()
            TeacherProfile.objects.create(
                user=user,
                employee_id=self.cleaned_data['employee_id'],
                department=self.cleaned_data['department'],
                qualification=self.cleaned_data['qualification'],
                institution=self.cleaned_data.get('institution', ''),
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
    department = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Academic Department'})
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
        fields = ['department', 'qualification', 'institution']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'user') and self.instance.user:
            self.fields['email'].initial = self.instance.user.email
            self.fields['full_name'].initial = self.instance.user.first_name

    def save(self, commit=True):
        profile = super().save(commit=False)
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