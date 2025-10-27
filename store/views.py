from django.shortcuts import render, get_object_or_404
from .models import Product
from category.models import Category
from carts.views import _cart_id
#from django.http import HttpResponse
from carts.models import Cart, CartItem
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q

# Create your views here.
def store(request, category_slug=None):
    categories = None
    products = Product.objects.filter(is_available=True)

    # Category filter
    if category_slug:
        categories = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=categories)

    # Filter by price range
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    # Pagination
    paginator = Paginator(products.order_by('id'), 6)
    page = request.GET.get('page')
    paged_product = paginator.get_page(page)
    product_count = products.count()

    context = {
        'products': paged_product,
        'product_count': product_count,
        'min_price': min_price,
        'max_price': max_price,
    }
    return render(request, 'store/store.html', context)


def product_detail(request, category_slug, product_slug):
    try:
        single_product = Product.objects.get(category__slug=category_slug, slug=product_slug)
        in_cart = CartItem.objects.filter(cart__cart_id=_cart_id(request), product=single_product).exists()
    except Exception as e:
        raise e
    
    context ={
        'single_product': single_product,
        'in_cart':  in_cart,
    }
    return render(request, 'store/product_detail.html', context)

def search(request):
    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        if keyword:
            products = Product.objects.order_by('-created_date').filter(Q(description__icontains=keyword) | Q(product_name__icontains=keyword))
            product_count =products.count()
    context = {
        'products': products,
        'product_count': product_count,
    }
    return render(request,'store/store.html', context)