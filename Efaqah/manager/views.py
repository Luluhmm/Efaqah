from django.db import IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest,HttpResponse
from doctor.models import PatientRecord, PatientSymptom
from nurse.models import Patient
from main.models import staffProfile
from django.contrib.auth.models import User, Group
from .forms import DoctorForm , NurseForm
from django.contrib import messages
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils.timezone import now


def manager_dashboard(request:HttpRequest):
    hospital = request.user.staffprofile.hospital
    doctors = staffProfile.objects.filter(role="doctor", hospital=request.user.staffprofile.hospital).order_by('-created_at')[:3]
    nurses = staffProfile.objects.filter(role="nurse", hospital=request.user.staffprofile.hospital).order_by('-created_at')[:3]
    patients = Patient.objects.filter(hospital=request.user.staffprofile.hospital).order_by('-created_at')[:3]
    num_doctor = staffProfile.objects.filter(role="doctor", hospital=request.user.staffprofile.hospital).count()
    num_nurse = staffProfile.objects.filter(role="nurse", hospital=request.user.staffprofile.hospital).count()
    num_patient = Patient.objects.filter(hospital=request.user.staffprofile.hospital).count()

    total_scans = PatientRecord.objects.filter(
    patient__hospital=hospital,
    ct_image__isnull=False
    ).exclude(ct_image='images/default.jpg').count()
    
    total_symptoms = PatientSymptom.objects.filter(record__patient__hospital=hospital).count()

    #total patient in each doctor 
    doctor_patient_counts = (
    Patient.objects.filter(hospital=hospital)
    .values("doctor__user__username")
    .annotate(total=Count("id"))
)
    labels = [d["doctor__user__username"] for d in doctor_patient_counts]
    data = [d["total"] for d in doctor_patient_counts]

    #total CT scans per doctor 
    doctor_scan_counts = (
        PatientRecord.objects.filter(patient__hospital=hospital, patient__doctor__isnull=False)
        .values("patient__doctor__user__username")
        .annotate(total=Count("id"))
    )

    scan_labels = [d["patient__doctor__user__username"] for d in doctor_scan_counts]
    scan_data = [d["total"] for d in doctor_scan_counts]
    return render(request, "manager/manager_dashboard.html", {"doctors":doctors, "nurses":nurses,"num_doctor":num_doctor,"num_nurse":num_nurse,"num_patient":num_patient,
                "labels": labels,"data": data,"patients":patients,"scan_labels":scan_labels,"scan_data":scan_data,"total_scans":total_scans,
                "total_symptoms":total_symptoms})
#------------------------------------------------------------------------------------------------------

def add_doctor(request):
    if request.method == "POST":
        form = DoctorForm(request.POST)
        if form.is_valid():
            try:
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

                messages.success(request, "Doctor added successfully.")
                return redirect("manager:all_doctor")

            except IntegrityError:
                messages.error(request, "This username already exists. Please choose another one.")
                return redirect("manager:add_doctor") 

    else:
        form = DoctorForm()

    return render(request, "manager/add_staff.html", {"form": form, "role": "doctor"})

#------------------------------------------------------------------------------------------------------

def add_nurse(request):
    if request.method == "POST":
        form = NurseForm(request.POST)
        if form.is_valid():
            try:
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
                messages.success(request, "Nurse added successfully.")
                return redirect("manager:all_nurse")
            
            except IntegrityError:
                messages.error(request, "This username already exists. Please choose another one.")
                return redirect("manager:add_nurse") 
    
    else:
        form = NurseForm()
    return render(request, "manager/add_staff.html", {"form":form , "role": "nurse"})

#------------------------------------------------------------------------------------------------------

def update_doctor(request, doctor_id):
    staff = get_object_or_404(staffProfile, id=doctor_id, role="doctor")

    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')

        staff.user.username = username
        staff.user.email = email
        staff.user.first_name = first_name
        staff.user.last_name = last_name

        staff.user.save()
        staff.save()

        messages.success(request, f"Doctor {staff.user.username} updated successfully.")
        return redirect("manager:detail_doctor",doctor_id)
    
    return render(request, "manager/update_staff.html", {"staff": staff, "role": "doctor"})

#------------------------------------------------------------------------------------------------------

def update_nurse(request, nurse_id):
    staff = get_object_or_404(staffProfile, id=nurse_id, role="nurse")

    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')

        staff.user.username = username
        staff.user.email = email
        staff.user.first_name = first_name
        staff.user.last_name = last_name

        staff.user.save()
        staff.save()

        messages.success(request, f"Nurse {staff.user.username} updated successfully.")
        return redirect("manager:detail_nurse",nurse_id)
    
    return render(request, "manager/update_staff.html", {"staff": staff, "role": "nurse"})

#------------------------------------------------------------------------------------------------------

def remove_doctor(request, doctor_id):
    doctor = get_object_or_404(staffProfile, id=doctor_id, role="doctor")
    user = doctor.user
    doctor.delete()
    user.delete()
    messages.success(request, f"Doctor {user.username} has been removed.")
    return redirect("manager:all_doctor")

#------------------------------------------------------------------------------------------------------
    
def remove_nurse(request, nurse_id):
    nurse = get_object_or_404(staffProfile, id=nurse_id, role="nurse")
    user = nurse.user
    nurse.delete()
    user.delete()
    messages.success(request, f"Nurse {user.username} has been removed.")
    return redirect("manager:all_nurse")

#------------------------------------------------------------------------------------------------------

def all_patient(request):
    patients = Patient.objects.filter(hospital=request.user.staffprofile.hospital)
    paginator = Paginator(patients, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    total_patient = patients.count()
    return render(request, "manager/all_patient.html", {"page_obj":page_obj,"total_patient":total_patient})

#------------------------------------------------------------------------------------------------------

def all_nurse(request):
    nurses = staffProfile.objects.filter(role="nurse", hospital=request.user.staffprofile.hospital)
    paginator = Paginator(nurses, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    total_nurse = nurses.count()
    return render(request, "manager/all_nurse.html", {"page_obj":page_obj,"total_nurse":total_nurse})

#------------------------------------------------------------------------------------------------------

def all_doctor(request):   
    doctors = staffProfile.objects.filter(role="doctor", hospital=request.user.staffprofile.hospital)
    paginator = Paginator(doctors, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    total_doctor = doctors.count()
    return render(request, "manager/all_doctors.html", {"page_obj":page_obj,"total_doctor":total_doctor})

#------------------------------------------------------------------------------------------------------

def detail_doctor(request,doctor_id:int):
    doctor = get_object_or_404(staffProfile, id=doctor_id, role="doctor")
    all_patient = Patient.objects.filter(doctor=doctor)
    patient_num = all_patient.count()
    total_ct_scans = PatientRecord.objects.filter(
        patient__in=all_patient,
        ct_image__isnull=False
    ).exclude(ct_image='images/default.jpg').count()
    return render(request, "manager/doctor_detail.html", {"doctor":doctor,"patient_num":patient_num,"total_ct_scans":total_ct_scans})

#------------------------------------------------------------------------------------------------------

def detail_nurse(request,nurse_id:int):
    nurse = get_object_or_404(staffProfile, id=nurse_id, role="nurse")
    return render(request, "manager/nurse_detail.html", {"nurse":nurse})