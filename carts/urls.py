from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.cart, name='cart'),
    path('add_cart/<int:product_id>/', views.add_cart, name='add_cart'),
    path('remove_cart/<int:product_id>/', views.remove_cart, name='remove_cart'),
    path('remove_cart_item/<int:product_id>/', views.remove_cart_item, name='remove_cart_item'),
    path('checkout/', views.checkout, name='checkout'),
    path('process_checkout/', views.process_checkout, name='process_checkout'),
    path('payment_page/', views.payment_page, name='payment_page'),
    path('payment_success/<order_number>/', views.payment_success, name='payment_success'),
    path('process_payment/', views.process_payment, name='process_payment'),
    path('mpesa_callback/', views.mpesa_callback, name='mpesa_callback'),
    path('payment_confirmation/<order_number>/', views.payment_confirmation, name='payment_confirmation'),
    path('check_payment_status/', views.check_payment_status, name='check_payment_status'),
]