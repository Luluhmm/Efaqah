from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpRequest,HttpResponse
from .models import Patient
from datetime import date
from main.models import staffProfile
from django.contrib.auth.decorators import login_required

def nurse_dashboard(request: HttpRequest):
    patients = Patient.objects.all()
    num_patient = Patient.objects.all().count()
    today = date.today()
    patients_today_count = Patient.objects.filter(created_at=today).count()
    return render(request, "nurse/nurse_dashboard.html", {
        "patients": patients,
        "patient_count": patients.count(),
        "GENDER_CHOICES": Patient.Gender.choices,
        "RESIDENCE_CHOICES": Patient.ResidenceType.choices,
        "today": timezone.now(),
        "patients_today_count":patients_today_count,
        "num_patient":num_patient
    })
#------------------------------------------------------------------------------------------------------
@login_required
def add_patient_view(request: HttpRequest):
     if request.method == "POST":
        patient_id = request.POST.get("patient_id")
        phone_number = request.POST.get("phone_number")

        # Check if patient already exists
        if Patient.objects.filter(patient_id=patient_id).exists() or \
           (phone_number and Patient.objects.filter(phone_number=phone_number).exists()):
            messages.error(request, "This patient already exists in the system.")
            return redirect('nurse:add_patient')  # Stay on the add patient page

        # Create new patient
        new_patient = Patient(
            patient_id=patient_id,
            first_name=request.POST.get("first_name"),
            last_name=request.POST.get("last_name"),
            age=request.POST.get("age"),
            gender=request.POST.get("gender"),
            residence_type=request.POST.get("residence_type"),
            doctor_name=request.POST.get("doctor_name"),
            phone_number=phone_number,
            emergency_phone=request.POST.get("emergency_phone"),
        )
        new_patient.save()
        messages.success(request, "Patient added successfully!")
        return redirect('nurse:nurse_dashboard')  # Redirect to dashboard after success
     nurse_profile = staffProfile.objects.get(user=request.user)   
     doctors = staffProfile.objects.filter(
     hospital=nurse_profile.hospital,
     role="doctor",
     is_active=True) 
    # GET: render the add patient page
     return render(request, "nurse/add_patient.html",{"GENDER_CHOICES": Patient.Gender.choices,
        "RESIDENCE_CHOICES": Patient.ResidenceType.choices,"doctors":doctors})

#------------------------------------------------------------------------------------------------------

def view_patient(request: HttpRequest,patient_id:int):
    patient = get_object_or_404(Patient, pk=patient_id) 
    return render(request, "nurse/patient_detial.html", {
        "patient": patient
    })

#------------------------------------------------------------------------------------------------------

def update_patient_view(request, patient_id):
    # جلب المريض أو إعطاء 404 إذا لم يوجد
    patient = get_object_or_404(Patient, id=patient_id)

    if request.method == "POST":
        # تحديث البيانات من الفورم
        patient.patient_id = request.POST.get('patient_id')
        patient.first_name = request.POST.get('first_name')
        patient.last_name = request.POST.get('last_name')
        patient.age = request.POST.get('age')
        patient.gender = request.POST.get('gender')
        patient.residence_type = request.POST.get('residence_type')
        patient.doctor_name = request.POST.get('doctor_name')
        patient.phone_number = request.POST.get('phone_number')
        patient.emergency_phone = request.POST.get('emergency_phone')

        try:
            patient.save()
            messages.success(request, "Patient updated successfully!")
            return redirect('nurse:nurse_dashboard')  # بعد التحديث نرجع للداشبورد
        except Exception as e:
            messages.error(request, f"Error updating patient: {str(e)}")

    # GET: عرض صفحة التحديث مع بيانات المريض
    return render(request, 'nurse/update_patient.html', {
        'patient_to_update': patient,
        'GENDER_CHOICES': Patient.Gender.choices,
        'RESIDENCE_CHOICES': Patient.ResidenceType.choices,
    })

#------------------------------------------------------------------------------------------------------

def delete_patient_view(request:HttpRequest, patient_id:int):
    patient = Patient.objects.get(pk=patient_id)
    patient.delete()
    return redirect('nurse:nurse_dashboard')
