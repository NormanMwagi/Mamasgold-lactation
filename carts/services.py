from .models import Cart, CartItem
from store.models import Product

def get_cart(request):
    cart_id = request.session.session_key or request.session.create()
    cart, _ = Cart.objects.get_or_create(cart_id=cart_id)
    return cart

def add_product_to_cart(request, product_id):
    cart = get_cart(request)
    product = Product.objects.get(id=product_id)
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart, 
        product=product, 
        defaults={"quantity": 1} 
        )
    
    if not created:
        cart_item.quantity += 1
    cart_item.save()
    return cart_item

def remove_product_from_cart(request, product_id, remove_all=False):
    cart = get_cart(request)
    product = Product.objects.get(id=product_id)
    try:
        cart_item = CartItem.objects.get(cart=cart, product=product)
        if remove_all or cart_item.quantity == 1:
            cart_item.delete()
        else:
            cart_item.quantity -= 1
            cart_item.save()
    except CartItem.DoesNotExist:
        pass

def calculate_cart_totals(cart):
    """Returns cart totals and items"""
    cart_items = CartItem.objects.filter(cart=cart, is_active=True)
    total = sum(item.product.price * item.quantity for item in cart_items)
    quantity = sum(item.quantity for item in cart_items)
    delivery_fee = 0  # later you can make this dynamic
    grand_total = total + delivery_fee
    return {
        "cart_items": cart_items,
        "total": total,
        "quantity": quantity,
        "delivery_fee": delivery_fee,
        "grand_total": grand_total,
    }
