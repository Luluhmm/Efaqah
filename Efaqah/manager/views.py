from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest,HttpResponse
from nurse.models import Patient
from main.models import staffProfile
from django.contrib.auth.models import User, Group
from .forms import DoctorForm , NurseForm
from django.contrib import messages
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now

# Create your views here.

def manager_dashboard(request:HttpRequest):
    hospital = request.user.staffprofile.hospital
    doctors = staffProfile.objects.filter(role="doctor", hospital=request.user.staffprofile.hospital).order_by('-created_at')[:3]
    nurses = staffProfile.objects.filter(role="nurse", hospital=request.user.staffprofile.hospital).order_by('-created_at')[:3]
    patients = Patient.objects.filter(hospital=request.user.staffprofile.hospital).order_by('-created_at')[:3]
    num_doctor = staffProfile.objects.filter(role="doctor", hospital=request.user.staffprofile.hospital).count()
    num_nurse = staffProfile.objects.filter(role="nurse", hospital=request.user.staffprofile.hospital).count()
    num_patient = Patient.objects.filter(hospital=request.user.staffprofile.hospital).count()
    #total patient in each doctor 
    doctor_patient_counts = (
    Patient.objects.filter(hospital=hospital)
    .values("doctor__user__username")
    .annotate(total=Count("id"))
)
    labels = [d["doctor__user__username"] for d in doctor_patient_counts]
    data = [d["total"] for d in doctor_patient_counts]
    return render(request, "manager/manager_dashboard.html", {"doctors":doctors, "nurses":nurses,"num_doctor":num_doctor,"num_nurse":num_nurse,"num_patient":num_patient,
                "labels": labels,"data": data,"patients":patients})

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
            return redirect('manager:manager_dashboard')
        patient_id = request.POST.get("patient_id")
        phone_number = request.POST.get("phone_number")
        doctor_id = request.POST.get("doctor")  # ForeignKey

        # Check for duplicates
        if Patient.objects.filter(patient_id=patient_id).exists() or \
           (phone_number and Patient.objects.filter(phone_number=phone_number).exists()):
            messages.error(request, "This patient already exists in the system.")
            return redirect('nurse:add_patient') 

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
        return redirect('manager:manager_dashboard')  

    # GET: render the add patient page
    return render(request, "manager/add_patient.html", {
        "GENDER_CHOICES": Patient.Gender.choices,
        "RESIDENCE_CHOICES": Patient.ResidenceType.choices,
        "doctors": doctors
    })
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
            return redirect('manager:manager_dashboard')  
        except Exception as e:
            messages.error(request, f"Error updating patient: {str(e)}")

    # GET: render update form
    return render(request, "manager/update_patient.html", {
        "patient_to_update": patient,
        "GENDER_CHOICES": Patient.Gender.choices,
        "RESIDENCE_CHOICES": Patient.ResidenceType.choices,
        "doctors": doctors
    })

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
            doctor_group, created = Group.objects.get_or_create(name="Doctor")
            user.groups.add(doctor_group)
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
            nurse_group, created = Group.objects.get_or_create(name="Nurse")
            user.groups.add(nurse_group)
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

def all_patient(request):
    patients = Patient.objects.filter(hospital=request.user.staffprofile.hospital)
    return render(request, "manager/all_patient.html", {"patients":patients})
def all_nurse(request):
    nurses = staffProfile.objects.filter(role="nurse", hospital=request.user.staffprofile.hospital)
    return render(request, "manager/all_nurse.html", {"nurses":nurses})
def all_doctor(request):   
    doctors = staffProfile.objects.filter(role="doctor", hospital=request.user.staffprofile.hospital)
    return render(request, "manager/all_doctors.html", {"doctors":doctors})