from django.db import models
from nurse.models import Patient

# Create your models here.

#patient record model 
class PatientRecord(models.Model): 
      patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="records")
      date = models.DateField()
      stroke_risk = models.FloatField()
      ct_result = models.CharField(max_length=255)
      symptom_score = models.FloatField()
      ct_image = models.ImageField(upload_to="images/", default="images/default.jpg")

#------------------------------------------------------------------------------------------------------

#patient symptom model 
class PatientSymptom(models.Model):
      class WorkTypeChoices(models.TextChoices):
        type1 = "children", "children"
        type2 = "Govt_jov", "Govt_jov"
        type3 = "Never_worked", "Never_worked"
        type4 = "Private", "Private"
        type5 = "Self-employed", "Self-employed"

      class SmokingStatusChoices(models.TextChoices):
        status1 = "formerly smoked", "formerly smoked"
        status2 = "never smoked", "never smoked"
        status3 = "smokes", "smokes"
        status4 = "Unknown", "Unknown"

      hypertension = models.BooleanField()
      heart_disease =  models.BooleanField()
      ever_married = models.BooleanField()
      stroke = models.BooleanField()
      work_type = models.CharField(max_length=1024, choices=WorkTypeChoices.choices)
      smoking_status = models.CharField(max_length=1024, choices=SmokingStatusChoices.choices)
      bmi = models.FloatField()
      record = models.OneToOneField(PatientRecord, on_delete=models.CASCADE, related_name="symptoms")
      created_at = models.DateField(auto_now_add=True)


