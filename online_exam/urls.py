from django.contrib import admin
from django.urls import path, include
from accounts import views

urlpatterns = [
    path('', views.home, name='home'),
    path('design/', views.design_system, name='design_system_root'),

    path('admin/', admin.site.urls),

    path('accounts/', include('accounts.urls')),
    path('exams/', include('exams.urls')),
    path('results/', include('results.urls')),
]