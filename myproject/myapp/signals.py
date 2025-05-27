from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Purchase, Notification
from django.dispatch import receiver
from django.db.models.signals import post_save

@receiver(post_save, sender=Purchase)
def notify_order_status(sender, instance, created, **kwargs):
    if not created and instance.status == 'preparing':
        Notification.objects.create(
            user=instance.user,
            message=f"คำสั่งซื้อ #{instance.id} ของคุณกำลังจัดเตรียม",
        )