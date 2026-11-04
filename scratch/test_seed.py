import os, sys
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'online_exam.settings')
import django
django.setup()
from django.utils import timezone
from accounts.models import Department, Course, StudentEnrollment, StudentProfile

# 1. Ensure Departments exist
dept_bca, _ = Department.objects.get_or_create(
    code='BCA',
    defaults={'name': 'Computer Applications', 'description': 'Department of Computer Applications'}
)
dept_cs, _ = Department.objects.get_or_create(
    code='CS',
    defaults={'name': 'Computer Science', 'description': 'Department of Computer Science & Engineering'}
)

# 2. Ensure Courses exist
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

# 3. Sync existing StudentProfile records into StudentEnrollment (marked as registered)
for sp in StudentProfile.objects.all():
    roll = sp.roll_number
    # determine dept and course
    dept = None
    if 'BCA' in sp.department or 'Application' in sp.department:
        dept = dept_bca
        course = course_bca
    else:
        dept = dept_cs
        course = course_bsc_cs

    enr, created = StudentEnrollment.objects.get_or_create(
        roll_number=roll,
        defaults={
            'full_name': sp.full_name or sp.user.get_full_name() or sp.user.username,
            'email': sp.user.email,
            'department': dept,
            'course': course,
            'course_name': course.name if course else (dept.name if dept else ''),
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
# so student registration can retrieve them immediately
sample_enrollments = [
    {
        'roll_number': 'BCA202601',
        'full_name': 'Aarav Sharma',
        'email': 'aarav.sharma@eps.edu',
        'course': course_bca,
        'department': dept_bca,
        'semester': '3'
    },
    {
        'roll_number': 'BCA202602',
        'full_name': 'Priya Patel',
        'email': 'priya.patel@eps.edu',
        'course': course_bca,
        'department': dept_bca,
        'semester': '3'
    },
    {
        'roll_number': 'BCA202603',
        'full_name': 'Kavya Nair',
        'email': 'kavya.nair@eps.edu',
        'course': course_bca,
        'department': dept_bca,
        'semester': '3'
    },
    {
        'roll_number': 'BCA202677',
        'full_name': 'Meera Sen',
        'email': 'meera.sen@eps.edu',
        'course': course_bca,
        'department': dept_bca,
        'semester': '3'
    },
    {
        'roll_number': 'CS2026101',
        'full_name': 'Aditya Verma',
        'email': 'aditya.verma@eps.edu',
        'course': course_bsc_cs,
        'department': dept_cs,
        'semester': '1'
    },
    {
        'roll_number': 'CS2026102',
        'full_name': 'Sneha Rao',
        'email': 'sneha.rao@eps.edu',
        'course': course_bsc_cs,
        'department': dept_cs,
        'semester': '1'
    },
]

for data in sample_enrollments:
    # check if studentprofile already has this roll number
    is_already_registered = StudentProfile.objects.filter(roll_number__iexact=data['roll_number']).exists()
    StudentEnrollment.objects.get_or_create(
        roll_number=data['roll_number'],
        defaults={
            'full_name': data['full_name'],
            'email': data['email'],
            'department': data['department'],
            'course': data['course'],
            'course_name': data['course'].name,
            'semester': data['semester'],
            'is_active': True,
            'is_registered': is_already_registered
        }
    )

print("Seed test completed successfully!")
print("Total Departments:", Department.objects.count())
print("Total Courses:", Course.objects.count())
print("Total Enrollments:", StudentEnrollment.objects.count())
print("Available Unregistered Enrollments:", StudentEnrollment.objects.filter(is_registered=False, is_active=True).count())
