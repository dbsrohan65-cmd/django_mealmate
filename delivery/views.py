from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt

import razorpay
from django.conf import settings
# from mealmate.mealmate import settings
from .models import Customer,Restaurant,Item,Cart
# Create your views here.
def say_hello(request):
    # return HttpResponse("Say Hello my app is working!")
    return render(request,"index.html")

def open_signup(request):
    return render(request,"signup.html")

def open_signin(request):
    return render(request,"signin.html")

def signup(request):
    if request.method=='POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        mobile = request.POST.get('mobile')
        address = request.POST.get('address')
        try:
            Customer.objects.get(username = username)
            return HttpResponse("Duplicate username!")
        except:
            Customer.objects.create(
                username = username,
                password = password,
                email = email,
                mobile = mobile,
                address = address, 
            )
    return render(request, 'signin.html')

def signin(request):
    if request.method=='POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
    try:
        Customer.objects.get(username = username, password = password)
        if username == 'admin':
            return render(request,'admin_home.html')
        else:
            restaurantList=Restaurant.objects.all()
            return render(request,'customer_home.html',{"restaurantList":restaurantList,"username":username})
    except Customer.DoesNotExist:
        return render(request,'fail.html')

def open_add_restaurant(request):
    return render(request,'add_restaurant.html')

def add_restaurant(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        picture = request.POST.get('picture')
        cusine = request.POST.get('cusine')
        rating = request.POST.get('rating')
        try:
            Restaurant.objects.get(name = name)
            return HttpResponse("Duplicate Restaurant !")
        except:
            Restaurant.objects.create(
                name = name,
                picture = picture,
                cusine = cusine,
                rating = rating,
            )
    return render(request,'admin_home.html')

def open_show_restaurant(request):
    restaurantList = Restaurant.objects.all()
    return render(request,'show_restaurants.html',{"restaurantList":restaurantList}) 

def open_update_restaurant(request,restaurant_id):
    restaurant = Restaurant.objects.get(id=restaurant_id)
    return render(request,'update_restaurant.html',{"restaurant":restaurant}) 

def update_restaurant(request,restaurant_id):
    restaurant=Restaurant.objects.get(id=restaurant_id)
    if request.method=='POST':
        name = request.POST.get('name')
        picture = request.POST.get('picture')
        cusine = request.POST.get('cusine')
        rating = request.POST.get('rating')  

        restaurant.name = name
        restaurant.picture = picture
        restaurant.cusine = cusine
        restaurant.rating = rating 

        restaurant.save()
    restaurantList = Restaurant.objects.all()
    return render(request,'show_restaurants.html',{"restaurantList":restaurantList})  

def delete_restaurant(request,restaurant_id):
    restaurant=Restaurant.objects.get(id=restaurant_id)
    restaurant.delete()
    restaurantList=Restaurant.objects.all() 
    return render(request,'show_restaurants.html',{"restaurantList":restaurantList})

def open_update_menu(request, restaurant_id):
    restaurant = Restaurant.objects.get(id = restaurant_id)
    itemList = restaurant.items.all()
    #itemList = Item.objects.all()
    return render(request, 'update_menu.html',{"itemList" : itemList, "restaurant" : restaurant})

def update_menu(request, restaurant_id):
    restaurant = Restaurant.objects.get(id = restaurant_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        vegeterian = request.POST.get('vegeterian') == 'on'
        picture = request.POST.get('picture')
        
        try:
            Item.objects.get(name = name)
            return HttpResponse("Duplicate item!")
        except:
            Item.objects.create(
                restaurant = restaurant,
                name = name,
                description = description,
                price = price,
                vegeterian = vegeterian,
                picture = picture,
            )
    return render(request, 'admin_home.html')

def view_menu(request, restaurant_id, username):
    restaurant=Restaurant.objects.get(id=restaurant_id)
    itemList=restaurant.items.all()
    return render(request,'customer_menu.html',{"itemList":itemList,"restaurant":restaurant,"username":username})

def add_to_cart(request,item_id,username):
    item = Item.objects.get(id=item_id)
    customer = Customer.objects.get(username=username)
    cart, created = Cart.objects.get_or_create(customer = customer)

    cart.items.add(item)

    return HttpResponse('added to cart')

def show_cart(request,username):
    customer = Customer.objects.get(username = username)
    cart = Cart.objects.filter(customer = customer).first()
    if cart:
        items = cart.items.all()
        total_price = cart.total_price()
    else:
        items=[]
        total_price=0
    return render(request,'cart.html',{"itemList":items, "total_price":total_price,"username":username})
    
def checkout(request, username):
    customer = get_object_or_404(Customer, username=username)
    cart = Cart.objects.filter(customer=customer).first()

    if cart:
        cart_items = cart.items.all()
        total_price = cart.total_price()
    else:
        cart_items = []
        total_price = 0

    if total_price == 0:
        return render(request, 'checkout.html', {'error': 'Your cart is empty!'})

    amount_paise = round(total_price * 100)
    if amount_paise < 100:
        return render(request, 'checkout.html', {
            'error': 'Minimum order amount is ₹1.',
        })

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    try:
        order = client.order.create(data={
            'amount': amount_paise,
            'currency': 'INR',
            'payment_capture': 1,
        })
    except razorpay.errors.BadRequestError as exc:
        return render(request, 'checkout.html', {
            'error': f'Unable to start payment. Please try again. ({exc})',
        })

    return render(request, 'checkout.html', {
        'username': username,
        'customer': customer,
        'cart_items': cart_items,
        'total_price': total_price,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'order_id': order['id'],
        'amount_paise': amount_paise,
        'is_test_mode': settings.RAZORPAY_KEY_ID.startswith('rzp_test_'),
        'debug': settings.DEBUG,
    })


@csrf_exempt
def verify_payment(request, username):
    if request.method != 'POST':
        return redirect('checkout', username=username)

    payment_id = request.POST.get('razorpay_payment_id')
    order_id = request.POST.get('razorpay_order_id')
    signature = request.POST.get('razorpay_signature')

    if not all([payment_id, order_id, signature]):
        return render(request, 'checkout.html', {
            'error': 'Payment details were incomplete. Please try again.',
        })

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature,
        })
    except razorpay.errors.SignatureVerificationError:
        return render(request, 'checkout.html', {
            'error': 'Payment verification failed. Please try again.',
        })

    return redirect('orders', username=username)


def skip_payment_dev(request, username):
    if not settings.DEBUG:
        return HttpResponse("Not allowed.", status=403)
    return redirect('orders', username=username)

def orders(request, username):
    customer = get_object_or_404(Customer, username=username)
    cart = Cart.objects.filter(customer=customer).first()
    # Fetch cart items and total price before clearing the cart
    if cart:
        cart_items = cart.items.all()
        total_price = cart.total_price()

        # Clear the cart after fetching details
        cart.items.clear()
    else:
        cart_items = []
        total_price = 0

    return render(request, 'orders.html', {
        'username': username,
        'customer': customer,
        'cart_items': cart_items,
        'total_price': total_price,
    })
    