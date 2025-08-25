from . import views
from django.urls import path

app_name = "main"

urlpatterns = [
    path('', views.landing_page, name="landing_page"),

    path('login/', views.user_login, name="login"),
    path('subscribe/', views.subscribe_view, name="subscribe_view"),
    path('request_form/', views.request_form, name="request_form"),

    path('subscribe_form/', views.subscribe_form, name="subscribe_form"),
    path('create-checkout/<str:plan>/<int:hospital_id>/', views.create_checkout_session, name="create_checkout_session"),
    path('payment/pending/', views.payment_pending, name="payment_pending"),
    path('payment/success/', views.payment_success, name="payment_success"),
    path('payment/cancelled/', views.payment_cancelled, name="payment_cancelled"),
]