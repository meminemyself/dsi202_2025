from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Tree, Equipment, PlantingLocation, UserPlanting, Notification, NewsArticle , Purchase # อย่าลืม import
from django.db.models import Q  # เพิ่ม Q สำหรับค้นหาแบบ flexible


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
def payment(request, tree_id):
    tree = get_object_or_404(Tree, pk=tree_id)

    # สร้าง location ปลอมสำหรับกรณีไม่เลือกเอง
    default_location, created = PlantingLocation.objects.get_or_create(
        name="Unknown Location",  # หรือ “ไม่ระบุพื้นที่”
        defaults={
            "description": "Auto-assigned due to direct payment.",
            "location_type": "unspecified"
        }
    )

    # เช็คว่าปลูกไปแล้วหรือยัง
    existing = UserPlanting.objects.filter(user=request.user, tree=tree)
    if not existing.exists():
        UserPlanting.objects.create(user=request.user, tree=tree, location=default_location)

    return render(request, 'myapp/payment.html', {'tree': tree})

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

@login_required
def my_orders(request):
    purchases = Purchase.objects.filter(user=request.user).order_by('-purchase_date')
    return render(request, 'myapp/my_orders.html', {'purchases': purchases})

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


def add_to_cart(request, tree_id):
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        tree = get_object_or_404(Tree, id=tree_id)

        cart = request.session.get('cart', [])
        cart.append({'id': tree.id, 'qty': quantity})
        request.session['cart'] = cart

        return redirect('cart')
    else:
        return redirect('tree_detail', tree_id=tree_id)

def cart_view(request):
    cart = request.session.get('cart', [])
    cart_items = []
    cart_total = 0

    for item in cart:
        tree = Tree.objects.get(id=item['id'])
        quantity = item.get('qty', 1)
        total_price = tree.price * quantity
        cart_items.append({
            'tree': tree,
            'quantity': quantity,
            'total_price': total_price,
        })
        cart_total += total_price

    context = {
        'cart_items': cart_items,
        'cart_total': cart_total
    }
    return render(request, 'myapp/cart.html', context)

def remove_from_cart(request, tree_id):
    cart = request.session.get('cart', [])
    cart = [item for item in cart if item['id'] != tree_id]
    request.session['cart'] = cart
    return redirect('cart')

from django.views.decorators.http import require_POST

@require_POST
def update_cart(request, tree_id):
    action = request.POST.get('action')
    cart = request.session.get('cart', [])

    for item in cart:
        if item['id'] == tree_id:
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