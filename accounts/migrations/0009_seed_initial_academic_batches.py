from django.db import migrations


def seed_initial_batches(apps, schema_editor):
    import sys
    if 'test' in sys.argv:
        # In test suite, tests create their own batches or fixtures as needed
        return

    Department = apps.get_model('accounts', 'Department')
    Course = apps.get_model('accounts', 'Course')
    AcademicBatch = apps.get_model('accounts', 'AcademicBatch')
    RollNumberReservation = apps.get_model('accounts', 'RollNumberReservation')

    # 1. 2026 BCA Batch
    course_bca = Course.objects.filter(code__iexact='BCA').first()
    if course_bca:
        batch_bca, created = AcademicBatch.objects.get_or_create(
            admission_year=2026,
            course=course_bca,
            batch_identifier='',
            defaults={
                'department': course_bca.department,
                'course_code': 'BCA',
                'batch_name': '2026 BCA',
                'prefix': '2026BCA',
                'capacity': 60,
                'start_roll_number': 1,
                'end_roll_number': 60,
                'admission_semester': '1',
                'total_semesters': 6,
                'current_semester': '1',
                'enrollment_status': 'open',
                'is_active': True,
            }
        )
        if created:
            reservations = []
            for seq in range(1, 61):
                reg_num = f"2026BCA{seq:02d}"
                reservations.append(
                    RollNumberReservation(
                        batch=batch_bca,
                        roll_sequence=seq,
                        registration_number=reg_num,
                        status='available'
                    )
                )
            RollNumberReservation.objects.bulk_create(reservations, ignore_conflicts=True)

    # 2. 2026 B.Sc CS Batch
    course_cs = Course.objects.filter(code__iexact='B.Sc CS').first() or Course.objects.filter(code__iexact='CS').first()
    if course_cs:
        batch_cs, created = AcademicBatch.objects.get_or_create(
            admission_year=2026,
            course=course_cs,
            batch_identifier='',
            defaults={
                'department': course_cs.department,
                'course_code': 'BSCCS',
                'batch_name': '2026 BSC CS',
                'prefix': '2026BSCCS',
                'capacity': 60,
                'start_roll_number': 1,
                'end_roll_number': 60,
                'admission_semester': '1',
                'total_semesters': 6,
                'current_semester': '1',
                'enrollment_status': 'open',
                'is_active': True,
            }
        )
        if created:
            reservations = []
            for seq in range(1, 61):
                reg_num = f"2026BSCCS{seq:02d}"
                reservations.append(
                    RollNumberReservation(
                        batch=batch_cs,
                        roll_sequence=seq,
                        registration_number=reg_num,
                        status='available'
                    )
                )
            RollNumberReservation.objects.bulk_create(reservations, ignore_conflicts=True)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_studentenrollment_roll_sequence_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_initial_batches, noop_reverse),
    ]
