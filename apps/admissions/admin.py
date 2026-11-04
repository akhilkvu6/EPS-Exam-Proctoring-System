"""
Django admin integration for apps.admissions models.
"""

from django.contrib import admin
from .models import RollSequenceCounter, RollAllocationRecord, AdmissionSupportingDocument


@admin.register(RollSequenceCounter)
class RollSequenceCounterAdmin(admin.ModelAdmin):
    list_display = ("prefix", "academic_year", "current_sequence", "updated_at")


@admin.register(RollAllocationRecord)
class RollAllocationRecordAdmin(admin.ModelAdmin):
    list_display = (
        "allocated_roll_number",
        "student_profile",
        "allocated_by",
        "allocation_ticket_id",
        "created_at",
    )
    search_fields = (
        "allocated_roll_number",
        "student_profile__registration_number",
        "student_profile__user__username",
    )
    readonly_fields = ("allocation_ticket_id", "created_at")


@admin.register(AdmissionSupportingDocument)
class AdmissionSupportingDocumentAdmin(admin.ModelAdmin):
    list_display = ("student_profile", "document_title", "is_verified", "uploaded_at")
    list_filter = ("is_verified", "uploaded_at")
