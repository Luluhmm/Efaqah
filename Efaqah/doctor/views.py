from itertools import count
from django.shortcuts import render,redirect
from django.http import HttpRequest, HttpResponse
from doctor.models import PatientRecord
from nurse.models import Patient
from django.core.paginator import Paginator
import csv
from django.db.models import Count,Q
from django.utils.timezone import now


# Create your views here.

def doctor_dashboard(request:HttpRequest):
    # All patients for this doctor
    doctor_profile = request.user.staffprofile
    all_patient = Patient.objects.filter(doctor=doctor_profile)
    patient_num = all_patient.count()

    # Critical patients: more than 2 stroke records
    critical_patient_ids = PatientRecord.objects.filter(
        patient__doctor=doctor_profile,
        symptoms__stroke=True
    ).values('patient').annotate(stroke_count=Count('symptoms')).filter(stroke_count__gt=2).values_list('patient', flat=True)
    critical_patient_num = Patient.objects.filter(id__in=critical_patient_ids).count()

    # Patients added this month
    current_month = now().month
    new_patient_month = all_patient.filter(created_at__month=current_month).count()

    # High stroke risk patients (latest record risk > 0.7)
    high_risk_patient_ids = []
    for patient in all_patient:
        latest_record = patient.records.order_by('-date').first()
        if latest_record and latest_record.stroke_risk > 0.7:
            high_risk_patient_ids.append(patient.id)
    high_risk_patient_num = len(high_risk_patient_ids)

    # Pagination
    paginator = Paginator(all_patient, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "patient_num": patient_num,
        "critical_patient_num": critical_patient_num,
        "new_patient_month": new_patient_month,
        "high_risk_patient_num": high_risk_patient_num,
        "all_patient": all_patient,
    }

    return render(request, "doctor/doctor_dashboard.html", context)
#------------------------------------------------------------------------------------------------------

def add_symptom_view(request:HttpRequest, patient_id:int):
    #add symptom to calculate the risk of happend strock 
    return render(request, "doctor/add_symptom.html")

#------------------------------------------------------------------------------------------------------

def add_ct_view(request:HttpRequest, patient_id:int):
    #add ct to detect the strock risk 
    patient = Patient.objects.get(pk=patient_id)
    return render(request, "doctor/add_ct.html",{"patient":patient})

#------------------------------------------------------------------------------------------------------

def all_patient_view(request:HttpRequest):
    #display all patients under logged in doctor 
    all_patient = Patient.objects.filter(doctor=request.user)
    paginator = Paginator(all_patient, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, "doctor/all_patient.html",{"page_obj":page_obj})

#------------------------------------------------------------------------------------------------------

def patient_detail_view(request:HttpRequest, patient_id:int):
    #patient detial 
    patient = Patient.objects.get(pk=patient_id)
    return render(request, "doctor/patient_detail.html", {
        "patient": patient})
#------------------------------------------------------------------------------------------------------

def history_view(request:HttpRequest, patient_id:int):
    #patient history 
    patient = Patient.objects.get(pk=patient_id)
    records = PatientRecord.objects.filter(patient=patient).select_related("symptoms")
    return render(request, "doctor/history.html",{"patient":patient,"records":records})

#------------------------------------------------------------------------------------------------------

def export_view(request:HttpRequest, patient_id: int):
    # Get patient and their records
    patient = Patient.objects.get(pk=patient_id)
    records = PatientRecord.objects.filter(patient=patient).select_related("symptoms")

    # Prepare CSV response
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{patient.first_name}_history.csv"'
    writer = csv.writer(response)

    # Header row (added Doctor Name)
    writer.writerow([
        "Doctor Name", "Date", "Stroke Risk", "CT Result", "Symptom Score", "CT Image",
        "Hypertension", "Heart Disease", "Stroke", "Work Type", "Smoking Status", "BMI"
    ])

    # Write records
    for record in records:
        symptoms = getattr(record, "symptoms", None)
        writer.writerow([
            patient.doctor_name,
            record.date.strftime("%Y-%m-%d"),
            record.stroke_risk,
            record.ct_result,
            record.symptom_score if record.symptom_score else "",
            record.ct_image.url if record.ct_image else "",
            symptoms.hypertension if symptoms else "",
            symptoms.heart_disease if symptoms else "",
            symptoms.stroke if symptoms else "",
            symptoms.work_type if symptoms else "",
            symptoms.smoking_status if symptoms else "",
            symptoms.bmi if symptoms else "",
        ])

    return response