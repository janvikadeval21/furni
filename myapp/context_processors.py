
from .models import Coupon

def coupon_context(request):
    return {
        'db_active_coupons': Coupon.objects.filter(active=True).order_by('-id')
    }