from django.shortcuts import render, redirect, get_object_or_404
from store.models import Product
from .models import Cart, CartItem, PaymentStatus
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.urls import reverse
import json, os, uuid, requests, base64
from datetime import datetime
from dotenv import load_dotenv 


load_dotenv()
CONSUMER_KEY = os.getenv('CONSUMER_KEY')
CONSUMER_SECRET = os.getenv('CONSUMER_SECRET')
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY')
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE')
MPESA_BASE_URL = os.getenv('MPESA_BASE_URL')
CALLBACK_URL = os.getenv('CALLBACK_URL')
def _cart_id(request):
    
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart

def add_cart(request, product_id):
    #get product
    product = Product.objects.get(id=product_id)

    try:
        cart = Cart.objects.get(cart_id=_cart_id(request)) # get the cart using the present cart_id
    except Cart.DoesNotExist:
        cart = Cart.objects.create(
            cart_id = _cart_id(request)
        )
    cart.save()

    #cart items
    try:
        cart_item = CartItem.objects.get(product=product, cart=cart)
        cart_item.quantity += 1 #increment quantity
        cart_item.save()
    except CartItem.DoesNotExist:
        cart_item = CartItem.objects.create(
            product = product,
            quantity = 1,
            cart = cart,
        )
        cart_item.save()
    return redirect("cart")

def remove_cart(request, product_id):
    product = Product.objects.get(id=product_id)

    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_item = CartItem.objects.get(product=product, cart=cart)
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        
        else:
            cart_item.delete()
    except (Cart.DoesNotExist, CartItem.DoesNotExist):
        pass # Handle cases where the cart or item does not exist
    return redirect('cart')

def remove_cart_item(request, product_id):
    product = Product.objects.get(id=product_id)

    try:
        cart = Cart.objects.get(cart_id = _cart_id(request))
        cart_item = CartItem.objects.get(product=product, cart = cart)
        cart_item.delete()
    except (Cart.DoesNotExist, CartItem.DoesNotExist):
        pass

    return redirect('cart')

def cart(request, total=0, quantity=0, cart_item=None):
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        #loop through all cart items
        for cart_item in cart_items:
            total += (cart_item.product.price * cart_item.quantity)
            quantity += cart_item.quantity
        delivery_fee = 0
        grand_total = delivery_fee + total
    except Cart.DoesNotExist:
        cart_items = []  # Assign an empty list
        delivery_fee = 0
        grand_total = delivery_fee

    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'delivery_fee': delivery_fee,
        'grand_total': grand_total
    }

    return render(request, 'store/cart.html', context)

@login_required(login_url='login')
def checkout( request, total=0, quantity=0, cart_item=None):
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        if not cart_items:
            return redirect('cart')
        #loop through all cart items
        for cart_item in cart_items:
            total += (cart_item.product.price * cart_item.quantity)
            quantity += cart_item.quantity
        delivery_fee = 300
        grand_total = delivery_fee + total
    except Cart.DoesNotExist:
        cart_items = []  # Assign an empty list
        delivery_fee = 0
        grand_total = delivery_fee

    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'delivery_fee': delivery_fee,
        'grand_total': grand_total
    }
    return render(request, 'store/checkout.html', context)

@login_required(login_url='login')
def process_checkout(request):
    if request.method == 'POST':
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        phone = request.POST['phone']
        email = request.POST['email']
        address = request.POST['address']
        city = request.POST['city']
        additional_info = request.POST['additional_info']

        try:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
            if not cart_items:
                messages.error(request, 'Your cart is empty')
                return redirect('cart')
                
            total = sum(item.product.price * item.quantity for item in cart_items)
            delivery_fee = 0
            grand_total = total + delivery_fee
            
        except Cart.DoesNotExist:
            messages.error(request, 'Cart not found')
            return redirect('cart')
        order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        
        # Store order details in session for payment processing
        request.session['order_data'] = {
            'order_number': order_number,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone,
            'address': address,
            'city': city,
            'additional_info': additional_info,
            'total': float(total),
            'delivery_fee': float(delivery_fee),
            'grand_total': float(grand_total),
        }
        
        return redirect('payment_page')
    
    return redirect('checkout')
@login_required(login_url='login')
def payment_page(request):
    """Display M-Pesa payment page"""
    order_data = request.session.get('order_data')
    if not order_data:
        messages.error(request, 'No order data found. Please checkout again.')
        return redirect('checkout')
    
    context = {
        'order_data': order_data,
    }
    return render(request, 'store/payment.html', context)
def generate_access_token():
    try:
        credentials = f"{CONSUMER_KEY}:{CONSUMER_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        headers = {"Authorization": f"Basic {encoded_credentials}"}
        
        response = requests.get(
            f"{MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials",
            headers=headers,
            timeout=30
        )
        
        response.raise_for_status()
        data = response.json()
        return data.get("access_token")
    
    except Exception as e:
        print(f"Access token error: {str(e)}")
        return None

def initiate_mpesa_stk_push(phone_number, amount, order_number, callback_url):
    try:
        access_token = generate_access_token()
        if not access_token:
            return {'success': False, 'message': 'Failed to get access token'}
        # Format phone number
        if phone_number.startswith('0'):        
            phone_number = '254' + phone_number[1:]
        elif not phone_number.startswith('254'):        
            phone_number = '254' + phone_number
        headers = {"Authorization": f"Bearer {access_token}",
                   "Content-Type": "application/json"}
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        stk_password = base64.b64encode(f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}".encode()).decode()

        request_body ={
            "BusinessShortCode": MPESA_SHORTCODE,
            "Password": stk_password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": phone_number,
            "PartyB": MPESA_SHORTCODE,
            "PhoneNumber": phone_number,
            "CallBackURL": CALLBACK_URL,
            'AccountReference': order_number,
            'TransactionDesc': f'Payment for order {order_number}'
        }
        response = requests.post(
            f"{MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest",
            json=request_body,
            headers=headers,
        )
        response.raise_for_status()
        return {
            'success': True,
            'data': response.json()
        }

    except requests.exceptions.RequestException as e:
        print(f"STK Push error: {e}")
        return {
            'success': False,
            'message': 'Failed to initiate payment'
        }


@login_required(login_url='login')
def process_payment(request):
    """Process M-Pesa payment"""
    if request.method == 'POST':
        order_data = request.session.get('order_data')
        if not order_data:
            return JsonResponse({
                'success': False, 
                'message': 'Order data not found'
            })
        
        phone_number = request.POST.get('phone_number')
        
        # Validate phone number
        if not phone_number or len(phone_number) < 10:
            return JsonResponse({
                'success': False, 
                'message': 'Please enter a valid phone number'
            })
        
        # Build callback URL
        callback_url = request.build_absolute_uri(reverse('mpesa_callback'))
        
        try:
            # Initiate M-Pesa STK Push
            payment_response = initiate_mpesa_stk_push(
                phone_number, 
                order_data['grand_total'],
                order_data['order_number'],
                callback_url
            )
            
            if payment_response['success']:
                response_data = payment_response['data']
                
                # Store payment details in session
                request.session['payment_data'] = {
                    'checkout_request_id': response_data.get('CheckoutRequestID'),
                    'merchant_request_id': response_data.get('MerchantRequestID'),
                    'phone_number': phone_number,
                    'amount': order_data['grand_total'],
                    'order_number': order_data['order_number']
                }
                
                return JsonResponse({
                    'success': True,
                    'message': 'Payment request sent successfully',
                    'checkout_request_id': response_data.get('CheckoutRequestID'),
                    'redirect_url': reverse('payment_confirmation')
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': payment_response.get('message', 'Payment initiation failed')
                })
                
        except Exception as e:
            print(f"Payment processing error: {e}")
            return JsonResponse({
                'success': False,
                'message': 'Payment processing error. Please try again.'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required(login_url='login')
def payment_confirmation(request):
    """Show payment confirmation page"""
    order_data = request.session.get('order_data')
    payment_data = request.session.get('payment_data')
    
    if not order_data or not payment_data:
        messages.error(request, 'Payment session expired. Please try again.')
        return redirect('checkout')
    
    context = {
        'order_data': order_data,
        'payment_data': payment_data,
    }
    return render(request, 'store/payment_confirmation.html', context)

@csrf_exempt
def mpesa_callback(request):
    """Handle M-Pesa payment callbacks"""
    if request.method == 'POST':
        try:
            callback_data = json.loads(request.body)
            stk_callback = callback_data.get('Body', {}).get('stkCallback', {})
            result_code = stk_callback.get('ResultCode')
            checkout_request_id = stk_callback.get('CheckoutRequestID')
            
            # Initialize payment results in session
            if 'payment_results' not in request.session:
                request.session['payment_results'] = {}
            
            # Store payment result
            request.session['payment_results'][checkout_request_id] = {
                'result_code': result_code,
                'timestamp': datetime.now().isoformat(),
                'raw_data': json.dumps(callback_data)  # Store for debugging
            }
            request.session.modified = True
            
            return JsonResponse({
                'ResultCode': 0,
                'ResultDesc': 'Success'
            })
            
        except Exception as e:
            return JsonResponse({
                'ResultCode': 1,
                'ResultDesc': f'Error: {str(e)}'
            })
    
    return JsonResponse({
        'ResultCode': 1,
        'ResultDesc': 'Invalid request method'
    })

def check_payment_status(request):
    """Check actual payment status via AJAX"""
    if request.method == 'GET':
        checkout_request_id = request.GET.get('checkout_request_id')
        
        if not checkout_request_id:
            return JsonResponse({
                'success': False,
                'message': 'No checkout request ID provided'
            })
        
        try:
            # Query M-Pesa API for payment status
            access_token = generate_access_token()
            if not access_token:
                return JsonResponse({
                    'success': False,
                    'message': 'Failed to get access token'
                })
                
            headers = {"Authorization": f"Bearer {access_token}"}
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password = base64.b64encode(
                f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}".encode()
            ).decode()
            
            payload = {
                "BusinessShortCode": MPESA_SHORTCODE,
                "Password": password,
                "Timestamp": timestamp,
                "CheckoutRequestID": checkout_request_id
            }
            
            # Add timeout and better error handling
            try:
                response = requests.post(
                    f"{MPESA_BASE_URL}/mpesa/stkpushquery/v1/query",
                    json=payload,
                    headers=headers,
                    timeout=15
                )
                response.raise_for_status()
                response_data = response.json()
            except requests.exceptions.RequestException as e:
                return JsonResponse({
                    'success': False,
                    'message': f'M-Pesa API error: {str(e)}'
                })
            except json.JSONDecodeError:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid response from M-Pesa'
                })
            
            # Check if we got a valid response
            if 'ResultCode' not in response_data:
                return JsonResponse({
                    'success': False,
                    'message': f'Unexpected response: {response_data}'
                })
            
            # Interpret response
            result_code = response_data.get('ResultCode')
            if result_code == '0':
                return JsonResponse({
                    'success': True,
                    'status': 'success',
                    'message': 'Payment confirmed'
                })
            else:
                # Payment failed
                return JsonResponse({
                    'success': True,
                    'status': 'failed',
                    'message': response_data.get('ResultDesc', 'Payment failed')
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error checking payment status: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    })
def payment_success(request):
    """Payment successful page"""
    payment_data = request.session.get('payment_data', {})
    checkout_request_id = payment_data.get('checkout_request_id')
    
    if not checkout_request_id:
        messages.error(request, 'Invalid payment session')
        return redirect('home')
    
    # Verify payment through database or session
    payment_verified = False
    if 'payment_results' in request.session:
        payment_results = request.session['payment_results']
        if checkout_request_id in payment_results:
            if payment_results[checkout_request_id]['result_code'] == 0:
                payment_verified = True
    
    if not payment_verified:
        messages.warning(request, 'Payment not confirmed yet')
        return redirect('payment_confirmation')
    
    # Clear session data
    keys_to_delete = ['order_data', 'payment_data', 'payment_results']
    for key in keys_to_delete:
        if key in request.session:
            del request.session[key]
    
    return render(request, 'store/payment_success.html')
def payment_failed(request):
    """Payment failed page"""
    checkout_request_id = request.session.get('payment_data', {}).get('checkout_request_id')
    
    if checkout_request_id:
        # Get failure reason
        payment_status = PaymentStatus.objects.filter(
            checkout_request_id=checkout_request_id
        ).exclude(result_code=0).first()
        
        if payment_status:
            failure_message = {
                1032: "Payment cancelled by user",
                1037: "Timeout - no response from user",
                2001: "Insufficient funds",
                17: "Transaction declined by user"
            }.get(payment_status.result_code, f"Error code: {payment_status.result_code}")
        else:
            failure_message = "Payment failed for unknown reason"
    else:
        failure_message = "Payment session expired"
    
    context = {'failure_message': failure_message}
    return render(request, 'store/payment_failed.html', context)