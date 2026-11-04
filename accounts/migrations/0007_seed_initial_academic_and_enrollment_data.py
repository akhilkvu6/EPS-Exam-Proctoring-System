from django.db import migrations
from django.utils import timezone


def seed_academic_data(apps, schema_editor):
    import sys
    if 'test' in sys.argv:
        return
    Department = apps.get_model('accounts', 'Department')
    Course = apps.get_model('accounts', 'Course')
    StudentProfile = apps.get_model('accounts', 'StudentProfile')
    StudentEnrollment = apps.get_model('accounts', 'StudentEnrollment')

    # 1. Ensure initial Departments exist
    dept_bca, _ = Department.objects.get_or_create(
        code='BCA',
        defaults={'name': 'Computer Applications', 'description': 'Department of Computer Applications'}
    )
    dept_cs, _ = Department.objects.get_or_create(
        code='CS',
        defaults={'name': 'Computer Science', 'description': 'Department of Computer Science & Engineering'}
    )

    # 2. Ensure initial Courses exist
    course_bca, _ = Course.objects.get_or_create(
        code='BCA',
        defaults={
            'name': 'Bachelor of Computer Applications',
            'department': dept_bca,
            'description': 'Undergraduate 3-year degree in Computer Applications',
            'total_semesters': 6
        }
    )
    course_bsc_cs, _ = Course.objects.get_or_create(
        code='B.Sc CS',
        defaults={
            'name': 'B.Sc Computer Science',
            'department': dept_cs,
            'description': 'Undergraduate degree in Computer Science',
            'total_semesters': 6
        }
    )

    # 3. Synchronize existing StudentProfiles into StudentEnrollment
    for sp in StudentProfile.objects.all():
        roll = sp.roll_number
        dept = dept_bca if ('BCA' in sp.department or 'Application' in sp.department) else dept_cs
        course = course_bca if ('BCA' in sp.department or 'Application' in sp.department) else course_bsc_cs

        enr, created = StudentEnrollment.objects.get_or_create(
            roll_number=roll,
            defaults={
                'full_name': sp.full_name or sp.user.username,
                'email': sp.user.email,
                'department': dept,
                'course': course,
                'course_name': course.name,
                'semester': sp.semester or '1',
                'is_active': True,
                'is_registered': True,
                'registered_student': sp,
                'registered_at': timezone.now()
            }
        )
        if not created and not enr.is_registered:
            enr.is_registered = True
            enr.registered_student = sp
            enr.save()

    # 4. Populate legitimate eligible enrollment records (unregistered, active)
    initial_roster = [
        ('BCA202601', 'Aarav Sharma', 'aarav.sharma@eps.edu', dept_bca, course_bca, '3'),
        ('BCA202602', 'Priya Patel', 'priya.patel@eps.edu', dept_bca, course_bca, '3'),
        ('BCA202603', 'Kavya Nair', 'kavya.nair@eps.edu', dept_bca, course_bca, '3'),
        ('BCA202677', 'Meera Sen', 'meera.sen@eps.edu', dept_bca, course_bca, '3'),
        ('CS2026101', 'Aditya Verma', 'aditya.verma@eps.edu', dept_cs, course_bsc_cs, '1'),
        ('CS2026102', 'Sneha Rao', 'sneha.rao@eps.edu', dept_cs, course_bsc_cs, '1'),
    ]

    for roll, name, email, dept, course, sem in initial_roster:
        already_reg = StudentProfile.objects.filter(roll_number__iexact=roll).exists()
        StudentEnrollment.objects.get_or_create(
            roll_number=roll,
            defaults={
                'full_name': name,
                'email': email,
                'department': dept,
                'course': course,
                'course_name': course.name,
                'semester': sem,
                'is_active': True,
                'is_registered': already_reg
            }
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_course_studentprofile_course_studentenrollment'),
    ]

    operations = [
        migrations.RunPython(seed_academic_data, noop_reverse),
    ]
