from django.urls import path
from . import views

urlpatterns = [
    path(
        'teacher/register/',
        views.teacher_register,
        name='teacher_register'
    ),

    path(
        'teacher/register/success/',
        views.teacher_registration_success,
        name='teacher_registration_success'
    ),

    path(
        'teacher/login/',
        views.teacher_login,
        name='teacher_login'
    ),

    path(
        'teacher/dashboard/',
        views.teacher_dashboard,
        name='teacher_dashboard'
    ),

    path(
        'logout/',
        views.user_logout,
        name='user_logout'
    ),
path(
    'student/register/',
    views.student_register,
    name='student_register'
),

path(
    'student/register/success/',
    views.student_registration_success,
    name='student_registration_success'
),
path(
    'student/login/',
    views.student_login,
    name='student_login'
),path(
    'student/dashboard/',
    views.student_dashboard,
    name='student_dashboard'
),

]