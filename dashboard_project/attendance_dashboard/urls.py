from django.urls import path
from . import views

app_name = 'attendance_dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/latest_attendance/', views.get_latest_attendance_data, name='latest_attendance_api'),
    path('login/', views.erp_login, name='erp_login'), # New login URL
] 