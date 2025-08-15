from django.db import models

# Create your models here.

class AttendanceData(models.Model):
    total_classes_conducted = models.IntegerField(default=0)
    classes_attended = models.IntegerField(default=0)
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attendance on {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
