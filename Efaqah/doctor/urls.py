from . import views
from django.urls import path


app_name = "doctor"

urlpatterns = [
 path('',views.doctor_dashboard,name="doctor_dashboard"),
 path('patients/', views.all_patient_view, name="all_patient_view"),
 path('detail/<int:patient_id>/',views.patient_detail_view,name="patient_detail_view"),
 path('history/<int:patient_id>/',views.history_view,name="history_view"),
 path('export/<int:patient_id>/',views.export_view,name="export_view"),
 path('ct/<int:patient_id>/',views.add_ct_view,name="add_ct_view"),

#  path('symptom/<int:patient_id>/',views.add_symptom_view,name="add_symptom_view")

 path('symptom/<int:patient_id>/',views.add_symptom_view,name="add_symptom_view"),
 path('demo_ct/<int:patient_id>/', views.demo_add_ct_view, name="demo_add_ct_view")

]
