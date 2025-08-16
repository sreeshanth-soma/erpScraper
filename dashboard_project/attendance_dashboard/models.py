from django.db import models
from django.contrib.auth.models import User
from datetime import date

# Create your models here.

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    attendance_goal = models.DecimalField(max_digits=5, decimal_places=2, default=75.00) # Default 75%

    def __str__(self):
        return f"{self.user.username}'s Profile"

class AttendanceData(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, null=True, blank=True)
    total_classes_conducted = models.IntegerField(default=0)
    classes_attended = models.IntegerField(default=0)
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    timestamp = models.DateTimeField(auto_now_add=True)
    date = models.DateField(default=date.today)  # Add a date field to track daily attendance

    class Meta:
        unique_together = ('user', 'date')  # Ensure only one attendance record per user per day

    def __str__(self):
        return f"Attendance for {self.user.user.username if self.user else 'Unknown User'} on {self.date}"
