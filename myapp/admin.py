from django.contrib import admin
from myapp.models import * 
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives

# Register your models here.

@admin.register(ContactMessage)
class contactadmin(admin.ModelAdmin):
    list_display = ['first_name','last_name','email','phone','subject','message']

@admin.register(Category)
class categoryadmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(Product)
class Productadmin(admin.ModelAdmin):
    list_display = ['name','price','description','stock']

@admin.register(Testimonial)
class Testimonialadmin(admin.ModelAdmin):
    list_display = ['name','rating','content']

class BlogImageInline(admin.TabularInline):
    model = BlogImage
    extra = 3

@admin.register(Blog)
class Blogadmin(admin.ModelAdmin):
    list_display = ['id','title','author']
    inlines = [
        BlogImageInline,
    ]

# @admin.register(Order)
# class Orderadmin(admin.ModelAdmin):
#     list_display = ['id',
#         'user',
#         'full_name',
#         'total',
#         'payment_method',
#         'payment_status',
#         'order_status',
#         'created_at',
#     ]

@admin.register(OrderItem)
class Orderitemadmin(admin.ModelAdmin):
    list_display = [ 'id',
        'order',
        'product',
        'quantity',
        'price',
        'total',]
@admin.register(NewsletterSubscriber)
class Newadmin(admin.ModelAdmin):
    list_display = ('id','name','email')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'order_status', 'total', 'created_at')
    list_filter = ('order_status',)
    search_fields = ('id', 'email')

    def save_model(self, request, obj, form, change):
        if change and 'order_status' in form.changed_data:
            target_statuses = ['Out for Delivery', 'Delivered', 'Cancelled']
            
            if obj.order_status in target_statuses:
                self.send_order_notification_email(obj)

        super().save_model(request, obj, form, change)

    def send_order_notification_email(self, order):
        if order.order_status == 'Out for Delivery':
            headline = "Your package is out for delivery! 🚚"
            message_body = "Our delivery partner is on the way with your furniture today."
            color = "#f39c12"
        elif order.order_status == 'Delivered':
            headline = "Your order has been delivered! 🎉"
            message_body = "Your package has been successfully delivered. Thank you for choosing Furni!"
            color = "#27ae60"
        elif order.order_status == 'Cancelled':
            headline = "Your order has been cancelled ❌"
            message_body = "Your order has been cancelled. Please contact us if you need further details."
            color = "#c0392b"
        else:
            return

        subject = f"Order #{order.id} Status Update: {order.order_status}"

        customer_name = ""
        if hasattr(order, 'full_name'):
            val = getattr(order, 'full_name')
            customer_name = val() if callable(val) else str(val)
        elif hasattr(order, 'first_name') and order.first_name:
            customer_name = f"{order.first_name} {getattr(order, 'last_name', '')}".strip()
        elif hasattr(order, 'name') and order.name:
            customer_name = str(order.name)

        if not customer_name:
            str_repr = str(order)
            if " - " in str_repr:
                customer_name = str_repr.split(" - ")[-1].strip()
            else:
                customer_name = "Valued Customer"

        html_message = render_to_string('emails/order_status_email.html', {
            'order': order,
            'customer_name': customer_name,
            'headline': headline,
            'message_body': message_body,
            'status_color': color,
        })
        plain_message = strip_tags(html_message)

        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[order.email],
                html_message=html_message,
                fail_silently=False,
            )
            print(f"SUCCESS: Email sent to {order.email} for Order #{order.id}")
        except Exception as e:
            print(f"EMAIL ERROR: {e}")

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'min_amount', 'active')
    list_filter = ('active', 'discount_type')
    search_fields = ('code',)

    def save_model(self, request, obj, form, change):
        send_email_notification = False

        if not change:
            if obj.active:
                send_email_notification = True
        else:
            old_instance = Coupon.objects.get(pk=obj.pk)
            if not old_instance.active and obj.active:
                send_email_notification = True

        super().save_model(request, obj, form, change)

        if send_email_notification:
            subscribers = NewsletterSubscriber.objects.all()
            for sub in subscribers:
                subject = f"Offer Activated: Use code {obj.code} on Furni! 🎉"
                html_content = render_to_string('emails/coupon_alert_email.html', {
                    'name': sub.name,
                    'coupon': obj,
                    'site_url': 'http://127.0.0.1:8000',
                })
                text_content = strip_tags(html_content)

                try:
                    msg = EmailMultiAlternatives(
                        subject,
                        text_content,
                        settings.DEFAULT_FROM_EMAIL,
                        [sub.email]
                    )
                    msg.attach_alternative(html_content, "text/html")
                    msg.send(fail_silently=True)
                except Exception as e:
                    print(f"Failed sending to {sub.email}: {e}")

@admin.register(CouponUsage)
class Couponusageadmin(admin.ModelAdmin):
    list_display = ['id','user','coupon']

