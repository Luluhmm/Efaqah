from . import views
from django.urls import path

app_name = "manager"

urlpatterns = [
    path('', views.manager_dashboard, name='manager_dashboard'),
    path('doctor/all/',views.all_doctor,name="all_doctor"),
    path('nurse/all/',views.all_nurse,name="all_nurse"),
    path('patient/all/',views.all_patient,name="all_patient"),
    path('doctor/add/', views.add_doctor, name='add_doctor'),
    path('nurse/add/', views.add_nurse, name='add_nurse'),
    path('doctor/<int:doctor_id>/update/', views.update_doctor, name='update_doctor'),
    path('doctor/<int:doctor_id>/detail/', views.detail_doctor, name='detail_doctor'),
    path('nurse/<int:nurse_id>/update/', views.update_nurse, name='update_nurse'),
    path('nurse/<int:nurse_id>/detail/',views.detail_nurse,name="detail_nurse"),
    path('doctor/<int:doctor_id>/delete', views.remove_doctor, name="remove_doctor"),
    path('nurse/<int:nurse_id>/delete', views.remove_nurse, name="remove_nurse"),
    path('patient/add/', views.add_patient_view, name="add_patient_view"),
    path('patient/<int:patient_id>/update/', views.update_patient_view, name='update_patient_view'),

]