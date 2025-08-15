from django.shortcuts import render
from django.http import JsonResponse
from .models import AttendanceData

# Create your views here.

def index(request):
    latest_attendance = AttendanceData.objects.order_by('-timestamp').first()
    context = {
        'attendance': latest_attendance
    }
    return render(request, 'attendance_dashboard/index.html', context)

def get_latest_attendance_data(request):
    latest_attendance = AttendanceData.objects.order_by('-timestamp').first()
    if latest_attendance:
        data = {
            'total_classes_conducted': latest_attendance.total_classes_conducted,
            'classes_attended': latest_attendance.classes_attended,
            'attendance_percentage': float(latest_attendance.attendance_percentage), # Convert Decimal to float for JSON
            'timestamp': latest_attendance.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }
    else:
        data = {}
    return JsonResponse(data)
