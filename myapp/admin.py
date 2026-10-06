from django.contrib import admin
from myapp.models import * 
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


from django.contrib import admin
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import Order

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'email', 'order_status', 'total', 'created_at')
    list_filter = ('order_status',)
    search_fields = ('id', 'name', 'email')

    def save_model(self, request, obj, form, change):
        # ૧. જો જૂનો ઓર્ડર એડિટ થતો હોય અને order_status બદલાયું હોય
        if change and 'order_status' in form.changed_data:
            target_statuses = ['Out for Delivery', 'Delivered', 'Cancelled']
            
            # જો નવું સ્ટેટસ આ ત્રણમાંથી કોઈ એક હોય
            if obj.order_status in target_statuses:
                self.send_order_notification_email(obj)

        # મોડેલ સેવ કરો
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

        # HTML Email ટેમ્પલેટ
        html_message = render_to_string('emails/order_status_email.html', {
            'order': order,
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
                recipient_list=[order.email], # ગ્રાહકે આપેલો ઈમેઈલ
                html_message=html_message,
                fail_silently=False,
            )
            print(f"SUCCESS: Email sent to {order.email} for Order #{order.id}")
        except Exception as e:
            print(f"EMAIL ERROR: {e}")