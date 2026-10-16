import os
import json
import hashlib
from django.conf import settings
from django.utils import timezone
from .models import AuditLog


POLICIES_FILE_PATH = os.path.join(settings.BASE_DIR, 'data', 'institutional_policies.json')

DEFAULT_POLICIES = {
    'late_entry_mins': 15,
    'late_entry_enabled': True,
    'early_entry_enabled': False,
    'attempt_allowance': 'single',  # 'single', 'dual', 'practice'
    'server_submission_enabled': True,
    'timing_accommodation': '1.0',  # '1.0', '1.25', '1.5', '2.0'
    'video_ingestion': 'dual',  # 'dual', 'single', 'disabled'
    'audio_monitor': 'threshold',  # 'threshold', 'continuous', 'disabled'
    'os_lockdown_enabled': True,
    'focus_trap_enabled': True,
    'clipboard_neutralization_enabled': True,
    'item_randomization_enabled': True,
    'distractor_shuffling_enabled': True,
    'negative_marking_scheme': 'mild',  # 'none', 'mild', 'strict'
    'score_embargo_enabled': True,
    'telemetry_retention_days': '90',  # '30', '90', '180'
    'audit_retention_years': '7y',  # '5y', '7y', '10y'
}


def compute_policy_hash(policies_dict):
    """Computes a deterministic SHA-256 hash of the sorted policy configuration."""
    clean_dict = {k: v for k, v in sorted(policies_dict.items())}
    serialized = json.dumps(clean_dict, sort_keys=True)
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


def get_institutional_policies():
    """Retrieves current institutional policies, falling back to defaults."""
    if os.path.exists(POLICIES_FILE_PATH):
        try:
            with open(POLICIES_FILE_PATH, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                policies = DEFAULT_POLICIES.copy()
                policies.update(saved)
                return policies
        except Exception:
            pass
    return DEFAULT_POLICIES.copy()


def save_institutional_policies(cleaned_data, user=None, request=None):
    """Persists validated policy configuration, records audit log, and returns saved dict."""
    os.makedirs(os.path.dirname(POLICIES_FILE_PATH), exist_ok=True)
    
    policies = DEFAULT_POLICIES.copy()
    for key in DEFAULT_POLICIES:
        if key in cleaned_data:
            policies[key] = cleaned_data[key]
            
    with open(POLICIES_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(policies, f, indent=2, sort_keys=True)
        
    policy_hash = compute_policy_hash(policies)
    
    if user:
        from .decorators import log_audit
        log_audit(
            actor=user,
            action='POLICY_UPDATE',
            target_user=None,
            request=request,
            details=f"Institutional examination and proctoring policies updated. SHA-256: 0x{policy_hash[:4]}..{policy_hash[-4:]}"
        )
        
    return policies


def get_policy_metadata():
    """Returns active policy hash, short hash, and latest audit timestamp/actor."""
    policies = get_institutional_policies()
    full_hash = compute_policy_hash(policies)
    short_hash = f"0x{full_hash[:4]}..{full_hash[-4:]}"
    
    latest_audit = AuditLog.objects.filter(action='POLICY_UPDATE').order_by('-created_at').first()
    if latest_audit:
        last_modified_at = latest_audit.created_at
        actor_name = latest_audit.actor.get_full_name() if latest_audit.actor else None
        last_modified_by = actor_name or (latest_audit.actor.username if latest_audit.actor else "Chief Administrator")
    else:
        last_modified_at = timezone.now()
        last_modified_by = "Chief Administrator (Institutional Governance)"
        
    return {
        'hash': full_hash,
        'short_hash': short_hash,
        'last_modified_at': last_modified_at,
        'last_modified_formatted': last_modified_at.strftime("%b %d, %Y, %H:%M UTC"),
        'last_modified_by': last_modified_by,
    }


def export_policy_manifest(user=None):
    """Builds a comprehensive JSON manifest for institutional export."""
    policies = get_institutional_policies()
    meta = get_policy_metadata()
    from accounts.models import Department
    from exams.models import Exam
    
    return {
        'manifest_version': '4.8',
        'governance_enclave': 'EPS Institutional Core',
        'policy_sha256_hash': meta['hash'],
        'short_hash': meta['short_hash'],
        'exported_at': timezone.now().isoformat(),
        'authorized_by': user.get_full_name() or user.username if user else 'Administrator',
        'academic_term': '2026 Academic Session',
        'stratum_ntp_sync': True,
        'department_enclaves_count': Department.objects.count(),
        'scheduled_exams_bound': Exam.objects.count(),
        'institutional_policies': policies,
    }
