from django.shortcuts import render, redirect, get_object_or_404
from store.models import Product
from .models import Cart, CartItem
from payments.models import Transaction, PaymentStatus

from orders.models import Order, OrderItem
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseBadRequest
from django.urls import reverse
import json, logging, os, uuid, requests, base64
from datetime import datetime
from dotenv import load_dotenv 
from .services import get_cart, add_product_to_cart, remove_product_from_cart, calculate_cart_totals
from orders.services import create_order

def _cart_id(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key
def add_cart(request, product_id):
    add_product_to_cart(request, product_id)
    return redirect("cart")

def remove_cart(request, product_id):
    remove_product_from_cart(request, product_id, remove_all=False)
    return redirect("cart")

def remove_cart_item(request, product_id):
    remove_product_from_cart(request, product_id, remove_all=True)
    return redirect("cart")
def cart(request):
    cart = get_cart(request)
    totals = calculate_cart_totals(cart)
    return render(request, "store/cart.html", totals)

@login_required
def checkout(request):
    cart = get_cart(request)
    totals = calculate_cart_totals(cart)
    if not totals["cart_items"]:
        return redirect("cart")
    return render(request, "store/checkout.html", totals)

@login_required
def process_checkout(request):
    if request.method == "POST":
        cart = get_cart(request)
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        if not cart_items:
            messages.error(request, "Your cart is empty")
            return redirect("cart")

        order = create_order(request.user, cart, cart_items, request.POST)
        cart_items.delete()  # clear cart
        request.session["order_number"] = order.order_number
        return redirect("payment_page")

    return redirect("checkout")

