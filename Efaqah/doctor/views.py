from itertools import count
from django.shortcuts import render,redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse
from doctor.models import PatientRecord, PatientSymptom
from nurse.models import Patient
from django.core.paginator import Paginator
import csv
from django.db.models import Count,Q
from django.utils.timezone import now
from .utils import predict_risk                     
from .utils_cnn import cnn_predict_from_uploaded_file 
from .forms import StrokeForm, CnnForm


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
    paginator = Paginator(all_patient, 10)
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

#-------------------- STROKE DETECTION -------------------------

# --- helpers ---
def _map_gender(code: str) -> str:
    # nurse.Patient.gender: 'M'/'F' => ML expects 'Male'/'Female'
    return {"M": "Male", "F": "Female"}.get((code or "").upper(), "Other")

def _map_residence(code: str) -> str:
    # nurse.Patient.residence_type: 'urban'/'rural' => ML expects 'Urban'/'Rural'
    low = (code or "").lower()
    return "Urban" if low == "urban" else ("Rural" if low == "rural" else "Urban")

def _normalize_work_type(val: str) -> str:
    return "Govt_job" if (val or "") in ("Govt_jov", "Govt_job") else (val or "")

def _band_from_prob(p: float) -> str:
    return "High" if p >= 0.60 else ("Medium" if p >= 0.30 else "Low")

def _compute_symptom_score(*, age: float, bmi: float, hypertension: int, heart_disease: int, smoking_status: str) -> float:
    score = 0
    if hypertension == 1: score += 1
    if heart_disease == 1: score += 1
    if (smoking_status or "").lower() in ("smokes", "formerly smoked"): score += 1
    if bmi > 30: score += 1
    if age > 65: score += 1
    return float(score)

# --- main view ---
def add_ct_view(request, patient_id: int):
    patient = get_object_or_404(Patient, pk=patient_id)

    result = None
    cnn_result = None
    error = None
    cnn_error = None

    if request.method == "POST":

        # -------- Symptoms --------
        if "predict_tabular" in request.POST:
            form = StrokeForm(request.POST)
            cnn_form = CnnForm()

            if form.is_valid():
                d = form.cleaned_data

                # pull from patient profile
                gender = _map_gender(patient.gender)
                age = float(patient.age or 0)
                residence = _map_residence(patient.residence_type)

                work_type = _normalize_work_type(d.get("work_type"))

                # build exact payload for the ML model (EXPECTED_COLS order doesn’t matter as utils enforces in utils.py)
                payload = {
                    "gender": gender,
                    "ever_married": d["ever_married"],
                    "work_type": work_type,
                    "Residence_type": residence,
                    "smoking_status": d["smoking_status"],
                    "age": age,
                    "hypertension": int(d["hypertension"]),
                    "heart_disease": int(d["heart_disease"]),
                    "avg_glucose_level": float(d["avg_glucose_level"]),
                    "bmi": float(d["bmi"]),
                }

                try:
                    proba, label, thr = predict_risk(payload)
                    band = _band_from_prob(proba)

                    result = {
                        "risk_pct": round(proba * 100, 1),
                        "prob": f"{proba:.6f}",
                        "label": "stroke" if label == 1 else "no stroke",
                        "threshold": f"{thr:.3f}",
                        "band": band,
                        "inputs": payload,
                    }

                    # save PatientRecord
                    rec = PatientRecord.objects.create(
                        patient=patient,
                        date=now().date(),
                        stroke_risk=proba,
                        ct_result="—",  # no image here
                        symptom_score=_compute_symptom_score(
                            age=age,
                            bmi=payload["bmi"],
                            hypertension=payload["hypertension"],
                            heart_disease=payload["heart_disease"],
                            smoking_status=payload["smoking_status"],
                        ),
                    )

                    # snapshot symptoms (including patient fields)
                    try:
                        PatientSymptom.objects.create(
                            hypertension=bool(payload["hypertension"]),
                            heart_disease=bool(payload["heart_disease"]),
                            ever_married=(payload["ever_married"] == "Yes"),
                            stroke=(label == 1),
                            work_type=work_type,
                            smoking_status=payload["smoking_status"],
                            bmi=payload["bmi"],
                            age=age,
                            avg_glucose_level=payload["avg_glucose_level"],
                            gender=gender,
                            Residence_type=residence,
                            record=rec,
                        )
                    except Exception:
                        pass

                except Exception as e:
                    error = str(e)
            else:
                error = "Please correct the form errors."

        # -------- CNN (CT Image) --------
        elif "predict_cnn" in request.POST:
            form = StrokeForm()
            cnn_form = CnnForm(request.POST, request.FILES)
            if cnn_form.is_valid():
                ct_file = cnn_form.cleaned_data["ct"]
                try:
                    prob, label = cnn_predict_from_uploaded_file(ct_file)
                    band = _band_from_prob(prob)

                    cnn_result = {
                        "prob": f"{prob:.6f}",
                        "prob_pct": round(prob * 100, 1),
                        "label": "stroke" if label == 1 else "normal",
                        "band": band,
                    }

                    # save record with image (cnn); no symptoms on this path
                    PatientRecord.objects.create(
                        patient=patient,
                        date=now().date(),
                        stroke_risk=prob,
                        ct_result=("Stroke likely" if label == 1 else "Normal"),
                        symptom_score=0.0,
                        ct_image=ct_file,
                    )
                except Exception as e:
                    cnn_error = str(e)
            else:
                cnn_error = "Please provide a CT image."

        else:
            form = StrokeForm()
            cnn_form = CnnForm()
    else:
        form = StrokeForm()
        cnn_form = CnnForm()

    return render(request, "doctor/add_ct.html", {
        "patient": patient,
        "form": form,
        "cnn_form": cnn_form,
        "result": result,
        "cnn_result": cnn_result,
        "error": error,
        "cnn_error": cnn_error,
    })

#-------------------- STROKE DETECTION -------------------------

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
    records = PatientRecord.objects.filter(patient=patient).select_related("symptoms").order_by("-date", "-id")  # newest first
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
        "Hypertension", "Heart Disease", "Stroke", "Work Type", "Smoking Status", "BMI",
        "Gender", "Residence Type", "Age", "Avg Glucose"
    ])

    # Write records
    for record in records:
        symptoms = getattr(record, "symptoms", None)
        writer.writerow([
            patient.doctor,
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
            getattr(symptoms, "gender", "") if symptoms else "",
            getattr(symptoms, "Residence_type", "") if symptoms else "",
            getattr(symptoms, "age", "") if symptoms else "",
            getattr(symptoms, "avg_glucose_level", "") if symptoms else "",
        ])

    return response



