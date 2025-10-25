from .models import Cart, CartItem
from store.models import Product

def get_cart(request):
    cart_id = request.session.session_key or request.session.create()
    cart, _ = Cart.objects.get_or_create(cart_id=cart_id)
    return cart

def add_product_to_cart(request, product_id):
    product = Product.objects.get(id=product_id)

    if request.user.is_authenticated:
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={"quantity": 1, "is_active": True}
        )
    else:
        cart = get_cart(request)
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": 1, "is_active": True}
        )

    if not created:
        cart_item.quantity += 1
    cart_item.save()
    return cart_item

def remove_product_from_cart(request, product_id, remove_all=False):
    product = Product.objects.get(id=product_id)

    if request.user.is_authenticated:
        qs = CartItem.objects.filter(user=request.user, product=product, is_active=True)
    else:
        cart = get_cart(request)
        qs = CartItem.objects.filter(cart=cart, product=product, is_active=True)

    try:
        cart_item = qs.get()
        if remove_all or cart_item.quantity == 1:
            cart_item.delete()
        else:
            cart_item.quantity -= 1
            cart_item.save()
    except CartItem.DoesNotExist:
        pass

def calculate_cart_totals(cart=None, user=None):
    """
    Accepts either a session cart OR a user and returns totals and cart_items.
    Usage:
      calculate_cart_totals(cart=cart)  OR  calculate_cart_totals(user=request.user)
    """
    if user and user.is_authenticated:
        cart_items = CartItem.objects.filter(user=user, is_active=True)
    elif cart is not None:
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)
    else:
        cart_items = CartItem.objects.none()

    total = sum(item.product.price * item.quantity for item in cart_items)
    quantity = sum(item.quantity for item in cart_items)
    delivery_fee = 0
    grand_total = total + delivery_fee

    return {
        "cart_items": cart_items,
        "total": total,
        "quantity": quantity,
        "delivery_fee": delivery_fee,
        "grand_total": grand_total,
    }

