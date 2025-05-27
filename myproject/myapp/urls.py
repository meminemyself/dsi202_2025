from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views

from . import views
from myapp.views import select_address_multi, confirm_cart_order, create_order_multi

urlpatterns = [
    # หน้าเว็บไซต์หลัก
    path('', views.home, name='home'),
    path('trees/', views.tree_list, name='tree_list'),
    path('trees/<int:tree_id>/', views.tree_detail, name='tree_detail'),
    path('equipment/', views.equipment_list, name='equipment_list'),
    path('equipment/<int:equipment_id>/', views.equipment_detail, name='equipment_detail'),

    # การซื้อและปลูกต้นไม้
    path('purchase/<int:equipment_id>/', views.purchase_equipment, name='purchase_equipment'),
    path('plant/<int:tree_id>/', views.plant_tree, name='plant_tree'),
    path('plant/<int:tree_id>/<int:location_id>/', views.plant_tree, name='plant_tree_with_location'),
    path('plant-tree/<int:tree_id>/<int:location_id>/', views.plant_tree_at_location, name='plant_tree_at_location'),
    path('confirm-location/<int:tree_id>/<int:location_id>/', views.confirm_location, name='confirm_location'),
    path('select-location/<int:tree_id>/', views.select_location_for_tree, name='select_location_for_tree'),
    path('payment/success/<int:tree_id>/', views.payment_success, name='payment_success'),

    # ต้นไม้ของฉัน
    path('my-trees/', views.my_trees, name='my_trees'),

    # โปรไฟล์
    path('profile/', views.user_profile, name='user_profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),

    # ข่าว / ค้นหา / ข้อมูล
    path('news/', views.news_list, name='news_list'),
    path('news/<int:article_id>/', views.news_detail, name='news_detail'),
    path('search/', views.search_results, name='search_results'),
    path('notifications/', views.notification_list, name='notification_list'),
    path('community/', views.community, name='community'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),

    # ตะกร้าและการชำระเงินรวม
    path('cart/', views.cart_view, name='cart'),
    path('cart/update/<str:item_type>/<int:item_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<str:item_type>/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/process/', views.process_cart_items, name='process_cart_items'),
    path('add-to-cart/<str:item_type>/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('confirm-cart/', confirm_cart_order, name='confirm_cart_order'),

    # ชำระเงินรวม
    path('payment-multi/', views.payment_multi, name='payment_multi'),
    path('go-to-payment/', views.proceed_to_payment_multi, name='proceed_to_payment_multi'),
    path('select-address-multi/', select_address_multi, name='select_address_multi'),
    path('create-order-multi/', create_order_multi, name='create_order_multi'),

    # การสั่งซื้ออุปกรณ์แยก
    path('equipment/select-address/<int:equipment_id>/', views.select_address, name='select_address'),
    path('equipment/payment/<int:equipment_id>/', views.equipment_payment, name='equipment_payment'),
    path('equipment/create-order/<int:equipment_id>/', views.create_pending_order, name='create_pending_order'),
    path('equipment/confirm-order/', views.confirm_equipment_order, name='confirm_equipment_order'),

    # คำสั่งซื้อของฉัน
    path('my-orders/', views.my_orders, name='my_orders'),
    path('my-orders/upload-slip/<int:order_id>/', views.upload_slip, name='upload_slip'),
    path('orders/upload-slip/<int:purchase_id>/', views.upload_slip, name='upload_slip'),
    path('cancel-order/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('auto-cancel/<int:order_id>/', views.auto_cancel_order, name='auto_cancel_order'),
    path('delete-slip/<int:purchase_id>/', views.delete_slip, name='delete_slip'),

    # ชำระเงินต้นไม้แบบเดี่ยว
    path('confirm-tree-payment/<int:tree_id>/', views.confirm_tree_payment, name='confirm_tree_payment'),

    # แผนการปลูกต้นไม้
    path('planting-plan/', views.planting_plan, name='planting_plan'),

    # ระบบบัญชี
    path('login/', auth_views.LoginView.as_view(template_name='myapp/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('signup/', views.signup, name='signup'),

    # Social login และ Django Admin
    path('accounts/', include('allauth.urls')),
    path('admin/', admin.site.urls),
]

# รองรับ static media
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)