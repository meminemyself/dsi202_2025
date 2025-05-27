from django.contrib import admin
from django.apps import apps
from .models import (
    Tree, Equipment, PlantingLocation, Notification, Purchase,
    NewsArticle, UserPlanting, PurchaseItem
)
from .views import send_notification
# Tree
@admin.register(Tree)
class TreeAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'is_recommended', 'average_rating', 'review_count']
    search_fields = ['name']

# Equipment
@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'description']
    search_fields = ['name']
    list_filter = ['price']
    fields = ['name', 'price', 'image_url', 'description']

# PlantingLocation
@admin.register(PlantingLocation)
class PlantingLocationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'location_type')
    search_fields = ('name', 'location_type')
    list_filter = ('location_type',)

from django.contrib import admin
from .models import UserPlanting

@admin.register(UserPlanting)
class UserPlantingAdmin(admin.ModelAdmin):
    list_display = ('user', 'tree', 'location', 'status', 'planting_date')
    list_filter = ('status', 'location')
    readonly_fields = ('planting_date',)

    def save_model(self, request, obj, form, change):
        # ถ้ามีการเปลี่ยน status
        if change and 'status' in form.changed_data:
            tree_name = obj.tree.name
            new_status = obj.get_status_display()
            send_notification(obj.user, f"ต้นไม้ {tree_name} ของคุณมีการอัปเดตสถานะใหม่: {new_status}")
        super().save_model(request, obj, form, change)
# Notification
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'message', 'notification_date', 'is_read')
    search_fields = ('user__username', 'message')
    list_filter = ('is_read',)

# Purchase
@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = (
        'order_number', 'user', 'item_summary', 'name', 'tel',
        'display_status', 'tracking_number', 'created_at', 'payment_slip'
    )
    list_filter = ('status', 'created_at')
    readonly_fields = ('created_at',)
    fields = (
        'user',
        'name', 'tel', 'address',
        'status', 'payment_slip', 'tracking_number', 'created_at'
    )

    def item_summary(self, obj):
        return ", ".join(
            f"{item.equipment.name if item.equipment else item.tree.name} × {item.quantity}"
            for item in obj.items.all()
        )
    item_summary.short_description = "สินค้าในออเดอร์"

    def display_status(self, obj):
        return dict(Purchase._meta.get_field('status').choices).get(obj.status)
    display_status.short_description = 'สถานะ'

from django.contrib import admin
from .models import NewsArticle

from django.contrib import admin
from .models import NewsArticle
from django.utils.html import format_html

@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'thumbnail')
    fields = ('title', 'description', 'image', 'article_url', 'created_at')
    readonly_fields = ('created_at',)

    def thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" style="border-radius: 8px;" />', obj.image.url)
        return "-"
    thumbnail.short_description = "รูปภาพ"