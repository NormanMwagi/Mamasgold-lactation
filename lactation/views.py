from django.shortcuts import render
from django.http import HttpResponse
from store.models import Product

#main view(home)
def index(request):
    #get all products
    products = Product.objects.all().filter(is_available = True)
    #pass products in dictionary for rendering
    context = {
        'products': products,
    }
    return render(request, 'index.html', context)