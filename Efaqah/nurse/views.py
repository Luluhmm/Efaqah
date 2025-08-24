from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpRequest,HttpResponse
from .models import Patient

def nurse_dashboard(request: HttpRequest):
    patients = Patient.objects.all()
    return render(request, "nurse/nurse_dashboard.html", {
        'patients': patients,
        'patient_count': patients.count(),
        'GENDER_CHOICES': Patient.Gender.choices,
        'RESIDENCE_CHOICES': Patient.ResidenceType.choices,
    })


def add_patient_view(request: HttpRequest):
    if request.method == "POST":
        patient_id = request.POST.get("patient_id")
        phone_number = request.POST.get("phone_number")

        # تحقق إذا المريض موجود بالفعل
        if Patient.objects.filter(patient_id=patient_id).exists() or \
           (phone_number and Patient.objects.filter(phone_number=phone_number).exists()):
            messages.error(request, "This patient already exists in the system.")
            return redirect('nurse:nurse_dashboard')  # ارجع للـ dashboard

        # إنشاء المريض الجديد
        new_patient = Patient(
            patient_id=patient_id,
            first_name=request.POST.get("first_name"),
            last_name=request.POST.get("last_name"),
            age=request.POST.get("age"),
            gender=request.POST.get("gender"),
            residence_type=request.POST.get("residence_type"),
            phone_number=phone_number,
            emergency_phone=request.POST.get("emergency_phone"),
        )
        new_patient.save()
        messages.success(request, "Patient added successfully!")
        return redirect('nurse:nurse_dashboard')

    # GET لا يحتاج شيء لأن الفورم يظهر في dashboard
    return redirect('nurse:nurse_dashboard')

def view_patient(request: HttpRequest):
    pass


def update_patient_view(request, patient_id):
    # جلب المريض أو إعطاء 404 إذا لم يوجد
    patient = get_object_or_404(Patient, id=patient_id)

    if request.method == "POST":
        # تحديث البيانات
        patient.patient_id = request.POST.get('patient_id')
        patient.first_name = request.POST.get('first_name')
        patient.last_name = request.POST.get('last_name')
        patient.age = request.POST.get('age')
        patient.gender = request.POST.get('gender')
        patient.residence_type = request.POST.get('residence_type')
        patient.phone_number = request.POST.get('phone_number')
        patient.emergency_phone = request.POST.get('emergency_phone')

        try:
            patient.save()
            messages.success(request, "Patient updated successfully!")
            return redirect('nurse:nurse_dashboard')
        except Exception as e:
            messages.error(request, f"Error updating patient: {str(e)}")

    # إذا GET، رجّع نفس صفحة الداشبورد لكن مع بيانات المريض
    patients = Patient.objects.all()
    return render(request, 'nurse/nurse_dashboard.html', {
        'patient_to_update': patient,   # هذا المتغير يحدد لو بنعرض بيانات مريض للتعديل
        'patients': patients,
        'GENDER_CHOICES': Patient.Gender.choices,
        'RESIDENCE_CHOICES': Patient.ResidenceType.choices,
        'patient_count': patients.count(),
    })
