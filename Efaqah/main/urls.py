from . import views
from django.urls import path

app_name = "main"

urlpatterns = [
    path('', views.landing_page, name="landing_page"),
    path('login/', views.user_login, name="login"),
    path('request_form/', views.request_form, name="request_form"),
    path('stripe/webhook/', views.stripe_webhook, name='stripe-webhook'),
]