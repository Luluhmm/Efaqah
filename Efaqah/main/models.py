from django.db import models
from django_countries.fields import CountryField
from django.conf import settings
import stripe
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from cities_light.models import City, Country as CitiesLightCountry

#------------------------------------------------------------------------------------------------------
class Hospital(models.Model):
    PLAN_CHOICES = (
        ('basic', 'Basic'),
        ('pro', 'Pro'),
        ('enterprise', 'Enterprise'),
    )

    SUBSCRIPTION_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('expired', 'Expired'),
        ('canceled', 'Canceled'),
    )

    name = models.CharField(max_length=255)
    country = models.ForeignKey(CitiesLightCountry, on_delete=models.SET_NULL, null=True, blank=True, related_name="hospitals")
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True, related_name="hospitals")
    address = models.TextField(blank=True, null=True)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20, blank=True, null=True)

    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='basic')
    subscription_status = models.CharField(max_length=20, choices=SUBSCRIPTION_STATUS_CHOICES, default="pending")
    subscription_start_date = models.DateField(null=True, blank=True)
    subscription_end_date = models.DateField(null=True, blank=True)
    payment_reference = models.CharField(max_length=255, null=True, blank=True)
    invoice_url = models.URLField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def activate_subscription(self, plan_year = 1):
        self.subscription_start_date = timezone.now().date()
        self.subscription_end_date = self.subscription_start_date.replace(year=self.subscription_start_date.year + plan_year)
        self.subscription_status = "paid"
        self.save()

    def is_active_subscription(self):
        return bool(self.subscription_end_date and self.subscription_end_date > timezone.now())

    def daily_patient_limit(self):
        limits = {
            "basic": 50,
            "pro": 150,
            "enterprise": 500,
        }
        return limits.get(self.plan, 50)

    def __str__(self):
        return self.name
    
#------------------------------------------------------------------------------------------------------

class DeletedHospital(models.Model):
    name = models.CharField(max_length=255)
    plan = models.CharField(max_length=50)
    subscription_status = models.CharField(max_length=50, default="paid")
    subscription_start_date = models.DateField(null=True, blank=True)
    deleted_at = models.DateTimeField(auto_now_add=True)

#------------------------------------------------------------------------------------------------------
#    
class staffProfile(models.Model):
    ROLE_CHOICES = (
        ('manager', 'Manager'),
        ('doctor', 'Doctor'),
        ('nurse', 'Nurse'),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name="staff")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.user.username} ({self.role}) - ({self.hospital.name})"

#------------------------------------------------------------------------------------------------------

class Registration(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
    )
    firstname = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    medical_affiliation = models.CharField(max_length=200)
    country = CountryField(blank_label="(Select country)")
    description = models.TextField(blank=True, null=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    stripe_session_id = models.CharField(max_length=255, blank=True, null=True)
    payment_link = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.firstname} {self.lastname} - {self.status}"
    
    def save(self, *args, **kwargs):
        
        super().save(*args, **kwargs) #Call the original save method


