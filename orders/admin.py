from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price')
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number', 'user', 'phone', 'address',
        'status', 'payment_status', 'grand_total',
        'created_at', 'updated_at'
    )
    list_filter = ('status', 'payment_status', 'created_at')
    search_fields = (
        'order_number', 'user__username', 'user__email',
        'phone', 'address', 'city'
    )
    inlines = [OrderItemInline]
    readonly_fields = ('order_number', 'created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        ("Order Info", {
            "fields": ("order_number", "user", "status", "payment_status", "grand_total")
        }),
        ("Customer Details", {
            "fields": ("first_name", "last_name", "email", "phone", "address", "city", "additional_info")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price')
    search_fields = ('order__order_number', 'product__product_name')
    list_filter = ('order__created_at',)
    ordering = ('-order__created_at',)
