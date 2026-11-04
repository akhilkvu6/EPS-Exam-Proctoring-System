from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.accounts.decorators import active_user_required
from apps.academics.models import Subject
from apps.academics.services.scoping import get_teacher_assigned_subjects as get_teacher_subjects
from apps.question_bank.forms import QuestionForm, QuestionOptionFormSet
from apps.question_bank.models import (
    Question,
    QuestionOption,
    QuestionType,
    QuestionDifficulty,
    QuestionSnapshot,
)
from apps.question_bank.services.snapshot import (
    create_or_get_question_snapshot,
    get_student_safe_snapshot_data,
)


def _check_subject_access(user, subject):
    """Verifies that the user has authority to manage items for the subject."""
    if user.role == "ADMIN":
        return True
    if user.role == "TEACHER":
        teacher_subjects = get_teacher_subjects(user)
        return subject in teacher_subjects
    return False


@login_required
@active_user_required
def question_list_view(request):
    """Lists questions scoped to the teacher's assigned subjects or all subjects for Admin."""
    user = request.user
    if user.role not in ["ADMIN", "TEACHER"]:
        raise PermissionDenied("Only faculty and administrators can access the question bank.")

    if user.role == "TEACHER":
        allowed_subjects = get_teacher_subjects(user)
        questions = Question.objects.filter(subject__in=allowed_subjects, is_archived=False)
    else:
        allowed_subjects = Subject.objects.filter(is_active=True)
        questions = Question.objects.filter(is_archived=False)

    # Filtering
    subject_id = request.GET.get("subject")
    q_type = request.GET.get("type")
    diff = request.GET.get("difficulty")
    search = request.GET.get("q")

    if subject_id:
        questions = questions.filter(subject_id=subject_id)
    if q_type:
        questions = questions.filter(question_type=q_type)
    if diff:
        questions = questions.filter(difficulty=diff)
    if search:
        questions = questions.filter(
            Q(title__icontains=search) | Q(content__icontains=search)
        )

    context = {
        "questions": questions.select_related("subject", "category", "author"),
        "subjects": allowed_subjects,
        "question_types": QuestionType.choices,
        "difficulties": QuestionDifficulty.choices,
        "selected_subject": subject_id,
        "selected_type": q_type,
        "selected_difficulty": diff,
        "search_query": search or "",
        "total_count": questions.count(),
    }
    return render(request, "question_bank/question_list.html", context)


@login_required
@active_user_required
@transaction.atomic
def question_create_view(request):
    """Creates a new question with dynamic options and generates an initial snapshot."""
    user = request.user
    if user.role not in ["ADMIN", "TEACHER"]:
        raise PermissionDenied("Only faculty and administrators can author questions.")

    if request.method == "POST":
        form = QuestionForm(request.POST, request.FILES, user=user)
        formset = QuestionOptionFormSet(request.POST)

        if form.is_valid():
            subject = form.cleaned_data["subject"]
            if not _check_subject_access(user, subject):
                raise PermissionDenied("You do not have permission to author questions for this subject.")

            question = form.save(commit=False)
            question.author = user
            question.version = 1
            question.save()

            formset.instance = question
            if formset.is_valid():
                formset.save()
                # Create initial immutable snapshot
                create_or_get_question_snapshot(question)
                messages.success(request, f"Question '{question.title}' created and version 1 snapshot locked.")
                return redirect("question_bank:question_list")
            else:
                messages.error(request, "Please correct the errors in the option set.")
    else:
        initial = {}
        if request.GET.get("subject"):
            initial["subject"] = request.GET.get("subject")
        form = QuestionForm(initial=initial, user=user)
        formset = QuestionOptionFormSet()

    return render(
        request,
        "question_bank/question_form.html",
        {"form": form, "formset": formset, "is_edit": False},
    )


@login_required
@active_user_required
@transaction.atomic
def question_edit_view(request, pk):
    """Updates an existing question and increments its immutable version."""
    user = request.user
    question = get_object_or_404(Question, pk=pk)

    if not _check_subject_access(user, question.subject):
        raise PermissionDenied("You do not have permission to modify questions for this subject.")

    if request.method == "POST":
        form = QuestionForm(request.POST, request.FILES, instance=question, user=user)
        formset = QuestionOptionFormSet(request.POST, instance=question)

        if form.is_valid():
            new_subject = form.cleaned_data["subject"]
            if not _check_subject_access(user, new_subject):
                raise PermissionDenied("You cannot reassign this question to an unauthorized subject.")

            # Increment version to protect exam snapshot immutability
            updated_question = form.save(commit=False)
            updated_question.version += 1
            updated_question.save()

            if formset.is_valid():
                formset.save()
                create_or_get_question_snapshot(updated_question)
                messages.success(
                    request,
                    f"Question updated successfully. New immutable version v{updated_question.version} created.",
                )
                return redirect("question_bank:question_list")
            else:
                messages.error(request, "Please review the option errors.")
    else:
        form = QuestionForm(instance=question, user=user)
        formset = QuestionOptionFormSet(instance=question)

    return render(
        request,
        "question_bank/question_form.html",
        {
            "form": form,
            "formset": formset,
            "question": question,
            "is_edit": True,
        },
    )


@login_required
@active_user_required
def question_detail_view(request, pk):
    """Previews a question, including option details, rubrics, snapshots and student-safe simulation."""
    user = request.user
    question = get_object_or_404(Question, pk=pk)

    if not _check_subject_access(user, question.subject):
        raise PermissionDenied("You do not have permission to view this question.")

    snapshot = create_or_get_question_snapshot(question)
    student_safe_data = get_student_safe_snapshot_data(snapshot)
    snapshots = question.snapshots.all()

    return render(
        request,
        "question_bank/question_detail.html",
        {
            "question": question,
            "options": question.options.all(),
            "snapshot": snapshot,
            "student_safe_data": student_safe_data,
            "snapshots": snapshots,
        },
    )


@login_required
@active_user_required
@transaction.atomic
def question_duplicate_view(request, pk):
    """Clones an existing question and its options for fast template authoring."""
    user = request.user
    original = get_object_or_404(Question, pk=pk)

    if not _check_subject_access(user, original.subject):
        raise PermissionDenied("Permission denied to clone this question.")

    cloned = Question.objects.create(
        subject=original.subject,
        category=original.category,
        author=user,
        question_type=original.question_type,
        difficulty=original.difficulty,
        title=f"{original.title} (Copy)",
        content=original.content,
        default_marks=original.default_marks,
        negative_marks=original.negative_marks,
        explanation=original.explanation,
        rubric=original.rubric,
        numerical_target=original.numerical_target,
        numerical_tolerance=original.numerical_tolerance,
        version=1,
    )

    for opt in original.options.all():
        QuestionOption.objects.create(
            question=cloned,
            option_text=opt.option_text,
            is_correct=opt.is_correct,
            order=opt.order,
        )

    create_or_get_question_snapshot(cloned)
    messages.success(request, f"Successfully cloned '{original.title}' as '{cloned.title}'.")
    return redirect("question_bank:question_edit", pk=cloned.pk)


@login_required
@active_user_required
def question_archive_view(request, pk):
    """Soft archives a question to prevent future additions to exams."""
    user = request.user
    question = get_object_or_404(Question, pk=pk)

    if not _check_subject_access(user, question.subject):
        raise PermissionDenied("Permission denied to archive this question.")

    if request.method == "POST":
        question.is_archived = True
        question.save(update_fields=["is_archived"])
        messages.info(request, f"Question '{question.title}' has been archived.")
        return redirect("question_bank:question_list")

    return render(
        request,
        "question_bank/question_confirm_archive.html",
        {"question": question},
    )
