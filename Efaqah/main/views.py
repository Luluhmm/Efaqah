from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
# Create your views here.
def landing_view(request):
    return render(request, "main/landing_page.html")

def login_view(request):
    return render(request, "main/login_page.html")