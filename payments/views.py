from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest
from django.urls import reverse
from datetime import datetime
import json, logging, requests, base64, time, os
from orders.models import Order  
from .models import Transaction, PaymentStatus
from dotenv import load_dotenv
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from payments.services import generate_access_token, initiate_mpesa_stk_push

 
load_dotenv()

CONSUMER_KEY = os.getenv('CONSUMER_KEY')
CONSUMER_SECRET = os.getenv('CONSUMER_SECRET')
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY')
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE')
MPESA_BASE_URL = os.getenv('MPESA_BASE_URL')
CALLBACK_URL = os.getenv('CALLBACK_URL')

logger = logging.getLogger(__name__)

@login_required(login_url='login')
def payment_page(request):
    """Display M-Pesa payment page"""
    order_number = request.session.get('order_number')
    if not order_number:
        messages.error(request, 'No order data found. Please checkout again.')
        return redirect('checkout')

    try:
        order = Order.objects.get(order_number=order_number, user=request.user)
    except Order.DoesNotExist:
        messages.error(request, "Order does not exist.")
        return redirect('checkout')

    context = {
        'order': order,
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
        # Print detailed error information
        if hasattr(e, 'response') and e.response:
            print(f"Response status: {e.response.status_code}")
            print(f"Response content: {e.response.text}")
        return {
            'success': False,
            'message': 'Failed to initiate payment'
        }

@login_required(login_url='login')
def process_payment(request):
    if request.method == 'POST':
        order_number = request.session.get('order_number')
        if not order_number:
            return JsonResponse({'success': False, 'message': 'Order not found in session'})
        
        try:
            order = Order.objects.get(order_number=order_number, user=request.user)
        except Order.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Order not found'})
        
        phone_number = request.POST.get('phone_number')
        if not phone_number or len(phone_number) < 10:
            return JsonResponse({'success': False, 'message': 'Please enter a valid phone number'})
        
        callback_url = request.build_absolute_uri(reverse('mpesa_callback'))
        
        try:
            payment_response = initiate_mpesa_stk_push(
                phone_number,
                order.grand_total,
                order.order_number,
                callback_url
            )
            
            if payment_response['success']:
                response_data = payment_response['data']
                
                # Create Transaction record
                transaction = Transaction.objects.create(
                    order=order,
                    checkout_request_id=response_data.get('CheckoutRequestID'),
                    amount=order.grand_total,
                    phone_number=phone_number,
                    status='pending'
                )
                
                request.session['payment_data'] = {
                    'checkout_request_id': response_data.get('CheckoutRequestID'),
                    'merchant_request_id': response_data.get('MerchantRequestID'),
                    'phone_number': phone_number,
                    'amount': float(order.grand_total),
                    'order_number': order.order_number,
                    'transaction_id': transaction.id  # Store transaction ID
                }
                
                return JsonResponse({
                    'success': True,
                    'message': 'Payment request sent successfully',
                    'checkout_request_id': response_data.get('CheckoutRequestID'),
                    'redirect_url': reverse('payment_confirmation', args=[order.order_number])
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': payment_response.get('message', 'Payment initiation failed')
                })
                
        except Exception as e:
            print(f"Payment processing error: {e}")
            return JsonResponse({'success': False, 'message': 'Payment processing error. Please try again.'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required(login_url='login')
def payment_confirmation(request, order_number):
    """Show payment confirmation page"""
    # Get order_number from URL parameter instead of session
    payment_data = request.session.get('payment_data')
    
    if not order_number or not payment_data:
        messages.error(request, 'Payment session expired. Please try again.')
        return redirect('checkout')
    
    try:
        order = Order.objects.get(order_number=order_number, user=request.user)
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('checkout')
    
    context = {
        'order': order,
        'payment_data': payment_data,
    }
    return render(request, 'store/payment_confirmation.html', context)

@csrf_exempt
def mpesa_callback(request):
    if request.method == 'POST':
        try:
            callback_data = json.loads(request.body)
            stk_callback = callback_data.get('Body', {}).get('stkCallback', {})
            result_code = stk_callback.get('ResultCode')
            checkout_request_id = stk_callback.get('CheckoutRequestID')
            
            # Update Transaction status
            try:
                transaction = Transaction.objects.get(checkout_request_id=checkout_request_id)
                if result_code == 0:
                    transaction.status = 'success'
                    # Extract receipt details from callback
                    callback_metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
                    for item in callback_metadata:
                        if item.get('Name') == 'MpesaReceiptNumber':
                            transaction.mpesa_receipt_number = item.get('Value')
                        elif item.get('Name') == 'TransactionDate':
                            transaction.transaction_date = datetime.strptime(
                                str(item.get('Value')), '%Y%m%d%H%M%S'
                            )
                    transaction.save()
                    order = transaction.order
                    order.payment_status = 'paid'
                    order.save()
                    # ✅ Send confirmation email to user
                    current_site = get_current_site(request)
                    mail_subject = 'Your Order has been Confirmed!'
                    message = render_to_string('store/order_success_email.html', {
                        'user': order.user,
                        'order': order,
                        'domain': current_site.domain,
                    })
                    to_email = order.user.email
                    email = EmailMessage(
                    mail_subject,
                    message,
                    settings.EMAIL_HOST_USER,  # must be your Gmail
                    [to_email]
                    )
                    email.content_subtype = "html"  # send as HTML
                    try:
                        email.send(fail_silently=False)
                        logger.info("Order confirmation email sent successfully to %s", to_email)
                    except Exception as e:
                        logger.error("Error sending order confirmation email: %s", str(e))

                else:
                    transaction.status = 'failed'
                    transaction.save()
            except Transaction.DoesNotExist:
                pass
            
            return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})
        
        except Exception as e:
            return JsonResponse({'ResultCode': 1, 'ResultDesc': f'Error: {str(e)}'})
    
    return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Invalid request method'})

def check_payment_status(request):
    """Check actual payment status via AJAX"""
    if request.method != 'GET':
        return JsonResponse({
            'success': False,
            'message': 'Invalid request method'
        })

    checkout_request_id = request.GET.get('checkout_request_id')
    if not checkout_request_id:
        return JsonResponse({
            'success': False,
            'message': 'No checkout request ID provided'
        })

    try:
        transaction = Transaction.objects.get(checkout_request_id=checkout_request_id)

        if transaction.status == 'success':
            return JsonResponse({
                'success': True,
                'status': 'success',
                'message': 'Payment confirmed',
                'mpesa_receipt': transaction.mpesa_receipt_number
            })

        elif transaction.status == 'failed':
            return JsonResponse({
                'success': True,
                'status': 'failed',
                'message': 'Payment failed'
            })

    except Transaction.DoesNotExist:
        pass  # Will proceed to query M-Pesa API

    try:
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

        response = requests.post(
            f"{MPESA_BASE_URL}/mpesa/stkpushquery/v1/query",
            json=payload,
            headers=headers,
            timeout=15
        )
        response.raise_for_status()
        response_data = response.json()

        if 'ResultCode' not in response_data:
            return JsonResponse({
                'success': False,
                'message': f'Unexpected response: {response_data}'
            })

        result_code = response_data.get('ResultCode')
        if result_code == '0':
            return JsonResponse({
                'success': True,
                'status': 'success',
                'message': 'Payment confirmed'
            })

        elif response_data.get('errorMessage') == "The transaction is being processed":
            return JsonResponse({
                'success': True,
                'status': 'pending',
                'message': 'Payment is still processing'
            })

        else:
            return JsonResponse({
                'success': True,
                'status': 'failed',
                'message': response_data.get('ResultDesc', 'Payment failed')
            })

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

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error checking payment status: {str(e)}'
        })

@login_required(login_url='login')
def payment_success(request, order_number):
    try:
        order = Order.objects.get(order_number=order_number, user=request.user)
        
        # Clear session data
        keys = ['order_number', 'payment_data', 'payment_results']
        [request.session.pop(key, None) for key in keys]
        
        return render(request, 'store/payment_success.html', {
            'order': order
        })
        
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('checkout')

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