from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpRequest,HttpResponse
from .models import Patient
from datetime import date
from main.models import staffProfile
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils.timezone import now

def nurse_dashboard(request: HttpRequest):
    patients = Patient.objects.all()
    num_patient = Patient.objects.all().count()
    patien_under_doctor = Patient.objects.exclude(doctor=None).count()
    today = date.today()
    patients_today_count = Patient.objects.filter(created_at=today).count()
    # Pagination
    paginator = Paginator(patients, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, "nurse/nurse_dashboard.html", {
        "page_obj": page_obj,
        "patient_count": patients.count(),
        "GENDER_CHOICES": Patient.Gender.choices,
        "RESIDENCE_CHOICES": Patient.ResidenceType.choices,
        "today": timezone.now(),
        "patients_today_count":patients_today_count,
        "num_patient":num_patient,
        "patien_under_doctor":patien_under_doctor
    })
#------------------------------------------------------------------------------------------------------
@login_required
def add_patient_view(request: HttpRequest):
    nurse_profile = staffProfile.objects.get(user=request.user)
    hospital = nurse_profile.hospital

    # Get doctors from the same hospital
    doctors = staffProfile.objects.filter(
        hospital=hospital,
        role="doctor",
        is_active=True
    )

    if request.method == "POST":
        today = now().date()
        patients_today = Patient.objects.filter(
            hospital=hospital,
            created_at=today
        ).count()
        if patients_today >= hospital.daily_patient_limit():
            messages.error(request, f"Daily limit reached ({hospital.daily_patient_limit()}) patients for {hospital.get_plan_display()} plan.")
            return redirect('nurse:nurse_dashboard')
        patient_id = request.POST.get("patient_id")
        phone_number = request.POST.get("phone_number")
        doctor_id = request.POST.get("doctor")  # ForeignKey

        # Check for duplicates
        if Patient.objects.filter(patient_id=patient_id).exists() or \
           (phone_number and Patient.objects.filter(phone_number=phone_number).exists()):
            messages.error(request, "This patient already exists in the system.")
            return redirect('nurse:add_patient_view') 

        # Get doctor object or None
        doctor_obj = staffProfile.objects.get(id=doctor_id) if doctor_id else None

        # Create new patient
        new_patient = Patient(
            hospital=nurse_profile.hospital,  
            patient_id=patient_id,
            first_name=request.POST.get("first_name"),
            last_name=request.POST.get("last_name"),
            age=request.POST.get("age"),
            gender=request.POST.get("gender"),
            residence_type=request.POST.get("residence_type"),
            doctor=doctor_obj,
            phone_number=phone_number,
            emergency_phone=request.POST.get("emergency_phone"),
        )
        new_patient.save()
        messages.success(request, "Patient added successfully!")
        return redirect('nurse:nurse_dashboard')  

    # GET: render the add patient page
    return render(request, "nurse/add_patient.html", {
        "GENDER_CHOICES": Patient.Gender.choices,
        "RESIDENCE_CHOICES": Patient.ResidenceType.choices,
        "doctors": doctors
    })
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

    # Get nurse profile
    nurse_profile = staffProfile.objects.get(user=request.user)

    # Get doctors from the same hospital
    doctors = staffProfile.objects.filter(
        hospital=nurse_profile.hospital,
        role="doctor",
        is_active=True
    )

    if request.method == "POST":
        # Update patient fields
        patient.patient_id = request.POST.get("patient_id")
        patient.first_name = request.POST.get("first_name")
        patient.last_name = request.POST.get("last_name")
        patient.age = request.POST.get("age")
        patient.gender = request.POST.get("gender")
        patient.residence_type = request.POST.get("residence_type")
        patient.phone_number = request.POST.get("phone_number")
        patient.emergency_phone = request.POST.get("emergency_phone")

        # Update doctor ForeignKey
        doctor_id = request.POST.get("doctor")
        patient.doctor = staffProfile.objects.get(id=doctor_id) if doctor_id else None

        try:
            patient.save()
            messages.success(request, "Patient updated successfully!")
            return redirect('nurse:nurse_dashboard')  
        except Exception as e:
            messages.error(request, f"Error updating patient: {str(e)}")

    # GET: render update form
    return render(request, "nurse/update_patient.html", {
        "patient_to_update": patient,
        "GENDER_CHOICES": Patient.Gender.choices,
        "RESIDENCE_CHOICES": Patient.ResidenceType.choices,
        "doctors": doctors
    })

#------------------------------------------------------------------------------------------------------

def delete_patient_view(request:HttpRequest, patient_id:int):
    patient = Patient.objects.get(pk=patient_id)
    patient.delete()
    return redirect('manager:manager_dashboard')
