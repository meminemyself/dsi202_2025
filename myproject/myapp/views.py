from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Tree, Equipment, PlantingLocation, UserPlanting, Notification, NewsArticle , Purchase
from django.db.models import Q
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages
from io import BytesIO
from myapp.utils.promptpay import generate_qr_base64
import qrcode
import base64
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta

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
        'equipments': equipments[:3],  # แนะนำไว้ sidebar
    }
    return render(request, 'myapp/equipment_list.html', context)

def equipment_detail(request, equipment_id):
    equipment = get_object_or_404(Equipment, id=equipment_id)
    return render(request, 'myapp/equipment_detail.html', {'equipment': equipment})



@login_required
def purchase_equipment(request, equipment_id):
    equipment = get_object_or_404(Equipment, id=equipment_id)
    quantity = int(request.GET.get('qty', 1))  # รับค่าจำนวนจาก URL

    Purchase.objects.create(
        user=request.user,
        equipment=equipment,
        quantity=quantity
    )

    return redirect('my_trees')

@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-notification_date')
    return render(request, 'myapp/notification_list.html', {'notifications': notifications})


@login_required
def plant_tree(request, tree_id, location_id):
    tree = get_object_or_404(Tree, pk=tree_id)
    location = get_object_or_404(PlantingLocation, pk=location_id)

    # เช็คว่าปลูกไปแล้วหรือยัง
    existing = UserPlanting.objects.filter(user=request.user, tree=tree, location=location)
    if not existing.exists():
        UserPlanting.objects.create(user=request.user, tree=tree, location=location)

    return redirect('payment', tree_id=tree.id)


@login_required
def plant_tree_at_location(request, tree_id, location_id):
    tree = Tree.objects.get(id=tree_id)
    location = PlantingLocation.objects.get(id=location_id)

    UserPlanting.objects.create(
        user=request.user,
        tree=tree,
        location=location,
        is_completed=True
    )

    return redirect('payment', tree_id=tree.id)

@login_required
def my_trees(request):
    trees = UserPlanting.objects.filter(user=request.user).select_related('tree', 'location')
    return render(request, 'myapp/my_trees.html', {'trees': trees})

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
    news = NewsArticle.objects.all().order_by('-published_date')  # เรียงข่าวใหม่สุดก่อน
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
    locations = PlantingLocation.objects.all()
    return render(request, 'myapp/select_location_for_tree.html', {
        'tree': tree,
        'locations': locations
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
    featured_tree = Tree.objects.order_by('?').first()  # สุ่มต้นไม้ 1 ต้น
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
    } ) 

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
        'query': query,
    })

def payment_success(request, tree_id):
    # ทำอะไรก็ได้ เช่นแสดงผล, ข้อมูลต้นไม้
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
    address = request.GET.get("address", "")  # รับ address มาจาก step ก่อนหน้า

    # คุณอาจบันทึก address หรือแสดงในหน้า payment ก็ได้
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

from datetime import timedelta  # อย่าลืม import นี้ด้วย

@login_required
def my_orders(request):
    user = request.user
    selected_status = request.GET.get('status', 'all')

    purchases = Purchase.objects.filter(user=user)
    if selected_status != 'all':
        purchases = purchases.filter(status=selected_status)

    phone_number = "0612345678"
    now = timezone.now()

    for order in purchases:
        order.items_list = order.items.all()
        order.total_price = sum(item.quantity * item.product.price for item in order.items_list)
        order.first_image = order.items_list.first().product.image.url if order.items_list else 'https://via.placeholder.com/80'

        if order.status == 'pending':
            expired_time = order.created_at + timedelta(minutes=30)
            if now > expired_time:
                order.status = 'cancelled'
                order.save()
                continue
            order.qr_base64 = generate_qr_base64(phone_number, order.total_price)

    context = {
        "purchases": purchases,
        "status_list": [
            ('all', 'ทั้งหมด', ''),
            ('pending', 'รอชำระเงิน', 'status-pending'),
            ('verifying', 'กำลังตรวจสอบ', 'status-verifying'),
            ('preparing', 'กำลังเตรียม', 'status-preparing'),
            ('shipping', 'กำลังจัดส่ง', 'status-shipping'),
            ('delivered', 'จัดส่งสำเร็จ', 'status-delivered'),
            ('cancelled', 'ยกเลิกแล้ว', 'status-cancelled'),
        ],
        "show_tracking_status": ['shipping', 'delivered'],
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

        # ตรวจสอบประเภท
        if item_type == 'tree':
            item = get_object_or_404(Tree, id=item_id)
        elif item_type == 'equipment':
            item = get_object_or_404(Equipment, id=item_id)
        else:
            return redirect('home')

        cart = request.session.get('cart', [])
        item_found = False

        # ตรวจสอบว่า item นั้นมีอยู่ใน cart แล้วหรือไม่
        for cart_item in cart:
            if cart_item['id'] == item.id and cart_item['type'] == item_type:
                cart_item['qty'] += quantity
                item_found = True
                break

        # ถ้ายังไม่เจอ item นี้เลยในตะกร้า
        if not item_found:
            cart.append({'id': item.id, 'qty': quantity, 'type': item_type})

        # บันทึกกลับเข้า session
        request.session['cart'] = cart

        return redirect('cart')
    
def cart_view(request):
    cart = request.session.get('cart', [])
    cart_items = []
    cart_total = 0

    for item in cart:
        item_type = item.get('type')
        item_id = item.get('id')
        quantity = item.get('qty', 1)

        try:
            if item_type == 'tree':
                product = Tree.objects.get(id=item_id)
            elif item_type == 'equipment':
                product = Equipment.objects.get(id=item_id)
            else:
                continue  # skip unknown type

            total_price = product.price * quantity
            cart_items.append({
                'item': product,
                'type': item_type,
                'quantity': quantity,
                'total_price': total_price,
            })
            cart_total += total_price

        except Exception as e:
            print(f"Error loading item {item_id} of type {item_type}: {e}")
            continue  # ข้ามถ้ามีปัญหา

    return render(request, 'myapp/cart.html', {
        'cart_items': cart_items,
        'cart_total': cart_total
    })

def remove_from_cart(request, item_type, item_id):
    cart = request.session.get('cart', [])
    cart = [item for item in cart if not (item['id'] == item_id and item['type'] == item_type)]
    request.session['cart'] = cart
    return redirect('cart')

from django.views.decorators.http import require_POST

@require_POST
def update_cart(request, item_type, item_id):
    action = request.POST.get('action')
    cart = request.session.get('cart', [])

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

def start_planting_redirect(request):
    tree_id = request.POST.get('tree_id')
    if tree_id:
        return redirect('select_location_for_tree', tree_id=tree_id)
    return redirect('cart')  # ถ้าไม่มี tree_id

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')  # หรือ redirect ไป my_trees ก็ได้
    else:
        form = UserCreationForm()
    return render(request, 'myapp/signup.html', {'form': form})

from django.shortcuts import redirect
from django.contrib import messages

def process_cart_items(request):
    cart = request.session.get('cart', [])

    has_tree = any(item['type'] == 'tree' for item in cart)
    has_equipment = any(item['type'] == 'equipment' for item in cart)

    if has_tree:
        # 👉 เริ่มจากเลือกพื้นที่ปลูกต้นไม้
        tree_id = next((item['id'] for item in cart if item['type'] == 'tree'), None)
        return redirect('select_location_for_tree', tree_id=tree_id)

    elif has_equipment:
        # 👉 ถ้าไม่มีต้นไม้ ก็ข้ามไปกรอกที่อยู่
        equipment_id = next((item['id'] for item in cart if item['type'] == 'equipment'), None)
        return redirect('select_address', equipment_id=equipment_id)

    else:
        messages.error(request, "ยังไม่มีรายการสินค้าในตะกร้า")
        return redirect('cart')
    
def split_cart_confirmation(request):
    return render(request, 'split_cart_confirmation.html')  # สร้างหน้าเปล่าๆ ก่อนก็ได้

from myapp.utils.promptpay import generate_qr_base64

@login_required
def equipment_payment(request, equipment_id):
    equipment = get_object_or_404(Equipment, pk=equipment_id)
    qty = int(request.GET.get("qty", 1))
    total = float(equipment.price) * qty

    phone_number = "0612345678"  # เปลี่ยนได้
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
        order.status = 'verifying'  # ✅ Set to verifying immediately
        order.save()
        return redirect('my_orders')


@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Purchase, id=order_id, user=request.user)
    if order.status == 'pending':
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
        order.status = 'verifying'  # 👈 เปลี่ยนสถานะทันที
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
        )
        messages.success(request, "สร้างรายการเรียบร้อยแล้ว คุณสามารถแนบสลิปภายหลังได้ในหน้าคำสั่งซื้อของฉัน")
        return redirect('my_orders')
    return redirect('equipment_payment', equipment_id=equipment_id)

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



