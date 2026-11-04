import copy
from typing import Dict, Any, Optional
from decimal import Decimal
from django.db import transaction
from apps.question_bank.models import Question, QuestionSnapshot


def serialize_question_to_dict(question: Question, include_solutions: bool = True) -> Dict[str, Any]:
    """
    Serializes a Question instance and its related options into an immutable dictionary.
    """
    options_data = []
    for opt in question.options.all().order_by("order", "id"):
        item = {
            "id": opt.id,
            "option_text": opt.option_text,
            "order": opt.order,
        }
        if include_solutions:
            item["is_correct"] = opt.is_correct
        options_data.append(item)

    data: Dict[str, Any] = {
        "question_id": question.id,
        "version": question.version,
        "subject_id": question.subject_id,
        "subject_code": question.subject.code,
        "subject_name": question.subject.name,
        "category_id": question.category_id,
        "category_name": question.category.name if question.category else None,
        "author_id": question.author_id,
        "author_name": (
            question.author.get_full_name() or question.author.username
            if question.author
            else "System"
        ),
        "question_type": question.question_type,
        "difficulty": question.difficulty,
        "title": question.title,
        "content": question.content,
        "image_url": question.image.url if question.image else None,
        "default_marks": str(question.default_marks),
        "negative_marks": str(question.negative_marks),
        "options": options_data,
        "created_at": question.created_at.isoformat(),
        "updated_at": question.updated_at.isoformat(),
    }

    if include_solutions:
        data["explanation"] = question.explanation
        data["rubric"] = question.rubric
        data["numerical_target"] = question.numerical_target
        data["numerical_tolerance"] = question.numerical_tolerance

    return data


@transaction.atomic
def create_or_get_question_snapshot(question: Question) -> QuestionSnapshot:
    """
    Retrieves or atomically creates an immutable versioned snapshot for a given question.
    """
    snapshot = QuestionSnapshot.objects.filter(
        question=question,
        version=question.version,
    ).first()

    if not snapshot:
        full_data = serialize_question_to_dict(question, include_solutions=True)
        snapshot = QuestionSnapshot.objects.create(
            question=question,
            version=question.version,
            snapshot_data=full_data,
        )
    return snapshot


def get_student_safe_snapshot_data(snapshot_or_data: Any) -> Dict[str, Any]:
    """
    Returns a candidate-safe dictionary guaranteed never to leak solutions,
    correct options, explanations, numerical targets, or rubrics.
    """
    if isinstance(snapshot_or_data, QuestionSnapshot):
        raw_data = snapshot_or_data.snapshot_data
    elif isinstance(snapshot_or_data, dict):
        raw_data = snapshot_or_data
    else:
        raise ValueError("Expected QuestionSnapshot instance or dictionary")

    safe_copy = copy.deepcopy(raw_data)

    # Strip confidential answer keys and grader guides
    safe_copy.pop("explanation", None)
    safe_copy.pop("rubric", None)
    safe_copy.pop("numerical_target", None)
    safe_copy.pop("numerical_tolerance", None)

    # Strip option correct indicators
    if "options" in safe_copy and isinstance(safe_copy["options"], list):
        for opt in safe_copy["options"]:
            opt.pop("is_correct", None)

    return safe_copy
