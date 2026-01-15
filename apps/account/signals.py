import os
from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import ManagerProfile


@receiver(pre_save, sender=ManagerProfile)
def delete_old_avatar_on_change(sender, instance, **kwargs):
    # فقط در حالت آپدیت (نه ایجاد)
    if not instance.pk:
        return 

    try:
        old_instance = ManagerProfile.objects.get(pk=instance.pk)
    except ManagerProfile.DoesNotExist:
        return

    old_avatar = old_instance.avatar
    new_avatar = instance.avatar

    # اگر عکس قبلی وجود داشت و تغییر کرده بود → حذف کن
    if old_avatar and old_avatar != new_avatar:
        if os.path.isfile(old_avatar.path):
            os.remove(old_avatar.path)
