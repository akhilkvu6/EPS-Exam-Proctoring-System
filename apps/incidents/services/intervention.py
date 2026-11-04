from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.exam_engine.models import ExamAttempt, AttemptStatus
from apps.incidents.models import (
    InvigilatorIntervention,
    InterventionAction,
    IncidentReviewRecord,
    FinalDisposition,
)
from apps.proctoring.models import ProctoringSummary


@transaction.atomic
def issue_warning(
    attempt: ExamAttempt,
    invigilator: User,
    message: str,
    notes: str = "",
) -> InvigilatorIntervention:
    """
    Issues an official urgent integrity warning dispatched to candidate exam room.
    """
    intervention = InvigilatorIntervention.objects.create(
        attempt=attempt,
        invigilator=invigilator,
        action_type=InterventionAction.OFFICIAL_WARNING,
        message_to_candidate=message,
        notes=notes,
    )
    return intervention


@transaction.atomic
def grant_time_extension(
    attempt: ExamAttempt,
    invigilator: User,
    minutes: int,
    notes: str = "",
) -> InvigilatorIntervention:
    """
    Extends server-authoritative timer for a candidate experiencing verified technical disruptions.
    """
    locked_attempt = ExamAttempt.objects.select_for_update().get(id=attempt.id)
    locked_attempt.expires_at += timedelta(minutes=minutes)
    locked_attempt.save(update_fields=["expires_at", "updated_at"])

    intervention = InvigilatorIntervention.objects.create(
        attempt=locked_attempt,
        invigilator=invigilator,
        action_type=InterventionAction.EXTEND_TIME,
        granted_extra_minutes=minutes,
        message_to_candidate=f"An invigilator has extended your examination timer by {minutes} minutes.",
        notes=notes,
    )
    return intervention


@transaction.atomic
def terminate_attempt_for_cause(
    attempt: ExamAttempt,
    invigilator: User,
    reason: str,
) -> InvigilatorIntervention:
    """
    Immediately expels and terminates a candidate examination attempt for severe security breaches.
    """
    locked_attempt = ExamAttempt.objects.select_for_update().get(id=attempt.id)
    locked_attempt.status = AttemptStatus.TERMINATED_SECURITY
    locked_attempt.submitted_at = timezone.now()
    locked_attempt.save(update_fields=["status", "submitted_at", "updated_at"])

    intervention = InvigilatorIntervention.objects.create(
        attempt=locked_attempt,
        invigilator=invigilator,
        action_type=InterventionAction.FORCE_TERMINATE,
        message_to_candidate=f"Your examination has been terminated by the proctor: {reason}",
        notes=reason,
    )

    summary, _ = ProctoringSummary.objects.get_or_create(attempt=locked_attempt)
    summary.requires_human_review = True
    summary.review_decision = "TERMINATED"
    summary.save(update_fields=["requires_human_review", "review_decision"])

    return intervention


@transaction.atomic
def adjudicate_incident(
    attempt: ExamAttempt,
    reviewer: User,
    disposition: str,
    penalty_percentage: Decimal = Decimal("0.00"),
    findings: str = "",
) -> IncidentReviewRecord:
    """
    Formal adjudication of suspicious proctoring incident records.
    """
    record, _ = IncidentReviewRecord.objects.update_or_create(
        attempt=attempt,
        defaults={
            "reviewer": reviewer,
            "final_disposition": disposition,
            "penalty_percentage": penalty_percentage,
            "findings_summary": findings,
        },
    )

    summary, _ = ProctoringSummary.objects.get_or_create(attempt=attempt)
    summary.review_decision = disposition
    summary.review_notes = findings
    summary.save(update_fields=["review_decision", "review_notes"])

    return record
