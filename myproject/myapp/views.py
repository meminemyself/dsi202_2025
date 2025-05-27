from datetime import timedelta
from io import BytesIO
import base64
import qrcode

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.db.models import Q, Count
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_POST

from .models import (
    Tree, Equipment, PlantingLocation, UserPlanting, Notification,
    NewsArticle, Purchase, PurchaseItem, TreePaymentSlip
)
from .utils.promptpay import generate_promptpay_payload
def generate_qr_base64(phone_number: str, amount: float, order_id=None) -> str:
    message = f"โอนเงิน {amount:.2f} บาท ไปยัง {phone_number}"
    if order_id:
        message += f" (Order #{order_id})"

    payload = generate_promptpay_payload(phone_number, amount, message=message)
    qr = qrcode.make(payload)
    buffer = BytesIO()
    qr.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode()

def tree_list(request):
    sort = request.GET.get('sort')
    if sort in ['name', 'price', '-price']:
        trees = Tree.objects.order_by(sort)
    else:
        trees = Tree.objects.all()

    query = request.GET.get('q')
    if query:
        trees = trees.filter(name__icontains=query)

    recommended_trees = Tree.objects.order_by('?')[:3]
    return render(request, 'myapp/tree_list.html', {
        'trees': trees,
        'recommended_trees': recommended_trees,
        'selected_sort': sort,
        'query': query,
    })
  

def tree_detail(request, tree_id):
    tree = get_object_or_404(Tree, id=tree_id)
    tag_list = [t.strip() for t in tree.tags.split(',')] if tree.tags else []

    similar_trees = Tree.objects.filter(tags__icontains=tag_list[0]).exclude(id=tree_id)[:4] if tag_list else []

    return render(request, 'myapp/tree_detail.html', {
        'tree': tree,
        'tag_list': tag_list,
        'similar_trees': similar_trees,
    })

def equipment_list(request):
    equipments = Equipment.objects.all()
    context = {
        'equipment_list': equipments,
        'equipments': equipments[:3],  
    }
    return render(request, 'myapp/equipment_list.html', context)

def equipment_detail(request, equipment_id):
    equipment = get_object_or_404(Equipment, id=equipment_id)
    return render(request, 'myapp/equipment_detail.html', {'equipment': equipment})



@login_required
def purchase_equipment(request, equipment_id):
    equipment = get_object_or_404(Equipment, id=equipment_id)
    quantity = int(request.GET.get('qty', 1))  

    Purchase.objects.create(
        user=request.user,
        equipment=equipment,
        quantity=quantity
    )

    return redirect('my_trees')

# views.py
from django.contrib.auth.decorators import login_required
from .models import Notification

@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-notification_date')
    return render(request, 'myapp/notification_list.html', {'notifications': notifications})
@login_required
def plant_tree(request, tree_id, location_id):
    tree = get_object_or_404(Tree, pk=tree_id)
    location = get_object_or_404(PlantingLocation, pk=location_id)

    existing = UserPlanting.objects.filter(user=request.user, tree=tree, location=location)
    if not existing.exists():
        UserPlanting.objects.create(user=request.user, tree=tree, location=location)

    return redirect('payment', tree_id=tree.id)


@login_required
def plant_tree_at_location(request, tree_id, location_id):
    request.session['tree_location'] = location_id
    return redirect('payment_multi')

@login_required
def proceed_to_payment_multi(request):
    return redirect('payment_multi') 

@login_required
def my_trees(request):
    status = request.GET.get('status', 'all')
    all_trees = UserPlanting.objects.filter(user=request.user).select_related('tree', 'location')


    completed_count = all_trees.filter(status='completed').count()
    in_progress_count = all_trees.filter(status='in_progress').count()
    verifying_count = all_trees.filter(status='verifying').count()
    all_count = all_trees.count()


    if status == 'completed':
        trees = all_trees.filter(status='completed')
    elif status == 'in_progress':
        trees = all_trees.filter(status='in_progress')
    elif status == 'verifying':
        trees = all_trees.filter(status='verifying')
    else:
        trees = all_trees

    return render(request, 'myapp/my_trees.html', {
        'trees': trees,
        'selected_status': status,
        'status_counts': {
            'all': all_count,
            'completed': completed_count,
            'in_progress': in_progress_count,
            'verifying': verifying_count,
        }
    })
@login_required
def user_profile(request):
    return render(request, 'myapp/user_profile.html', {'user': request.user})

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = UserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('user_profile')
    else:
        form = UserChangeForm(instance=request.user)

    return render(request, 'myapp/edit_profile.html', {'form': form})


def news_list(request):
    news = NewsArticle.objects.all().order_by('-created_at')
    return render(request, 'myapp/news_list.html', {'news': news})
    
def search_results(request):
    query = request.GET.get('q')
    trees = Tree.objects.filter(Q(name__icontains=query) | Q(description__icontains=query))
    equipments = Equipment.objects.filter(Q(name__icontains=query))
    news = NewsArticle.objects.filter(Q(title__icontains=query))

    return render(request, 'myapp/search_results.html', {
        'query': query,
        'trees': trees,
        'equipments': equipments,
        'news': news,
    })

def community(request):
    return render(request, 'myapp/community.html')

def about(request):
    return render(request, 'myapp/about.html')

@login_required
def select_location_for_tree(request, tree_id):
    tree = get_object_or_404(Tree, id=tree_id)
    query = request.GET.get('q', '')

    if query:
        locations = PlantingLocation.objects.filter(name__icontains=query)
    else:
        locations = PlantingLocation.objects.all()

    return render(request, 'myapp/select_location_for_tree.html', {
        'tree': tree,
        'locations': locations,
        'query': query
    })

@login_required
def plant_tree(request, tree_id, location_id):
    tree = get_object_or_404(Tree, id=tree_id)
    location = get_object_or_404(PlantingLocation, id=location_id)

    UserPlanting.objects.create(
        user=request.user,
        tree=tree,
        location=location,
        is_completed=True,
    )

    return render(request, 'myapp/plant_success.html', {
        'tree': tree,
        'location': location,
    })

def home(request):
    news_list = NewsArticle.objects.all().order_by('-created_at')[:5]
    featured_tree = Tree.objects.order_by('?').first() 
    return render(request, 'myapp/home.html', {
        'news_list': news_list,
        'featured_tree': featured_tree
    })

def contact(request):
    return render(request, 'myapp/contact.html')

def confirm_location(request, tree_id, location_id):
    tree = get_object_or_404(Tree, id=tree_id)
    location = get_object_or_404(PlantingLocation, id=location_id)
    return render(request, 'myapp/confirm_location.html', {
        'tree': tree,
        'location': location
    })

@login_required
def select_location_for_tree(request, tree_id):
    tree = get_object_or_404(Tree, id=tree_id)
    locations = PlantingLocation.objects.all()
    return render(request, 'myapp/select_location_for_tree.html', {
        'tree': tree,
        'locations': locations
    })

@login_required
def payment(request, tree_id):
    tree = get_object_or_404(Tree, pk=tree_id)

    default_location, created = PlantingLocation.objects.get_or_create(
        name="Unknown Location", 
        defaults={
            "description": "Auto-assigned due to direct payment.",
            "location_type": "unspecified"
        }
    )

    location = default_location 

    existing = UserPlanting.objects.filter(user=request.user, tree=tree)
    if not existing.exists():
        UserPlanting.objects.create(user=request.user, tree=tree, location=location)

    order = Purchase.objects.create(
        user=request.user,
        tree=tree,
        location=location,
        quantity=1,
        total_price=tree.price,
        status='pending'
    )

    return render(request, 'myapp/tree_payment.html', {
        'tree': tree,
        'location': location,
        'order': order,
    })
def payment_success(request, tree_id):
    return render(request, 'myapp/payment_success.html', {'tree_id': tree_id})

@login_required
def select_address(request, equipment_id):
    equipment = get_object_or_404(Equipment, pk=equipment_id)
    qty = request.GET.get("qty", 1)
    return render(request, 'myapp/select_address.html', {'equipment': equipment, 'qty': qty})


@login_required
def equipment_payment(request, equipment_id):
    equipment = get_object_or_404(Equipment, pk=equipment_id)
    qty = int(request.GET.get("qty", 1))
    address = request.GET.get("address", "") 


    return render(request, 'myapp/equipment_payment.html', {
        'equipment': equipment,
        'qty': qty,
        'address': address,
        'total': equipment.price * qty
    })

from io import BytesIO
def generate_qr_base64(total):
    qr = qrcode.make(f"โอนเงิน {total:.2f} บาท ไปยังบัญชี xxx-xxx")
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return qr_base64



@login_required
def my_orders(request):
    user = request.user
    selected_status = request.GET.get('status', 'all')

    purchases = Purchase.objects.filter(user=user)
    if selected_status != 'all':
        purchases = purchases.filter(status=selected_status)

    counts = {
        'all': Purchase.objects.filter(user=user).count(),
        'pending': Purchase.objects.filter(user=user, status='pending').count(),
        'verifying': Purchase.objects.filter(user=user, status='verifying').count(),
        'preparing': Purchase.objects.filter(user=user, status='preparing').count(),
        'shipping': Purchase.objects.filter(user=user, status='shipping').count(),
        'delivered': Purchase.objects.filter(user=user, status='delivered').count(),
        'cancelled': Purchase.objects.filter(user=user, status='cancelled').count(),
    }

    for order in purchases:
        order.items_list = order.items.filter(equipment__isnull=False)
        first_item = order.items_list.first()
        order.first_image = first_item.equipment.image_url if first_item and first_item.equipment else 'https://via.placeholder.com/80'

    context = {
        "purchases": purchases,
        "selected_status": selected_status,
        "status_counts": counts,
        "status_list": [
            ('all', 'ทั้งหมด', 'status-all'),
            ('verifying', 'กำลังตรวจสอบ', 'status-verifying'),
            ('preparing', 'กำลังเตรียม', 'status-preparing'),
            ('shipping', 'กำลังจัดส่ง', 'status-shipping'),
            ('delivered', 'จัดส่งสำเร็จ', 'status-delivered'),
            ('cancelled', 'ยกเลิกแล้ว', 'status-cancelled'),
        ],
    }

    return render(request, 'myapp/my_orders.html', context)



def search_results(request):
    query = request.GET.get('q')
    tree_results = Tree.objects.filter(Q(name__icontains=query) | Q(description__icontains=query))
    equipment_results = Equipment.objects.filter(Q(name__icontains=query) | Q(description__icontains=query))
    return render(request, 'myapp/search_results.html', {
        'query': query,
        'tree_results': tree_results,
        'equipment_results': equipment_results
    })

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'myapp/signup.html', {'form': form})

def planting_plan(request):
    return render(request, 'myapp/planting_plan.html')

    
def add_to_cart(request, item_type, item_id):
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))


        if item_type == 'tree':
            item = get_object_or_404(Tree, id=item_id)
        elif item_type == 'equipment':
            item = get_object_or_404(Equipment, id=item_id)
        else:
            return redirect('home')

        cart = request.session.get('cart', [])
        item_found = False

        for cart_item in cart:
            if cart_item['id'] == item.id and cart_item['type'] == item_type:
                cart_item['qty'] += quantity
                item_found = True
                break
        if not item_found:
            cart.append({'id': item.id, 'qty': quantity, 'type': item_type})


        request.session['cart'] = cart

        return redirect('cart')
    
def cart_view(request):
    cart = request.session.get('cart', [])
    cart_items_tree = []
    cart_items_equipment = []
    cart_total = 0

    for item in cart:
        item_type = item.get('type')
        item_id = item.get('id')
        quantity = item.get('qty', 1)

        if item_type == 'tree':
            product = get_object_or_404(Tree, id=item_id)
        elif item_type == 'equipment':
            product = get_object_or_404(Equipment, id=item_id)
        else:
            continue

        total_price = product.price * quantity
        item_data = {
            'item': product,
            'type': item_type,
            'quantity': quantity,
            'total_price': total_price
        }

        cart_total += total_price
        if item_type == 'tree':
            cart_items_tree.append(item_data)
        elif item_type == 'equipment':
            cart_items_equipment.append(item_data)

    item_groups = [
        {'group': 'equipment', 'items': cart_items_equipment, 'label': '📦 อุปกรณ์'},
        {'group': 'tree', 'items': cart_items_tree, 'label': '🌳 ต้นไม้ปลูกแทนคุณ'},
    ]

    return render(request, 'myapp/cart.html', {
        'cart_items_equipment': cart_items_equipment,
        'cart_items_tree': cart_items_tree,
        'cart_total': cart_total,
        'item_groups': item_groups,
    })
    

@require_POST
def remove_from_cart(request, item_type, item_id):
    cart = request.session.get('cart', [])
    cart = [item for item in cart if not (item['id'] == item_id and item['type'] == item_type)]
    request.session['cart'] = cart
    return redirect('cart')

@require_POST
def update_cart(request, item_type, item_id):
    cart = request.session.get('cart', [])
    action = request.POST.get('action')

    for item in cart:
        if item['id'] == item_id and item['type'] == item_type:
            if action == 'increase':
                item['qty'] += 1
            elif action == 'decrease':
                item['qty'] -= 1
                if item['qty'] <= 0:
                    cart.remove(item)
            break

    request.session['cart'] = cart
    return redirect('cart')
@login_required
def confirm_cart(request):
    cart = request.session.get('cart', [])
    if not cart:
        messages.error(request, "ไม่มีสินค้าในตะกร้า")
        return redirect('cart')

    items = []
    total = 0
    for c in cart:
        if c['type'] == 'equipment':
            item = get_object_or_404(Equipment, id=c['id'])
        else:
            item = get_object_or_404(Tree, id=c['id'])
        item_total = item.price * c['qty']
        total += item_total
        items.append({
            'item': item,
            'type': c['type'],
            'qty': c['qty'],
            'total': item_total
        })


@login_required
def process_cart_items(request):
    cart = request.session.get('cart', [])

    if not cart:
        messages.error(request, "ยังไม่มีสินค้าในตะกร้า")
        return redirect('cart')

    has_tree = any(item['type'] == 'tree' for item in cart)
    has_equipment = any(item['type'] == 'equipment' for item in cart)

    request.session['checkout_cart'] = cart

    if 'cart' in request.session:
        del request.session['cart']
    request.session.modified = True 

    if has_tree and has_equipment:
        return redirect('select_address_multi')

    elif has_tree:
        try:
            tree_item = next(item for item in cart if item['type'] == 'tree')
            return redirect('select_location_for_tree', tree_id=tree_item['id'])
        except StopIteration:
            messages.error(request, "ไม่พบต้นไม้ในตะกร้า")
            return redirect('cart')

    elif has_equipment:
        return redirect('select_address_multi')

    return redirect('cart')

def start_planting_redirect(request):
    tree_id = request.POST.get('tree_id')
    if tree_id:
        return redirect('select_location_for_tree', tree_id=tree_id)
    return redirect('cart') 

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home') 
    else:
        form = UserCreationForm()
    return render(request, 'myapp/signup.html', {'form': form})

@login_required
def process_cart_items(request):
    if request.method != "POST":
        return redirect('cart')

    selected = request.POST.get("selected_items", "")
    if not selected:
        messages.error(request, "กรุณาเลือกรายการอย่างน้อยหนึ่งรายการ")
        return redirect('cart')

    selected_items = selected.split(",")
    cart = request.session.get("cart", [])

    filtered_cart = [item for item in cart if f"{item['type']}:{item['id']}" in selected_items]

    if not filtered_cart:
        messages.error(request, "ไม่พบรายการที่เลือก")
        return redirect('cart')

    request.session['checkout_cart'] = filtered_cart

    has_tree = any(item['type'] == 'tree' for item in filtered_cart)
    has_equipment = any(item['type'] == 'equipment' for item in filtered_cart)

    if has_tree and has_equipment:
        return redirect('select_address_multi') 

    elif has_tree:
        tree_item = next(item for item in filtered_cart if item['type'] == 'tree')
        return redirect('select_location_for_tree', tree_id=tree_item['id'])

    elif has_equipment:
        return redirect('select_address_multi') 

    return redirect('cart')



@login_required
def select_location_for_tree(request, tree_id):
    tree = get_object_or_404(Tree, id=tree_id)
    query = request.GET.get('q', '')

    if query:
        locations = PlantingLocation.objects.filter(name__icontains=query)
    else:
        locations = PlantingLocation.objects.all()

    return render(request, 'myapp/select_location_for_tree.html', {
        'tree': tree,
        'locations': locations,
        'query': query
    })
    

from myapp.utils.promptpay import generate_qr_base64

@login_required
def equipment_payment(request, equipment_id):
    equipment = get_object_or_404(Equipment, pk=equipment_id)
    qty = int(request.GET.get("qty", 1))
    total = float(equipment.price) * qty

    phone_number = "0612438750"  
    qr_base64 = generate_qr_base64(phone_number, total)

    return render(request, 'myapp/equipment_payment.html', {
    'equipment': equipment,
    'qty': qty,
    'total': total,
    'qr_base64': qr_base64,
    'name': request.GET.get("name", ""),
    'tel': request.GET.get("tel", ""),
    'full_address': f"{request.GET.get('address', '')}, ต.{request.GET.get('subdistrict', '')}, อ.{request.GET.get('district', '')}, จ.{request.GET.get('province', '')} {request.GET.get('zipcode', '')}",
})

@login_required
def confirm_equipment_payment(request, equipment_id):
    if request.method == 'POST':
        equipment = get_object_or_404(Equipment, id=equipment_id)
        slip_file = request.FILES.get('payment_slip')

        if slip_file:
            quantity = int(request.POST.get("qty", 1))
            purchase = Purchase.objects.create(
                user=request.user,
                equipment=equipment,
                quantity=quantity,
                name=request.POST.get('name'),
                tel=request.POST.get('tel'),
                address=request.POST.get('address'),
                payment_slip=slip_file,
                status='pending'
            )
            messages.success(request, "ส่งข้อมูลสำเร็จ กรุณารอการตรวจสอบจากแอดมิน")
            return redirect('my_orders')
        
@login_required
def upload_slip(request, order_id):
    order = get_object_or_404(Purchase, id=order_id, user=request.user)
    if request.method == 'POST' and request.FILES.get('payment_slip'):
        order.payment_slip = request.FILES['payment_slip']
        order.status = 'verifying' 
        order.save()
        return redirect('my_orders')


@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Purchase, id=order_id, user=request.user)
    if order.status == 'verifying':
        order.status = 'cancelled'
        order.save()
        messages.success(request, "คำสั่งซื้อถูกยกเลิกแล้ว")
    else:
        messages.warning(request, "ไม่สามารถยกเลิกคำสั่งซื้อนี้ได้")
    return redirect('my_orders')


def upload_slip(request, order_id):
    order = get_object_or_404(Purchase, id=order_id, user=request.user)
    if request.method == 'POST' and request.FILES.get('payment_slip'):
        order.payment_slip = request.FILES['payment_slip']
        order.status = 'verifying'
        order.save()
        return redirect('my_orders')

@login_required
def admin_payment_verification(request):
    if not request.user.is_staff:
        return redirect('home')
    orders = Purchase.objects.filter(status='pending', payment_slip__isnull=False)
    return render(request, 'myapp/admin_verify_payments.html', {'orders': orders})

@login_required
def verify_payment(request, order_id):
    order = get_object_or_404(Purchase, id=order_id)
    order.status = 'confirmed'
    order.save()
    messages.success(request, 'ยืนยันการชำระเงินเรียบร้อยแล้ว')
    return redirect('admin_payment_verification')

@login_required
def cancel_payment(request, order_id):
    order = get_object_or_404(Purchase, id=order_id)
    order.status = 'expired'
    order.save()
    messages.warning(request, 'ยกเลิกคำสั่งซื้อแล้ว')
    return redirect('admin_payment_verification')

@login_required
def create_pending_order(request, equipment_id):
    if request.method == 'POST':
        equipment = get_object_or_404(Equipment, id=equipment_id)
        qty = int(request.POST.get("qty", 1))

        Purchase.objects.create(
            user=request.user,
            equipment=equipment,
            quantity=qty,
            name=request.POST.get('name'),
            tel=request.POST.get('tel'),
            address=request.POST.get('address'),
            status='pending',
        )

        messages.success(request, "สร้างรายการเรียบร้อยแล้ว คุณสามารถแนบสลิปภายหลังได้ในหน้าคำสั่งซื้อของฉัน")
        return redirect('my_orders')
    return redirect('equipment_payment', equipment_id=equipment_id)

@login_required
def create_pending_order(request, equipment_id):
    if request.method == 'POST':
        equipment = get_object_or_404(Equipment, id=equipment_id)
        qty = int(request.POST.get("qty", 1))
        Purchase.objects.create(
            user=request.user,
            equipment=equipment,
            quantity=qty,
            name=request.POST.get('name'),
            tel=request.POST.get('tel'),
            address=request.POST.get('address'),
            status='pending',
            payment_slip=request.FILES.get('payment_slip')
        )
        messages.success(request, "สร้างรายการเรียบร้อยแล้ว คุณสามารถแนบสลิปภายหลังได้ในหน้าคำสั่งซื้อของฉัน")
        return redirect('my_orders')
    return redirect('payment_multi.html', equipment_id=equipment_id)

@csrf_exempt
def auto_cancel_order(request, order_id):
    if request.method == "POST":
        try:
            order = Purchase.objects.get(id=order_id, status='pending')
            order.status = 'cancelled'
            order.save()
            return JsonResponse({'status': 'cancelled'})
        except Purchase.DoesNotExist:
            return JsonResponse({'status': 'not_found'})
    return JsonResponse({'status': 'invalid'})

@login_required
def delete_slip(request, purchase_id):
    purchase = get_object_or_404(Purchase, id=purchase_id, user=request.user)
    if purchase.payment_slip:
        purchase.payment_slip.delete()
        purchase.payment_slip = None
        purchase.save()
    return redirect('my_orders')

@login_required
def confirm_equipment_order(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        tel = request.POST.get('tel')
        province = request.POST.get('province')
        district = request.POST.get('district')
        subdistrict = request.POST.get('subdistrict')
        zipcode = request.POST.get('zipcode')
        address_detail = request.POST.get('address')
        qty = int(request.POST.get('qty'))

        full_address = f"{address_detail}, ต.{subdistrict}, อ.{district}, จ.{province}, {zipcode}"

        equipment_id = request.POST.get('equipment_id')
        if not equipment_id:
            raise Http404("ไม่พบรหัสสินค้า")

        equipment = get_object_or_404(Equipment, id=equipment_id)

        total = qty * equipment.price

        phone = "0612438750"
        qr_base64 = generate_qr_base64(phone, total)

        return render(request, 'myapp/equipment_payment.html', {
            'equipment': equipment,
            'qty': qty,
            'name': name,
            'tel': tel,
            'full_address': full_address,
            'total': total,
            'qr_base64': qr_base64,
        })

    return redirect('cart')




@login_required
def payment_multi(request):
    cart = request.session.get('checkout_cart', [])
    order_info = request.session.get('order_info', {})
    tree_location_id = request.session.get('tree_location', None)
    
    total = 0
    detailed_items = []

    for item in cart:
        item_type = item.get('type')
        item_id = item.get('id')
        qty = int(item.get('qty', 1))

        if item_type == 'equipment':
            product = get_object_or_404(Equipment, id=item_id)
        elif item_type == 'tree':
            product = get_object_or_404(Tree, id=item_id)
        else:
            continue

        item_total = product.price * qty
        total += item_total

        detailed_items.append({
            'name': product.name,
            'image_url': product.image_url,
            'price': product.price,
            'qty': qty,
            'total': item_total,
            'type': item_type
        })

    qr_base64 = generate_qr_base64("0612438750", total)

    from django.utils import timezone
    now = timezone.now()
    order_id = f"PJ{now.strftime('%Y%m%d%H%M%S')}"
    total_items = sum(item['qty'] for item in detailed_items)

    tree_location = PlantingLocation.objects.filter(id=tree_location_id).first() if tree_location_id else None

    return render(request, 'myapp/payment_multi.html', {
        'items': detailed_items,
        'total': total,
        'qr_base64': qr_base64,
        'order_id': order_id,
        'order_date': now,
        'total_items': total_items,
        'name': order_info.get('name', ''),
        'tel': order_info.get('tel', ''),
        'full_address': order_info.get('address', ''),
        'tree_location': tree_location,
        'has_tree': any(item['type'] == 'tree' for item in detailed_items),
        'has_equipment': any(item['type'] == 'equipment' for item in detailed_items),  # ✅ ใช้ `:` แทน `=`
    })


@login_required
def create_order_multi(request):
    if request.method == 'POST':
        cart = request.session.get('checkout_cart', [])
        if not cart:
            return redirect('cart')

        name = request.POST.get('name', '')
        tel = request.POST.get('tel', '')
        address = request.POST.get('address', '')
        slip = request.FILES.get('payment_slip', None)

        has_tree = False
        has_equipment = False
        purchase = None

        for item in cart:
            if item['type'] == 'equipment':
                if not purchase:
                    purchase = Purchase.objects.create(
                        user=request.user,
                        name=name,
                        tel=tel,
                        address=address,
                        payment_slip=slip,
                        status='pending'
                    )
                product = get_object_or_404(Equipment, id=item['id'])
                PurchaseItem.objects.create(
                    purchase=purchase,
                    equipment=product,
                    quantity=item['qty']
                )
                has_equipment = True

        for item in cart:
            if item['type'] == 'tree':
                product = get_object_or_404(Tree, id=item['id'])
                location_id = request.session.get('tree_location')
                location = get_object_or_404(PlantingLocation, id=location_id) if location_id else None
                UserPlanting.objects.create(
                    user=request.user,
                    tree=product,
                    location=location,
                    status='verifying' 
                )
                send_notification(request.user, f"ต้นไม้ {product.name} ของคุณถูกเพิ่มเรียบร้อยแล้ว รอการดูแลหรือปลูกจริงในเร็ว ๆ นี้")
                has_tree = True

        request.session.pop('checkout_cart', None)
        request.session.pop('tree_location', None)
        request.session.pop('order_info', None)
        request.session.pop('shipping_info', None)

        if has_tree and not has_equipment:
            return redirect('my_trees')
        elif has_equipment:
            return redirect('my_orders')

    return redirect('cart')

@login_required
def select_address_multi(request):
    cart = request.session.get('cart', [])
    if not cart:
        return redirect('cart') 

    if request.method == 'POST':
        request.session['shipping_info'] = {
            'name': request.POST.get('name'),
            'tel': request.POST.get('tel'),
            'province': request.POST.get('province'),
            'district': request.POST.get('district'),
            'subdistrict': request.POST.get('subdistrict'),
            'zipcode': request.POST.get('zipcode'),
            'address': request.POST.get('address'),
        }
        return redirect('confirm_cart_order') 

    return render(request, 'myapp/select_address_multi.html', {
        'cart': cart
    })


@login_required
def confirm_cart_order(request):
    if request.method == 'POST':
        cart = request.session.get('checkout_cart', [])

        name = request.POST.get('name')
        tel = request.POST.get('tel')
        province = request.POST.get('province')
        district = request.POST.get('district')
        subdistrict = request.POST.get('subdistrict')
        zipcode = request.POST.get('zipcode')
        address_detail = request.POST.get('address')

        full_address = f"{address_detail}, ต.{subdistrict}, อ.{district}, จ.{province}, {zipcode}"

        request.session['order_info'] = {
            'name': name,
            'tel': tel,
            'address': full_address,
        }

        tree_item = next((item for item in cart if item['type'] == 'tree'), None)
        if tree_item:
            return redirect('select_location_for_tree', tree_id=tree_item['id'])

        return redirect('payment_multi')

    return redirect('cart')


@login_required
def select_location_for_tree(request, tree_id):
    locations = PlantingLocation.objects.all()
    query = request.GET.get('q')
    if query:
        locations = locations.filter(name__icontains=query)

    if request.method == 'POST':
        selected_location_id = request.POST.get('location_id')
        request.session['tree_location'] = selected_location_id
        return redirect('payment_multi')

    return render(request, 'myapp/select_location_for_tree.html', {
        'tree': get_object_or_404(Tree, id=tree_id),
        'locations': locations,
        'query': query,
    })




def confirm_cart_split(request):
    if request.method == 'POST':
        choice = request.POST.get('choice')
        if choice == 'separate':
            return redirect('separate_order_flow') 
        else:
            return redirect('combine_order_flow')



@login_required
@csrf_protect
def plant_tree_in_province(request):
    if request.method == 'POST':
        province = request.POST.get('province')
        return render(request, 'myapp/confirm_province_plant.html', {'province': province})
    return redirect('select_province_page')

    

@login_required
def confirm_tree_payment(request, tree_id):
    if request.method == 'POST' and request.FILES.get('payment_slip'):
        tree = get_object_or_404(Tree, id=tree_id)
        TreePaymentSlip.objects.create(
            user=request.user,
            tree=tree,
            image=request.FILES['payment_slip']
        )
        return redirect('my_trees')
    return redirect('home')

def home(request):
    return render(request, 'myapp/home.html')



def home(request):

    top_tree = Tree.objects.annotate(order_count=Count('userplanting')).order_by('-order_count').first()

    context = {
        'top_tree': top_tree,
    }

    return render(request, 'myapp/home.html', context)

@receiver(post_save, sender=Purchase)
def send_notification_on_status_change(sender, instance, created, **kwargs):
    if not created:
        status_messages = {
            'verifying': f"คำสั่งซื้อ #{instance.id} กำลังตรวจสอบสลิป",
            'preparing': f"คำสั่งซื้อ #{instance.id} กำลังจัดเตรียมสินค้า",
            'shipping': f"คำสั่งซื้อ #{instance.id} กำลังจัดส่ง",
            'delivered': f"คำสั่งซื้อ #{instance.id} จัดส่งสำเร็จแล้ว",
            'cancelled': f"คำสั่งซื้อ #{instance.id} ถูกยกเลิก",
        }
        msg = status_messages.get(instance.status)
        if msg:
            Notification.objects.create(
                user=instance.user,
                message=msg
            )

def news_detail(request, article_id):
    article = get_object_or_404(NewsArticle, id=article_id)
    return render(request, 'myapp/news_detail.html', {'article': article})

@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-notification_date')
    return render(request, 'myapp/notification_list.html', {
        'notifications': notifications
    })

def send_notification(user, message):
    Notification.objects.create(user=user, message=message)



@receiver(post_save, sender=Purchase)
def send_notification_on_status_change(sender, instance, created, **kwargs):
    if not created:
        status_messages = {
            'verifying': f"คำสั่งซื้อ #{instance.id} กำลังตรวจสอบสลิป",
            'preparing': f"คำสั่งซื้อ #{instance.id} กำลังจัดเตรียมสินค้า",
            'shipping': f"คำสั่งซื้อ #{instance.id} กำลังจัดส่ง",
            'delivered': f"คำสั่งซื้อ #{instance.id} จัดส่งสำเร็จแล้ว",
            'cancelled': f"คำสั่งซื้อ #{instance.id} ถูกยกเลิก",
        }
        msg = status_messages.get(instance.status)
        if msg:
            Notification.objects.create(user=instance.user, message=msg)

def mark_planting_completed(request, planting_id):
    planting = get_object_or_404(UserPlanting, id=planting_id)
    planting.status = 'completed'
    planting.save()
    send_notification(planting.user, f"ต้นไม้ {planting.tree.name} ของคุณปลูกสำเร็จแล้ว 🌳")
    return redirect('some_admin_page')
