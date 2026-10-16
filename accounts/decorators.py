from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from .models import AuditLog, Notification


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_audit(actor, action, target_user=None, request=None, details=''):
    ip = get_client_ip(request) if request else None
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        target_user=target_user,
        ip_address=ip,
        details=details
    )


def send_notification(recipient, title, message, notification_type='system', link=''):
    """Creates an in-application notification for the recipient. No email is used."""
    return Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link
    )


def student_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('common_login')
        
        if request.user.role != 'student':
            messages.error(request, 'Access restricted to student accounts.')
            if request.user.role == 'teacher':
                return redirect('teacher_dashboard')
            elif request.user.is_admin_user:
                return redirect('admin_dashboard')
            return redirect('common_login')
        
        # Check approval status
        if hasattr(request.user, 'student_profile'):
            status = request.user.student_profile.verification_status
            if status != 'approved':
                return redirect('account_status')
        else:
            return redirect('account_status')
            
        return view_func(request, *args, **kwargs)
    return wrapper


def teacher_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('common_login')
        
        if request.user.role != 'teacher':
            messages.error(request, 'Access restricted to teacher accounts.')
            if request.user.role == 'student':
                return redirect('student_dashboard')
            elif request.user.is_admin_user:
                return redirect('admin_dashboard')
            return redirect('common_login')
        
        # Check approval status
        if hasattr(request.user, 'teacher_profile'):
            status = request.user.teacher_profile.verification_status
            if status != 'approved':
                return redirect('account_status')
        else:
            return redirect('account_status')
            
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('common_login')
        
        if not (request.user.role == 'admin' or request.user.is_superuser or request.user.is_staff):
            messages.error(request, 'Access restricted to institutional administrators.')
            if request.user.role == 'student':
                return redirect('student_dashboard')
            elif request.user.role == 'teacher':
                return redirect('teacher_dashboard')
            return redirect('common_login')
            
        return view_func(request, *args, **kwargs)
    return wrapper


def check_teacher_exam_access(user, exam):
    """
    Verifies that the authenticated user has authorization to access/modify/grade the exam.
    Rules:
    - Superuser or role == 'admin': Allowed
    - Exam creator (exam.created_by == user): Allowed
    - Teacher whose department matches exam.subject.department (name or code): Allowed
    - Otherwise: Denied (False)
    """
    if hasattr(exam, 'is_accessible_by_teacher'):
        return exam.is_accessible_by_teacher(user)
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.role == 'admin':
        return True
    if user.role != 'teacher':
        return False
    if exam.created_by_id == user.id:
        return True
    if hasattr(user, 'teacher_profile') and getattr(exam, 'subject', None) and getattr(exam.subject, 'department', None):
        teacher_dept = (user.teacher_profile.department or '').strip().lower()
        dept_name = exam.subject.department.name.strip().lower()
        dept_code = exam.subject.department.code.strip().lower()
        return bool(teacher_dept and (teacher_dept == dept_name or teacher_dept == dept_code))
    return False
