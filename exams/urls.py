from django.urls import path
from . import views

urlpatterns = [
    # Examination Authoring & Management (Teacher/Admin)
    path('manage/', views.manage_exams, name='manage_exams'),
    path('create/', views.create_exam, name='create_exam'),
    path('<int:exam_id>/', views.exam_detail, name='exam_detail'),
    path('<int:exam_id>/edit/', views.edit_exam, name='edit_exam'),
    path('<int:exam_id>/publish/', views.publish_exam, name='publish_exam'),
    path('<int:exam_id>/close/', views.close_exam, name='close_exam'),
    path('<int:exam_id>/preview/', views.exam_preview, name='exam_preview'),
    path('<int:exam_id>/add-question/', views.add_question_to_exam, name='add_question_to_exam'),
    path('<int:exam_id>/add-random-questions/', views.add_random_questions, name='add_random_questions'),
    path('<int:exam_id>/remove-question/<int:exam_question_id>/', views.remove_question_from_exam, name='remove_question_from_exam'),

    # Question Bank & Subjects
    path('questions/', views.question_bank, name='question_bank'),
    path('questions/create/', views.create_question, name='create_question'),
    path('questions/<int:question_id>/edit/', views.edit_question, name='edit_question'),
    path('questions/<int:question_id>/delete/', views.delete_question, name='delete_question'),
    path('questions/import/', views.import_questions, name='import_questions'),
    path('questions/import/template/', views.download_question_template, name='download_question_template'),
    path('questions/export/csv/', views.export_questions_csv, name='export_questions_csv'),
    path('subjects/', views.manage_subjects, name='manage_subjects'),

    # Student Examination Portal & Engine
    path('my-exams/', views.student_exam_list, name='student_exam_list'),
    path('<int:exam_id>/readiness/', views.exam_readiness, name='exam_readiness'),
    path('<int:exam_id>/start/', views.start_exam, name='start_exam'),
    path('attempt/<int:attempt_id>/room/', views.exam_room, name='exam_room'),
    path('attempt/<int:attempt_id>/save-answer/', views.save_answer, name='save_answer'),
    path('attempt/<int:attempt_id>/submit/', views.submit_exam, name='submit_exam'),
    path('attempt/<int:attempt_id>/submitted/', views.exam_submitted, name='exam_submitted'),
    path('attempt/<int:attempt_id>/log-incident/', views.log_proctoring_event, name='log_proctoring_event'),

    # Teacher Live Invigilation & Proctoring Incident Review
    path('<int:exam_id>/invigilate/', views.live_invigilation, name='live_invigilation'),
    path('incidents/<int:incident_id>/review/', views.review_incident, name='review_incident'),

    # Institutional Administrator Examination & Proctoring Oversight
    path('admin/all/', views.admin_all_exams, name='admin_all_exams'),
    path('admin/attempts/', views.admin_exam_attempts, name='admin_exam_attempts'),
    path('admin/proctoring/', views.admin_proctoring_overview, name='admin_proctoring_overview'),
    path('admin/incidents/', views.admin_proctoring_incidents, name='admin_proctoring_incidents'),
]
