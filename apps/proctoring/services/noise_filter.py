from decimal import Decimal
from typing import Dict, Any, Tuple
from django.db import transaction
from apps.exam_engine.models import ExamAttempt, AttemptStatus
from apps.proctoring.models import (
    ProctoringEvent,
    ProctoringSummary,
    ProctoringEventType,
    EventSeverity,
)

# Operational noise filtering thresholds (Section 13)
BLUR_NOISE_THRESHOLD_SECONDS = 1.5
TRUST_SCORE_REVIEW_THRESHOLD = Decimal("75.00")


@transaction.atomic
def record_proctoring_event(
    attempt: ExamAttempt,
    event_type: str,
    duration_seconds: float = 0.0,
    metadata: Dict[str, Any] = None,
) -> Tuple[ProctoringEvent, ProctoringSummary]:
    """
    Ingests raw client proctoring events, applies noise filtering for transient
    operating system focus shifts, and recalculates candidate trust score.
    """
    if metadata is None:
        metadata = {}

    summary, _ = ProctoringSummary.objects.select_for_update().get_or_create(attempt=attempt)

    # 1. Evaluate Noise Filter
    is_noise = False
    severity = EventSeverity.WARNING
    penalty_points = Decimal("0.00")

    if event_type in [ProctoringEventType.TAB_SWITCH, ProctoringEventType.FULLSCREEN_EXIT]:
        if duration_seconds < BLUR_NOISE_THRESHOLD_SECONDS:
            is_noise = True
            severity = EventSeverity.INFO
            penalty_points = Decimal("0.00")
        else:
            if event_type == ProctoringEventType.FULLSCREEN_EXIT:
                penalty_points = Decimal("5.00")
                summary.fullscreen_exit_count += 1
            else:
                penalty_points = Decimal("4.00") + Decimal(str(round(duration_seconds / 10.0, 2)))
                summary.tab_switch_count += 1

            summary.total_out_of_focus_seconds += duration_seconds

    elif event_type in [ProctoringEventType.CLIPBOARD_COPY, ProctoringEventType.CLIPBOARD_PASTE]:
        summary.clipboard_violation_count += 1
        penalty_points = Decimal("5.00")
        severity = EventSeverity.WARNING

    elif event_type in [ProctoringEventType.DEVTOOLS_ATTEMPT, ProctoringEventType.AI_DEVICE_DETECTED, ProctoringEventType.AI_MULTIFACE]:
        summary.ai_anomaly_count += 1
        penalty_points = Decimal("15.00")
        severity = EventSeverity.CRITICAL

    elif event_type in [ProctoringEventType.AI_ABSENCE, ProctoringEventType.AI_GAZE_AWAY]:
        if duration_seconds < 2.0:
            is_noise = True
            severity = EventSeverity.INFO
        else:
            summary.ai_anomaly_count += 1
            penalty_points = Decimal("6.00")
            severity = EventSeverity.WARNING
    else:
        penalty_points = Decimal("2.00")

    # 2. Persist ProctoringEvent
    event = ProctoringEvent.objects.create(
        attempt=attempt,
        event_type=event_type,
        severity=severity,
        duration_seconds=duration_seconds,
        metadata=metadata,
        is_noise_filtered=is_noise,
    )

    # 3. Adjust Trust Score
    if not is_noise:
        new_score = summary.trust_score - penalty_points
        summary.trust_score = max(Decimal("0.00"), new_score)

        if summary.trust_score < TRUST_SCORE_REVIEW_THRESHOLD or severity == EventSeverity.CRITICAL:
            summary.requires_human_review = True

    summary.save()
    return event, summary
