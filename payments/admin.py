from django.contrib import admin
from .models import Transaction, PaymentStatus

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('order', 'phone_number', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order__order_number', 'phone_number', 'mpesa_receipt_number')


@admin.register(PaymentStatus)
class PaymentStatusAdmin(admin.ModelAdmin):
    list_display = ('checkout_request_id', 'result_code', 'result_desc', 'created_at')
    list_filter = ('result_code',)
    search_fields = ('checkout_request_id',)
