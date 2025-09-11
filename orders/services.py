import uuid
from .models import Order, OrderItem
from carts.services import calculate_cart_totals

def create_order(user, cart, cart_items, form_data):
    order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    totals = calculate_cart_totals(cart)

    order = Order.objects.create(
        user=user,
        order_number=order_number,
        first_name=form_data["first_name"],
        last_name=form_data["last_name"],
        email=form_data["email"],
        phone=form_data["phone"],
        address=form_data["address"],
        city=form_data["city"],
        additional_info=form_data.get("additional_info", ""),
        total=totals["total"],
        delivery_fee=totals["delivery_fee"],
        grand_total=totals["grand_total"],
    )

    # Add order items
    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.product.price,
        )

    return order
