from . import views
from django.urls import path

app_name = "main"

urlpatterns = [
    path('', views.landing_view, name="landing_view"),
    path('login/',views.login_view, name="login_view"),
]