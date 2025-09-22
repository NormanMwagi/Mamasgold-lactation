from django.shortcuts import render
from django.http import HttpResponse
from store.models import Product
from django.http import HttpResponse
from django.contrib.auth import get_user_model

def index(request):

    products = Product.objects.all().filter(is_available = True)
    context = {
        'products': products,
    }
    return render(request, 'index.html', context)

def about(request):
    return render(request, 'about.html')
def create_admin(request):
    User = get_user_model()
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser(
            username="mwagi",
            email="normannyareru@gmail.com",
            password="Nyareru123"  # change this!
        )
        return HttpResponse("✅ Superuser created: mwagi / Nyareru123")
    return HttpResponse("⚠️ Superuser already exists.")