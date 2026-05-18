from django.shortcuts import render

# Create your views here.
from django.shortcuts import render

def login_view(request):
    return render(request, 'login.html')

def dashboard(request):
    return render(request, 'dashboard.html')

def upload(request):
    return render(request, 'upload.html')

def reports(request):
    return render(request, 'reports.html')