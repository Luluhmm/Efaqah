from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest,HttpResponse
from main.models import staffProfile
from django.contrib.auth.models import User
from .forms import DoctorForm , NurseForm
from django.contrib import messages

# Create your views here.

def manager_dashboard(request:HttpRequest):
    doctors = staffProfile.objects.filter(role="doctor", hospital=request.user.staffprofile.hospital)
    nurses = staffProfile.objects.filter(role="nurse", hospital=request.user.staffprofile.hospital)
    return render(request, "manager/manager_dashboard.html", {"doctors":doctors, "nurses":nurses})


def add_doctor(request):
    if request.method == "POST":
        form = DoctorForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name']
            )
            staffProfile.objects.create(
                user=user,
                hospital=request.user.staffprofile.hospital,
                role="doctor"
            )
            return redirect("manager:manager_dashboard")
    
    else:
        form = DoctorForm()
    return render(request, "manager/add_doctor.html", {"form":form})

def add_nurse(request):
    if request.method == "POST":
        form = NurseForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name']
            )
            staffProfile.objects.create(
                user=user,
                hospital=request.user.staffprofile.hospital,
                role="nurse"
            )
            return redirect("manager:manager_dashboard")
    
    else:
        form = NurseForm()
    return render(request, "manager/add_nurse.html", {"form":form})

def update_doctor(request, doctor_id):
    doctor = get_object_or_404(staffProfile, id=doctor_id, role="doctor")

    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')

        doctor.user.username = username
        doctor.user.email = email
        doctor.user.first_name = first_name
        doctor.user.last_name = last_name
        
        if password:
            doctor.user.set_password(password)

        doctor.user.save()
        doctor.save()

        messages.success(request, f"Doctor {doctor.user.username} updated successfully.")
        return redirect("manager:manager_dashboard")
    
    return render(request, "manager/update_doctor.html", {"doctor":doctor})


def update_nurse(request, nurse_id):
    nurse = get_object_or_404(staffProfile, id=nurse_id, role="nurse")

    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')

        nurse.user.username = username
        nurse.user.email = email
        nurse.user.first_name = first_name
        nurse.user.last_name = last_name
        
        if password:
            nurse.user.set_password(password)

        nurse.user.save()
        nurse.save()

        messages.success(request, f"Nurse {nurse.user.username} updated successfully.")
        return redirect("manager:manager_dashboard")
    
    return render(request, "manager/update_nurse.html", {"nurse":nurse})


def remove_doctor(request, doctor_id):
    doctor = get_object_or_404(staffProfile, id=doctor_id, role="doctor")
    user = doctor.user
    doctor.delete()
    user.delete()
    messages.success(request, f"Doctor {user.username} has been removed.")
    return redirect("manager:manager_dashboard")
    
def remove_nurse(request, nurse_id):
    nurse = get_object_or_404(staffProfile, id=nurse_id, role="nurse")
    user = nurse.user
    nurse.delete()
    user.delete()
    messages.success(request, f"Nurse {user.username} has been removed.")
    return redirect("manager:manager_dashboard")