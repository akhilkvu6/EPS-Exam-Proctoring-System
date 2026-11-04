from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.accounts.decorators import active_user_required
from apps.examinations.forms import (
    ExaminationForm,
    ExamSectionForm,
    AddQuestionToSectionForm,
)
from apps.examinations.models import (
    Examination,
    ExamSection,
    ExamQuestion,
    CandidateAssignment,
    ExamStatus,
)
from apps.examinations.services.scheduling import (
    check_teacher_exam_access,
    add_question_to_section,
    publish_examination,
)
from apps.academics.services.scoping import (
    get_teacher_assigned_subjects,
    get_teacher_assigned_batches,
)
from apps.question_bank.models import Question


@login_required
@active_user_required
def exam_list_view(request):
    """Lists examinations accessible to the teacher or admin."""
    user = request.user
    if user.role not in ["ADMIN", "TEACHER"]:
        raise PermissionDenied("Only faculty and administrators can access examination scheduling.")

    if user.role == "TEACHER":
        subjects = get_teacher_assigned_subjects(user)
        batches = get_teacher_assigned_batches(user)
        exams = Examination.objects.filter(subject__in=subjects, batch__in=batches)
    else:
        exams = Examination.objects.all()

    # Filter by status
    status_filter = request.GET.get("status")
    if status_filter:
        exams = exams.filter(status=status_filter)

    context = {
        "exams": exams.select_related("subject", "batch", "created_by"),
        "statuses": ExamStatus.choices,
        "selected_status": status_filter,
    }
    return render(request, "examinations/exam_list.html", context)


@login_required
@active_user_required
@transaction.atomic
def exam_create_view(request):
    """Creates a new Examination record."""
    user = request.user
    if user.role not in ["ADMIN", "TEACHER"]:
        raise PermissionDenied("Permission denied.")

    if request.method == "POST":
        form = ExaminationForm(request.POST, user=user)
        if form.is_valid():
            exam = form.save(commit=False)
            if not check_teacher_exam_access(user, exam):
                raise PermissionDenied("You are not assigned to instruct this subject/batch.")

            exam.created_by = user
            exam.status = ExamStatus.DRAFT
            exam.save()

            # Create default Section 1
            ExamSection.objects.create(
                examination=exam,
                title="Section A: Core Assessment",
                order=1,
            )

            messages.success(request, f"Examination '{exam.title}' initiated. Please configure sections and questions.")
            return redirect("examinations:exam_detail", pk=exam.pk)
    else:
        form = ExaminationForm(user=user)

    return render(request, "examinations/exam_form.html", {"form": form, "is_edit": False})


@login_required
@active_user_required
def exam_detail_view(request, pk):
    """Full examination management overview (sections, snapshots, roster, publish action)."""
    user = request.user
    exam = get_object_or_404(
        Examination.objects.select_related("subject", "batch", "created_by"),
        pk=pk,
    )

    if not check_teacher_exam_access(user, exam):
        raise PermissionDenied("Access to this examination is restricted.")

    sections = exam.sections.prefetch_related(
        "exam_questions__question",
        "exam_questions__snapshot",
    ).all()

    total_questions = sum(s.exam_questions.count() for s in sections)
    candidates_count = exam.assigned_candidates.count()

    context = {
        "exam": exam,
        "sections": sections,
        "total_questions": total_questions,
        "candidates_count": candidates_count,
        "is_editable": exam.status in [ExamStatus.DRAFT, ExamStatus.CONFIGURED],
    }
    return render(request, "examinations/exam_detail.html", context)


@login_required
@active_user_required
@transaction.atomic
def exam_add_section_view(request, pk):
    """Adds a new section to an examination in draft/configured status."""
    user = request.user
    exam = get_object_or_404(Examination, pk=pk)

    if not check_teacher_exam_access(user, exam):
        raise PermissionDenied("Permission denied.")
    if exam.status not in [ExamStatus.DRAFT, ExamStatus.CONFIGURED]:
        messages.error(request, "Cannot modify sections for a locked or published examination.")
        return redirect("examinations:exam_detail", pk=exam.pk)

    if request.method == "POST":
        form = ExamSectionForm(request.POST)
        if form.is_valid():
            sec = form.save(commit=False)
            sec.examination = exam
            sec.save()
            messages.success(request, f"Section '{sec.title}' added.")
            return redirect("examinations:exam_detail", pk=exam.pk)
    else:
        next_order = exam.sections.count() + 1
        form = ExamSectionForm(initial={"order": next_order})

    return render(request, "examinations/exam_section_form.html", {"form": form, "exam": exam})


@login_required
@active_user_required
@transaction.atomic
def exam_add_question_view(request, exam_pk, section_pk):
    """Attaches a question from the question bank to a section, locking its QuestionSnapshot."""
    user = request.user
    exam = get_object_or_404(Examination, pk=exam_pk)
    section = get_object_or_404(ExamSection, pk=section_pk, examination=exam)

    if not check_teacher_exam_access(user, exam):
        raise PermissionDenied("Permission denied.")
    if exam.status not in [ExamStatus.DRAFT, ExamStatus.CONFIGURED]:
        messages.error(request, "Cannot add questions to an active or published examination.")
        return redirect("examinations:exam_detail", pk=exam.pk)

    if request.method == "POST":
        form = AddQuestionToSectionForm(request.POST, subject=exam.subject)
        if form.is_valid():
            question = form.cleaned_data["question"]
            marks = form.cleaned_data.get("marks")
            negative_marks = form.cleaned_data.get("negative_marks")

            try:
                add_question_to_section(
                    section=section,
                    question=question,
                    marks=marks,
                    negative_marks=negative_marks,
                )
                if exam.status == ExamStatus.DRAFT:
                    exam.status = ExamStatus.CONFIGURED
                    exam.save(update_fields=["status"])

                messages.success(request, f"Question '{question.title}' attached and version snapshot locked.")
                return redirect("examinations:exam_detail", pk=exam.pk)
            except Exception as e:
                messages.error(request, f"Error attaching question: {str(e)}")
    else:
        form = AddQuestionToSectionForm(subject=exam.subject)

    return render(
        request,
        "examinations/exam_add_question.html",
        {"form": form, "exam": exam, "section": section},
    )


@login_required
@active_user_required
@transaction.atomic
def exam_publish_view(request, pk):
    """Validates, locks snapshots, provisions candidate roster, and schedules exam."""
    user = request.user
    exam = get_object_or_404(Examination, pk=pk)

    if not check_teacher_exam_access(user, exam):
        raise PermissionDenied("Permission denied.")

    if request.method == "POST":
        try:
            success, msg, count = publish_examination(exam, triggered_by=user)
            if success:
                messages.success(request, msg)
            else:
                messages.error(request, msg)
        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, "message") else e))

        return redirect("examinations:exam_detail", pk=exam.pk)

    return render(request, "examinations/exam_confirm_publish.html", {"exam": exam})


@login_required
@active_user_required
def exam_candidate_roster_view(request, pk):
    """Displays candidate assignments with eligibility toggles and accommodations."""
    user = request.user
    exam = get_object_or_404(Examination, pk=pk)

    if not check_teacher_exam_access(user, exam):
        raise PermissionDenied("Permission denied.")

    candidates = exam.assigned_candidates.select_related("student", "student__student_profile").all()

    return render(
        request,
        "examinations/exam_roster.html",
        {"exam": exam, "candidates": candidates},
    )
