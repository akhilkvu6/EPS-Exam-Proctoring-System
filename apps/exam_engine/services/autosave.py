from typing import List, Dict, Any, Tuple
from django.db import transaction
from django.utils import timezone
from apps.exam_engine.models import ExamAttempt, AttemptQuestion, AttemptStatus


@transaction.atomic
def process_batch_answer_sync(
    attempt: ExamAttempt,
    updates: List[Dict[str, Any]],
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """
    Processes an array of candidate answer updates from the client offline/online journal.
    Uses select_for_update on AttemptQuestion to guarantee concurrency-safe persistence.
    """
    if attempt.status != AttemptStatus.IN_PROGRESS:
        return False, [], f"Cannot sync answers. Attempt is in status: {attempt.get_status_display()}"

    if attempt.is_expired():
        from apps.exam_engine.services.delivery import submit_attempt
        submit_attempt(attempt, is_auto=True)
        return False, [], "Examination timer has expired. Attempt auto-submitted."

    results = []
    # Lock attempt questions for this attempt
    questions_map = {
        str(q.id): q
        for q in AttemptQuestion.objects.select_for_update().filter(attempt=attempt)
    }

    for item in updates:
        qid = str(item.get("question_id"))
        answer_payload = item.get("answer", {})
        time_spent = int(item.get("time_spent_seconds", 0))

        if qid not in questions_map:
            results.append({"question_id": qid, "status": "not_found"})
            continue

        att_q = questions_map[qid]

        # Determine answered status
        is_answered = bool(answer_payload)
        if isinstance(answer_payload, dict):
            if "selected_option_ids" in answer_payload:
                is_answered = len(answer_payload["selected_option_ids"]) > 0
            elif "text" in answer_payload:
                is_answered = len(str(answer_payload["text"]).strip()) > 0
            elif "value" in answer_payload:
                is_answered = answer_payload["value"] is not None

        att_q.candidate_answer = answer_payload
        att_q.is_answered = is_answered
        if time_spent > 0:
            att_q.time_spent_seconds += time_spent
        att_q.save(update_fields=["candidate_answer", "is_answered", "time_spent_seconds"])

        results.append({
            "question_id": qid,
            "status": "synchronized",
            "is_answered": att_q.is_answered,
        })

    return True, results, f"Successfully synchronized {len(results)} items."
