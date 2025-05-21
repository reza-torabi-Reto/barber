import random
import string

def generate_referral_code(length=8):
    from .models import Shop
    characters = string.ascii_uppercase + string.digits  # حروف بزرگ و اعداد
    while True:
        code = ''.join(random.choice(characters) for _ in range(length))
        if not Shop.objects.filter(referral_code=code).exists():  # چک کردن تکراری نبودن
            return code
