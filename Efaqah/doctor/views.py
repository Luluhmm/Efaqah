from itertools import count
from django.shortcuts import render,redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from doctor.models import PatientRecord, PatientSymptom
from nurse.models import Patient
from django.core.paginator import Paginator
import csv
from django.db.models import Count,Q
from django.utils.timezone import now
from .utils import predict_risk                     
from .utils_cnn import cnn_predict_from_uploaded_file 
from .forms import StrokeForm, CnnForm
from django.db.models import F, FloatField, ExpressionWrapper
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime


# Create your views here.

def doctor_dashboard(request: HttpRequest):
    doctor_profile = request.user.staffprofile
    all_patient = Patient.objects.filter(doctor=doctor_profile).order_by("-id")
    patient_num = all_patient.count()

    # ===== Critical Patients =====
    # patients with >= 3 stroke-positive records IN THE CURRENT MONTH,
    today = now().date()
    this_year, this_month = today.year, today.month

    critical_patient_ids_qs = (
        PatientRecord.objects
        .filter(
            patient__doctor=doctor_profile,
            date__year=this_year,
            date__month=this_month,
        )
        .filter(
            Q(symptoms__stroke=True) |
            Q(ct_result__iexact="Stroke likely")
        )
        .values('patient')
        .annotate(pos_count=Count('id'))
        .filter(pos_count__gte=3)
        .values_list('patient', flat=True)
    )
    critical_patient_ids = list(critical_patient_ids_qs)
    critical_patient_num = len(critical_patient_ids)

    # ===== New Patients This Month =====
    new_patient_month = all_patient.filter(
        created_at__year=this_year,
        created_at__month=this_month
    ).count()

    # ===== High Risk (latest record > 0.7) =====
    high_risk_patient_ids = []
    for p in all_patient:
        latest_record = p.records.order_by('-date', '-id').first()
        if latest_record and latest_record.stroke_risk > 0.7:
            high_risk_patient_ids.append(p.id)
    high_risk_patient_num = len(high_risk_patient_ids)

    # ===== Clinical Alerts (who is unstable and what worsened) =====
    def _is_abnormal_glucose(v):
        try:
            return float(v) > 140
        except Exception:
            return False

    def _is_abnormal_bmi(v):
        try:
            return float(v) >= 30
        except Exception:
            return False

    unstable_details = []
    for p in all_patient:
        qs = (
            PatientRecord.objects
            .filter(patient=p, symptoms__isnull=False)
            .select_related("symptoms")
            .order_by("-date", "-id")
        )
        latest = qs[0] if qs else None
        prev   = qs[1] if len(qs) > 1 else None
        if not (latest and prev and latest.symptoms and prev.symptoms):
            continue

        score_up     = (latest.symptom_score or 0) > (prev.symptom_score or 0)
        glucose_up   = _is_abnormal_glucose(getattr(latest.symptoms, "avg_glucose_level", None)) and not _is_abnormal_glucose(getattr(prev.symptoms, "avg_glucose_level", None))
        bmi_up       = _is_abnormal_bmi(getattr(latest.symptoms, "bmi", None)) and not _is_abnormal_bmi(getattr(prev.symptoms, "bmi", None))

        if score_up or glucose_up or bmi_up:
            unstable_details.append({
                "patient": p,
                "score_up": score_up,
                "glucose_up": glucose_up,
                "bmi_up": bmi_up,
                "glucose_from": getattr(prev.symptoms, "avg_glucose_level", None),
                "glucose_to": getattr(latest.symptoms, "avg_glucose_level", None),
                "bmi_from": getattr(prev.symptoms, "bmi", None),
                "bmi_to": getattr(latest.symptoms, "bmi", None),
                "score_from": prev.symptom_score,
                "score_to": latest.symptom_score,
            })

    trend_alerts_num = len(unstable_details)

    # ===== Recent Activity (last 5) =====
    recent_records = (
        PatientRecord.objects
        .filter(patient__doctor=doctor_profile)
        .select_related("patient", "symptoms")
        .annotate(risk_pct=ExpressionWrapper(F("stroke_risk") * 100.0, output_field=FloatField()))
        .order_by("-date", "-id")[:5]
    )

    # ===== Patient list slice =====
    paginator = Paginator(all_patient, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "patient_num": patient_num,
        "critical_patient_num": critical_patient_num,
        "new_patient_month": new_patient_month,
        "high_risk_patient_num": high_risk_patient_num,
        "trend_alerts_num": trend_alerts_num,       # same key your template already uses
        "recent_records": recent_records,
        "critical_patient_ids": critical_patient_ids,
        "high_risk_patient_ids": high_risk_patient_ids,
        "unstable_patients": all_patient.filter(id__in=[u["patient"].id for u in unstable_details])[:6],
        "unstable_details": unstable_details,       # optional: use if you want to show who & what
    }
    return render(request, "doctor/doctor_dashboard.html", context)

#------------------------------------------------------------------------------------------------------

# def add_symptom_view(request:HttpRequest, patient_id:int):
#     #add symptom to calculate the risk of happend strock 
#     return render(request, "doctor/add_symptom.html")

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

def _is_abnormal_glucose(v): 
    try:
        return float(v) > 140
    except Exception:
        return False

def _is_abnormal_bmi(v):
    try:
        return float(v) >= 30
    except Exception:
        return False

def _latest_two_symptom_records(patient: Patient):
    """
    Return (latest_with_symptoms, previous_with_symptoms) for a patient.
    """
    qs = PatientRecord.objects.filter(patient=patient, symptoms__isnull=False).select_related("symptoms").order_by("-date", "-id")
    latest = qs[0] if qs else None
    prev = qs[1] if len(qs) > 1 else None
    return latest, prev

# --- main view ---
def add_ct_view(request, patient_id: int):
    patient = get_object_or_404(Patient, pk=patient_id)

    result = None
    cnn_result = None
    error = None
    cnn_error = None

    if request.method == "POST":

        # -------- Symptoms (tabular ML) --------
        if "predict_tabular" in request.POST:
            form = StrokeForm(request.POST)
            cnn_form = CnnForm()

            if form.is_valid():
                d = form.cleaned_data

                gender = _map_gender(patient.gender)
                age = float(patient.age or 0)
                residence = _map_residence(patient.residence_type)
                work_type = _normalize_work_type(d.get("work_type"))

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
                        "label": "Stroke" if label == 1 else "No Stroke",
                        "threshold": f"{thr:.3f}",
                        "band": band,
                    }

                    rec = PatientRecord.objects.create(
                        patient=patient,
                        date=now().date(),
                        stroke_risk=proba,
                        ct_result="—",
                        symptom_score=_compute_symptom_score(
                            age=age,
                            bmi=payload["bmi"],
                            hypertension=payload["hypertension"],
                            heart_disease=payload["heart_disease"],
                            smoking_status=payload["smoking_status"],
                        ),
                    )

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
                        "prob_pct": round(prob * 100, 1),
                        "label": "Stroke" if label == 1 else "Normal",
                        "band": band,
                    }

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

    # Last 5 scans for gallery
    last_scans = patient.records.filter(ct_result__in=["Normal", "Stroke likely"]).order_by("-date", "-id")[:5]

    return render(request, "doctor/add_ct.html", {
        "patient": patient,
        "form": form,
        "cnn_form": cnn_form,
        "result": result,
        "cnn_result": cnn_result,
        "error": error,
        "cnn_error": cnn_error,
        "last_scans": last_scans,
    })

#-------------------- STROKE DETECTION -------------------------

def all_patient_view(request: HttpRequest):
    """
    Shows all patients for the logged-in doctor, with optional filters:
      ?critical=1  -> patients with >=3 stroke-positive records THIS MONTH (ML or CNN)
      ?highrisk=1  -> patients whose latest record has stroke_risk > 0.7
    """
    doctor_profile = request.user.staffprofile
    patients_qs = Patient.objects.filter(doctor=doctor_profile).order_by("-id")

    # --- CRITICAL (match dashboard definition exactly) ---
    if request.GET.get("critical") == "1":
        today = now().date()
        this_year, this_month = today.year, today.month
        critical_ids = (
            PatientRecord.objects
            .filter(
                patient__doctor=doctor_profile,
                date__year=this_year,
                date__month=this_month,
            )
            .filter(Q(symptoms__stroke=True) | Q(ct_result__iexact="Stroke likely"))
            .values("patient")
            .annotate(pos_count=Count("id"))
            .filter(pos_count__gte=3)
            .values_list("patient", flat=True)
        )
        patients_qs = patients_qs.filter(id__in=critical_ids)

    # --- HIGHRISK (latest record > 0.7) ---
    if request.GET.get("highrisk") == "1":
        highrisk_ids = []
        # iterate only over the already-filtered set (works with or without critical)
        for p in patients_qs:
            latest = p.records.order_by("-date", "-id").first()
            if latest and latest.stroke_risk > 0.7:
                highrisk_ids.append(p.id)
        patients_qs = patients_qs.filter(id__in=highrisk_ids)

    # --- paginate ---
    paginator = Paginator(patients_qs, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "doctor/all_patient.html", {"page_obj": page_obj})

#------------------------------------------------------------------------------------------------------

def patient_detail_view(request: HttpRequest, patient_id: int):
    patient = get_object_or_404(Patient, pk=patient_id)
    last_records = (
    patient.records
    .select_related("symptoms")
    .annotate(risk_pct=ExpressionWrapper(F("stroke_risk") * 100, output_field=FloatField()))
    .order_by("-date", "-id")[:3]
)
    last_scans = patient.records.filter(ct_result__in=["Normal", "Stroke likely"]).order_by("-date", "-id")[:5]
    return render(request, "doctor/patient_detail.html", {
        "patient": patient,
        "last_records": last_records,
        "last_scans": last_scans,
    })
#------------------------------------------------------------------------------------------------------

def history_view(request: HttpRequest, patient_id: int):
    """
    Show ML vs CNN history with date filters on-page.
    ?start=YYYY-MM-DD&end=YYYY-MM-DD
    """
    patient = get_object_or_404(Patient, pk=patient_id)
    start = request.GET.get("start")
    end   = request.GET.get("end")

    ml_qs = (
        PatientRecord.objects
        .filter(patient=patient, symptoms__isnull=False)
        .select_related("symptoms")
    )
    cnn_qs = (
        PatientRecord.objects
        .filter(patient=patient, symptoms__isnull=True)
    )

    if start and end:
        ml_qs  = ml_qs.filter(date__range=[start, end])
        cnn_qs = cnn_qs.filter(date__range=[start, end])

    ml_records = ml_qs.annotate(
        risk_pct=ExpressionWrapper(F("stroke_risk") * 100.0, output_field=FloatField())
    ).order_by("-date", "-id")

    cnn_records = cnn_qs.annotate(
        risk_pct=ExpressionWrapper(F("stroke_risk") * 100.0, output_field=FloatField())
    ).order_by("-date", "-id")

    return render(request, "doctor/history.html", {
        "patient": patient,
        "ml_records": ml_records,
        "cnn_records": cnn_records,
        "start": start or "",
        "end": end or "",
    })

#------------------------------------------------------------------------------------------------------

def export_view(request: HttpRequest, patient_id: int):
    """
    Export history to CSV, optionally filtered by:
      ?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
    If no records in range, returns a CSV with headers only.
    """
    patient = get_object_or_404(Patient, pk=patient_id)

    # --- Parse dates safely (optional) ---
    start_raw = request.GET.get("start_date")
    end_raw = request.GET.get("end_date")
    start = end = None

    def _parse(d):
        try:
            return datetime.strptime(d, "%Y-%m-%d").date()
        except Exception:
            return None

    if start_raw:
        start = _parse(start_raw)
        if start is None:
            return HttpResponseBadRequest("Invalid start_date, expected YYYY-MM-DD.")
    if end_raw:
        end = _parse(end_raw)
        if end is None:
            return HttpResponseBadRequest("Invalid end_date, expected YYYY-MM-DD.")

    # If only one is provided, we just ignore the filter (export all)
    records = (PatientRecord.objects
               .filter(patient=patient)
               .select_related("patient")
               .order_by("date", "id"))

    if start and end:
        # If user inverted dates, swap
        if start > end:
            start, end = end, start
        records = records.filter(date__range=[start, end])

    # --- Prepare CSV response ---
    response = HttpResponse(content_type="text/csv")
    filename = f"{patient.first_name}_{patient.last_name}_history.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "Date", "Risk %", "Band", "Decision", "CT Result", "Symptom Score",
        "Glucose", "BMI", "Hypertension", "Heart Disease", "Smoking",
        "Age", "Gender", "Residence",
    ])

    # If no rows, return headers-only CSV (no error)
    if not records.exists():
        return response

    # --- Write rows safely (symptoms may not exist) ---
    for r in records:
        try:
            s = r.symptoms  # OneToOne; may not exist
        except ObjectDoesNotExist:
            s = None

        # Band from risk
        band = "High" if r.stroke_risk >= 0.60 else ("Medium" if r.stroke_risk >= 0.30 else "Low")
        # Decision: positive if ML says stroke OR CNN says "Stroke likely"
        decision = "Stroke" if ((s and s.stroke) or (r.ct_result and r.ct_result.lower() == "stroke likely")) else "No Stroke / Normal"

        writer.writerow([
            r.date,
            f"{(r.stroke_risk or 0) * 100:.1f}",
            band,
            decision,
            (r.ct_result or "—"),
            (f"{r.symptom_score:.1f}" if r.symptom_score is not None else "—"),
            (f"{s.avg_glucose_level:.1f}" if s and s.avg_glucose_level is not None else "—"),
            (f"{s.bmi:.1f}" if s and s.bmi is not None else "—"),
            (("Yes" if s.hypertension else "No") if s is not None else "—"),
            (("Yes" if s.heart_disease else "No") if s is not None else "—"),
            (s.smoking_status if s is not None else "—"),
            (f"{s.age:.0f}" if s and s.age is not None else "—"),
            (s.gender if s is not None else "—"),
            (s.Residence_type if s is not None else "—"),
        ])

    return response



