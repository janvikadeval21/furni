from django.shortcuts import render ,redirect ,get_object_or_404
from myapp.models import *
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required 
from django.contrib.auth import login,logout,authenticate
from django.contrib import messages
from decimal import Decimal
from django.http import JsonResponse , HttpResponse ,Http404
from myapp.utils import send_email 
from django.urls import reverse
from io import BytesIO
from django.template.loader import get_template, render_to_string
from django.core.mail import EmailMultiAlternatives
from xhtml2pdf import pisa
from .models import Order
from django.conf import settings
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .razorpay_utils import verify_payment,create_razorpay_order
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import json
import re
from django.views.decorators.csrf import csrf_exempt
def test_email(request):
 
    send_email(
        subject="Welcome to My Store",
        to_email="janvikadeval@gmail.com",
        template_name="emails/welcome_email.html",
        context={
            "name": "Janvi"
        }
    )
    return HttpResponse("Email sent successfully")
def create_order(request):
 
    order = create_razorpay_order(
        amount=500,
        receipt="test_receipt_001"
    )
 
    return JsonResponse(order)


def payment_page(request):
 
    amount = 500
 
    order = create_razorpay_order(
        amount=amount,
        receipt="test_receipt_002"
    )
 
    context = {
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "amount": order["amount"],
        "order_id": order["id"],
    }
 
    return render(request, "payment.html", context)
@require_POST
@login_required
def verify_payment_view(request):
    try:
        data = json.loads(request.body)
        payment_id = data.get("razorpay_payment_id")
        razorpay_order_id = data.get("razorpay_order_id")
        signature = data.get("razorpay_signature")
        local_order_id = data.get("local_order_id")

        is_verified = verify_payment(
            payment_id=payment_id,
            order_id=razorpay_order_id,
            signature=signature
        )

        if is_verified:
            order = get_object_or_404(Order, id=local_order_id, user=request.user)
            
            # ઓર્ડર પેમેન્ટ સ્ટેટસ અપડેટ
            if hasattr(order, 'payment_status'):
                order.payment_status = 'Paid'
            if hasattr(order, 'razorpay_payment_id'):
                order.razorpay_payment_id = payment_id
            order.save()

            # --- કૂપન વપરાશ રેકોર્ડ સેવ કરો (Online Payment સક્સેસ) ---
            if 'coupon_code' in request.session:
                applied_code = request.session.get('coupon_code')
                try:
                    used_coupon = Coupon.objects.get(code=applied_code)
                    CouponUsage.objects.get_or_create(
                        user=request.user,
                        coupon=used_coupon
                    )
                except Coupon.DoesNotExist:
                    pass
                # સેશનમાંથી કૂપન અને ડિસ્કાઉન્ટ ક્લીન કરો
                request.session.pop('coupon_code', None)
                request.session.pop('discount', None)
                request.session.pop('discount_amount', None)

            # કાર્ટ ખાલી કરો
            request.session['cart'] = {}

            return JsonResponse({
                "status": "success",
                "message": "Payment verified successfully.",
                "redirect_url": "/order-success/"
            })

        return JsonResponse({
            "status": "failed",
            "message": "Payment verification signature mismatch."
        }, status=400)
    except Exception as e:
        return JsonResponse({"status": "failed", "message": str(e)}, status=500)
    
def register(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if not username or not password:
            messages.error(request,"Please enter username or password")
            return redirect('register')

        if password != confirm_password:
            messages.error(request,"password and confirm password not match")
            return redirect('register')

        if User.objects.filter(username = username).exists():
            messages.error(request, "username already exists.")
            return redirect('register')

        if User.objects.filter(email = email).exists():
            messages.error(request, "email already exists.")
            return redirect('register')

        user =User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )

        login(request,user)
        messages.success(request,"User created succesfully")
        return redirect('index')

    return render(request,'register.html')

def login_user(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(username =username , password =password)

        if user is not None:
            login(request,user)
            return redirect('index')
        else:
            messages.error(request,"username not found")
            return redirect('login')

    return render(request ,'login.html')
    
def logout_user(request):
    logout(request)
    return redirect('login')

def contact(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        if first_name and last_name and email and message:
            ContactMessage.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                subject=subject,
                message=message
            )
            messages.success(request,"Your message has been sent successfully!")
        else:
            messages.error(request,"Please fill in all required fields.")
    return render(request,'contact.html')


def category(request):
    categories = Category.objects.all()
    return render(request,'category.html' , {'categories' : categories })

def product(request,id):
    product = get_object_or_404(Product , id=id)
    return render(request,'product.html',{'product':product})

def category_products(request,id):
    category = get_object_or_404(Category , id=id)
    products = Product.objects.filter(category=category)
    return render(request,'category_products.html',{'products':products , 'category':category})

@login_required
def profile(request):
   
    user_name = request.user.get_full_name() or request.user.username

    user_testimonials = Testimonial.objects.filter(name=user_name).order_by('-id')
    
    return render(request, 'profile.html', {
        'user': request.user,
        'testimonials': user_testimonials,
    })


@login_required
def add_testimonial(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        designation = request.POST.get('designation')
        content = request.POST.get('content')
        rating = request.POST.get('rating', 5)

        if not name:
            name = request.user.get_full_name() or request.user.username

        Testimonial.objects.create(
            name=name,
            designation=designation,
            content=content,
            rating=int(rating),
            page='all',          
            is_active=True       
        )

        messages.success(request, "Your testimonial has been submitted successfully! Thank you for your feedback.")
        return redirect('profile')

    return redirect('profile')

def add_to_cart(request):

    if request.method != "POST":
        return redirect('index')


    product_id = request.POST.get('product_id')
    quantity = request.POST.get('quantity', 1)


    product = get_object_or_404(
        Product,
        id=product_id
    )
    try:
        quantity = int(quantity)

    except (ValueError, TypeError):
        quantity = 1


    if quantity < 1:
        quantity = 1

    if product.stock <= 0:

        messages.error(
            request,
            f"{product.name} is out of stock."
        )

        return redirect(
            request.META.get('HTTP_REFERER', '/')
        )

    if quantity > product.stock:
        quantity = product.stock

    if not request.user.is_authenticated:

        return redirect('login')
    
    cart = request.session.get(
        'cart',
        {}
    )


    product_id = str(product.id)

    if product_id in cart:

        cart[product_id] += quantity

    else:

        cart[product_id] = quantity

    request.session['cart'] = cart

    request.session.modified = True

    return redirect(
        request.META.get(
            'HTTP_REFERER',
            '/'
        )
    )
def cart_count(request):

    cart = request.session.get('cart', {})

    total_quantity = sum(cart.values())

    return {
        'cart_total_quantity': total_quantity
    }
def cart(request):
    cart = request.session.get('cart', {})

    cart_items = []
    subtotal = 0

    for product_id, quantity in cart.items():
        product = get_object_or_404(Product, id=product_id)
        total = product.price * quantity

        cart_items.append({
            'product': product,
            'quantity': quantity,
            'total': total,
        })

        subtotal += total

    
    request.session['cart_subtotal'] = float(subtotal)


    discount = float(request.session.get('discount_amount', 0))
    coupon_code = request.session.get('coupon_code', None)

    # ૩. છેલ્લો ગ્રાન્ડ ટોટલ ગણો (સબટોટલ - ડિસ્કાઉન્ટ)
    grand_total = max(float(subtotal) - discount, 0.0)

    return render(
        request,
        'cart.html',
        {
            'cart_items': cart_items,
            'subtotal': subtotal,
            'discount': discount,
            'total': grand_total,
            'coupon_code': coupon_code,
        }
    )
            
def update_cart_quantity(request):
    if request.method != "POST":
        return JsonResponse({'success' : False , 'message' : 'Invalid request'})

    product_id = request.POST.get('product_id')
    quantity = request.POST.get('quantity')

    product = get_object_or_404(Product,id = product_id)
    try:
        quantity =int(quantity)
    except (ValueError,TypeError):
        return JsonResponse({'success':False,'message':'Invalid Quantity'})

    if quantity <1:
        quantity = 1

    if quantity > product.stock:
        quantity = product.stock

    cart = request.session.get('cart',{})
    product_id = str(product.id)

    if quantity>0:
        cart[product_id] = quantity
    else:
        cart.pop(product_id,None)

    request.session['cart'] = cart
    request.session.modified = True

    item_total = product.price * quantity

    cart_total = 0
    cart_quantity = 0 

    for pid , qty in cart.items():
        p=get_object_or_404(Product,id=pid)

        cart_total += p.price * qty
        cart_quantity += qty 

    return JsonResponse({
        'success':True,
        'quantity':quantity,
        'item_total' :float(item_total),
        'cart_subtotal' :float(cart_total),
        'cart_total' :float(cart_total),
        'cart_quantity' :cart_quantity,
    })

def remove_from_cart(request,id):
    if request.method == "POST":
        cart = request.session.get('cart',{})
        product_id = str(id)
        if product_id in cart:
            del cart[product_id]

        request.session['cart'] = cart
        request.session.modified = True

        messages.success(request,"Product removed from cart")
    return redirect('cart')

def clear_Cart(request):
    if request.method == "POST":
        request.session['cart'] = {}

        request.session.pop('coupon_code',None)
        request.session.pop('coupon_percent',None)

        request.session.modified = True

        messages.success(request,"Your cart has been cleared Successfully")

    return redirect('cart')

def blog(request):
    blogs = Blog.objects.all().order_by('-created_at')
    testimonials = Testimonial.objects.filter(page__in=['blog'], is_active=True).order_by('?')[:3]
    
    return render(request, 'blog.html', {
        'blogs': blogs,
        'testimonials': testimonials
    })

def blog_detail(request,id):
    blog = get_object_or_404(Blog,id=id)
    return render(request,'blog_detail.html',{'blog':blog})
@login_required
def checkout(request):
    cart = request.session.get('cart', {})

    if not cart:
        messages.warning(request, "Your cart is empty")
        return redirect('cart')

    cart_items = []
    subtotal = 0 

    for product_id, quantity in cart.items():
        product = get_object_or_404(Product, id=product_id)
        total = product.price * quantity
        cart_items.append({
            'product': product,
            'quantity': quantity,
            'total': total,
        })
        subtotal += total

    discount = request.session.get('discount_amount', request.session.get('discount', 0))
    try:
        discount = Decimal(str(discount))
    except:
        discount = Decimal('0')

    grand_total = subtotal - discount
    if grand_total < 0:
        grand_total = 0

    if request.method == "POST":
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        city = request.POST.get('city')
        state = request.POST.get('state')
        pincode = request.POST.get('pincode')
        payment_method = request.POST.get('payment_method')

        if not all([full_name, email, phone, address, city, state, pincode, payment_method]):
            messages.error(request, "Please fill all required fields")
            return redirect('checkout')

        if payment_method not in ['cod', 'online']:
            messages.error(request, "Please select a valid payment method")
            return redirect('checkout')

        order = Order.objects.create(
            user=request.user,
            full_name=full_name,
            email=email,
            phone=phone,
            address=address,
            city=city,
            state=state,
            pincode=pincode,
            subtotal=subtotal,
            discount=discount,
            total=grand_total,
            payment_method=payment_method,
            payment_status='Pending',
            order_status='Pending'
        )

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item['product'],
                quantity=item['quantity'],
                price=item['product'].price,
                total=item['total']
            )

        # ૧. Cash on Delivery (COD) હોય ત્યારે:
        if payment_method == 'cod':
            order.payment_status = 'Pending'
            order.order_status = 'Confirmed'
            order.save()

            # --- કૂપન વપરાશ રેકોર્ડ સેવ કરો (COD માટે) ---
            if 'coupon_code' in request.session:
                applied_code = request.session.get('coupon_code')
                try:
                    used_coupon = Coupon.objects.get(code=applied_code)
                    CouponUsage.objects.get_or_create(
                        user=request.user,
                        coupon=used_coupon
                    )
                except Coupon.DoesNotExist:
                    pass
                request.session.pop('coupon_code', None)
                request.session.pop('discount', None)
                request.session.pop('discount_amount', None)

            request.session['cart'] = {} 
            request.session['last_order_id'] = order.id
            request.session['payment_method'] = 'Cash on delivery'

            return redirect('order_success')

        # ૨. Online Payment હોય ત્યારે:
        elif payment_method == 'online':
            request.session['last_order_id'] = order.id
            request.session['payment_method'] = 'Online Payment'
            # નોંધ: ઓનલાઇનમાં verify_payment_view માં કૂપન સેવ અને ડીલીટ થશે
            return redirect('online_payment', order_id=order.id)

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'discount': discount,
        'total': grand_total,
    }
    return render(request, 'checkout.html', context)

@login_required
def online_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    import time
    receipt_id = f"rcpt_{order.id}_{int(time.time())}"

    razorpay_order = create_razorpay_order(
        amount=order.total,
        receipt=receipt_id
    )

    context = {
        'order': order,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'razorpay_order_id': razorpay_order['id'],
        'amount': razorpay_order['amount'],
    }
    return render(request, 'online_payment.html', context)

def generate_pdf_bytes(template_src, context_dict):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return result.getvalue()
    return None


def send_email(subject, to_email, template_name, context=None, attachments=None):
    if context is None:
        context = {}

    html_content = render_to_string(template_name, context)

    email = EmailMultiAlternatives(
        subject=subject,
        body="Please view this email in an HTML compatible email viewer.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    email.attach_alternative(html_content, "text/html")

    if attachments:
        for filename, content, mimetype in attachments:
            email.attach(filename, content, mimetype)

    email.send(fail_silently=False)
    return True
@login_required
def order_success(request):
    order_id = request.session.get('last_order_id')

    if not order_id:
        return redirect('index')

    order = get_object_or_404(Order, id=order_id)

    if order.user != request.user:
        messages.error(request, "You are not authorized to view this order.")
        return redirect('index')

    payment_method = request.session.get('payment_method', getattr(order, 'payment_method', 'N/A'))

    # સેફટી ક્લીનઅપ: જો હજુ સુધી કૂપન સેશનમાં રહી ગયું હોય તો અહીં સેવ કરીને હટાવી દો
    if 'coupon_code' in request.session:
        applied_code = request.session.get('coupon_code')
        try:
            used_coupon = Coupon.objects.get(code=applied_code)
            CouponUsage.objects.get_or_create(
                user=request.user,
                coupon=used_coupon
            )
        except Coupon.DoesNotExist:
            pass
        request.session.pop('coupon_code', None)
        request.session.pop('discount', None)
        request.session.pop('discount_amount', None)

    email_session_key = f'email_sent_{order.id}'
    if not request.session.get(email_session_key, False):
        try:
            recipient_email = getattr(order, 'email', None) or request.user.email

            pdf_context = {'order': order}
            pdf_bytes = generate_pdf_bytes('emails/invoice_pdf.html', pdf_context)

            attachments = []
            if pdf_bytes:
                attachments.append((f"Invoice_Order_{order.id}.pdf", pdf_bytes, "application/pdf"))

            download_url = request.build_absolute_uri(
                reverse('download_invoice', args=[order.id])
            )

            send_email(
                subject=f"Order Confirmed - #{order.id}",
                to_email=recipient_email,
                template_name='emails/order_placed.html',
                context={
                    'order': order,
                    'user': request.user,
                    'download_url': download_url,
                },
                attachments=attachments,
            )

            request.session[email_session_key] = True

        except Exception as e:
            print(f"Error in sending order confirmation: {e}")

    return render(
        request,
        'order_success.html',
        {
            'order': order,
            'payment_method': payment_method
        }
    )

@login_required
def download_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.user != request.user:
        messages.error(request, "Unauthorized access.")
        return redirect('index')

    pdf_bytes = generate_pdf_bytes('emails/invoice_pdf.html', {'order': order})

    if not pdf_bytes:
        raise Http404("Invoice generation failed.")

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice_{order.id}.pdf"'
    return response

def wishlist(request):
    wishlist = request.session.get('wishlist',[])

    wishlist = [str(product_id) for product_id in wishlist]

    products = Product.objects.filter(id__in=wishlist)

    return render(request,'wishlist.html',{'products' : products})

def add_wishlist(request,product_id):
    product = get_object_or_404(Product,id=product_id)
    wishlist = request.session.get('wishlist',[])

    wishlist = [str(item) for item in wishlist]
    product_id = str(product_id)

    if product_id not in wishlist:
        wishlist.append(product_id)
        request.session['wishlist'] = wishlist
        request.session.modified = True

        messages.success(request,f'{product.name} added to your wishlist')
    else:
        messages.info(request,f'{product.name} is already in your wishlist')

    return redirect(request.META.get('HTTP_REFERER','wishlist'))

def remove_wishlist(request,product_id):
    wishlist = request.session.get('wishlist',[])
    wishlist = [str(item) for item in wishlist]

    product_id = str(product_id)

    if product_id in wishlist:
        wishlist.remove(product_id)

        request.session['wishlist'] = wishlist
        request.session.modified = True

        messages.success(request,'Product removed from wishlist')
    return redirect('wishlist')
def wishlist_add_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    cart = request.session.get('cart', {})
    product_id = str(product_id)

    if product_id in cart:
        cart[product_id] += 1
    else:
        cart[product_id] = 1

    request.session['cart'] = cart
    request.session.modified = True

    messages.success(request, f'{product.name} added to cart')

    return redirect('wishlist')

def track_order(request, order_id=None):
    order = None
    query_order_id = order_id or request.GET.get('order_id')
    query_email = request.GET.get('email')

    if query_order_id:
        query_order_id = str(query_order_id).strip()
        
        try:
            if request.user.is_authenticated:
                order = Order.objects.get(id=query_order_id, user=request.user)

            
            else:
                if query_email:
                    order = Order.objects.get(
                        id=query_order_id,
                        email__iexact=query_email.strip()
                    )
                else:
                    messages.error(request, "Please enter both Order ID and Billing Email to track your order.")
                    
        except Order.DoesNotExist:
            messages.error(request, f"No order found with ID #{query_order_id} matching your details.")

    
    steps = ['Confirmed', 'Processing', 'Shipped', 'Out for Delivery', 'Delivered']
    
    current_status = getattr(order, 'order_status', 'Confirmed') if order else 'Confirmed'

    current_step_index = 0
    if order and current_status in steps:
        current_step_index = steps.index(current_status)
    elif order and current_status == 'Cancelled':
        current_step_index = -1

    return render(request, 'track_order.html', {
        'order': order,
        'current_status': current_status,
        'steps': steps,
        'current_step_index': current_step_index,
        'query_order_id': query_order_id,
        'query_email': query_email,
    })
# Create your views here.

def index(request):
    testimonials = Testimonial.objects.filter(
        page__in=['home', 'all'], 
        is_active=True
    ).order_by('?')[:3]

    recent_blogs = Blog.objects.all().order_by('-created_at')[:3]

    return render(
        request, 
        'index.html', 
        {
            'testimonials': testimonials,
            'recent_blogs': recent_blogs,
        }
    )
def about(request):
    return render(request,'about.html')
@login_required
def myorder(request):
    orders = Order.objects.filter(user=request.user).order_by('-id')
    return render(request, 'myorder.html', {'orders': orders})

def services(request):
    testimonials = Testimonial.objects.filter(page__in=['services'], is_active=True).order_by('?')[:3]
    return render(request, 'services.html', {'testimonials': testimonials})


def thankyou(request):
    return render(request,'thankyou.html')
import json
import re
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Order, Coupon, Category

MAIN_MENU_OPTIONS = [
    {"label": "🛍️ Shop by Category", "value": "shop_category"},
    {"label": "📦 Track My Order", "url": "/track_order/"},
    {"label": "🎁 Offers & Coupons", "value": "offers_coupons"},
    {"label": "🚚 Shipping Info", "value": "shipping_info"},
    {"label": "🔄 Returns & Refunds", "value": "returns_refunds"},
    {"label": "💬 Chat Freely", "value": "chat_freely"}
]

@csrf_exempt
def chatbot_response(request):
    if request.method != "POST":
        return JsonResponse({"reply": "Invalid request method."}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        raw_msg = data.get("message", "").strip()
        msg = raw_msg.lower()
    except Exception as e:
        print(f"Chatbot payload error: {e}")
        return JsonResponse({"reply": "Invalid request payload."}, status=400)

    if not msg:
        return JsonResponse({'reply': "Please type a message!", 'options': MAIN_MENU_OPTIONS})

    try:
        if msg in ["main_menu", "hi", "hello", "hey", "reset", "menu", "🏠 main menu", "restart chat", "namaste"]:
            reply = "Hi! 👋 I'm <strong>ShopBot</strong> — your personal Furni assistant. How can I help you today?"
            return JsonResponse({"reply": reply, "options": MAIN_MENU_OPTIONS})

        if msg in ["chat_freely", "chat freely", "💬 chat freely"]:
            reply = (
                "💬 <strong>Chat Freely:</strong><br>"
                "Feel free to ask any question regarding our products, styles, materials, payments, or delivery!<br><br>"
            )
            options = [
                {"label": "🛍️ Shop by Category", "value": "shop_category"},
                {"label": "📞 Helpline", "value": "helpline"},
                {"label": "🏠 Main Menu", "value": "main_menu"}
            ]
            return JsonResponse({"reply": reply, "options": options})

        contact_words = ['phone', 'call', 'helpline', 'contact', 'number', 'mobile', 'support', 'help', 'email', 'address']
        if any(w in msg for w in contact_words):
            reply = (
                "📞 <strong>Furni Customer Helpline & Support:</strong><br><br>"
                "• <strong>Phone / Call:</strong> <a href='tel:+919876543210' style='color:#3b5d50; font-weight:bold;'>+91 98765 43210</a><br>"
                "• <strong>Email:</strong> <a href='mailto:support@furni.com' style='color:#3b5d50;'>support@furni.com</a><br>"
                "• <strong>Studio Address:</strong> 104, Furni Studio, Near S.G. Highway, Ahmedabad, Gujarat - 380054<br><br>"
                "Available Monday to Saturday, 9:00 AM to 7:00 PM."
            )
            options = [
                {"label": "🛍️ Shop by Category", "value": "shop_category"},
                {"label": "🏠 Main Menu", "value": "main_menu"}
            ]
            return JsonResponse({"reply": reply, "options": options})

        furniture_words = ['sofa', 'chair', 'table', 'bed', 'desk', 'decor', 'furniture', 'catalog', 'collection', 'shop_category', 'category', 'categories', '🛍️ shop by category']
        if any(w in msg for w in furniture_words):
            if 'sofa' in msg:
                reply = "🛋️ Explore our luxury 2-seater, 3-seater, and sectional fabric sofa sets:"
            elif 'chair' in msg:
                reply = "🪑 Check out our handcrafted ergonomic chairs, study chairs, and modern lounge seating:"
            elif 'bed' in msg:
                reply = "🛏️ Discover our premium solid-wood double beds and minimalist bedroom frames:"
            else:
                reply = "✨ Explore our furniture categories below or view our complete catalog:"

            options = []
            try:
                categories = Category.objects.all()[:4]
                for cat in categories:
                    options.append({
                        "label": f"🪑 {cat.name}",
                        "url": f"/category/?category_id={cat.id}"
                    })
            except Exception:
                pass

            options.append({"label": "🛍️ View Full Catalog", "url": "/category/"})
            options.append({"label": "🏠 Main Menu", "value": "main_menu"})
            return JsonResponse({"reply": reply, "options": options})

        coupon_words = ['coupon', 'coupons', 'offer', 'offers', 'discount', 'code', 'promo', 'offers_coupons', '🎁 offers & coupons']
        if any(w in msg for w in coupon_words):
            active_coupons = Coupon.objects.filter(active=True).order_by('-id')
            if active_coupons.exists():
                reply = "🎉 <strong>Active Store Offers & Coupons:</strong><br><br>"
                for coupon in active_coupons:
                    if getattr(coupon, 'discount_type', None) == 'Flat':
                        val = getattr(coupon, 'discount_value', 0)
                        discount_str = f"₹{int(val)} FLAT OFF"
                    elif hasattr(coupon, 'discount_value'):
                        discount_str = f"{int(coupon.discount_value)}% OFF"
                    else:
                        discount_str = f"{coupon.discount}% OFF"

                    min_str = ""
                    if coupon.min_amount and float(coupon.min_amount) > 0:
                        min_str = f" (on orders above ₹{int(coupon.min_amount)})"

                    reply += f"• Code <strong>{coupon.code}</strong>: Get {discount_str}{min_str}<br>"
                reply += "<br><em>Apply these codes on the cart or checkout page!</em>"
            else:
                reply = "Currently there are no active coupon codes. Use code <strong>WELCOME10</strong> on your first order!"

            options = [
                {"label": "🛍️ Shop Now", "url": "/category/"},
                {"label": "🏠 Main Menu", "value": "main_menu"}
            ]
            return JsonResponse({"reply": reply, "options": options})

        if any(w in msg for w in ['shipping_info', 'shipping info', 'delivery', 'shipping', '🚚 shipping info']):
            reply = (
                "🚚 <strong>Shipping Policy:</strong><br>"
                "Standard furniture delivery takes between <strong>3 to 7 business days</strong> with free doorstep delivery across India.<br>"
                "You can track live shipment progress anytime on our tracking page."
            )
            options = [
                {"label": "📦 Track My Order", "url": "/track_order/"},
                {"label": "🛍️ Shop by Category", "value": "shop_category"},
                {"label": "🏠 Main Menu", "value": "main_menu"}
            ]
            return JsonResponse({"reply": reply, "options": options})

        if any(w in msg for w in ['returns_refunds', 'returns & refunds', 'return', 'refund', 'replacement', '🔄 returns & refunds']):
            reply = (
                "🔄 <strong>Easy Return Policy:</strong><br>"
                "We offer a <strong>7-day hassle-free replacement warranty</strong> for items damaged during transit or with manufacturing defects."
            )
            options = [
                {"label": "📞 Helpline", "value": "helpline"},
                {"label": "💬 Chat Freely", "value": "chat_freely"},
                {"label": "🏠 Main Menu", "value": "main_menu"}
            ]
            return JsonResponse({"reply": reply, "options": options})

        order_match = re.search(r'\b\d+\b', msg)
        if order_match and not any(k in msg for k in ["above", "rs", "off", "coupon", "discount"]):
            order_id = order_match.group(0)
            try:
                order = Order.objects.get(id=order_id)
                status = getattr(order, 'order_status', 'Confirmed')
                cust_name = getattr(order, 'name', None) or getattr(order, 'full_name', None) or "Valued Customer"
                if callable(cust_name):
                    cust_name = cust_name()

                reply = (
                    f"📦 <strong>Order #{order.id}</strong><br>"
                    f"Status: <strong style='color:#3b5d50;'>{status}</strong><br>"
                    f"Customer: {cust_name}<br>"
                    f"Total: ₹{order.total}<br><br>"
                    f"<a href='/track_order/?order_id={order.id}&email={order.email}' "
                   
                )
                options = [
                    {"label": "📦 Track Order Page", "url": "/track_order/"},
                    {"label": "🛍️ Shop by Category", "value": "shop_category"},
                    {"label": "🏠 Main Menu", "value": "main_menu"}
                ]
                return JsonResponse({"reply": reply, "options": options})
            except Order.DoesNotExist:
                reply = f"❌ No order found matching Order ID <strong>#{order_id}</strong>. You can search directly on our tracking page:"
                options = [
                    {"label": "📦 Go to Track Order Page", "url": "/track_order/"},
                    {"label": "🏠 Main Menu", "value": "main_menu"}
                ]
                return JsonResponse({"reply": reply, "options": options})

        reply = (
            "I didn't quite catch that. You can type:<br>"
            "• <strong>'sofa'</strong> or <strong>'chair'</strong> to browse items<br>"
            "• <strong>'phone'</strong> or <strong>'helpline'</strong> for support<br>"
            "• <strong>'coupon'</strong> to view active discounts<br>"
            "• Your <strong>Order ID</strong> (e.g. <code>#19</code>)<br><br>"
            "Or select an option below:"
        )
        return JsonResponse({"reply": reply, "options": MAIN_MENU_OPTIONS})

    except Exception as e:
        print(f"Chatbot server error: {e}")
        return JsonResponse({"reply": "An error occurred while processing your request.", "options": MAIN_MENU_OPTIONS}, status=500)

def apply_coupon(request):
    if request.method == "POST":
        code = request.POST.get('coupon_code', '').strip()
        cart = request.session.get('cart', {})

        # ૧. કાર્ટ ટોટલ ગણતરી
        cart_total = 0.0
        for product_id, quantity in cart.items():
            try:
                prod = Product.objects.get(id=product_id)
                cart_total += float(prod.price) * int(quantity)
            except Product.DoesNotExist:
                continue

        if cart_total <= 0:
            messages.error(request, "Your cart is empty.")
            return redirect('cart')

        try:
            coupon = Coupon.objects.get(code__iexact=code, active=True)

            if coupon.code.upper() == 'WELCOME10':
                if not request.user.is_authenticated:
                    messages.error(request, "Please log in to apply the WELCOME10 coupon.")
                    return redirect('cart')

                already_used = CouponUsage.objects.filter(user=request.user, coupon=coupon).exists()
                if already_used:
                    messages.error(request, "The WELCOME10 coupon is only valid once per user.")
                    return redirect('cart')

                has_previous_orders = Order.objects.filter(
                    user=request.user
                ).exclude(order_status='Cancelled').exists()
                
                if has_previous_orders:
                    messages.error(request, "The WELCOME10 coupon is only applicable on your first order.")
                    return redirect('cart')
            min_required = float(getattr(coupon, 'min_amount', 0) or 0)
            if cart_total < min_required:
                messages.error(
                    request, 
                    f"Coupon '{coupon.code}' is applicable only on orders above ₹{min_required:.0f}."
                )
                return redirect('cart')

            discount_amount = 0.0
            discount_type = getattr(coupon, 'discount_type', 'Percentage')
            val = float(getattr(coupon, 'discount_value', getattr(coupon, 'discount', 0)))

            if discount_type == 'Percentage':
                discount_amount = (cart_total * val) / 100.0
                max_discount = getattr(coupon, 'max_discount', None)
                if max_discount and discount_amount > float(max_discount):
                    discount_amount = float(max_discount)
            else:
                discount_amount = val

            discount_amount = min(discount_amount, cart_total)

            request.session['coupon_code'] = coupon.code
            request.session['discount_amount'] = discount_amount
            request.session['cart_subtotal'] = cart_total

            messages.success(request, f"Coupon '{coupon.code}' applied successfully! Saved ₹{discount_amount:.2f}")

        except Coupon.DoesNotExist:
            messages.error(request, "Invalid or expired coupon code.")

    return redirect('cart')
def remove_coupon(request):
    for key in ['coupon_id', 'coupon_code', 'coupon_discount_type', 'coupon_discount_value', 'discount_amount']:
        if key in request.session:
            del request.session[key]
    messages.info(request, "Coupon removed successfully.")
    return redirect('cart')

def subscribe_newsletter(request):
    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()

        if name and email:
            subscriber, created = NewsletterSubscriber.objects.get_or_create(
                email=email,
                defaults={'name': name}
            )

            if created:
                subject = "Welcome to Furni! 🛋️ Here is your Welcome Gift"
                html_content = render_to_string('emails/welcome_email.html', {
                    'name': name,
                    'site_url': 'http://127.0.0.1:8000',
                })
                text_content = strip_tags(html_content)

                # ૨. ઈમેઈલ સેન્ડ કરો
                try:
                    msg = EmailMultiAlternatives(
                        subject,
                        text_content,
                        settings.DEFAULT_FROM_EMAIL,
                        [email]
                    )
                    msg.attach_alternative(html_content, "text/html")
                    msg.send(fail_silently=True)
                except Exception as e:
                    print(f"Email sending failed: {e}")

                messages.success(request, "Subscribed successfully! Check your inbox for a special welcome offer.")
            else:
                messages.info(request, "You are already subscribed with this email.")
        else:
            messages.error(request, "Please enter both your name and email.")

    return redirect(request.META.get('HTTP_REFERER', 'index'))

    