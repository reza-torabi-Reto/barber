import os
from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from .models import Shop


@receiver(pre_save, sender=Shop)
def delete_old_logo_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        old_shop = Shop.objects.get(pk=instance.pk)
    except Shop.DoesNotExist:
        return

    old_logo = old_shop.logo
    new_logo = instance.logo

    if old_logo and old_logo != new_logo:
        if os.path.isfile(old_logo.path):
            os.remove(old_logo.path)


@receiver(pre_save, sender=Shop)
def delete_old_image_shop_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        old_shop = Shop.objects.get(pk=instance.pk)
    except Shop.DoesNotExist:
        return

    old_image = old_shop.image_shop
    new_image = instance.image_shop

    if old_image and old_image != new_image:
        if os.path.isfile(old_image.path):
            os.remove(old_image.path)
