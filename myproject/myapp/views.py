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
    })

@login_required
def select_location_for_tree(request, tree_id):
    tree = get_object_or_404(Tree, id=tree_id)
    locations = PlantingLocation.objects.all()
    return render(request, 'myapp/select_location_for_tree.html', {
        'tree': tree,
        'locations': locations
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
        first_item = order.items_list.first()
        if first_item:
            if first_item.equipment:
                order.first_image = first_item.equipment.image_url
            elif first_item.tree:
                order.first_image = first_item.tree.image_url
            else:
                order.first_image = 'https://via.placeholder.com/80'
        else:
            order.first_image = 'https://via.placeholder.com/80'

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
        else:
            cart_items_equipment.append(item_data)

    return render(request, 'myapp/cart.html', {
        'cart_items_equipment': cart_items_equipment,
        'cart_items_tree': cart_items_tree,
        'cart_total': cart_total
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

    # เตรียมข้อมูลสินค้าและยอดรวม
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
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

@login_required
def process_cart_items(request):
    cart = request.session.get('cart', [])

    if not cart:
        messages.error(request, "ยังไม่มีสินค้าในตะกร้า")
        return redirect('cart')

    # แยกประเภทสินค้า
    has_tree = any(item['type'] == 'tree' for item in cart)
    has_equipment = any(item['type'] == 'equipment' for item in cart)

    # บันทึก cart ลง session สำหรับใช้ในขั้นถัดไป
    request.session['checkout_cart'] = cart

    if has_tree and has_equipment:
        return redirect('split_cart_confirmation')
    
    elif has_tree:
        # 🔍 ตรวจให้แน่ใจว่ามี tree_id ก่อน redirect
        try:
            tree_item = next(item for item in cart if item['type'] == 'tree')
            tree_id = tree_item['id']
            return redirect('select_location_for_tree', tree_id=tree_id)
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

# ✅ views.py (เฉพาะฟังก์ชัน process_cart_items)
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

@login_required
def process_cart_items(request):
    cart = request.session.get('cart', [])

    if not cart:
        messages.error(request, "ยังไม่มีสินค้าในตะกร้า")
        return redirect('cart')

    has_tree = any(item['type'] == 'tree' for item in cart)
    has_equipment = any(item['type'] == 'equipment' for item in cart)

    request.session['checkout_cart'] = cart

    if has_tree and has_equipment:
        print(">>> CART มีทั้ง TREE และ EQUIPMENT:", cart)
        return redirect('split_cart_confirmation')

    elif has_tree:
        try:
            tree_item = next(item for item in cart if item['type'] == 'tree')
            tree_id = tree_item['id']
            print(">>> CART:", cart)
            print(">>> REDIRECT TO TREE:", tree_id)
            return redirect('select_location_for_tree', tree_id=tree_id)
        except StopIteration:
            messages.error(request, "ไม่พบต้นไม้ในตะกร้า")
            return redirect('cart')

    elif has_equipment:
        print(">>> CART มีแต่ EQUIPMENT:", cart)
        return redirect('select_address_multi')

    print(">>> CART EMPTY OR INVALID:", cart)
    return redirect('cart')




# ✅ select_location_for_tree.html (check this file exists in templates/myapp/)
# ✅ Ensure the view is like this:
from django.shortcuts import render, get_object_or_404
from .models import Tree, PlantingLocation
from django.contrib.auth.decorators import login_required

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
    if order.status == 'verifying':  # ✅ เฉพาะตอนกำลังตรวจสอบเท่านั้น
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
            payment_slip=request.FILES.get('payment_slip')
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

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Equipment # ถ้าคุณใช้ฟังก์ชันสร้าง QR
from django.http import Http404

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

        # ✅ ดึงจาก POST (ไม่ใช้ session)
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

        total = 0
        detailed_items = []
        for item in cart:
            item_type = item.get('type')
            item_id = item.get('id')
            qty = int(item.get('qty', 1))

            if item_type == 'equipment':
                product = get_object_or_404(Equipment, id=item_id)
            else:
                continue  # ยังไม่รองรับ tree ตรงนี้

            item_total = qty * product.price
            total += item_total

            detailed_items.append({
                'name': product.name,
                'image_url': product.image_url,
                'price': product.price,
                'qty': qty,
                'total': item_total
            })

        qr_base64 = generate_qr_base64("0612345678", total)

        return render(request, 'myapp/payment_multi.html', {
            'items': detailed_items,
            'total': total,
            'qr_base64': qr_base64,
            'name': name,
            'tel': tel,
            'full_address': full_address,
        })

    return redirect('cart')

from .models import Purchase, PurchaseItem, Equipment
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404, render
from django.contrib import messages

@login_required
def create_order_multi(request):
    if request.method == 'POST':
        cart = request.session.get('checkout_cart', [])
        if not cart:
            messages.error(request, "ไม่พบรายการสินค้า")
            return redirect('cart')

        name = request.POST.get('name')
        tel = request.POST.get('tel')
        address = request.POST.get('address')
        slip = request.FILES.get('payment_slip')
        total_quantity = sum(item['qty'] for item in cart if item['type'] == 'equipment')
        # สร้างออเดอร์หลัก (รวมทั้งหมด)
        purchase = Purchase.objects.create(
            user=request.user,
            name=name,
            tel=tel,
            address=address,
            payment_slip=slip,
            status='pending',
        )

        for item in cart:
            if item['type'] == 'equipment':
                product = get_object_or_404(Equipment, id=item['id'])
                PurchaseItem.objects.create(
                    purchase=purchase,
                    equipment=product,
                    quantity=item['qty']
                )
            # หมายเหตุ: ถ้ามี tree จะต้องแยก flow ไปอีกแบบ ไม่ควรมาอยู่ในนี้

        del request.session['checkout_cart']
        request.session.pop('shipping_info', None)        
        messages.success(request, "สั่งซื้อสำเร็จแล้ว กรุณารอการตรวจสอบสลิป")
        return redirect('my_orders')

    return redirect('cart')

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def select_address_multi(request):
    cart = request.session.get('cart', [])
    if not cart:
        return redirect('cart')  # กลับไปถ้าไม่มีสินค้า

    if request.method == 'POST':
        # เก็บข้อมูลที่อยู่ลงใน session
        request.session['shipping_info'] = {
            'name': request.POST.get('name'),
            'tel': request.POST.get('tel'),
            'province': request.POST.get('province'),
            'district': request.POST.get('district'),
            'subdistrict': request.POST.get('subdistrict'),
            'zipcode': request.POST.get('zipcode'),
            'address': request.POST.get('address'),
        }
        return redirect('confirm_cart_order')  # ไปขั้นตอนถัดไป

    # ถ้า GET ให้แสดงฟอร์ม
    return render(request, 'myapp/select_address_multi.html', {
        'cart': cart
    })


def split_cart_confirmation(request):
    return render(request, 'myapp/split_cart_confirmation.html')

def confirm_cart_split(request):
    if request.method == 'POST':
        choice = request.POST.get('choice')
        if choice == 'separate':
            return redirect('separate_order_flow')  # เปลี่ยนชื่อ view ให้ตรงกับจริง
        else:
            return redirect('combine_order_flow')


from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required

PROVINCE_DATA = {
    "ภาคเหนือ": ["เชียงใหม่", "เชียงราย", "ลำพูน", "ลำปาง", "แพร่", "น่าน", "พะเยา", "แม่ฮ่องสอน", "อุตรดิตถ์", "ตาก"],
    "ภาคกลาง": ["กรุงเทพมหานคร", "นนทบุรี", "ปทุมธานี", "พระนครศรีอยุธยา", "สมุทรปราการ", "สมุทรสาคร", "สมุทรสงคราม", "นครปฐม", "สุพรรณบุรี", "สระบุรี", "อ่างทอง", "ลพบุรี", "ชัยนาท", "สิงห์บุรี"],
    "ภาคตะวันออก": ["ชลบุรี", "ระยอง", "จันทบุรี", "ตราด", "ปราจีนบุรี", "สระแก้ว", "ฉะเชิงเทรา"],
    "ภาคตะวันตก": ["กาญจนบุรี", "ราชบุรี", "เพชรบุรี", "ประจวบคีรีขันธ์"],
    "ภาคตะวันออกเฉียงเหนือ": ["ขอนแก่น", "อุบลราชธานี", "นครราชสีมา", "มหาสารคาม", "ร้อยเอ็ด", "ชัยภูมิ", "อุดรธานี", "สกลนคร", "นครพนม", "มุกดาหาร", "บึงกาฬ", "หนองคาย", "หนองบัวลำภู", "ยโสธร", "ศรีสะเกษ", "อำนาจเจริญ", "กาฬสินธุ์", "เลย", "สุรินทร์", "บุรีรัมย์"],
    "ภาคใต้": ["ภูเก็ต", "สงขลา", "สุราษฎร์ธานี", "กระบี่", "ตรัง", "พังงา", "นครศรีธรรมราช", "ชุมพร", "ระนอง", "ปัตตานี", "ยะลา", "นราธิวาส", "สตูล"]
}

@login_required
def select_province_page(request):
    return render(request, 'myapp/select_location_by_province.html', {
        'province_groups': PROVINCE_DATA
    })

@login_required
@csrf_protect
def plant_tree_in_province(request):
    if request.method == 'POST':
        province = request.POST.get('province')
        # ทำอะไรบางอย่าง เช่น redirect ไปหน้าเลือกต้นไม้ หรือหน้าคอนเฟิร์มพื้นที่
        return render(request, 'myapp/confirm_province_plant.html', {'province': province})
    return redirect('select_province_page')