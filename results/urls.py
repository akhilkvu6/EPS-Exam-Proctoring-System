from django.urls import path
from . import views

urlpatterns = [
    # Student Results Portal
    path('my-results/', views.student_results, name='student_results'),
    path('my-results/<int:result_id>/', views.student_result_detail, name='student_result_detail'),

    # Faculty Evaluation, Grading & Analytics
    path('exam/<int:exam_id>/', views.teacher_exam_results, name='teacher_exam_results'),
    path('attempt/<int:attempt_id>/grade/', views.grade_attempt, name='grade_attempt'),
    path('exam/<int:exam_id>/publish-toggle/', views.toggle_result_publication, name='toggle_result_publication'),
    path('exam/<int:exam_id>/export/csv/', views.export_results_csv, name='export_results_csv'),

    # Institutional Administrator Results & Reports Oversight
    path('admin/overview/', views.admin_results_overview, name='admin_results_overview'),
    path('admin/export/', views.admin_results_export, name='admin_results_export'),
]
