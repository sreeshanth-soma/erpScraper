from django import forms
from .models import UserProfile

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['attendance_goal']

class LoginForm(forms.Form):
    username = forms.CharField(label="ERP Username", max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(label="ERP Password", max_length=100, widget=forms.PasswordInput(attrs={'class': 'form-control'})) 