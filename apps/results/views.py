from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.decorators import active_user_required
from apps.examinations.models import Examination, ExamStatus
from apps.examinations.services.scheduling import check_teacher_exam_access
from apps.results.models import ExaminationResult
from apps.results.services.pdf_generator import generate_scorecard_pdf
from apps.results.services.publisher import publish_examination_results


@login_required
@active_user_required
def student_results_list_view(request):
    """Lists published examination results for the authenticated student."""
    user = request.user
    results = ExaminationResult.objects.filter(
        student=user,
        is_published=True,
    ).select_related("examination", "examination__subject")

    return render(request, "results/student_results.html", {"results": results})


@login_required
@active_user_required
def scorecard_view(request, result_id):
    """Web scorecard display for a published result."""
    user = request.user
    result = get_object_or_404(
        ExaminationResult.objects.select_related(
            "examination",
            "examination__subject",
            "student",
            "student__student_profile",
        ),
        id=result_id,
        is_published=True,
    )

    # Permission check: student owner or faculty/admin
    if user != result.student and user.role not in ["ADMIN", "TEACHER"]:
        raise PermissionDenied("Access to this scorecard is restricted.")

    return render(request, "results/scorecard.html", {"result": result})


@login_required
@active_user_required
def download_scorecard_pdf_view(request, result_id):
    """Generates and streams cryptographic PDF scorecard."""
    user = request.user
    result = get_object_or_404(
        ExaminationResult.objects.select_related(
            "examination",
            "examination__subject",
            "examination__batch",
            "student",
            "student__student_profile",
        ),
        id=result_id,
        is_published=True,
    )

    if user != result.student and user.role not in ["ADMIN", "TEACHER"]:
        raise PermissionDenied("Access to this scorecard is restricted.")

    pdf_bytes = generate_scorecard_pdf(result)
    roll = getattr(result.student, "student_profile", None)
    roll_str = roll.roll_number if roll else result.student.username
    filename = f"Scorecard_{result.examination.code}_{roll_str}.pdf"

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


def public_verify_result_view(request, result_id):
    """
    Public verification portal for employers, registrars, and students to authenticate
    cryptographic transcripts without authentication.
    """
    result = get_object_or_404(
        ExaminationResult.objects.select_related(
            "examination",
            "examination__subject",
            "student",
            "student__student_profile",
        ),
        id=result_id,
        is_published=True,
    )

    return render(request, "results/verify.html", {"result": result})


@login_required
@active_user_required
@require_POST
def publish_results_view(request, exam_pk):
    """Publishes official examination results across the candidate cohort."""
    user = request.user
    exam = get_object_or_404(Examination, pk=exam_pk)

    if not check_teacher_exam_access(user, exam):
        raise PermissionDenied("Unauthorized to publish results for this examination.")

    success, message, count = publish_examination_results(exam, published_by=user)
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect("evaluation:exam_overview", exam_pk=exam.pk)
