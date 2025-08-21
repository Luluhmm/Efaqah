from django.db import models
from django_countries.fields import CountryField
from django.conf import settings
import stripe
from django.core.mail import send_mail

# Create your models here.

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
    payment_link = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.firstname} {self.lastname} - {self.status}"
    
    def save(self, *args, **kwargs):
        
        super().save(*args, **kwargs) #Call the original save method
