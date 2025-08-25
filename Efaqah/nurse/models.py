from django.db import models
from main.models import Hospital


class Patient(models.Model):

    class Gender(models.TextChoices):
        MALE = 'M', 'Male'
        FEMALE = 'F', 'Female'

    class ResidenceType(models.TextChoices):
        URBAN = 'urban', 'Urban'
        RURAL = 'rural', 'Rural'

    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name="patients")
    patient_id = models.IntegerField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    emergency_phone = models.CharField(max_length=20, null=True, blank=True)
    gender = models.CharField(max_length=1, choices=Gender.choices)
    age = models.IntegerField()
    residence_type = models.CharField(max_length=10, choices=ResidenceType.choices, null=True, blank=True)
    doctor_name = models.CharField(max_length=255, null=True, blank=True, default=None)
    created_at = models.DateField(auto_now_add=True)