
from django.urls import path
from . import views

urlpatterns = [
    path('payment_page/', views.payment_page, name='payment_page'),
    path('process_payment/', views.process_payment, name='process_payment'),
    path('payment_confirmation/<str:order_number>/', views.payment_confirmation, name='payment_confirmation'),
    path('payment_success/<str:order_number>/', views.payment_success, name='payment_success'),
    path('payment_failed/', views.payment_failed, name='payment_failed'),
    path('mpesa_callback/', views.mpesa_callback, name='mpesa_callback'),
    path('check_payment_status/', views.check_payment_status, name='check_payment_status'),
]
