"""
Automated tests for Phase 6: Admissions & Concurrency-Safe Roll Allocation.
Compliant with Section 8.5 (Concurrency safety, database uniqueness, audit history).
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import User, UserRole, UserStatus
from apps.student.models import StudentProfile, AdmissionApplicationStatus
from apps.admissions.models import RollSequenceCounter, RollAllocationRecord
from apps.admissions.services.roll_allocator import (
    allocate_roll_number_atomic,
    RollAllocationError,
)


class ConcurrencySafeRollAllocationTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Admin user
        self.admin = User.objects.create_user(
            username="admin_dean",
            password="DeanPassword123!",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )

        # Faculty user
        self.teacher = User.objects.create_user(
            username="prof_vector",
            password="VectorPassword123!",
            role=UserRole.TEACHER,
            status=UserStatus.ACTIVE,
        )

        # Pending student
        self.pending_user = User.objects.create_user(
            username="candidate_cedric",
            password="CedricPassword123!",
            role=UserRole.STUDENT,
            status=UserStatus.PENDING_APPROVAL,
        )
        self.pending_profile = StudentProfile.objects.create(
            user=self.pending_user,
            registration_number="APP-CEDRIC-01",
            admission_status=AdmissionApplicationStatus.SUBMITTED,
        )

        # Approved student
        self.approved_user1 = User.objects.create_user(
            username="stud_draco",
            password="DracoPassword123!",
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
        )
        self.approved_profile1 = StudentProfile.objects.create(
            user=self.approved_user1,
            registration_number="APP-DRACO-01",
            admission_status=AdmissionApplicationStatus.APPROVED,
        )

        # Approved student 2
        self.approved_user2 = User.objects.create_user(
            username="stud_pansy",
            password="PansyPassword123!",
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
        )
        self.approved_profile2 = StudentProfile.objects.create(
            user=self.approved_user2,
            registration_number="APP-PANSY-01",
            admission_status=AdmissionApplicationStatus.APPROVED,
        )

    def test_roll_allocation_rejected_if_not_approved(self):
        """Roll allocation strictly fails with RollAllocationError if candidate is not approved."""
        with self.assertRaises(RollAllocationError) as ctx:
            allocate_roll_number_atomic(self.pending_profile, allocated_by=self.admin)
        self.assertIn("strictly required before allocation", str(ctx.exception))
        self.assertIsNone(self.pending_profile.roll_number)

    def test_sequential_roll_allocation(self):
        """Successive approved students receive sequential roll numbers without collision."""
        current_year = timezone.now().year

        roll1 = allocate_roll_number_atomic(self.approved_profile1, allocated_by=self.admin)
        expected_roll1 = f"EP-{current_year}-0001"
        self.assertEqual(roll1, expected_roll1)

        roll2 = allocate_roll_number_atomic(self.approved_profile2, allocated_by=self.admin)
        expected_roll2 = f"EP-{current_year}-0002"
        self.assertEqual(roll2, expected_roll2)

        # Verify database records
        self.approved_profile1.refresh_from_db()
        self.approved_profile2.refresh_from_db()
        self.assertEqual(self.approved_profile1.roll_number, expected_roll1)
        self.assertEqual(self.approved_profile2.roll_number, expected_roll2)

        # Verify audit ledger
        self.assertTrue(RollAllocationRecord.objects.filter(allocated_roll_number=expected_roll1).exists())
        self.assertTrue(RollAllocationRecord.objects.filter(allocated_roll_number=expected_roll2).exists())

    def test_idempotent_roll_allocation(self):
        """Calling allocator on an already allocated student returns existing roll without advancing sequence."""
        current_year = timezone.now().year

        roll1 = allocate_roll_number_atomic(self.approved_profile1, allocated_by=self.admin)
        # Call again
        roll1_repeat = allocate_roll_number_atomic(self.approved_profile1, allocated_by=self.admin)
        self.assertEqual(roll1, roll1_repeat)

        # Verify counter did not increment again
        counter = RollSequenceCounter.objects.get(prefix="EP", academic_year=current_year)
        self.assertEqual(counter.current_sequence, 1)

    def test_custom_override_roll_allocation_and_collision_check(self):
        """Custom roll number override works and prevents duplicate collisions."""
        roll = allocate_roll_number_atomic(
            self.approved_profile1,
            allocated_by=self.admin,
            custom_override="SPECIAL-ROLL-777",
        )
        self.assertEqual(roll, "SPECIAL-ROLL-777")

        # Second student attempting same custom roll must fail
        with self.assertRaises(RollAllocationError) as ctx:
            allocate_roll_number_atomic(
                self.approved_profile2,
                allocated_by=self.admin,
                custom_override="SPECIAL-ROLL-777",
            )
        self.assertIn("already allocated", str(ctx.exception))

    def test_roll_registry_view_permissions(self):
        """Faculty and Admin can access roll registry ledger; students are blocked."""
        # Faculty allowed
        self.client.login(username="prof_vector", password="VectorPassword123!")
        response = self.client.get(reverse("admissions:roll_registry"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Official Roll Number Allocation Ledger")

        # Active student blocked with 403 Forbidden
        self.client.login(username="stud_draco", password="DracoPassword123!")
        response = self.client.get(reverse("admissions:roll_registry"))
        self.assertEqual(response.status_code, 403)

    def test_application_status_api(self):
        """Public candidate status API returns JSON."""
        response = self.client.get(
            reverse("admissions:application_status_api", kwargs={"registration_number": "APP-DRACO-01"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        data = response.json()
        self.assertEqual(data["registration_number"], "APP-DRACO-01")
        self.assertTrue(data["is_approved"])
