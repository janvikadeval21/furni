from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator

# Create your models here.
class ContactMessage(models.Model):
    first_name = models.CharField(max_length=100,null=True,blank=True)
    last_name = models.CharField(max_length=100,null=True,blank=True)
    email = models.EmailField(max_length=254)
    phone = models.CharField(max_length=100,null=True,blank=True)
    subject = models.CharField(max_length=100,null=True,blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Category(models.Model):
    name = models.CharField(null=True,blank=True,max_length=50)
    image = models.ImageField(upload_to='categories/')

    def __str__(self):
        return f"{self.name}"

class Product(models.Model):
    category = models.ForeignKey(Category,on_delete=models.CASCADE,related_name='products')
    name = models.CharField(max_length=100,null=True,blank=True)
    price =models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/')
    description = models.TextField()
    stock = models.PositiveBigIntegerField(default=0)

    def __str__(self):
        return self.name

class Testimonial(models.Model):
    PAGE_CHOICES = (
        ('all', 'All Pages'),
        ('home', 'Home Page'),
        ('services', 'Services Page'),
        ('blog', 'Blog Page'),
    )

    name = models.CharField(max_length=100) # e.g. Maria Jones
    designation = models.CharField(max_length=150, blank=True, null=True) # e.g. Verified Buyer / Interior Designer
    content = models.TextField() # Review text
    rating = models.PositiveSmallIntegerField(default=5) # 1 to 5 Stars
    page = models.CharField(max_length=20, choices=PAGE_CHOICES, default='all') # કયા પેજ પર બતાવવો છે
    is_active = models.BooleanField(default=True) # વેબસાઇટ પર બતાવવો કે નહિ
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.page}"
    
class Blog(models.Model):
    title = models.CharField(max_length=255,null=True,blank=True)
    content = models.TextField()
    author = models.CharField(max_length=255,default='Admin')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class BlogImage(models.Model):
    blog = models.ForeignKey(Blog,on_delete=models.CASCADE,related_name='images')
    image = models.ImageField(upload_to='blogs/')

    def __str__(self):
        return self.blog.title

class Order(models.Model): 
    PAYMENT_CHOICES = (
        ('cod','Cash on Delivery'),
        ('online', 'Online Payment'),
    )

    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Out for Delivery', 'Out for Delivery'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    )

    user = models.ForeignKey(User,on_delete=models.CASCADE,null=True,blank=True)
    full_name = models.CharField(max_length=150,null=True,blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=150,null=True,blank=True)

    address = models.TextField()
    city = models.CharField(max_length=100,null=True,blank=True)
    state = models.CharField(max_length=100,null=True,blank=True)
    pincode = models.CharField(max_length=100,null=True,blank=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount =models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total =models.DecimalField(max_digits=12, decimal_places=2)

    payment_method = models.CharField(max_length=20,choices=PAYMENT_CHOICES)
    payment_status = models.CharField(max_length=30,default='Pending')
    order_status = models.CharField(max_length=30,choices=STATUS_CHOICES,default='Pending')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.full_name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order,on_delete=models.CASCADE,related_name='items')

    product = models.ForeignKey('Product',on_delete=models.CASCADE)
    quantity = models.PositiveBigIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = (
        ('Percentage', 'Percentage (%)'),
        ('Flat', 'Flat Amount (₹)'),
    )

    code = models.CharField(max_length=50, unique=True, help_text="e.g. FURNI500 or FESTIVE20")
    discount_type = models.CharField(
        max_length=20, 
        choices=DISCOUNT_TYPE_CHOICES, 
        default='Percentage'
    )
    discount_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="If Percentage: enter 10 for 10%. If Flat: enter 500 for ₹500 off.",
        validators=[MinValueValidator(1)]
    )
    min_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Minimum cart total required (e.g. 5000 so coupon only applies above ₹5000)"
    )
    max_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional: Maximum discount cap for Percentage coupons (e.g. max ₹1500 off)"
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.discount_type == 'Percentage':
            return f"{self.code} - {self.discount_value}% OFF (Min Order: ₹{self.min_amount})"
        return f"{self.code} - ₹{self.discount_value} FLAT OFF (Min Order: ₹{self.min_amount})"

    def calculate_discount(self, cart_total):
        cart_total = float(cart_total)
        discount = 0.0

        if self.discount_type == 'Percentage':
            discount = (cart_total * float(self.discount_value)) / 100.0
           
            if self.max_discount and discount > float(self.max_discount):
                discount = float(self.max_discount)
        else:
           
            discount = float(self.discount_value)

     
        return min(discount, cart_total)