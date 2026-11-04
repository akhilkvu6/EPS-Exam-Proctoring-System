import csv
import io
import os
import re
from datetime import timedelta
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_GET
from django.utils import timezone
from django.db import transaction, connection
from django.db.models import Q, Count, Avg, Max, Min
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from exams.models import Exam, ExamAttempt, ProctoringIncident, Subject
from results.models import Result
from .models import (
    User, TeacherProfile, StudentProfile, Department, Course, StudentEnrollment,
    ClassGroup, Notification, ApprovalRecord, AuditLog,
    AcademicBatch, RollNumberReservation, StudentSemesterHistory
)
from .forms import (
    LoginForm, StudentRegistrationForm, TeacherRegistrationForm,
    InAppPasswordChangeForm, DepartmentForm, ClassGroupForm, InstitutionalPolicyForm,
    StudentProfileEditForm, TeacherProfileEditForm, AdminProfileEditForm,
    AcademicBatchForm, BatchSemesterPromotionForm, RollNumberCorrectionForm
)
from .policies import (
    get_institutional_policies, save_institutional_policies,
    get_policy_metadata, export_policy_manifest
)
from .decorators import student_required, teacher_required, admin_required, log_audit, send_notification


def home(request):
    """Institutional landing page."""
    return render(request, 'home.html')


def design_system(request):
    """EPS Design Foundation (EDF) interactive showcase and design token playground."""
    return render(request, 'design.html')


def common_login(request):
    """
    Unified common login for Students, Teachers, and Administrators.
    Auto-detects role and redirects to the appropriate portal.
    """
    if request.user.is_authenticated:
        if request.user.role == 'student':
            if hasattr(request.user, 'student_profile') and request.user.student_profile.verification_status == 'approved':
                return redirect('student_dashboard')
            return redirect('account_status')
        elif request.user.role == 'teacher':
            if hasattr(request.user, 'teacher_profile') and request.user.teacher_profile.verification_status == 'approved':
                return redirect('teacher_dashboard')
            return redirect('account_status')
        elif request.user.role == 'admin' or request.user.is_superuser or request.user.is_staff:
            return redirect('admin_dashboard')
        return redirect('home')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data.get('authenticated_user')
            if not user:
                raw_identifier = form.cleaned_data.get('username', '').strip()
                password = form.cleaned_data.get('password')
                user = authenticate(request, username=raw_identifier, password=password)

            if user is not None:
                if not user.is_active:
                    form.add_error(None, 'This account has been deactivated by administration.')
                    return render(request, 'accounts/login.html', {'form': form})

                status = user.get_status()
                if status == 'suspended':
                    form.add_error(None, 'Your account has been suspended. Please contact the administrator.')
                    return render(request, 'accounts/login.html', {'form': form})

                login(request, user)
                if form.cleaned_data.get('remember_me', False) or request.POST.get('remember_device'):
                    request.session.set_expiry(1209600)  # 2 weeks
                else:
                    request.session.set_expiry(0)  # browser session

                log_audit(user, 'USER_LOGIN', user, request, f"Successful login as {user.role}")

                # Role-based redirection
                if user.role == 'student':
                    if hasattr(user, 'student_profile') and user.student_profile.verification_status == 'approved':
                        return redirect('student_dashboard')
                    return redirect('account_status')

                elif user.role == 'teacher':
                    if hasattr(user, 'teacher_profile') and user.teacher_profile.verification_status == 'approved':
                        return redirect('teacher_dashboard')
                    return redirect('account_status')

                elif user.role == 'admin' or user.is_superuser or user.is_staff:
                    return redirect('admin_dashboard')

                return redirect('home')
        else:
            raw_identifier = request.POST.get('username', '').strip()
            log_audit(None, 'FAILED_LOGIN_ATTEMPT', None, request, f"Failed attempt for identifier: {raw_identifier}")
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def student_login(request):
    """Legacy redirect to common login."""
    return redirect('common_login')


def teacher_login(request):
    """Legacy redirect to common login."""
    return redirect('common_login')


def user_logout(request):
    """Secure logout view with audit logging."""
    if request.user.is_authenticated:
        log_audit(request.user, 'USER_LOGOUT', request.user, request, "User logged out")
    logout(request)
    messages.info(request, 'You have been securely logged out.')
    return redirect('common_login')


def central_register(request):
    """
    Central registration flow: One entry point, two roles (Student and Teacher).
    Role selection cards for choosing between Student and Teacher,
    backed by real database validation and institution enrollment verification.
    """
    if request.user.is_authenticated:
        return redirect('home')

    raw_role = request.POST.get("role") or request.GET.get("role", "")
    role_locked = bool(raw_role in ("student", "teacher"))
    active_role = raw_role if role_locked else ""

    student_form = StudentRegistrationForm()
    teacher_form = TeacherRegistrationForm()
    form_errors = []

    if request.method == 'POST':
        submitted_role = request.POST.get('role', 'student')
        active_role = submitted_role
        role_locked = True

        if submitted_role == 'student':
            student_form = StudentRegistrationForm(request.POST)
            if student_form.is_valid():
                user = student_form.save()
                log_audit(user, 'STUDENT_REGISTERED', user, request, f"Student registered: {user.username} (Roll: {user.student_profile.roll_number})")

                # In-app notification to department faculty
                teachers = User.objects.filter(role='teacher', teacher_profile__verification_status='approved')
                if hasattr(user, 'student_profile') and user.student_profile.department:
                    dept_teachers = teachers.filter(teacher_profile__department__iexact=user.student_profile.department)
                    target_teachers = dept_teachers if dept_teachers.exists() else teachers
                else:
                    target_teachers = teachers

                for t in target_teachers:
                    send_notification(
                        recipient=t,
                        title="New Student Registration Pending",
                        message=f"Student {user.get_full_name() or user.username} (Roll: {user.student_profile.roll_number}) has registered and requires approval.",
                        notification_type="registration",
                        link="/accounts/teacher/student-approvals/"
                    )
                return redirect('registration_success')
            else:
                for field, err_list in student_form.errors.items():
                    for err in err_list:
                        prefix = f"{student_form[field].label}: " if field != '__all__' and field in student_form.fields else ""
                        form_errors.append(f"{prefix}{err}")

        elif submitted_role == 'teacher':
            teacher_form = TeacherRegistrationForm(request.POST)
            if teacher_form.is_valid():
                user = teacher_form.save()
                log_audit(user, 'TEACHER_REGISTERED', user, request, f"Teacher registered: {user.username} (EmpID: {user.teacher_profile.employee_id})")

                # In-app notification to administrators
                admins = User.objects.filter(Q(role='admin') | Q(is_superuser=True) | Q(is_staff=True))
                for a in admins:
                    send_notification(
                        recipient=a,
                        title="New Teacher Verification Request",
                        message=f"Teacher {user.get_full_name() or user.username} (Dept: {user.teacher_profile.department}) has registered and requires administrator approval.",
                        notification_type="registration",
                        link="/accounts/admin/teacher-approvals/"
                    )
                return redirect('registration_success')
            else:
                for field, err_list in teacher_form.errors.items():
                    for err in err_list:
                        prefix = f"{teacher_form[field].label}: " if field != '__all__' and field in teacher_form.fields else ""
                        form_errors.append(f"{prefix}{err}")

    courses = Course.objects.all().order_by('name')
    departments = Department.objects.all().order_by('name')
    batches = AcademicBatch.objects.filter(is_active=True, enrollment_status='open').select_related('department', 'course').order_by('-admission_year', 'course_code', 'batch_name')

    return render(request, 'accounts/register.html', {
        'student_form': student_form,
        'teacher_form': teacher_form,
        'active_role': active_role,
        'role_locked': role_locked,
        'form_errors': form_errors,
        'courses': courses,
        'departments': departments,
        'batches': batches,
    })


def registration_success(request):
    """In-app registration confirmation with pending review notice."""
    return render(request, 'accounts/registration_success.html')


def student_register(request):
    """Direct / backwards-compatible endpoint for student registration."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            log_audit(user, 'STUDENT_REGISTERED', user, request, f"Student registration: {user.username}")

            # Notify teachers of this department or all teachers
            teachers = User.objects.filter(role='teacher', teacher_profile__verification_status='approved')
            dept_teachers = teachers.filter(teacher_profile__department__iexact=user.student_profile.department)
            target_teachers = dept_teachers if dept_teachers.exists() else teachers

            for t in target_teachers:
                send_notification(
                    recipient=t,
                    title="New Student Registration Pending",
                    message=f"Student {user.get_full_name() or user.username} (Roll: {user.student_profile.roll_number}) has registered and is awaiting your approval.",
                    notification_type="registration",
                    link="/accounts/teacher/dashboard/"
                )

            return redirect('student_registration_success')
        else:
            return render(request, 'accounts/student_register.html', {'form': form})
    return redirect('/accounts/register/?role=student')


def student_registration_success(request):
    return render(request, 'accounts/student_registration_success.html')


def teacher_register(request):
    """Direct / backwards-compatible endpoint for teacher registration."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = TeacherRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            log_audit(user, 'TEACHER_REGISTERED', user, request, f"Teacher registration: {user.username}")

            # Notify all administrators
            admins = User.objects.filter(Q(role='admin') | Q(is_superuser=True) | Q(is_staff=True))
            for admin_user in admins:
                send_notification(
                    recipient=admin_user,
                    title="New Teacher Verification Request",
                    message=f"Teacher {user.get_full_name() or user.username} (Dept: {user.teacher_profile.department}) has registered and requires administrator approval.",
                    notification_type="registration",
                    link="/accounts/admin/dashboard/"
                )

            return redirect('teacher_registration_success')
        else:
            return render(request, 'accounts/teacher_register.html', {'form': form})
    return redirect('/accounts/register/?role=teacher')


def teacher_registration_success(request):
    return render(request, 'accounts/teacher_registration_success.html')


def account_status(request):
    """Status screen explaining Pending, Rejected, or Suspended states."""
    if not request.user.is_authenticated:
        return redirect('common_login')

    user = request.user
    role = user.role
    profile = None
    status = 'pending'
    rejection_reason = ''
    reviewed_at = None

    if role == 'teacher' and hasattr(user, 'teacher_profile'):
        profile = user.teacher_profile
        status = profile.verification_status
        rejection_reason = profile.rejection_reason
        reviewed_at = profile.reviewed_at
    elif role == 'student' and hasattr(user, 'student_profile'):
        profile = user.student_profile
        status = profile.verification_status
        rejection_reason = profile.rejection_reason
        reviewed_at = profile.reviewed_at

    # If already approved, redirect to portal
    if status == 'approved':
        if role == 'student':
            return redirect('student_dashboard')
        elif role == 'teacher':
            return redirect('teacher_dashboard')
        elif role == 'admin':
            return redirect('admin_dashboard')

    context = {
        'status': status,
        'role': role,
        'profile': profile,
        'rejection_reason': rejection_reason,
        'reviewed_at': reviewed_at,
    }
    return render(request, 'accounts/account_status.html', context)


@student_required
def student_dashboard(request):
    """Personalized student dashboard with real academic context, exams, attempts, and scorecard."""
    student = request.user
    prof = student.student_profile
    now = timezone.now()

    # Query assigned published exams
    query = Q(status='published') & (
        Q(assigned_students=student) |
        (Q(assigned_classes=prof.class_group) if prof.class_group else Q()) |
        (Q(assigned_classes__isnull=True, assigned_students__isnull=True, subject__department__name__iexact=prof.department))
    )
    assigned_exams = Exam.objects.filter(query).distinct().select_related('subject', 'created_by')

    # Student's attempts
    attempts = ExamAttempt.objects.filter(student=student).select_related('exam')
    attempted_exam_ids = set(attempts.values_list('exam_id', flat=True))
    submitted_attempts = attempts.filter(status__in=['submitted', 'auto_submitted'])

    available_exams = []
    scheduled_exams = []
    past_exams = []

    for ex in assigned_exams:
        if ex.id in attempted_exam_ids:
            past_exams.append(ex)
        elif ex.start_time <= now <= ex.end_time:
            available_exams.append(ex)
        elif now < ex.start_time:
            scheduled_exams.append(ex)
        else:
            past_exams.append(ex)

    # Published results
    published_results = Result.objects.filter(student=student, is_published=True).select_related('exam')
    avg_score = published_results.aggregate(Avg('percentage'))['percentage__avg']
    avg_percentage = round(avg_score, 1) if avg_score is not None else None

    # GPA conversion (4.0 scale)
    gpa = round(float(avg_percentage) / 25.0, 2) if avg_percentage is not None else "N/A"

    next_exam = scheduled_exams[0] if scheduled_exams else (available_exams[0] if available_exams else None)
    recent_notifications = student.notifications.all()[:5]

    context = {
        'profile': prof,
        'assigned_exams': assigned_exams,
        'available_exams': available_exams,
        'scheduled_exams': scheduled_exams,
        'past_exams': past_exams,
        'available_count': len(available_exams),
        'scheduled_count': len(scheduled_exams),
        'completed_count': submitted_attempts.count(),
        'published_results': published_results,
        'published_count': published_results.count(),
        'avg_percentage': avg_percentage,
        'gpa': gpa,
        'next_exam': next_exam,
        'recent_notifications': recent_notifications,
        'now': now,
    }
    return render(request, 'accounts/student_dashboard.html', context)


@teacher_required
def teacher_dashboard(request):
    """Teacher dashboard with student approval queue, examination overview, and grading queue."""
    teacher_profile = request.user.teacher_profile
    dept = teacher_profile.department
    assigned_classes = teacher_profile.assigned_classes.all()
    now = timezone.now()

    dept_query = (
        Q(department__iexact=dept) |
        Q(course__department__name__iexact=dept) |
        Q(course__department__code__iexact=dept) |
        Q(class_group__department__name__iexact=dept) |
        Q(class_group__department__code__iexact=dept)
    )

    if assigned_classes.exists():
        pending_students = StudentProfile.objects.filter(
            Q(class_group__in=assigned_classes) | dept_query,
            verification_status='pending'
        ).select_related('user', 'class_group', 'course')
        approved_students = StudentProfile.objects.filter(
            Q(class_group__in=assigned_classes) | dept_query,
            verification_status='approved'
        ).select_related('user', 'class_group', 'course')
    else:
        pending_students = StudentProfile.objects.filter(
            dept_query,
            verification_status='pending'
        ).select_related('user', 'class_group', 'course')
        approved_students = StudentProfile.objects.filter(
            dept_query,
            verification_status='approved'
        ).select_related('user', 'class_group', 'course')

    # Search filter on approved students
    q = request.GET.get('q', '').strip()
    if q:
        approved_students = approved_students.filter(
            Q(user__username__icontains=q) |
            Q(full_name__icontains=q) |
            Q(roll_number__icontains=q)
        )

    # Teacher's examinations
    exams = Exam.objects.filter(
        Q(created_by=request.user) | Q(subject__department__name__iexact=dept)
    ).select_related('subject', 'created_by').prefetch_related('attempts', 'exam_questions')

    scheduled_exams = [e for e in exams if e.status == 'published' and e.start_time > now]
    active_exams = [e for e in exams if e.status == 'published' and e.start_time <= now <= e.end_time]
    next_exam = scheduled_exams[0] if scheduled_exams else (active_exams[0] if active_exams else None)

    # Pending grading submissions
    pending_grading_count = Result.objects.filter(
        exam__in=exams, grading_status='pending_manual'
    ).count()

    # Proctoring incidents awaiting review
    flagged_incidents_count = ProctoringIncident.objects.filter(
        attempt__exam__in=exams, review_status='unreviewed'
    ).count()

    recent_notifications = request.user.notifications.all()[:5]

    context = {
        'teacher_profile': teacher_profile,
        'pending_students': pending_students,
        'approved_students': approved_students,
        'pending_count': pending_students.count(),
        'approved_count': approved_students.count(),
        'exams': exams,
        'scheduled_count': len(scheduled_exams),
        'active_count': len(active_exams),
        'next_exam': next_exam,
        'pending_grading_count': pending_grading_count,
        'flagged_incidents_count': flagged_incidents_count,
        'recent_notifications': recent_notifications,
        'search_query': q,
        'now': now,
    }
    return render(request, 'accounts/teacher_dashboard.html', context)


@teacher_required
def review_student(request, student_id):
    """
    Teacher action to approve or reject a student application.
    Enforces strict departmental boundary validation: teachers may only review
    students belonging to their own assigned department.
    """
    student = get_object_or_404(StudentProfile, id=student_id)
    teacher = request.user

    # Administrators and superusers retain global review authority
    is_admin = teacher.role == 'admin' or teacher.is_superuser or teacher.is_staff

    if not is_admin:
        teacher_prof = getattr(teacher, 'teacher_profile', None)
        teacher_dept = (teacher_prof.department or '').strip().lower() if teacher_prof else ''
        student_dept = (student.department or '').strip().lower()

        # Unassigned departments cannot be verified or matched
        if not teacher_dept or not student_dept:
            messages.error(request, 'Access denied: Department authorization could not be verified.')
            return HttpResponseForbidden('Access denied: You are not authorized to review this student.')

        # Department match check (by department name, linked class group, or course department)
        dept_match = (teacher_dept == student_dept)
        if not dept_match and student.class_group and student.class_group.department:
            class_dept_name = student.class_group.department.name.strip().lower()
            class_dept_code = student.class_group.department.code.strip().lower()
            if teacher_dept in (class_dept_name, class_dept_code):
                dept_match = True
        if not dept_match and student.course and student.course.department:
            c_dept_name = student.course.department.name.strip().lower()
            c_dept_code = student.course.department.code.strip().lower()
            if teacher_dept in (c_dept_name, c_dept_code):
                dept_match = True

        if not dept_match:
            messages.error(request, 'Access denied: You can only review student applicants in your own department.')
            return HttpResponseForbidden('Access denied: You are not authorized to review students outside your assigned department.')

    if request.method == 'POST':
        action = request.POST.get('action')
        reason = request.POST.get('reason', '').strip()

        if action == 'approve':
            student.verification_status = 'approved'
            student.reviewed_by = teacher
            student.reviewed_at = timezone.now()
            student.rejection_reason = ''
            student.save()

            # Batch Roll Reservation transition: pending -> assigned
            if student.batch and student.roll_sequence:
                res = RollNumberReservation.objects.filter(batch=student.batch, roll_sequence=student.roll_sequence).first()
                if res:
                    res.status = 'assigned'
                    res.student_profile = student
                    res.expires_at = None
                    res.save()
            student.user.is_active = True
            student.user.save()

            ApprovalRecord.objects.create(
                applicant=student.user,
                reviewed_by=teacher,
                role='student',
                decision='approved',
                reason=reason
            )
            log_audit(teacher, 'STUDENT_APPROVED', student.user, request, f"Approved by teacher {teacher.username}")

            send_notification(
                recipient=student.user,
                title="Account Registration Approved",
                message=f"Congratulations! Your student account has been approved by Prof. {teacher.get_full_name() or teacher.username}. You may now access all student portal features and examinations.",
                notification_type="approval",
                link="/accounts/student/dashboard/"
            )
            messages.success(request, f"Student {student.user.username} has been successfully approved.")

        elif action == 'reject':
            student.verification_status = 'rejected'
            student.reviewed_by = teacher
            student.reviewed_at = timezone.now()
            student.rejection_reason = reason or 'Application rejected by department teacher.'
            student.save()

            # Batch Roll Reservation transition: release reservation
            if student.batch and student.roll_sequence:
                res = RollNumberReservation.objects.filter(batch=student.batch, roll_sequence=student.roll_sequence).first()
                if res:
                    res.status = 'released'
                    res.student_profile = None
                    res.session_key = ''
                    res.reserved_by_email = ''
                    res.reserved_by_name = ''
                    res.expires_at = None
                    res.save()

            ApprovalRecord.objects.create(
                applicant=student.user,
                reviewed_by=teacher,
                role='student',
                decision='rejected',
                reason=student.rejection_reason
            )
            log_audit(teacher, 'STUDENT_REJECTED', student.user, request, f"Rejected by teacher {teacher.username}: {student.rejection_reason}")

            send_notification(
                recipient=student.user,
                title="Account Registration Not Approved",
                message=f"Your student registration was rejected. Reason: {student.rejection_reason}",
                notification_type="approval",
                link="/accounts/status/"
            )
            messages.warning(request, f"Student {student.user.username} has been rejected.")

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or ''
    if 'dashboard' in str(next_url):
        return redirect('teacher_dashboard')
    return redirect('teacher_student_approvals')


@teacher_required
def teacher_student_approvals(request):
    """
    Teacher queue to review and approve/reject pending student applicants.
    Strictly isolated to students within the teacher's department.
    """
    teacher_prof = getattr(request.user, 'teacher_profile', None)
    dept = (teacher_prof.department or '').strip() if teacher_prof else ''

    if not dept:
        students_list = StudentProfile.objects.none()
    else:
        pending_students = StudentProfile.objects.filter(verification_status='pending').select_related('user', 'class_group', 'course', 'course__department')
        # Filter strictly within the teacher's department
        students_list = pending_students.filter(
            Q(department__iexact=dept) |
            Q(course__department__name__iexact=dept) |
            Q(course__department__code__iexact=dept) |
            Q(class_group__department__name__iexact=dept) |
            Q(class_group__department__code__iexact=dept)
        )

    q = request.GET.get('q', '').strip()
    if q and students_list.exists():
        students_list = students_list.filter(
            Q(full_name__icontains=q) |
            Q(roll_number__icontains=q) |
            Q(user__username__icontains=q) |
            Q(user__email__icontains=q)
        )

    return render(request, 'accounts/student_approvals.html', {
        'pending_students': students_list,
        'q': q,
        'teacher_department': dept,
        'total_pending': students_list.count(),
    })


@teacher_required
def teacher_students(request):
    """
    Teacher student roster: view approved students in teacher's department or assigned classes.
    Supports search (name, roll, username), filter by semester/class, and assigning a student to a class group.
    """
    teacher_prof = request.user.teacher_profile
    dept = teacher_prof.department
    assigned_classes = teacher_prof.assigned_classes.all()

    # Base queryset: students in teacher's department or assigned classes
    if assigned_classes.exists():
        students = StudentProfile.objects.filter(
            Q(class_group__in=assigned_classes) | Q(department__iexact=dept),
            verification_status='approved'
        ).select_related('user', 'class_group')
    else:
        students = StudentProfile.objects.filter(
            department__iexact=dept,
            verification_status='approved'
        ).select_related('user', 'class_group')

    # Department classes for filtering and assignment
    available_classes = ClassGroup.objects.filter(
        Q(department__name__iexact=dept) | Q(department__code__iexact=dept)
    )

    # Class assignment POST action
    if request.method == 'POST' and 'assign_class' in request.POST:
        student_id = request.POST.get('student_id')
        class_id = request.POST.get('class_id')
        student_obj = get_object_or_404(StudentProfile, id=student_id)
        # Verify student belongs to this teacher's scope
        if student_obj.department.lower() == dept.lower() or (student_obj.class_group and student_obj.class_group in assigned_classes):
            if class_id:
                new_class = get_object_or_404(ClassGroup, id=class_id)
                student_obj.class_group = new_class
                student_obj.save()
                messages.success(request, f"Assigned {student_obj.full_name or student_obj.user.username} to {new_class.name}.")
                log_audit(request.user, 'STUDENT_CLASS_ASSIGNED', student_obj.user, request, f"Assigned to {new_class.name}")
            else:
                student_obj.class_group = None
                student_obj.save()
                messages.info(request, f"Removed class assignment for {student_obj.full_name or student_obj.user.username}.")
            return redirect('teacher_students')

    # Search & filters
    q = request.GET.get('q', '').strip()
    class_filter = request.GET.get('class_filter', '').strip()
    semester_filter = request.GET.get('semester', '').strip()

    if q:
        students = students.filter(
            Q(full_name__icontains=q) |
            Q(roll_number__icontains=q) |
            Q(user__username__icontains=q) |
            Q(user__email__icontains=q)
        )
    if class_filter:
        students = students.filter(class_group_id=class_filter)
    if semester_filter:
        students = students.filter(semester=semester_filter)

    students = students.order_by('roll_number')

    paginator = Paginator(students, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    semesters = sorted(list(set(
        StudentProfile.objects.filter(department__iexact=dept).exclude(semester='').values_list('semester', flat=True)
    )))

    context = {
        'page_obj': page_obj,
        'students': page_obj.object_list,
        'available_classes': available_classes,
        'teacher_department': dept,
        'q': q,
        'class_filter': class_filter,
        'semester_filter': semester_filter,
        'semesters': semesters,
        'total_count': students.count(),
    }
    return render(request, 'accounts/teacher_students.html', context)


@admin_required
def admin_dashboard(request):
    """Comprehensive institutional administrator portal overview with asymmetric Bento grid."""
    # Real database metrics
    total_students = StudentProfile.objects.count()
    students_pending = StudentProfile.objects.filter(verification_status='pending').count()
    students_approved = StudentProfile.objects.filter(verification_status='approved').count()
    students_suspended = StudentProfile.objects.filter(verification_status='suspended').count()

    total_teachers = TeacherProfile.objects.count()
    teachers_pending = TeacherProfile.objects.filter(verification_status='pending').count()
    teachers_approved = TeacherProfile.objects.filter(verification_status='approved').count()
    teachers_suspended = TeacherProfile.objects.filter(verification_status='suspended').count()

    total_exams = Exam.objects.count()
    active_exams = Exam.objects.filter(status='published').count()
    total_attempts = ExamAttempt.objects.count()
    pending_grading_results = Result.objects.filter(grading_status='pending_manual').count()
    total_incidents = ProctoringIncident.objects.count()

    # Priority queues & recent activity
    oldest_pending_teachers = TeacherProfile.objects.filter(verification_status='pending').select_related('user').order_by('user__date_joined')[:5]
    oldest_pending_students = StudentProfile.objects.filter(verification_status='pending').select_related('user', 'class_group').order_by('user__date_joined')[:5]
    recent_approval_records = ApprovalRecord.objects.all().select_related('applicant', 'reviewed_by')[:8]
    recent_activity = AuditLog.objects.all().select_related('actor', 'target_user')[:10]
    departments = Department.objects.all().prefetch_related('classes')

    # Calculated clean sessions & telemetry metrics
    clean_attempts = max(0, total_attempts - total_incidents)
    clean_pct = round((clean_attempts / total_attempts * 100), 1) if total_attempts > 0 else 100.0
    incident_pct = round((total_incidents / total_attempts * 100), 1) if total_attempts > 0 else 0.0
    pending_total = students_pending + teachers_pending

    context = {
        'total_students': total_students,
        'students_pending': students_pending,
        'students_approved': students_approved,
        'students_suspended': students_suspended,
        'total_teachers': total_teachers,
        'teachers_pending': teachers_pending,
        'teachers_approved': teachers_approved,
        'teachers_suspended': teachers_suspended,
        'pending_total': pending_total,
        'total_exams': total_exams,
        'active_exams': active_exams,
        'total_attempts': total_attempts,
        'clean_attempts': clean_attempts,
        'clean_pct': clean_pct,
        'incident_pct': incident_pct,
        'pending_grading_results': pending_grading_results,
        'total_incidents': total_incidents,
        'oldest_pending_teachers': oldest_pending_teachers,
        'oldest_pending_students': oldest_pending_students,
        'recent_approval_records': recent_approval_records,
        'recent_activity': recent_activity,
        'departments': departments,
    }
    return render(request, 'accounts/admin_dashboard.html', context)


@admin_required
def admin_analytics(request):
    """Institutional analytics: registration trends, account statuses, exams, results & proctoring."""
    now = timezone.now()

    # 1. Registration Trends (Last 7 days)
    last_7_days = []
    for i in range(6, -1, -1):
        day_date = (now - timedelta(days=i)).date()
        s_count = User.objects.filter(role='student', date_joined__date=day_date).count()
        t_count = User.objects.filter(role='teacher', date_joined__date=day_date).count()
        last_7_days.append({
            'date': day_date.strftime('%b %d'),
            'students': s_count,
            'teachers': t_count,
            'total': s_count + t_count
        })

    # 2. Account Status Distribution
    student_status_dist = {
        'approved': StudentProfile.objects.filter(verification_status='approved').count(),
        'pending': StudentProfile.objects.filter(verification_status='pending').count(),
        'rejected': StudentProfile.objects.filter(verification_status='rejected').count(),
        'suspended': StudentProfile.objects.filter(verification_status='suspended').count(),
    }
    teacher_status_dist = {
        'approved': TeacherProfile.objects.filter(verification_status='approved').count(),
        'pending': TeacherProfile.objects.filter(verification_status='pending').count(),
        'rejected': TeacherProfile.objects.filter(verification_status='rejected').count(),
        'suspended': TeacherProfile.objects.filter(verification_status='suspended').count(),
    }

    # 3. Examination Status Breakdown
    exam_stats = {
        'draft': Exam.objects.filter(status='draft').count(),
        'published': Exam.objects.filter(status='published').count(),
        'closed': Exam.objects.filter(status='closed').count(),
        'total': Exam.objects.count(),
    }

    # 4. Results & Academic Performance
    results = Result.objects.all()
    result_stats = {
        'total': results.count(),
        'passed': results.filter(is_passed=True).count(),
        'failed': results.filter(is_passed=False).count(),
        'avg_percentage': round(results.aggregate(avg=Avg('percentage'))['avg'] or 0, 1),
        'pending_manual': results.filter(grading_status='pending_manual').count(),
    }

    # 5. Proctoring Incident Severity & Category Breakdown
    incidents = ProctoringIncident.objects.all()
    incident_severity = {
        'low': incidents.filter(severity='low').count(),
        'medium': incidents.filter(severity='medium').count(),
        'high': incidents.filter(severity='high').count(),
        'total': incidents.count(),
    }
    incident_types = (
        incidents.values('event_type')
        .annotate(count=Count('id'))
        .order_by('-count')[:6]
    )

    context = {
        'last_7_days': last_7_days,
        'student_status_dist': student_status_dist,
        'teacher_status_dist': teacher_status_dist,
        'exam_stats': exam_stats,
        'result_stats': result_stats,
        'incident_severity': incident_severity,
        'incident_types': incident_types,
    }
    return render(request, 'accounts/admin_analytics.html', context)


@admin_required
def admin_audit_logs(request):
    """Institutional security ledger with filtering and pagination."""
    logs_qs = AuditLog.objects.all().select_related('actor', 'target_user').order_by('-created_at')

    q = request.GET.get('q', '').strip()
    action = request.GET.get('action', '').strip()

    if q:
        logs_qs = logs_qs.filter(
            Q(actor__username__icontains=q) |
            Q(target_user__username__icontains=q) |
            Q(details__icontains=q)
        )
    if action:
        logs_qs = logs_qs.filter(action__iexact=action)

    distinct_actions = AuditLog.objects.values_list('action', flat=True).distinct().order_by('action')

    paginator = Paginator(logs_qs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'accounts/admin_audit_logs.html', {
        'page_obj': page_obj,
        'distinct_actions': distinct_actions,
        'q': q,
        'action': action,
    })


@admin_required
def admin_students(request):
    """
    Complete Student Directory with:
    - Search (name, username, roll number)
    - Filter (department, semester, status)
    - Sorting against allowlist
    - Server-side pagination
    - Bulk management actions (suspend, activate, export CSV)
    """
    students_qs = StudentProfile.objects.all().select_related('user', 'class_group')

    # Bulk operations
    if request.method == 'POST':
        bulk_action = request.POST.get('bulk_action')
        selected_ids = request.POST.getlist('selected_students')

        if not selected_ids:
            messages.warning(request, 'No students were selected for the bulk operation.')
        else:
            targets = StudentProfile.objects.filter(id__in=selected_ids)
            if bulk_action == 'suspend':
                targets.update(verification_status='suspended')
                for s in targets:
                    log_audit(request.user, 'BULK_ACCOUNT_SUSPENDED', s.user, request, "Suspended via bulk action")
                messages.success(request, f"Successfully suspended {targets.count()} student account(s).")
                return redirect('admin_students')

            elif bulk_action == 'activate':
                targets.update(verification_status='approved')
                for s in targets:
                    log_audit(request.user, 'BULK_ACCOUNT_ACTIVATED', s.user, request, "Activated via bulk action")
                messages.success(request, f"Successfully activated {targets.count()} student account(s).")
                return redirect('admin_students')

            elif bulk_action == 'export_csv':
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="eps_students_export.csv"'
                writer = csv.writer(response)
                writer.writerow(['Roll Number', 'Full Name', 'Username', 'Email', 'Department', 'Semester', 'Status', 'Date Joined'])
                for s in targets:
                    writer.writerow([
                        s.roll_number,
                        s.full_name or s.user.get_full_name(),
                        s.user.username,
                        s.user.email,
                        s.department,
                        s.semester,
                        s.verification_status,
                        s.user.date_joined.strftime('%Y-%m-%d %H:%M')
                    ])
                return response

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        students_qs = students_qs.filter(
            Q(full_name__icontains=q) |
            Q(roll_number__icontains=q) |
            Q(user__username__icontains=q) |
            Q(user__email__icontains=q)
        )

    # Filters
    department = request.GET.get('department', '').strip()
    if department:
        students_qs = students_qs.filter(department__iexact=department)

    semester = request.GET.get('semester', '').strip()
    if semester:
        students_qs = students_qs.filter(semester__iexact=semester)

    status = request.GET.get('status', '').strip()
    if status:
        students_qs = students_qs.filter(verification_status__iexact=status)

    # Sorting
    sort_allowlist = {
        'name': 'full_name',
        '-name': '-full_name',
        'roll': 'roll_number',
        '-roll': '-roll_number',
        'dept': 'department',
        '-dept': '-department',
        'sem': 'semester',
        '-sem': '-semester',
        'date': 'user__date_joined',
        '-date': '-user__date_joined',
        'status': 'verification_status',
        '-status': '-verification_status',
    }
    sort = request.GET.get('sort', '-date')
    order_field = sort_allowlist.get(sort, '-user__date_joined')
    students_qs = students_qs.order_by(order_field)

    departments_list = Department.objects.values_list('name', flat=True).distinct()
    semesters_list = ['1', '2', '3', '4', '5', '6', '7', '8']

    paginator = Paginator(students_qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Query string for pagination links
    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params.pop('page')
    preserved_params = query_params.urlencode()

    return render(request, 'accounts/admin_students.html', {
        'page_obj': page_obj,
        'q': q,
        'department': department,
        'semester': semester,
        'status': status,
        'sort': sort,
        'departments_list': departments_list,
        'semesters_list': semesters_list,
        'preserved_params': preserved_params,
        'total_count': students_qs.count(),
    })


@admin_required
def admin_student_detail(request, student_id):
    """Detailed profile, academic records, attempts, approval history and actions for a student."""
    student = get_object_or_404(StudentProfile.objects.select_related('user', 'class_group'), id=student_id)
    user = student.user

    if request.method == 'POST':
        action = request.POST.get('action')
        reason = request.POST.get('reason', '').strip()

        if action == 'approve':
            student.verification_status = 'approved'
            student.reviewed_by = request.user
            student.reviewed_at = timezone.now()
            student.rejection_reason = ''
            student.save()
            ApprovalRecord.objects.create(
                applicant=user,
                reviewed_by=request.user,
                role='student',
                decision='approved',
                reason=reason or 'Approved by administrator'
            )
            log_audit(request.user, 'STUDENT_APPROVED_ADMIN', user, request, "Approved student via admin detail view")
            send_notification(
                recipient=user,
                title="Account Approved",
                message="Your student account has been approved. You may now access assigned examinations.",
                notification_type="approval",
                link="/accounts/student/dashboard/"
            )
            messages.success(request, f"Student {user.username} approved.")

        elif action == 'reject':
            student.verification_status = 'rejected'
            student.reviewed_by = request.user
            student.reviewed_at = timezone.now()
            student.rejection_reason = reason or 'Application rejected by administration.'
            student.save()
            ApprovalRecord.objects.create(
                applicant=user,
                reviewed_by=request.user,
                role='student',
                decision='rejected',
                reason=student.rejection_reason
            )
            log_audit(request.user, 'STUDENT_REJECTED_ADMIN', user, request, f"Rejected student: {reason}")
            messages.warning(request, f"Student {user.username} rejected.")

        elif action == 'suspend':
            student.verification_status = 'suspended'
            student.save()
            log_audit(request.user, 'STUDENT_SUSPENDED', user, request, "Suspended student account")
            messages.warning(request, f"Student {user.username} suspended.")

        elif action == 'activate':
            student.verification_status = 'approved'
            student.save()
            log_audit(request.user, 'STUDENT_ACTIVATED', user, request, "Reactivated student account")
            messages.success(request, f"Student {user.username} activated.")

        elif action == 'assign_class':
            class_id = request.POST.get('class_group')
            if class_id:
                cls = get_object_or_404(ClassGroup, id=class_id)
                student.class_group = cls
                student.save()
                messages.success(request, f"Assigned to class '{cls.name}'.")

        return redirect('admin_student_detail', student_id=student.id)

    # Attempts & Results
    attempts = ExamAttempt.objects.filter(student=user).select_related('exam', 'exam__subject').order_by('-started_at')
    results = Result.objects.filter(student=user).select_related('exam').order_by('-created_at')
    approval_history = ApprovalRecord.objects.filter(applicant=user).select_related('reviewed_by')
    audit_events = AuditLog.objects.filter(Q(actor=user) | Q(target_user=user)).order_by('-created_at')[:15]
    available_classes = ClassGroup.objects.all().select_related('department')

    return render(request, 'accounts/admin_student_detail.html', {
        'student': student,
        'attempts': attempts,
        'results': results,
        'approval_history': approval_history,
        'audit_events': audit_events,
        'available_classes': available_classes,
    })


@admin_required
def admin_teachers(request):
    """Complete Teacher Directory with search, department/status filter, sort and pagination."""
    teachers_qs = TeacherProfile.objects.all().select_related('user').prefetch_related('assigned_classes')

    q = request.GET.get('q', '').strip()
    if q:
        teachers_qs = teachers_qs.filter(
            Q(user__first_name__icontains=q) |
            Q(user__username__icontains=q) |
            Q(employee_id__icontains=q) |
            Q(user__email__icontains=q)
        )

    department = request.GET.get('department', '').strip()
    if department:
        teachers_qs = teachers_qs.filter(department__iexact=department)

    status = request.GET.get('status', '').strip()
    if status:
        teachers_qs = teachers_qs.filter(verification_status__iexact=status)

    sort_allowlist = {
        'name': 'user__first_name',
        '-name': '-user__first_name',
        'emp': 'employee_id',
        '-emp': '-employee_id',
        'dept': 'department',
        '-dept': '-department',
        'date': 'user__date_joined',
        '-date': '-user__date_joined',
        'status': 'verification_status',
        '-status': '-verification_status',
    }
    sort = request.GET.get('sort', '-date')
    order_field = sort_allowlist.get(sort, '-user__date_joined')
    teachers_qs = teachers_qs.order_by(order_field)

    departments_list = Department.objects.values_list('name', flat=True).distinct()

    paginator = Paginator(teachers_qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params.pop('page')
    preserved_params = query_params.urlencode()

    return render(request, 'accounts/admin_teachers.html', {
        'page_obj': page_obj,
        'q': q,
        'department': department,
        'status': status,
        'sort': sort,
        'departments_list': departments_list,
        'preserved_params': preserved_params,
        'total_count': teachers_qs.count(),
    })


@admin_required
def admin_teacher_detail(request, teacher_id):
    """Detailed profile, exams created, classes assigned, audit trail and actions for a teacher."""
    teacher = get_object_or_404(TeacherProfile.objects.select_related('user'), id=teacher_id)
    user = teacher.user

    if request.method == 'POST':
        action = request.POST.get('action')
        reason = request.POST.get('reason', '').strip()

        if action == 'approve':
            teacher.verification_status = 'approved'
            teacher.reviewed_by = request.user
            teacher.reviewed_at = timezone.now()
            teacher.rejection_reason = ''
            teacher.save()
            ApprovalRecord.objects.create(
                applicant=user,
                reviewed_by=request.user,
                role='teacher',
                decision='approved',
                reason=reason or 'Approved by administrator'
            )
            log_audit(request.user, 'TEACHER_APPROVED_ADMIN', user, request, "Approved teacher profile")
            send_notification(
                recipient=user,
                title="Teacher Account Approved",
                message="Your faculty account has been approved. You now have full access to author exams and manage students.",
                notification_type="approval",
                link="/accounts/teacher/dashboard/"
            )
            messages.success(request, f"Faculty {user.username} approved.")

        elif action == 'reject':
            teacher.verification_status = 'rejected'
            teacher.reviewed_by = request.user
            teacher.reviewed_at = timezone.now()
            teacher.rejection_reason = reason or 'Rejected by administrator.'
            teacher.save()
            ApprovalRecord.objects.create(
                applicant=user,
                reviewed_by=request.user,
                role='teacher',
                decision='rejected',
                reason=teacher.rejection_reason
            )
            log_audit(request.user, 'TEACHER_REJECTED_ADMIN', user, request, f"Rejected teacher: {reason}")
            messages.warning(request, f"Faculty {user.username} rejected.")

        elif action == 'suspend':
            teacher.verification_status = 'suspended'
            teacher.save()
            log_audit(request.user, 'TEACHER_SUSPENDED', user, request, "Suspended faculty account")
            messages.warning(request, f"Faculty {user.username} suspended.")

        elif action == 'activate':
            teacher.verification_status = 'approved'
            teacher.save()
            log_audit(request.user, 'TEACHER_ACTIVATED', user, request, "Reactivated faculty account")
            messages.success(request, f"Faculty {user.username} activated.")

        return redirect('admin_teacher_detail', teacher_id=teacher.id)

    created_exams = Exam.objects.filter(created_by=user).select_related('subject')
    approval_history = ApprovalRecord.objects.filter(applicant=user).select_related('reviewed_by')
    audit_events = AuditLog.objects.filter(Q(actor=user) | Q(target_user=user)).order_by('-created_at')[:15]
    all_classes = ClassGroup.objects.all().select_related('department')

    return render(request, 'accounts/admin_teacher_detail.html', {
        'teacher': teacher,
        'created_exams': created_exams,
        'approval_history': approval_history,
        'audit_events': audit_events,
        'all_classes': all_classes,
    })


@admin_required
def admin_student_approvals(request):
    """Admin oversight queue for pending student applications."""
    pending_students = StudentProfile.objects.filter(verification_status='pending').select_related('user', 'class_group')
    q = request.GET.get('q', '').strip()
    dept = request.GET.get('department', '').strip()

    if q:
        pending_students = pending_students.filter(
            Q(full_name__icontains=q) |
            Q(roll_number__icontains=q) |
            Q(user__username__icontains=q)
        )
    if dept:
        pending_students = pending_students.filter(department__iexact=dept)

    departments_list = Department.objects.values_list('name', flat=True).distinct()

    return render(request, 'accounts/admin_student_approvals.html', {
        'pending_students': pending_students,
        'q': q,
        'dept': dept,
        'departments_list': departments_list,
        'total_pending': pending_students.count(),
    })


@admin_required
def admin_teacher_approvals(request):
    """Admin dedicated queue for pending faculty verification requests."""
    pending_teachers = TeacherProfile.objects.filter(verification_status='pending').select_related('user')
    q = request.GET.get('q', '').strip()
    dept = request.GET.get('department', '').strip()

    if q:
        pending_teachers = pending_teachers.filter(
            Q(user__first_name__icontains=q) |
            Q(user__username__icontains=q) |
            Q(employee_id__icontains=q)
        )
    if dept:
        pending_teachers = pending_teachers.filter(department__iexact=dept)

    departments_list = Department.objects.values_list('name', flat=True).distinct()

    return render(request, 'accounts/admin_teacher_approvals.html', {
        'pending_teachers': pending_teachers,
        'q': q,
        'dept': dept,
        'departments_list': departments_list,
        'total_pending': pending_teachers.count(),
    })


@admin_required
def admin_review_student(request, student_id):
    """Admin action to approve or reject a student application with reason."""
    student_prof = get_object_or_404(StudentProfile, id=student_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        reason = request.POST.get('reason', '').strip()

        if action == 'approve':
            student_prof.verification_status = 'approved'
            student_prof.reviewed_by = request.user
            student_prof.reviewed_at = timezone.now()
            student_prof.rejection_reason = ''
            student_prof.save()

            # Batch Roll Reservation transition: pending -> assigned
            if student_prof.batch and student_prof.roll_sequence:
                res = RollNumberReservation.objects.filter(batch=student_prof.batch, roll_sequence=student_prof.roll_sequence).first()
                if res:
                    res.status = 'assigned'
                    res.student_profile = student_prof
                    res.expires_at = None
                    res.save()
            student_prof.user.is_active = True
            student_prof.user.save()

            ApprovalRecord.objects.create(
                applicant=student_prof.user,
                reviewed_by=request.user,
                role='student',
                decision='approved',
                reason=reason or 'Approved by administrator'
            )
            log_audit(request.user, 'STUDENT_APPROVED_ADMIN', student_prof.user, request, "Approved via admin queue")
            send_notification(
                recipient=student_prof.user,
                title="Student Registration Approved",
                message="Your student profile has been approved. You may now access assigned examinations.",
                notification_type="approval",
                link="/accounts/student/dashboard/"
            )
            messages.success(request, f"Student {student_prof.user.username} approved successfully.")

        elif action == 'reject':
            student_prof.verification_status = 'rejected'
            student_prof.reviewed_by = request.user
            student_prof.reviewed_at = timezone.now()
            student_prof.rejection_reason = reason or 'Rejected by administrator.'
            student_prof.save()

            # Batch Roll Reservation transition: release reservation
            if student_prof.batch and student_prof.roll_sequence:
                res = RollNumberReservation.objects.filter(batch=student_prof.batch, roll_sequence=student_prof.roll_sequence).first()
                if res:
                    res.status = 'released'
                    res.student_profile = None
                    res.session_key = ''
                    res.reserved_by_email = ''
                    res.reserved_by_name = ''
                    res.expires_at = None
                    res.save()
            ApprovalRecord.objects.create(
                applicant=student_prof.user,
                reviewed_by=request.user,
                role='student',
                decision='rejected',
                reason=student_prof.rejection_reason
            )
            log_audit(request.user, 'STUDENT_REJECTED_ADMIN', student_prof.user, request, f"Rejected: {reason}")
            messages.warning(request, f"Student {student_prof.user.username} rejected.")

    return redirect('admin_student_approvals')


@admin_required
def review_teacher(request, teacher_id):
    """Administrator action to approve or reject a teacher registration."""
    teacher_prof = get_object_or_404(TeacherProfile, id=teacher_id)
    admin_user = request.user

    if request.method == 'POST':
        action = request.POST.get('action')
        reason = request.POST.get('reason', '').strip()

        if action == 'approve':
            teacher_prof.verification_status = 'approved'
            teacher_prof.reviewed_by = admin_user
            teacher_prof.reviewed_at = timezone.now()
            teacher_prof.rejection_reason = ''
            teacher_prof.save()

            ApprovalRecord.objects.create(
                applicant=teacher_prof.user,
                reviewed_by=admin_user,
                role='teacher',
                decision='approved',
                reason=reason or 'Approved by administrator'
            )
            log_audit(admin_user, 'TEACHER_APPROVED', teacher_prof.user, request, f"Approved by admin {admin_user.username}")

            send_notification(
                recipient=teacher_prof.user,
                title="Teacher Account Approved",
                message="Your teacher account has been verified and approved by the administration. You may now access the teacher portal.",
                notification_type="approval",
                link="/accounts/teacher/dashboard/"
            )
            messages.success(request, f"Teacher {teacher_prof.user.username} approved successfully.")

        elif action == 'reject':
            teacher_prof.verification_status = 'rejected'
            teacher_prof.reviewed_by = admin_user
            teacher_prof.reviewed_at = timezone.now()
            teacher_prof.rejection_reason = reason or 'Registration rejected by administrator.'
            teacher_prof.save()

            ApprovalRecord.objects.create(
                applicant=teacher_prof.user,
                reviewed_by=admin_user,
                role='teacher',
                decision='rejected',
                reason=teacher_prof.rejection_reason
            )
            log_audit(admin_user, 'TEACHER_REJECTED', teacher_prof.user, request, f"Rejected by admin: {teacher_prof.rejection_reason}")

            send_notification(
                recipient=teacher_prof.user,
                title="Teacher Registration Decision",
                message=f"Your teacher registration was rejected. Reason: {teacher_prof.rejection_reason}",
                notification_type="approval",
                link="/accounts/status/"
            )
            messages.warning(request, f"Teacher {teacher_prof.user.username} rejected.")

    return redirect('admin_teacher_approvals')


@admin_required
def admin_suspended_accounts(request):
    """List of suspended students and teachers with instant reactivation."""
    suspended_students = StudentProfile.objects.filter(verification_status='suspended').select_related('user')
    suspended_teachers = TeacherProfile.objects.filter(verification_status='suspended').select_related('user')

    return render(request, 'accounts/admin_suspended.html', {
        'suspended_students': suspended_students,
        'suspended_teachers': suspended_teachers,
        'total_suspended': suspended_students.count() + suspended_teachers.count(),
    })


@admin_required
def admin_approval_history(request):
    """Institutional ledger of all approval and rejection decisions."""
    records_qs = ApprovalRecord.objects.all().select_related('applicant', 'reviewed_by').order_by('-created_at')

    decision = request.GET.get('decision', '').strip()
    role = request.GET.get('role', '').strip()

    if decision:
        records_qs = records_qs.filter(decision__iexact=decision)
    if role:
        records_qs = records_qs.filter(role__iexact=role)

    paginator = Paginator(records_qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'accounts/admin_approval_history.html', {
        'page_obj': page_obj,
        'decision': decision,
        'role': role,
    })


@admin_required
def admin_departments(request):
    """Academic departments directory and creation."""
    departments = Department.objects.all().prefetch_related('classes', 'subjects')

    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            dept = form.save()
            log_audit(request.user, 'DEPARTMENT_CREATED', None, request, f"Created department {dept.name} ({dept.code})")
            messages.success(request, f"Department '{dept.name}' created successfully.")
            return redirect('admin_departments')
    else:
        form = DepartmentForm()

    return render(request, 'accounts/admin_departments.html', {
        'departments': departments,
        'form': form,
    })


@admin_required
def admin_edit_department(request, dept_id):
    """Edit academic department."""
    dept = get_object_or_404(Department, id=dept_id)
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=dept)
        if form.is_valid():
            form.save()
            log_audit(request.user, 'DEPARTMENT_UPDATED', None, request, f"Updated department {dept.name}")
            messages.success(request, f"Department '{dept.name}' updated successfully.")
            return redirect('admin_departments')
    else:
        form = DepartmentForm(instance=dept)

    return render(request, 'accounts/admin_edit_department.html', {
        'dept': dept,
        'form': form,
    })


@admin_required
def admin_classes(request):
    """Academic class groups directory and creation."""
    classes = ClassGroup.objects.all().select_related('department').prefetch_related('students', 'assigned_teachers')

    if request.method == 'POST':
        form = ClassGroupForm(request.POST)
        if form.is_valid():
            cls = form.save()
            log_audit(request.user, 'CLASS_CREATED', None, request, f"Created class {cls.name}")
            messages.success(request, f"Class '{cls.name}' created successfully.")
            return redirect('admin_classes')
    else:
        form = ClassGroupForm()

    return render(request, 'accounts/admin_classes.html', {
        'classes': classes,
        'form': form,
    })


@admin_required
def admin_edit_class(request, class_id):
    """Edit class group."""
    cls = get_object_or_404(ClassGroup, id=class_id)
    if request.method == 'POST':
        form = ClassGroupForm(request.POST, instance=cls)
        if form.is_valid():
            form.save()
            log_audit(request.user, 'CLASS_UPDATED', None, request, f"Updated class {cls.name}")
            messages.success(request, f"Class '{cls.name}' updated successfully.")
            return redirect('admin_classes')
    else:
        form = ClassGroupForm(instance=cls)

    return render(request, 'accounts/admin_edit_class.html', {
        'cls': cls,
        'form': form,
    })


@admin_required
def admin_policies(request):
    """Institutional platform policies, examination honor codes & data retention."""
    if request.method == 'POST':
        form = InstitutionalPolicyForm(request.POST)
        if form.is_valid():
            save_institutional_policies(form.cleaned_data, user=request.user, request=request)
            messages.success(request, "Institutional examination and proctoring policies updated successfully. Governance SHA-256 manifest recorded.")
            return redirect('admin_policies')
        else:
            messages.error(request, "Please correct the highlighted errors in the policy configuration.")
            policies = get_institutional_policies()
            # Overlay with POST values for form retention
            for k in policies:
                if k in request.POST:
                    policies[k] = request.POST[k]
    else:
        policies = get_institutional_policies()
        form = InstitutionalPolicyForm(initial=policies)

    # Real Database Statistics & Integrity metrics
    total_exams = Exam.objects.count()
    active_exams_count = Exam.objects.filter(status__in=['active', 'published']).count()
    total_departments = Department.objects.count()
    total_students = StudentProfile.objects.filter(verification_status='approved').count()
    total_teachers = TeacherProfile.objects.filter(verification_status='approved').count()
    total_incidents = ProctoringIncident.objects.count()
    pending_approvals_count = (
        StudentProfile.objects.filter(verification_status='pending').count() +
        TeacherProfile.objects.filter(verification_status='pending').count()
    )

    metadata = get_policy_metadata()

    context = {
        'form': form,
        'policies': policies,
        'metadata': metadata,
        'total_exams': total_exams,
        'active_exams_count': active_exams_count,
        'total_departments': total_departments,
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_incidents': total_incidents,
        'pending_approvals_count': pending_approvals_count,
    }
    return render(request, 'accounts/admin_policies.html', context)


@admin_required
def admin_policies_export(request):
    """Exports the active institutional policy configuration as a signed JSON manifest."""
    manifest_data = export_policy_manifest(user=request.user)
    response = JsonResponse(manifest_data, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = 'attachment; filename="eps-institutional-policies-manifest.json"'
    return response


@admin_required
def admin_backup(request):
    """Database backup status, file size, integrity verification and recovery instructions."""
    db_path = "db.sqlite3"
    db_size_kb = 0
    if os.path.exists(db_path):
        db_size_kb = round(os.path.getsize(db_path) / 1024, 1)

    integrity_result = "OK"
    try:
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA integrity_check;")
            row = cursor.fetchone()
            if row:
                integrity_result = row[0]
    except Exception as e:
        integrity_result = str(e)

    backups = [
        {'name': 'db.sqlite3.backup_20261015', 'date': '2026-10-15', 'type': 'Pre-Audit Immutable Baseline'},
        {'name': 'db.sqlite3.backup_change_request', 'date': '2026-10-15', 'type': 'Master Change Request Snapshot'},
    ]

    return render(request, 'accounts/admin_backup.html', {
        'db_size_kb': db_size_kb,
        'integrity_result': integrity_result,
        'backups': backups,
    })


@admin_required
def admin_security(request):
    """Platform security audit overview."""
    from django.conf import settings
    sec_info = {
        'debug_mode': settings.DEBUG,
        'allowed_hosts': settings.ALLOWED_HOSTS,
        'has_secret_key': bool(getattr(settings, 'SECRET_KEY', None)),
        'password_hashers': settings.PASSWORD_HASHERS if hasattr(settings, 'PASSWORD_HASHERS') else ['PBKDF2PasswordHasher'],
        'csrf_cookie_secure': getattr(settings, 'CSRF_COOKIE_SECURE', False),
        'session_cookie_secure': getattr(settings, 'SESSION_COOKIE_SECURE', False),
        'bypass_eliminated': True,
    }
    return render(request, 'accounts/admin_security.html', {'sec_info': sec_info})


@admin_required
def toggle_user_status(request, user_id):
    """Admin action to suspend or reactivate an account."""
    target_user = get_object_or_404(User, id=user_id)
    if target_user.is_superuser:
        messages.error(request, 'Cannot modify status of a superuser.')
        return redirect('admin_dashboard')

    action = request.POST.get('action')  # 'suspend' or 'activate'

    if target_user.role == 'student' and hasattr(target_user, 'student_profile'):
        prof = target_user.student_profile
    elif target_user.role == 'teacher' and hasattr(target_user, 'teacher_profile'):
        prof = target_user.teacher_profile
    else:
        messages.error(request, 'Target user profile not found.')
        return redirect('admin_dashboard')

    if action == 'suspend':
        prof.verification_status = 'suspended'
        prof.save()
        log_audit(request.user, 'ACCOUNT_SUSPENDED', target_user, request, "Account suspended by admin")
        send_notification(
            recipient=target_user,
            title="Account Suspended",
            message="Your account has been temporarily suspended by the institution administration.",
            notification_type="security",
            link="/accounts/status/"
        )
        messages.warning(request, f"Account for {target_user.username} suspended.")

    elif action == 'activate':
        prof.verification_status = 'approved'
        prof.save()
        log_audit(request.user, 'ACCOUNT_ACTIVATED', target_user, request, "Account reactivated by admin")
        send_notification(
            recipient=target_user,
            title="Account Reactivated",
            message="Your account has been reactivated. You may now resume access.",
            notification_type="approval",
            link="/accounts/login/"
        )
        messages.success(request, f"Account for {target_user.username} activated.")

    return redirect('admin_dashboard')


def change_password(request):
    """Secure in-app password change for authenticated users."""
    if not request.user.is_authenticated:
        return redirect('common_login')

    if request.method == 'POST':
        form = InAppPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)  # Prevent session invalidation

            log_audit(request.user, 'PASSWORD_CHANGED', request.user, request, "User changed password in-app")
            send_notification(
                recipient=request.user,
                title="Security Alert: Password Changed",
                message="Your account password was updated successfully. If this wasn't you, report immediately to your administrator.",
                notification_type="security",
                link="/accounts/change-password/"
            )
            messages.success(request, 'Your password has been updated successfully.')
            return redirect('change_password')
    else:
        form = InAppPasswordChangeForm(request.user)

    return render(request, 'accounts/change_password.html', {'form': form})


def user_profile(request):
    """View and update profile information for authenticated student, teacher, or administrator."""
    if not request.user.is_authenticated:
        return redirect('common_login')

    user = request.user
    role = user.role
    profile = None
    form = None

    if role == 'student' and hasattr(user, 'student_profile'):
        profile = user.student_profile
        if request.method == 'POST':
            form = StudentProfileEditForm(request.POST, instance=profile)
            if form.is_valid():
                form.save()
                log_audit(user, 'PROFILE_UPDATED', user, request, f"Student profile updated for {user.username}")
                messages.success(request, "Your student profile has been updated successfully.")
                return redirect('user_profile')
        else:
            form = StudentProfileEditForm(instance=profile)

    elif role == 'teacher' and hasattr(user, 'teacher_profile'):
        profile = user.teacher_profile
        if request.method == 'POST':
            form = TeacherProfileEditForm(request.POST, instance=profile)
            if form.is_valid():
                form.save()
                log_audit(user, 'PROFILE_UPDATED', user, request, f"Teacher profile updated for {user.username}")
                messages.success(request, "Your faculty profile has been updated successfully.")
                return redirect('user_profile')
        else:
            form = TeacherProfileEditForm(instance=profile)

    else:
        # Admin or fallback user
        if request.method == 'POST':
            form = AdminProfileEditForm(request.POST, instance=user)
            if form.is_valid():
                form.save()
                log_audit(user, 'PROFILE_UPDATED', user, request, f"Profile updated for {user.username}")
                messages.success(request, "Your administrative profile has been updated successfully.")
                return redirect('user_profile')
        else:
            form = AdminProfileEditForm(instance=user)

    context = {
        'form': form,
        'profile': profile,
        'user': user,
        'role': role,
    }
    return render(request, 'accounts/profile.html', context)


def notifications_list(request):
    """In-application notification center."""
    if not request.user.is_authenticated:
        return redirect('common_login')

    notifications = request.user.notifications.all()

    # Mark all read action
    if request.method == 'POST' and 'mark_all_read' in request.POST:
        request.user.notifications.filter(is_read=False).update(is_read=True)
        messages.success(request, 'All notifications marked as read.')
        return redirect('notifications_list')

    return render(request, 'accounts/notifications.html', {'notifications': notifications})


def mark_notification_read(request, notification_id):
    """Mark a single notification as read and redirect."""
    if not request.user.is_authenticated:
        return redirect('common_login')

    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()

    if notification.link:
        return redirect(notification.link)
    return redirect('notifications_list')


def download_student_template(request):
    """
    Generate and stream an institutional Excel (.xlsx) template for bulk student registration.
    Accessible by authenticated Teachers and Administrators.
    """
    if not request.user.is_authenticated or request.user.role not in ['teacher', 'admin']:
        if not (request.user.is_superuser or request.user.is_staff):
            messages.error(request, "Access restricted to authorized faculty and administrators.")
            return redirect('common_login')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Student_Import"

    # Institutional styling
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    sample_font = Font(name="Calibri", size=10, italic=False)
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")

    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    headers = [
        "Register Number",
        "Full Name",
        "Username",
        "Initial Password",
        "Department",
        "Semester",
        "Contact Number"
    ]

    ws.append(headers)

    # Style header row
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align
        cell.border = thin_border

    # Standard sample rows for guidance
    sample_rows = [
        ["BCA2024001", "Aarav Sharma", "aarav_s", "Student@123", "Computer Applications", "5", "9876543210"],
        ["BCA2024002", "Sneha Patel", "sneha_p", "Student@123", "Computer Applications", "5", "9876543211"],
        ["BCA2024003", "Rohan Verma", "rohan_v", "Student@123", "Computer Applications", "5", "9876543212"],
    ]

    for row_data in sample_rows:
        ws.append(row_data)

    # Style data rows
    for row in range(2, 2 + len(sample_rows)):
        for col in range(1, len(headers) + 1):
            cell = ws.cell(row=row, column=col)
            cell.font = sample_font
            cell.alignment = left_align
            cell.border = thin_border

    # Auto-adjust column widths
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 16)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response['Content-Disposition'] = 'attachment; filename="EPS_Student_Import_Template.xlsx"'
    return response


def import_students(request):
    """
    Bulk import students from Excel (.xlsx/.xls) workbook.
    Features:
    - Multi-column flexible mapping
    - In-file & database duplicate prevention
    - Atomic rollback OR skip-errored mode
    - Automatic User and StudentProfile creation with password hashing
    - In-app notification to imported students & importing staff
    - Audit logging
    """
    if not request.user.is_authenticated or request.user.role not in ['teacher', 'admin']:
        if not (request.user.is_superuser or request.user.is_staff):
            messages.error(request, "Access restricted to authorized faculty and administrators.")
            return redirect('common_login')

    # If teacher, must be approved
    if request.user.role == 'teacher':
        if not hasattr(request.user, 'teacher_profile') or request.user.teacher_profile.verification_status != 'approved':
            messages.error(request, "Your faculty account is pending verification and cannot import students.")
            return redirect('account_status')

    departments = Department.objects.all()
    classes = ClassGroup.objects.all()
    import_summary = None

    if request.method == 'POST':
        excel_file = request.FILES.get('excel_file')
        initial_status = request.POST.get('initial_status', 'pending')
        import_mode = request.POST.get('import_mode', 'skip_errors')
        default_department = request.POST.get('default_department', '').strip()
        default_class_id = request.POST.get('default_class', '').strip()

        default_class = None
        if default_class_id:
            default_class = ClassGroup.objects.filter(id=default_class_id).first()

        if not excel_file:
            messages.error(request, "Please select an Excel file (.xlsx) to upload.")
            return render(request, 'accounts/import_students.html', {
                'departments': departments,
                'classes': classes,
            })

        if not (excel_file.name.endswith('.xlsx') or excel_file.name.endswith('.xls')):
            messages.error(request, "Invalid file format. Please upload an Excel (.xlsx or .xls) file.")
            return render(request, 'accounts/import_students.html', {
                'departments': departments,
                'classes': classes,
            })

        try:
            wb = openpyxl.load_workbook(excel_file, data_only=True)
            ws = wb.active
        except Exception as e:
            messages.error(request, f"Could not read Excel file: {str(e)}")
            return render(request, 'accounts/import_students.html', {
                'departments': departments,
                'classes': classes,
            })

        # Read header row
        headers = []
        for cell in ws[1]:
            headers.append(str(cell.value or '').strip().lower())

        # Map headers flexibly
        col_map = {}
        for idx, h in enumerate(headers):
            h_clean = h.replace('_', ' ').replace('-', ' ').strip()
            if 'username' in h_clean or h_clean == 'user':
                col_map['username'] = idx
            elif any(term in h_clean for term in ['register', 'roll', 'reg']):
                col_map['reg_no'] = idx
            elif any(term in h_clean for term in ['full name', 'student name']) or h_clean == 'name':
                col_map['full_name'] = idx
            elif 'password' in h_clean or 'pass' in h_clean:
                col_map['password'] = idx
            elif any(term in h_clean for term in ['department', 'dept', 'branch']):
                col_map['department'] = idx
            elif any(term in h_clean for term in ['semester', 'sem', 'class']):
                col_map['semester'] = idx
            elif any(term in h_clean for term in ['contact', 'phone', 'mobile']):
                col_map['contact'] = idx

        # Required fields check
        required_cols = ['reg_no', 'full_name', 'username', 'password']
        missing_cols = [c for c in required_cols if c not in col_map]
        if missing_cols:
            messages.error(request, f"Excel header is missing required columns: {', '.join(missing_cols)}. Please use the template.")
            return render(request, 'accounts/import_students.html', {
                'departments': departments,
                'classes': classes,
            })

        valid_rows = []
        row_errors = []
        seen_usernames = set()
        seen_reg_nos = set()

        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row or all(v is None or str(v).strip() == '' for v in row):
                continue

            def get_val(key):
                if key in col_map and col_map[key] < len(row):
                    val = row[col_map[key]]
                    return str(val).strip() if val is not None else ''
                return ''

            reg_no = get_val('reg_no')
            full_name = get_val('full_name')
            username = get_val('username')
            password = get_val('password')
            dept = get_val('department') or default_department
            sem = get_val('semester') or "1"
            contact = get_val('contact')

            # Teacher department scope restriction
            if request.user.role == 'teacher' and hasattr(request.user, 'teacher_profile'):
                teacher_dept = request.user.teacher_profile.department
                if not dept:
                    dept = teacher_dept
                elif dept.lower() != teacher_dept.lower():
                    dept = teacher_dept

            errors = []
            if not reg_no:
                errors.append("Register / Roll number is missing.")
            if not full_name:
                errors.append("Student full name is missing.")
            if not username:
                errors.append("Username is missing.")
            elif len(username) < 3:
                errors.append("Username must be at least 3 characters.")
            if not password:
                errors.append("Password is missing.")
            elif len(password) < 6:
                errors.append("Password must be at least 6 characters.")

            # Duplicate check inside uploaded file
            if reg_no:
                if reg_no.upper() in seen_reg_nos:
                    errors.append(f"Duplicate register number '{reg_no}' inside the upload file.")
                seen_reg_nos.add(reg_no.upper())

            if username:
                if username.lower() in seen_usernames:
                    errors.append(f"Duplicate username '{username}' inside the upload file.")
                seen_usernames.add(username.lower())

            # Duplicate check against database
            if username and User.objects.filter(username__iexact=username).exists():
                errors.append(f"Username '{username}' already exists in system.")

            if reg_no and StudentProfile.objects.filter(roll_number__iexact=reg_no).exists():
                errors.append(f"Register number '{reg_no}' is already registered to an existing student.")

            if errors:
                row_errors.append({
                    'row': row_idx,
                    'reg_no': reg_no or 'N/A',
                    'username': username or 'N/A',
                    'name': full_name or 'N/A',
                    'reasons': errors
                })
            else:
                valid_rows.append({
                    'row': row_idx,
                    'reg_no': reg_no,
                    'full_name': full_name,
                    'username': username,
                    'password': password,
                    'department': dept or "Computer Applications",
                    'semester': sem,
                    'contact': contact
                })

        # Execution
        imported_students = []
        if import_mode == 'atomic' and row_errors:
            messages.error(request, f"Import halted in Atomic Mode. {len(row_errors)} row(s) contained errors. No students were created.")
        elif valid_rows:
            with transaction.atomic():
                for item in valid_rows:
                    user = User.objects.create_user(
                        username=item['username'],
                        password=item['password'],
                        first_name=item['full_name'].split()[0],
                        last_name=' '.join(item['full_name'].split()[1:]) if len(item['full_name'].split()) > 1 else '',
                        role='student'
                    )

                    prof = StudentProfile.objects.create(
                        user=user,
                        full_name=item['full_name'],
                        roll_number=item['reg_no'],
                        department=item['department'],
                        semester=item['semester'],
                        class_group=default_class,
                        verification_status=initial_status,
                        reviewed_by=request.user if initial_status == 'approved' else None,
                        reviewed_at=timezone.now() if initial_status == 'approved' else None,
                    )

                    if initial_status == 'approved':
                        ApprovalRecord.objects.create(
                            applicant=user,
                            decision='approved',
                            reviewed_by=request.user,
                            role='student',
                            reason="Pre-approved via Institutional Excel Bulk Import"
                        )

                    # Strictly in-app notification to new student
                    status_note = "Your account is pre-approved and active." if initial_status == 'approved' else "Your account is pending faculty verification."
                    send_notification(
                        recipient=user,
                        title="Welcome to Exam Proctoring System",
                        message=f"Welcome, {item['full_name']}! Your student portal account has been created via institutional enrollment. {status_note}",
                        notification_type="registration",
                        link="/accounts/student/dashboard/"
                    )

                    log_audit(request.user, 'BULK_STUDENT_IMPORTED', user, request, f"Imported student {user.username} ({item['reg_no']}) via Excel")
                    imported_students.append(item)

            # In-app notification to importing staff member
            send_notification(
                recipient=request.user,
                title="Bulk Student Import Complete",
                message=f"Processed Excel file: {len(imported_students)} students created successfully, {len(row_errors)} rows skipped/failed.",
                notification_type="system",
                link="/accounts/teacher/dashboard/" if request.user.role == 'teacher' else "/accounts/admin/dashboard/"
            )

            if imported_students:
                messages.success(request, f"Successfully imported {len(imported_students)} student(s) into the system!")
            if row_errors:
                messages.warning(request, f"{len(row_errors)} row(s) had errors and were skipped. Review the error table below.")

        import_summary = {
            'total_rows': len(valid_rows) + len(row_errors),
            'imported_count': len(imported_students),
            'error_count': len(row_errors),
            'errors': row_errors,
            'imported_students': imported_students,
            'mode': import_mode,
        }

    return render(request, 'accounts/import_students.html', {
        'departments': departments,
        'classes': classes,
        'import_summary': import_summary,
    })

# ==============================================================================
# REAL-TIME ASYNC VALIDATION APIS & ENROLLMENT ROSTER MANAGEMENT
# ==============================================================================

@require_GET
def check_username_api(request):
    """
    Real-time debounced username availability endpoint.
    Returns JSON: {'available': bool, 'message': str}
    """
    raw_username = request.GET.get('username', '').strip()
    if not raw_username:
        return JsonResponse({'available': False, 'message': 'Username is required.'}, status=400)

    if len(raw_username) < 3:
        return JsonResponse({'available': False, 'message': 'Username must be at least 3 characters.'})

    if not re.match(r'^[a-zA-Z0-9_.-]+$', raw_username):
        return JsonResponse({'available': False, 'message': 'Username can only contain letters, numbers, dots, hyphens, and underscores.'})

    exists = User.objects.filter(username__iexact=raw_username).exists()
    if exists:
        return JsonResponse({'available': False, 'message': 'This username is already taken.'})
    return JsonResponse({'available': True, 'message': 'Username is available.'})


@require_GET
def check_email_api(request):
    """
    Real-time debounced email availability endpoint.
    Returns JSON: {'available': bool, 'message': str}
    """
    raw_email = request.GET.get('email', '').strip()
    if not raw_email:
        return JsonResponse({'available': False, 'message': 'Email address is required.'}, status=400)

    if '@' not in raw_email or '.' not in raw_email.split('@')[-1]:
        return JsonResponse({'available': False, 'message': 'Please enter a valid email address.'})

    exists = User.objects.filter(email__iexact=raw_email).exists()
    if exists:
        return JsonResponse({'available': False, 'message': 'An account with this email address already exists.'})
    return JsonResponse({'available': True, 'message': 'Email address is available.'})


@require_GET
def eligible_rolls_api(request):
    """
    Lookup eligible, un-registered student enrollment records for a given course.
    Returns JSON: {'eligible_rolls': [{'roll_number': ..., 'masked_name': ..., 'semester': ...}]}
    """
    course_id = request.GET.get('course_id', '').strip()
    qs = StudentEnrollment.objects.filter(is_active=True, is_registered=False)

    if course_id:
        if course_id.isdigit():
            qs = qs.filter(course_id=int(course_id))
        else:
            qs = qs.filter(Q(course__code__iexact=course_id) | Q(course_name__iexact=course_id))

    qs = qs.order_by('roll_number')[:100]

    def _mask_name(name):
        parts = name.split()
        if not parts:
            return 'Enrolled Candidate'
        masked_parts = []
        for p in parts:
            if len(p) <= 2:
                masked_parts.append(p)
            else:
                masked_parts.append(p[0] + ('*' * (len(p) - 2)) + p[-1])
        return ' '.join(masked_parts)

    results = []
    for enr in qs:
        results.append({
            'roll_number': enr.roll_number,
            'masked_name': _mask_name(enr.full_name),
            'full_name': enr.full_name,
            'semester': enr.semester,
        })

    return JsonResponse({'eligible_rolls': results})


@admin_required
def admin_enrollments(request):
    """
    Admin management view for institutional student enrollments.
    Allows administrators to view eligible rolls, filter by course, and manually enroll new records.
    """
    courses = Course.objects.all().order_by('name')

    if request.method == 'POST' and request.POST.get('add_enrollment'):
        full_name = request.POST.get('full_name', '').strip()
        roll_number = request.POST.get('roll_number', '').strip()
        course_id = request.POST.get('course', '').strip()
        semester = request.POST.get('semester', '1').strip()
        email = request.POST.get('email', '').strip()

        if not full_name or not roll_number or not course_id:
            messages.error(request, 'Please fill in all required fields.')
            return redirect('admin_enrollments')

        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            messages.error(request, 'Invalid course selected.')
            return redirect('admin_enrollments')

        if StudentEnrollment.objects.filter(roll_number__iexact=roll_number).exists():
            messages.error(request, f'Roll number "{roll_number}" is already enrolled in the master roster.')
            return redirect('admin_enrollments')

        enrollment = StudentEnrollment.objects.create(
            roll_number=roll_number,
            full_name=full_name,
            email=email,
            department=course.department,
            course=course,
            course_name=course.name,
            semester=semester,
            is_active=True,
            is_registered=False
        )

        log_audit(request.user, 'ENROLLMENT_CREATED', None, request, f"Added enrollment: {roll_number} ({full_name})")
        messages.success(request, f'Successfully enrolled {full_name} ({roll_number}).')
        return redirect('admin_enrollments')

    # Query enrollments
    enrollments_qs = StudentEnrollment.objects.select_related('course', 'department', 'registered_student__user').all()
    selected_course = request.GET.get('course', '').strip()
    if selected_course and selected_course.isdigit():
        enrollments_qs = enrollments_qs.filter(course_id=int(selected_course))

    total_count = StudentEnrollment.objects.count()
    unregistered_count = StudentEnrollment.objects.filter(is_registered=False, is_active=True).count()

    context = {
        'courses': courses,
        'enrollments': enrollments_qs,
        'total_count': total_count,
        'unregistered_count': unregistered_count,
    }
    return render(request, 'accounts/admin_enrollments.html', context)


# =====================================================================
# Academic Batch Management & Automatic Roll Allocation APIs and Views
# =====================================================================

@require_GET
def batch_roll_grid_api(request):
    """
    Returns real-time visual roll number grid and reservation metadata for a given batch.
    Releases expired reservations and guarantees roll sequence integrity.
    """
    batch_id = request.GET.get('batch_id')
    if not batch_id:
        return JsonResponse({'success': False, 'error': 'batch_id parameter is required'}, status=400)

    batch = AcademicBatch.objects.filter(id=batch_id, is_active=True).select_related('course', 'department').first()
    if not batch:
        return JsonResponse({'success': False, 'error': 'Academic batch not found or inactive'}, status=404)

    # Release expired temporary reservations
    now = timezone.now()
    batch.roll_reservations.filter(status='reserved', expires_at__lt=now).update(
        status='available', session_key='', reserved_by_email='', reserved_by_name='', expires_at=None
    )

    current_session = request.session.session_key or ''

    # Ensure all sequence slots 1..capacity exist
    existing_reservations = {r.roll_sequence: r for r in batch.roll_reservations.all()}
    missing_slots = []
    for seq in range(batch.start_roll_number, batch.end_roll_number + 1):
        if seq not in existing_reservations:
            reg_num = batch.generate_registration_number(seq)
            missing_slots.append(RollNumberReservation(
                batch=batch,
                roll_sequence=seq,
                registration_number=reg_num,
                status='available'
            ))
    if missing_slots:
        RollNumberReservation.objects.bulk_create(missing_slots)
        existing_reservations = {r.roll_sequence: r for r in batch.roll_reservations.all()}

    positions_data = []
    pad_width = 3 if batch.capacity > 99 else 2
    for seq in range(batch.start_roll_number, batch.end_roll_number + 1):
        res = existing_reservations.get(seq)
        status = res.status if res else 'available'
        is_mine = bool(res and res.session_key and res.session_key == current_session and status == 'reserved')
        is_selectable = (status in ['available', 'released']) or is_mine

        positions_data.append({
            'sequence': seq,
            'label': f"{seq:0{pad_width}d}",
            'registration_number': res.registration_number if res else batch.generate_registration_number(seq),
            'status': status,
            'status_display': res.get_status_display() if res else 'Available',
            'is_mine': is_mine,
            'is_selectable': is_selectable
        })

    summary_counts = batch.get_positions_summary()

    return JsonResponse({
        'success': True,
        'batch': {
            'id': batch.id,
            'name': batch.batch_name,
            'identifier': batch.batch_identifier,
            'course_id': batch.course.id,
            'course_name': batch.course.name,
            'course_code': batch.course_code,
            'department_id': batch.department.id,
            'department_name': batch.department.name,
            'prefix': batch.prefix,
            'capacity': batch.capacity,
            'start_roll_number': batch.start_roll_number,
            'end_roll_number': batch.end_roll_number,
            'current_semester': batch.current_semester,
            'admission_semester': batch.admission_semester,
            'enrollment_status': batch.enrollment_status,
        },
        'counts': summary_counts,
        'positions': positions_data,
    })


def reserve_roll_api(request):
    """
    Temporarily holds a roll sequence for 30 minutes during registration.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'}, status=405)

    batch_id = request.POST.get('batch_id')
    roll_sequence = request.POST.get('roll_sequence')
    name = request.POST.get('name', '').strip()
    email = request.POST.get('email', '').strip()

    if not batch_id or not roll_sequence:
        return JsonResponse({'success': False, 'error': 'batch_id and roll_sequence are required'}, status=400)

    try:
        roll_sequence = int(roll_sequence)
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid roll_sequence'}, status=400)

    batch = AcademicBatch.objects.filter(id=batch_id, is_active=True).first()
    if not batch:
        return JsonResponse({'success': False, 'error': 'Academic batch not found or inactive'}, status=404)

    if roll_sequence < batch.start_roll_number or roll_sequence > batch.end_roll_number:
        return JsonResponse({'success': False, 'error': f'Roll sequence must be between {batch.start_roll_number} and {batch.end_roll_number}'}, status=400)

    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    with transaction.atomic():
        now = timezone.now()
        # Clean expired
        batch.roll_reservations.filter(status='reserved', expires_at__lt=now).update(
            status='available', session_key='', reserved_by_email='', reserved_by_name='', expires_at=None
        )

        res, _ = RollNumberReservation.objects.select_for_update().get_or_create(
            batch=batch,
            roll_sequence=roll_sequence,
            defaults={
                'registration_number': batch.generate_registration_number(roll_sequence),
                'status': 'available'
            }
        )

        if res.status in ['assigned', 'pending']:
            return JsonResponse({'success': False, 'error': f'Roll position {res.registration_number} is already occupied or pending review.'}, status=409)

        if res.status == 'reserved' and res.session_key and res.session_key != session_key:
            return JsonResponse({'success': False, 'error': f'Roll position {res.registration_number} is currently reserved by another student.'}, status=409)

        # Release any other roll previously reserved in this batch by this same session
        RollNumberReservation.objects.filter(batch=batch, session_key=session_key, status='reserved').exclude(id=res.id).update(
            status='available', session_key='', reserved_by_email='', reserved_by_name='', expires_at=None
        )

        # Apply 30 minute reservation
        res.status = 'reserved'
        res.session_key = session_key
        res.reserved_by_name = name
        res.reserved_by_email = email
        res.reserved_at = now
        res.expires_at = now + timedelta(minutes=30)
        res.save()

        return JsonResponse({
            'success': True,
            'registration_number': res.registration_number,
            'roll_sequence': roll_sequence,
            'expires_at': res.expires_at.isoformat(),
            'expires_in_seconds': 1800,
            'message': f'Roll number {res.registration_number} temporarily held for 30 minutes.'
        })


@admin_required
def admin_batches_list(request):
    """
    Administrator batch overview dashboard with KPI cards and department/course filters.
    """
    batches = AcademicBatch.objects.all().select_related('department', 'course').annotate(
        total_reservations=Count('roll_reservations'),
        assigned_count=Count('roll_reservations', filter=Q(roll_reservations__status='assigned')),
        pending_count=Count('roll_reservations', filter=Q(roll_reservations__status='pending')),
    ).order_by('-admission_year', 'course_code', 'batch_name')

    dept_id = request.GET.get('department')
    if dept_id and dept_id.isdigit():
        batches = batches.filter(department_id=int(dept_id))
    course_id = request.GET.get('course')
    if course_id and course_id.isdigit():
        batches = batches.filter(course_id=int(course_id))
    status_filter = request.GET.get('status')
    if status_filter:
        batches = batches.filter(enrollment_status=status_filter)
    search = request.GET.get('search', '').strip()
    if search:
        batches = batches.filter(
            Q(batch_name__icontains=search) |
            Q(course_code__icontains=search) |
            Q(prefix__icontains=search) |
            Q(batch_identifier__icontains=search)
        )

    all_batches = AcademicBatch.objects.all()
    total_batches = all_batches.count()
    total_capacity = sum(b.capacity for b in all_batches)
    total_assigned = RollNumberReservation.objects.filter(status='assigned').count()
    total_pending = RollNumberReservation.objects.filter(status='pending').count()
    total_available = max(0, total_capacity - (total_assigned + total_pending))

    departments = Department.objects.all().order_by('name')
    courses = Course.objects.all().order_by('name')

    return render(request, 'accounts/admin_batches.html', {
        'batches': batches,
        'total_batches': total_batches,
        'total_capacity': total_capacity,
        'total_assigned': total_assigned,
        'total_pending': total_pending,
        'total_available': total_available,
        'departments': departments,
        'courses': courses,
        'selected_dept': dept_id,
        'selected_course': course_id,
        'selected_status': status_filter,
        'search_query': search,
    })


@admin_required
def admin_batch_create(request):
    """
    Create a new academic batch with auto-generated roll reservation matrix.
    """
    if request.method == 'POST':
        form = AcademicBatchForm(request.POST, user=request.user)
        if form.is_valid():
            batch = form.save()
            log_audit(request.user, 'BATCH_CREATED', None, request, f"Batch created: {batch.batch_name} (Prefix: {batch.prefix})")
            messages.success(request, f"Academic Batch '{batch.batch_name}' created successfully with {batch.capacity} roll allocation positions.")
            return redirect('admin_batch_detail', batch_id=batch.id)
    else:
        form = AcademicBatchForm(user=request.user)

    return render(request, 'accounts/admin_batch_form.html', {
        'form': form,
        'is_edit': False,
        'title': 'Create Academic Batch',
    })


@admin_required
def admin_batch_detail(request, batch_id):
    """
    Batch detail page displaying visual 4-state roll allocation grid and enrolled student roster.
    """
    batch = get_object_or_404(AcademicBatch.objects.select_related('department', 'course'), id=batch_id)

    # Clean expired
    now = timezone.now()
    batch.roll_reservations.filter(status='reserved', expires_at__lt=now).update(
        status='available', session_key='', reserved_by_email='', reserved_by_name='', expires_at=None
    )

    summary = batch.get_positions_summary()
    reservations = batch.roll_reservations.all().select_related('student_profile__user').order_by('roll_sequence')
    enrolled_students = StudentProfile.objects.filter(batch=batch).select_related('user', 'class_group').order_by('roll_sequence')

    return render(request, 'accounts/admin_batch_detail.html', {
        'batch': batch,
        'summary': summary,
        'reservations': reservations,
        'enrolled_students': enrolled_students,
    })


@admin_required
def admin_batch_edit(request, batch_id):
    """
    Edit batch parameters with strict identity protection.
    """
    batch = get_object_or_404(AcademicBatch, id=batch_id)
    if request.method == 'POST':
        form = AcademicBatchForm(request.POST, instance=batch, user=request.user)
        if form.is_valid():
            batch = form.save()
            log_audit(request.user, 'BATCH_UPDATED', None, request, f"Batch updated: {batch.batch_name}")
            messages.success(request, f"Batch '{batch.batch_name}' updated successfully.")
            return redirect('admin_batch_detail', batch_id=batch.id)
    else:
        form = AcademicBatchForm(instance=batch, user=request.user)

    return render(request, 'accounts/admin_batch_form.html', {
        'form': form,
        'batch': batch,
        'is_edit': True,
        'title': f'Edit Batch: {batch.batch_name}',
    })


@admin_required
def admin_batch_promote(request, batch_id):
    """
    Promote an academic batch and all its enrolled students to the next semester.
    Preserves batch identity, roll numbers, and prefixes while recording semester history.
    """
    batch = get_object_or_404(AcademicBatch, id=batch_id)
    if request.method == 'POST':
        form = BatchSemesterPromotionForm(request.POST)
        if form.is_valid():
            target_sem = str(form.cleaned_data['target_semester'])
            session = form.cleaned_data.get('academic_session', '')
            reason = form.cleaned_data.get('reason', '')
            old_sem = batch.current_semester

            with transaction.atomic():
                batch.current_semester = target_sem
                batch.save()

                students = StudentProfile.objects.filter(batch=batch)
                updated_count = 0
                for s in students:
                    prev_s_sem = s.semester
                    s.semester = target_sem
                    s.save()
                    StudentSemesterHistory.objects.create(
                        student=s,
                        batch=batch,
                        previous_semester=prev_s_sem,
                        new_semester=target_sem,
                        academic_session=session,
                        changed_by=request.user,
                        reason=reason
                    )
                    updated_count += 1

                StudentEnrollment.objects.filter(batch=batch).update(semester=target_sem)
                log_audit(request.user, 'BATCH_SEMESTER_PROMOTED', None, request, f"Promoted {batch.batch_name} from Sem {old_sem} to Sem {target_sem} ({updated_count} students).")

            messages.success(request, f"Batch '{batch.batch_name}' successfully advanced to Semester {target_sem}. {updated_count} students updated.")
            return redirect('admin_batch_detail', batch_id=batch.id)
    else:
        current_num = int(batch.current_semester) if batch.current_semester.isdigit() else 1
        next_sem = min(current_num + 1, batch.total_semesters)
        form = BatchSemesterPromotionForm(initial={'target_semester': next_sem})

    return render(request, 'accounts/admin_batch_promote.html', {
        'batch': batch,
        'form': form,
    })


@admin_required
def admin_roll_correction(request, batch_id=None):
    """
    Controlled administrative roll number reassignment.
    Atomically updates roll number, username, reservation, and enrollment with full audit log.
    """
    initial_batch = None
    if batch_id:
        initial_batch = get_object_or_404(AcademicBatch, id=batch_id)

    if request.method == 'POST':
        form = RollNumberCorrectionForm(request.POST)
        if form.is_valid():
            student = form.cleaned_data['student']
            new_seq = form.cleaned_data['new_roll_sequence']
            new_reg_num = form.cleaned_data['new_registration_number']
            target_res = form.cleaned_data.get('target_reservation')
            reason = form.cleaned_data['reason']
            batch = student.batch

            old_seq = student.roll_sequence
            old_reg = student.roll_number
            old_uname = student.user.username

            with transaction.atomic():
                # Release old reservation
                if old_seq:
                    old_res = RollNumberReservation.objects.filter(batch=batch, roll_sequence=old_seq).first()
                    if old_res:
                        old_res.status = 'released'
                        old_res.student_profile = None
                        old_res.session_key = ''
                        old_res.reserved_by_name = ''
                        old_res.reserved_by_email = ''
                        old_res.expires_at = None
                        old_res.save()

                # Assign new reservation
                if not target_res:
                    target_res, _ = RollNumberReservation.objects.get_or_create(
                        batch=batch,
                        roll_sequence=new_seq,
                        defaults={'registration_number': new_reg_num}
                    )
                target_res.status = 'assigned'
                target_res.student_profile = student
                target_res.session_key = ''
                target_res.reserved_by_name = student.full_name
                target_res.reserved_by_email = student.user.email
                target_res.expires_at = None
                target_res.save()

                # Update student profile
                student.roll_sequence = new_seq
                student.roll_number = new_reg_num
                student.save()

                # Update user username
                student.user.username = new_reg_num
                student.user.save()

                # Update StudentEnrollment
                StudentEnrollment.objects.filter(roll_number=old_reg).update(
                    roll_number=new_reg_num,
                    roll_sequence=new_seq
                )

                # Audit Log
                log_audit(
                    request.user,
                    'ROLL_NUMBER_CORRECTED',
                    student.user,
                    request,
                    f"Roll corrected: {old_reg} -> {new_reg_num} (Seq {old_seq} -> {new_seq}). Reason: {reason}"
                )

                # In-app notification
                send_notification(
                    recipient=student.user,
                    title="Institutional Roll Number Reassigned",
                    message=f"Your official roll number and username have been reassigned to {new_reg_num}. Reason: {reason}",
                    notification_type="general",
                    link="/accounts/profile/"
                )

            messages.success(request, f"Roll number successfully corrected for {student.full_name}: {old_reg} -> {new_reg_num}.")
            return redirect('admin_batch_detail', batch_id=batch.id)
    else:
        form = RollNumberCorrectionForm()
        if initial_batch:
            form.fields['student'].queryset = StudentProfile.objects.filter(batch=initial_batch).select_related('user', 'batch')

    recent_corrections = AuditLog.objects.filter(action='ROLL_NUMBER_CORRECTED').select_related('actor', 'target_user').order_by('-created_at')[:10]

    return render(request, 'accounts/admin_roll_correction.html', {
        'form': form,
        'initial_batch': initial_batch,
        'recent_corrections': recent_corrections,
    })


@admin_required
def admin_batch_export(request, batch_id):
    """
    Exports the academic batch allocation roster to Excel (.xlsx).
    """
    batch = get_object_or_404(AcademicBatch.objects.select_related('department', 'course'), id=batch_id)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"{batch.prefix} Roster"

    title_font = Font(name='Calibri', size=14, bold=True, color='1A365D')
    header_font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='1E3A8A', end_color='1E3A8A', fill_type='solid')

    ws.merge_cells('A1:G1')
    ws['A1'] = f"EPS MASTER ENROLLMENT ROSTER — {batch.batch_name} ({batch.prefix})"
    ws['A1'].font = title_font

    headers = ['Roll Seq', 'Registration Number / Username', 'Full Name', 'Email Address', 'Semester', 'Status', 'Assigned Date']
    ws.append([])
    ws.append(headers)

    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=3, column=col_num)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')

    reservations = batch.roll_reservations.all().select_related('student_profile__user').order_by('roll_sequence')
    for r in reservations:
        student = r.student_profile
        uname = student.user.username if (student and student.user) else r.registration_number
        fname = student.full_name if student else (r.reserved_by_name or '—')
        email = student.user.email if (student and student.user) else (r.reserved_by_email or '—')
        sem = student.semester if student else batch.current_semester
        assigned_date = student.user.date_joined.strftime('%Y-%m-%d') if (student and student.user) else '—'

        ws.append([
            r.roll_sequence,
            uname,
            fname,
            email,
            f"Sem {sem}",
            r.get_status_display(),
            assigned_date
        ])

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="EPS_Batch_{batch.prefix}_Roster.xlsx"'
    wb.save(response)
    return response


@teacher_required
def teacher_batches_list(request):
    """
    Teacher batch view: Scoped strictly to teacher's assigned department.
    """
    teacher_prof = getattr(request.user, 'teacher_profile', None)
    teacher_dept = (teacher_prof.department or '').strip() if teacher_prof else ''

    matching_dept = Department.objects.filter(Q(name__iexact=teacher_dept) | Q(code__iexact=teacher_dept)).first()
    if matching_dept:
        batches = AcademicBatch.objects.filter(department=matching_dept)
    else:
        batches = AcademicBatch.objects.filter(department__name__iexact=teacher_dept)

    batches = batches.select_related('department', 'course').order_by('-admission_year', 'course_code', 'batch_name')

    return render(request, 'accounts/teacher_batches.html', {
        'batches': batches,
        'teacher_dept': teacher_dept,
    })


@teacher_required
def teacher_batch_create(request):
    """
    Teacher batch creation: Strictly constrained to teacher's assigned department.
    """
    teacher_prof = getattr(request.user, 'teacher_profile', None)
    teacher_dept = (teacher_prof.department or '').strip() if teacher_prof else ''

    if request.method == 'POST':
        form = AcademicBatchForm(request.POST, user=request.user)
        if form.is_valid():
            batch = form.save()
            log_audit(request.user, 'BATCH_CREATED_TEACHER', None, request, f"Teacher created batch: {batch.batch_name}")
            messages.success(request, f"Batch '{batch.batch_name}' created successfully with {batch.capacity} roll slots.")
            return redirect('teacher_batch_detail', batch_id=batch.id)
    else:
        form = AcademicBatchForm(user=request.user)

    return render(request, 'accounts/teacher_batch_form.html', {
        'form': form,
        'teacher_dept': teacher_dept,
    })


@teacher_required
def teacher_batch_detail(request, batch_id):
    """
    Teacher batch detail: Departmental boundary enforcement and roll matrix inspection.
    """
    teacher_prof = getattr(request.user, 'teacher_profile', None)
    teacher_dept = (teacher_prof.department or '').strip().lower() if teacher_prof else ''

    batch = get_object_or_404(AcademicBatch.objects.select_related('department', 'course'), id=batch_id)

    # Department boundary check for non-admins
    is_admin = request.user.role == 'admin' or request.user.is_superuser or request.user.is_staff
    if not is_admin:
        dept_name = (batch.department.name or '').strip().lower()
        dept_code = (batch.department.code or '').strip().lower()
        if teacher_dept not in (dept_name, dept_code):
            return HttpResponseForbidden("Access denied: You are not authorized to view batches outside your assigned department.")

    now = timezone.now()
    batch.roll_reservations.filter(status='reserved', expires_at__lt=now).update(
        status='available', session_key='', reserved_by_email='', reserved_by_name='', expires_at=None
    )

    summary = batch.get_positions_summary()
    reservations = batch.roll_reservations.all().select_related('student_profile__user').order_by('roll_sequence')
    enrolled_students = StudentProfile.objects.filter(batch=batch).select_related('user', 'class_group').order_by('roll_sequence')

    return render(request, 'accounts/teacher_batch_detail.html', {
        'batch': batch,
        'summary': summary,
        'reservations': reservations,
        'enrolled_students': enrolled_students,
    })

