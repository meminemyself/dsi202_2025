from django.contrib import admin
from .models import Tree, Equipment, PlantingLocation, UserPlanting, Notification, Purchase, NewsArticle


@admin.register(Tree)
class TreeAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'is_recommended', 'average_rating', 'review_count']
    search_fields = ['name']


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'description']
    search_fields = ['name']
    list_filter = ['price']
    fields = ['name', 'price', 'image_url', 'description']


@admin.register(PlantingLocation)
class PlantingLocationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'location_type')
    search_fields = ('name', 'location_type')
    list_filter = ('location_type',)


@admin.register(UserPlanting)
class UserPlantingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'tree', 'location', 'planting_date', 'is_completed')
    search_fields = ('user__username', 'tree__name', 'location__name')
    list_filter = ('is_completed', 'planting_date')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'message', 'notification_date', 'is_read')
    search_fields = ('user__username', 'message')
    list_filter = ('is_read',)

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'equipment', 'quantity', 'name', 'tel', 'display_status',
        'tracking_number', 'created_at', 'payment_slip'
    )
    list_filter = ('status', 'created_at')
    readonly_fields = ('created_at',)
    fields = (
        'user', 'equipment', 'quantity',
        'name', 'tel', 'address',  # เพิ่มฟิลด์ข้อมูลลูกค้า
        'status', 'payment_slip', 'tracking_number', 'created_at'
    )

    def display_status(self, obj):
        return dict(Purchase._meta.get_field('status').choices).get(obj.status)
    display_status.short_description = 'สถานะ'


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at')
    search_fields = ('title',)
    list_filter = ('created_at',)