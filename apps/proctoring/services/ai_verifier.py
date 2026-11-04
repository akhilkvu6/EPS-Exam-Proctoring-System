from decimal import Decimal
from typing import Dict, Any, Tuple
from django.db import transaction
from apps.exam_engine.models import ExamAttempt
from apps.proctoring.models import ProctoringEvent, ProctoringSummary, ProctoringEventType, EventSeverity
from apps.proctoring.services.noise_filter import record_proctoring_event


def verify_and_log_ai_telemetry(
    attempt: ExamAttempt,
    anomaly_type: str,
    duration_seconds: float,
    metadata: Dict[str, Any] = None,
) -> Tuple[ProctoringEvent, ProctoringSummary]:
    """
    Ingests client-side computer vision metadata events (strictly metadata, zero video data).
    Validates event taxonomy and updates candidate integrity scoring.
    """
    valid_ai_types = [
        ProctoringEventType.AI_ABSENCE,
        ProctoringEventType.AI_MULTIFACE,
        ProctoringEventType.AI_GAZE_AWAY,
        ProctoringEventType.AI_DEVICE_DETECTED,
    ]

    if anomaly_type not in valid_ai_types:
        raise ValueError(f"Unrecognized AI proctoring telemetry event: {anomaly_type}")

    # Ensure metadata does not contain raw video or binary blobs
    sanitized_metadata = {}
    if metadata and isinstance(metadata, dict):
        for k, v in metadata.items():
            if k in ["video", "frame_bytes", "stream"]:
                continue
            sanitized_metadata[k] = v

    return record_proctoring_event(
        attempt=attempt,
        event_type=anomaly_type,
        duration_seconds=duration_seconds,
        metadata=sanitized_metadata,
    )
