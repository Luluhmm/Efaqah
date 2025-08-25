from django.urls import path
from . import views

app_name = "nurse"

urlpatterns = [
    path('', views.nurse_dashboard, name="nurse_dashboard"),
    path('add/', views.add_patient_view, name="add_patient_view"),
    path('patient/<int:pk>/', views.view_patient, name='view_patient'),
    path('detail/<int:patient_id>',views.view_patient,name="view_patient"),
    path("update/<int:patient_id>/", views.update_patient_view, name="update_patient_view"),
    path('delete/<int:patient_id>',views.delete_patient_view,name="delete_patient_view")
]