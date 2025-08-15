from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import AttendanceData, UserProfile
from .forms import UserProfileForm, LoginForm # Import LoginForm
from django.contrib.auth.models import User 
import logging # Import logging

# Scraper related imports
import sys
import os
# Adjust the path to import scraper.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from scraper import setup_driver, login, navigate_to_attendance_page, scrape_attendance, teardown_driver, driver, wait # Import scraper functions and global driver/wait

# Configure scraper logging to output to console as well
scraper_logger = logging.getLogger('scraper')
scraper_logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
scraper_logger.addHandler(handler)

def erp_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            try:
                logging.info("Attempting to run scraper from Django...")
                # Call scraper functions
                global driver # Declare driver as global to modify it
                global wait   # Declare wait as global to modify it
                driver, wait = setup_driver() # Setup the driver
                login(username, password) # Use provided credentials
                navigate_to_attendance_page()
                scrape_attendance()
                teardown_driver()
                logging.info("Scraper run successfully. Redirecting to dashboard.")
                return redirect('attendance_dashboard:index')
            except Exception as e:
                logging.error(f"Scraper run failed: {e}")
                form.add_error(None, f"Scraping failed: {e}")
                teardown_driver()
    else:
        form = LoginForm()
    return render(request, 'attendance_dashboard/erp_login.html', {'form': form})

def index(request):
    # Get or create the first superuser as the dashboard user
    # In a real application, you would use request.user for authenticated users
    user, created = User.objects.get_or_create(username='dashboard_user', defaults={'is_superuser': True, 'is_staff': True, 'email': 'dashboard@example.com'})
    if created:
        user.set_password('defaultpassword') # Set a default password for the superuser
        user.save()

    user_profile, created = UserProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user_profile)
        if form.is_valid():
            form.save()
            return redirect('attendance_dashboard:index') # Redirect to prevent form re-submission on refresh
    else:
        form = UserProfileForm(instance=user_profile)

    latest_attendance = AttendanceData.objects.order_by('-timestamp').first()

    attendance_status = "N/A"
    if latest_attendance and user_profile:
        if latest_attendance.attendance_percentage >= user_profile.attendance_goal:
            attendance_status = "Above Target"
        else:
            attendance_status = "Below Target"

    context = {
        'attendance': latest_attendance,
        'form': form, # Pass the UserProfileForm to the template
        'attendance_status': attendance_status,
        'attendance_goal': user_profile.attendance_goal
    }
    return render(request, 'attendance_dashboard/index.html', context)

def get_latest_attendance_data(request):
    latest_attendance = AttendanceData.objects.order_by('-timestamp').first()
    # Assume a single user for simplicity; in a real app, use request.user
    user_profile = UserProfile.objects.first() 

    data = {}
    if latest_attendance and user_profile:
        attendance_status = "N/A"
        if latest_attendance.attendance_percentage >= user_profile.attendance_goal:
            attendance_status = "Above Target"
        else:
            attendance_status = "Below Target"

        data = {
            'total_classes_conducted': latest_attendance.total_classes_conducted,
            'classes_attended': latest_attendance.classes_attended,
            'attendance_percentage': float(latest_attendance.attendance_percentage), # Convert Decimal to float for JSON
            'timestamp': latest_attendance.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'attendance_goal': float(user_profile.attendance_goal),
            'attendance_status': attendance_status
        }
    else:
        data = {'message': 'No attendance data available yet.'}
    return JsonResponse(data)
