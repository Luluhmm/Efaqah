from django import forms
from .models import Registration
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget


class RegistrationForm(forms.ModelForm):
    country = CountryField().formfield(
        widget=CountrySelectWidget(attrs={'class': 'form-input'})
    )
    class Meta:
        model = Registration
        fields = ["firstname", "lastname", "email", "phone", "medical_affiliation", "country","description"]