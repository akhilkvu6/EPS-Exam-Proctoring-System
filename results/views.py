from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Avg, Max, Min, Count, Q
from decimal import Decimal
import csv

from .models import Result
from exams.models import Exam, ExamAttempt, StudentAnswer
from accounts.models import User
from accounts.decorators import (
    student_required, teacher_required, admin_required,
    log_audit, send_notification, check_teacher_exam_access
)


@student_required
def student_results(request):
    """Student view of their published examination results."""
    student = request.user
    # Master rule: Only published results are accessible to students
    published_results = Result.objects.filter(
        student=student,
        is_published=True
    ).select_related('exam', 'exam__subject')

    context = {
        'results': published_results,
    }
    return render(request, 'results/student_results.html', context)


@student_required
def student_result_detail(request, result_id):
    """Detailed score card and question-by-question review for published exams."""
    student = request.user
    result = get_object_or_404(Result, id=result_id, student=student, is_published=True)
    attempt = result.attempt

    answers = attempt.answers.select_related('question', 'selected_option').prefetch_related('question__options').all()

    context = {
        'result': result,
        'attempt': attempt,
        'exam': result.exam,
        'answers': answers,
    }
    return render(request, 'results/student_result_detail.html', context)


@teacher_required
def teacher_exam_results(request, exam_id):
    """Teacher examination analytics and student results list."""
    exam = get_object_or_404(Exam, id=exam_id)
    if not check_teacher_exam_access(request.user, exam):
        messages.error(request, 'Access denied: You do not have permission to view results for this examination.')
        return redirect('manage_exams')

    results = Result.objects.filter(exam=exam).select_related('student', 'student__student_profile', 'attempt')

    # Calculate statistics
    total_submissions = results.count()
    if total_submissions > 0:
        avg_score = results.aggregate(Avg('total_marks_obtained'))['total_marks_obtained__avg'] or 0.0
        max_score = results.aggregate(Max('total_marks_obtained'))['total_marks_obtained__max'] or 0.0
        min_score = results.aggregate(Min('total_marks_obtained'))['total_marks_obtained__min'] or 0.0
        pass_count = results.filter(is_passed=True).count()
        pass_percentage = round((pass_count / total_submissions) * 100, 1)
    else:
        avg_score = max_score = min_score = pass_count = pass_percentage = 0

    pending_manual_count = results.filter(grading_status='pending_manual').count()
    published_count = results.filter(is_published=True).count()

    context = {
        'exam': exam,
        'results': results,
        'total_submissions': total_submissions,
        'avg_score': round(avg_score, 2),
        'max_score': max_score,
        'min_score': min_score,
        'pass_count': pass_count,
        'pass_percentage': pass_percentage,
        'pending_manual_count': pending_manual_count,
        'published_count': published_count,
    }
    return render(request, 'results/teacher_exam_results.html', context)


@teacher_required
def grade_attempt(request, attempt_id):
    """Manual grading interface for descriptive and short-answer responses."""
    attempt = get_object_or_404(ExamAttempt, id=attempt_id)
    exam = attempt.exam
    if not check_teacher_exam_access(request.user, exam):
        messages.error(request, 'Access denied: You do not have permission to evaluate this examination attempt.')
        return redirect('manage_exams')

    answers = attempt.answers.select_related('question', 'selected_option').all()

    if request.method == 'POST':
        for ans in answers:
            if ans.question.question_type in ['short_answer', 'descriptive']:
                marks_key = f"marks_{ans.id}"
                feedback_key = f"feedback_{ans.id}"

                if marks_key in request.POST:
                    try:
                        awarded = Decimal(request.POST[marks_key].strip())
                        awarded = min(ans.question.marks, max(Decimal('0.0'), awarded))
                        ans.marks_awarded = awarded
                        ans.evaluator_feedback = request.POST.get(feedback_key, '').strip()
                        ans.is_evaluated = True
                        ans.save()
                    except Exception:
                        pass

        # Recalculate result safely without IntegrityError on multiple attempts
        result = Result.objects.filter(exam=exam, student=attempt.student).first()
        if result:
            result.attempt = attempt
            result.maximum_marks = exam.total_marks
            result.save()
        else:
            result = Result.objects.create(
                attempt=attempt,
                exam=exam,
                student=attempt.student,
                maximum_marks=exam.total_marks
            )
        result.recalculate()

        log_audit(request.user, 'MANUAL_GRADING_SAVED', attempt.student, request, f"Graded answers for {exam.title}")
        messages.success(request, f"Grades saved for {attempt.student.username}. Total score updated to {result.total_marks_obtained}.")
        return redirect('teacher_exam_results', exam_id=exam.id)

    context = {
        'attempt': attempt,
        'exam': exam,
        'answers': answers,
    }
    return render(request, 'results/grade_attempt.html', context)


@teacher_required
def toggle_result_publication(request, exam_id):
    """Publish or withhold results for an entire examination."""
    exam = get_object_or_404(Exam, id=exam_id)
    if not check_teacher_exam_access(request.user, exam):
        messages.error(request, 'Access denied: You do not have permission to modify result publication for this examination.')
        return redirect('manage_exams')

    action = request.POST.get('action')  # 'publish' or 'withhold'

    results = Result.objects.filter(exam=exam)

    if action == 'publish':
        now = timezone.now()
        results.update(
            is_published=True,
            published_at=now,
            published_by=request.user
        )

        # Notify all students in-app
        for r in results:
            send_notification(
                recipient=r.student,
                title=f"Results Published: {exam.title}",
                message=f"Official evaluation results for '{exam.title}' have been published. Your score: {r.total_marks_obtained}/{r.maximum_marks} ({'PASS' if r.is_passed else 'FAIL'}).",
                notification_type="result",
                link="/results/my-results/"
            )

        log_audit(request.user, 'RESULTS_PUBLISHED', None, request, f"Published results for {exam.title} ({results.count()} students)")
        messages.success(request, f"Results for '{exam.title}' published successfully! Students notified in-app.")

    elif action == 'withhold':
        results.update(is_published=False)
        log_audit(request.user, 'RESULTS_WITHHELD', None, request, f"Withheld results for {exam.title}")
        messages.info(request, f"Results for '{exam.title}' withheld from student view.")

    return redirect('teacher_exam_results', exam_id=exam.id)


@teacher_required
def export_results_csv(request, exam_id):
    """Generate and download a CSV report of examination results."""
    exam = get_object_or_404(Exam, id=exam_id)
    if not check_teacher_exam_access(request.user, exam):
        messages.error(request, 'Access denied: You do not have permission to export results for this examination.')
        return redirect('manage_exams')

    results = Result.objects.filter(exam=exam).select_related('student', 'student__student_profile')

    response = HttpResponse(content_type='text/csv')
    filename = f"Results_{exam.subject.code}_{exam.title.replace(' ', '_')}_{timezone.now().strftime('%Y%m%d')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        'Register / Roll Number',
        'Student Full Name',
        'Username',
        'Department',
        'Semester',
        'Total Marks Obtained',
        'Maximum Marks',
        'Percentage',
        'Result Status',
        'Grading Status',
        'Published Status',
        'Submission Timestamp'
    ])

    for r in results:
        prof = getattr(r.student, 'student_profile', None)
        writer.writerow([
            prof.roll_number if prof else 'N/A',
            prof.full_name if prof else r.student.get_full_name(),
            r.student.username,
            prof.department if prof else 'N/A',
            prof.semester if prof else 'N/A',
            r.total_marks_obtained,
            r.maximum_marks,
            f"{r.percentage}%",
            'PASS' if r.is_passed else 'FAIL',
            r.get_grading_status_display(),
            'Published' if r.is_published else 'Unpublished',
            r.attempt.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if r.attempt.submitted_at else 'N/A'
        ])

    return response


# ==============================================================================
# ADMINISTRATOR RESULTS & INSTITUTIONAL REPORTS OVERSIGHT
# ==============================================================================

@admin_required
def admin_results_overview(request):
    """Institutional overview of student examination performance across all courses."""
    results = Result.objects.all().select_related('exam', 'exam__subject', 'student', 'student__student_profile')

    total_results = results.count()
    published_results = results.filter(is_published=True).count()
    unpublished_results = total_results - published_results
    passed_count = results.filter(is_passed=True).count()
    failed_count = results.filter(is_passed=False).count()
    avg_pct = round(results.aggregate(avg=Avg('percentage'))['avg'] or 0, 1)

    # Exam-wise performance breakdown
    exams_data = []
    for exam in Exam.objects.all().select_related('subject', 'created_by').order_by('-start_time'):
        exam_res = results.filter(exam=exam)
        if exam_res.exists():
            exams_data.append({
                'exam': exam,
                'count': exam_res.count(),
                'passed': exam_res.filter(is_passed=True).count(),
                'failed': exam_res.filter(is_passed=False).count(),
                'avg_pct': round(exam_res.aggregate(avg=Avg('percentage'))['avg'] or 0, 1),
                'is_published': exam_res.filter(is_published=True).count() == exam_res.count(),
                'pending_manual': exam_res.filter(grading_status='pending_manual').count(),
            })

    context = {
        'total_results': total_results,
        'published_results': published_results,
        'unpublished_results': unpublished_results,
        'passed_count': passed_count,
        'failed_count': failed_count,
        'avg_pct': avg_pct,
        'exams_data': exams_data,
    }
    return render(request, 'results/admin_overview.html', context)


@admin_required
def admin_results_export(request):
    """Generate institutional reports and downloadable CSV exports."""
    report_type = request.GET.get('report')

    if report_type == 'results':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="eps_all_results_export.csv"'
        writer = csv.writer(response)
        writer.writerow(['Exam Title', 'Subject Code', 'Roll Number', 'Student Name', 'Username', 'Marks Obtained', 'Max Marks', 'Percentage', 'Status', 'Grading', 'Published', 'Date'])
        for r in Result.objects.all().select_related('exam', 'exam__subject', 'student', 'student__student_profile'):
            prof = getattr(r.student, 'student_profile', None)
            writer.writerow([
                r.exam.title,
                r.exam.subject.code,
                prof.roll_number if prof else 'N/A',
                prof.full_name if prof else r.student.get_full_name(),
                r.student.username,
                r.total_marks_obtained,
                r.maximum_marks,
                f"{r.percentage}%",
                'PASS' if r.is_passed else 'FAIL',
                r.get_grading_status_display(),
                'Yes' if r.is_published else 'No',
                r.created_at.strftime('%Y-%m-%d %H:%M')
            ])
        return response

    elif report_type == 'students':
        from accounts.models import StudentProfile
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="eps_students_directory.csv"'
        writer = csv.writer(response)
        writer.writerow(['Roll Number', 'Full Name', 'Username', 'Email', 'Department', 'Semester', 'Status', 'Registration Date'])
        for s in StudentProfile.objects.all().select_related('user'):
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

    elif report_type == 'teachers':
        from accounts.models import TeacherProfile
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="eps_faculty_directory.csv"'
        writer = csv.writer(response)
        writer.writerow(['Employee ID', 'Full Name', 'Username', 'Email', 'Department', 'Qualification', 'Institution', 'Status', 'Registration Date'])
        for t in TeacherProfile.objects.all().select_related('user'):
            writer.writerow([
                t.employee_id,
                t.user.get_full_name() or t.user.username,
                t.user.username,
                t.user.email,
                t.department,
                t.qualification,
                t.institution,
                t.verification_status,
                t.user.date_joined.strftime('%Y-%m-%d %H:%M')
            ])
        return response

    elif report_type == 'incidents':
        from exams.models import ProctoringIncident
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="eps_proctoring_incidents.csv"'
        writer = csv.writer(response)
        writer.writerow(['Timestamp', 'Candidate Username', 'Exam Title', 'Incident Category', 'Severity', 'Details'])
        for inc in ProctoringIncident.objects.all().select_related('attempt', 'attempt__student', 'attempt__exam'):
            writer.writerow([
                inc.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                inc.attempt.student.username,
                inc.attempt.exam.title,
                inc.get_event_type_display(),
                inc.severity.upper(),
                inc.details
            ])
        return response

    elif report_type == 'audit':
        from accounts.models import AuditLog
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="eps_audit_logs.csv"'
        writer = csv.writer(response)
        writer.writerow(['Timestamp', 'Actor', 'Action', 'Target User', 'IP Address', 'Details'])
        for log in AuditLog.objects.all().select_related('actor', 'target_user'):
            writer.writerow([
                log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                log.actor.username if log.actor else 'System',
                log.action,
                log.target_user.username if log.target_user else 'N/A',
                log.ip_address or 'N/A',
                log.details
            ])
        return response

    # Render report dashboard
    return render(request, 'results/admin_export.html', {
        'total_results': Result.objects.count(),
        'total_students': User.objects.filter(role='student').count(),
        'total_teachers': User.objects.filter(role='teacher').count(),
        'total_incidents': Exam.objects.count(),
    })
