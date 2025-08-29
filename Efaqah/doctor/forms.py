from django import forms
from doctor.models import PatientSymptom

# ------------------Stroke model (Machine Learning) ------------------------
WORK_CHOICES = [
    ("Private","Private"),
    ("Self-employed","Self-employed"),
    ("Govt_job","Govt_job"),
    ("children","children"),
    ("Never_worked","Never_worked"),
]
SMOKE_CHOICES = [
    ("never smoked","never smoked"),
    ("formerly smoked","formerly smoked"),
    ("smokes","smokes"),
    ("Unknown","Unknown"),
]
MARRIED_CHOICES = [("Yes","Yes"), ("No","No")]

_base = {"class": "w-full border rounded-md p-2"}

class StrokeForm(forms.Form):
    ever_married = forms.ChoiceField(label="Ever married", choices=MARRIED_CHOICES,
                                     widget=forms.Select(attrs=_base))
    work_type = forms.ChoiceField(choices=WORK_CHOICES, widget=forms.Select(attrs=_base))
    smoking_status = forms.ChoiceField(choices=SMOKE_CHOICES, widget=forms.Select(attrs=_base))

    hypertension = forms.IntegerField(min_value=0, max_value=1, widget=forms.NumberInput(attrs=_base))
    heart_disease = forms.IntegerField(min_value=0, max_value=1, widget=forms.NumberInput(attrs=_base))
    avg_glucose_level = forms.FloatField(min_value=0, widget=forms.NumberInput(attrs=_base))
    bmi = forms.FloatField(min_value=0, widget=forms.NumberInput(attrs=_base))


class DemoStrokeForm(forms.Form):
    ever_married = forms.ChoiceField(label="Ever married", choices=MARRIED_CHOICES,
                                     widget=forms.Select(attrs=_base))
    work_type = forms.ChoiceField(choices=WORK_CHOICES, widget=forms.Select(attrs=_base))
    smoking_status = forms.ChoiceField(choices=SMOKE_CHOICES, widget=forms.Select(attrs=_base))

    hypertension = forms.IntegerField(min_value=0, max_value=1, widget=forms.NumberInput(attrs=_base))
    heart_disease = forms.IntegerField(min_value=0, max_value=1, widget=forms.NumberInput(attrs=_base))
    avg_glucose_level = forms.FloatField(min_value=0, widget=forms.NumberInput(attrs=_base))
    bmi = forms.FloatField(min_value=0, widget=forms.NumberInput(attrs=_base))

    age = forms.FloatField(min_value=0, widget=forms.NumberInput(attrs=_base), required=True)
    gender = forms.ChoiceField(choices=PatientSymptom.GenderChoices.choices , widget=forms.Select(attrs=_base), required=True)
    residence_type = forms.ChoiceField(choices=PatientSymptom.ResidenceChoices.choices , widget=forms.Select(attrs=_base), required=True)

# ------------------Stroke model (Deep Learning) ------------------------
class CnnForm(forms.Form):
    ct = forms.ImageField(
        label="CT Image (JPG/PNG)",
        required=True,
        help_text="Upload a single brain CT image.",
        widget=forms.ClearableFileInput(attrs={"class": "w-full border rounded-md p-2 bg-white"})
    )