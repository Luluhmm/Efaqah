from . import views
from django.urls import path

app_name = "main"

urlpatterns = [
    path('', views.landing_page, name="landing_page"),
    path('go-home/', views.go_home, name='go_home'),
    path('login/', views.user_login, name="login"),
    path('subscribe/', views.subscribe_view, name="subscribe_view"),
    path('request_form/', views.request_form, name="request_form"),
    path('subscribe_form/', views.subscribe_form, name="subscribe_form"),
    path('create-checkout/<str:plan>/<int:hospital_id>/', views.create_checkout_session, name="create_checkout_session"),
    path('payment/pending/', views.payment_pending, name="payment_pending"),
    path('payment/success/', views.payment_success, name="payment_success"),
    path('payment/cancelled/', views.payment_cancelled, name="payment_cancelled"),
    path('get-cities/<int:country_id>/', views.get_cities, name='get_cities'),
    path('admin_view/',views.admin_view,name="admin_view"),
    path('request_demo/',views.request_demo,name="request_demo"),
    path('update/request_demo/<int:demo_id>/',views.update_status,name="update_status"),
    path('delete/request_demo/<int:demo_id>/',views.delete_demo,name="delete_demo"),
    path('about/',views.about_view,name="about_view"),
    path('contact/',views.contact_view,name="contact_view"),
    path('all_hospital/',views.all_hospital_view,name="all_hospital_view"),
    path('remove_hospital/<int:hospital_id>',views.delete_hospital,name="delete_hospital"),
    path('hospital_detail/<int:hospital_id>',views.hospital_detail,name="hospital_detail"),
    path('hospital_update/<int:hospital_id>',views.update_hospital,name="update_hospital"),
    path('privacy/',views.privacy_view,name="privacy_view"),
    path('logout/',views.logout_view,name="logout_view"),
    path("disclaimer/", views.disclaimer_view, name="disclaimer_view"),

]