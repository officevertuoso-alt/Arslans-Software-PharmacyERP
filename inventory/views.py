from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, Purchase, Supplier, Return, CustomerProfile, CustomerPayment, ProductBatch, SaleBatchAllocation
from datetime import timedelta
from django.utils import timezone
from django.contrib import messages
import pandas as pd
from django.contrib.auth.models import User
from django.http import HttpResponse
import barcode
from barcode.writer import ImageWriter

from datetime import date

from .forms import ProductForm, SupplierForm, ReturnForm, SignUpForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test


LOGIN_URL = 'login'

def home(request):
    products = Product.objects.filter(quantity__gt=0, expiry_date__gte=timezone.now().date())
    return render(request, 'inventory/home.html', {'products': products})


def login_view(request):
    message = ''
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('customer_product_list')
        else:
            message = 'Invalid username or password.'
    return render(request, 'inventory/login.html', {'message': message})

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('customer_product_list')
    else:
        form = SignUpForm()
    return render(request, 'inventory/signup.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')

def admin_required(view_func):
    decorated_view_func = login_required(user_passes_test(lambda u: u.is_staff)(view_func))
    return decorated_view_func

@admin_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'inventory/product_form.html', {'form': form, 'action': 'Add'})

@admin_required
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'inventory/product_form.html', {'form': form, 'action': 'Edit'})


@admin_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        return redirect('product_list')
    return render(request, 'inventory/product_confirm_delete.html', {'product': product})


@admin_required
def product_list(request):
    products = Product.objects.all()
    low_stock_count = sum(1 for p in products if p.is_low_stock)
    today = timezone.now().date()
    return render(request, 'inventory/product_list.html', {'products': products, 'today': today, 'low_stock_count': low_stock_count})

@admin_required
def expired_products(request):
    today = timezone.now().date()
    products = Product.objects.filter(expiry_date__lt=today)
    return render(request, 'inventory/expired_products.html', {'products': products})

@admin_required
def expiring_soon_products(request):
    today = timezone.now().date()
    soon = today + timedelta(days=7)
    products = Product.objects.filter(expiry_date__range=[today, soon])
    return render(request, 'inventory/expiring_soon.html', {'products': products})

@admin_required
def low_stock_products(request):
    products = [p for p in Product.objects.all() if p.is_low_stock]
    return render(request, 'inventory/low_stock_products.html', {'products': products})

@admin_required
def income_report(request):
    purchases = Purchase.objects.all()
    total_income = sum(purchase.total_price for purchase in purchases)
    
    # You can add more complex filtering/aggregation here if needed
    # For example, income by month, by product, etc.

    context = {
        'purchases': purchases,
        'total_income': total_income,
    }
    return render(request, 'inventory/income_report.html', context)

@login_required
def customer_product_list(request):
    products = Product.objects.all()  # or filter as you prefer
    today = date.today()
    return render(request, 'inventory/customer_product_list.html', {
        'products': products,
        'today': today
    })

@login_required
def purchase_product(request, pk):
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=pk)
        try:
            quantity_to_buy = int(request.POST.get('quantity', 1))
        except ValueError:
            messages.error(request, "Invalid quantity.")
            return redirect('customer_product_list')

        if quantity_to_buy <= 0:
            messages.error(request, "Quantity must be at least 1.")
            return redirect('customer_product_list')

        if product.quantity >= quantity_to_buy:
            # Don't decrease stock here yet, do it in checkout
            # product.quantity -= quantity_to_buy
            # product.save()
            total_cost = product.price * quantity_to_buy
            request.session['purchase_info'] = {
                'product_id': product.pk,
                'quantity': quantity_to_buy,
                'total_cost': str(total_cost) # Store as string to avoid Decimal serialization issues
            }
            return redirect('checkout')
        else:
            messages.error(request, f"Not enough {product.name} in stock. Available: {product.quantity}.")
    return redirect('customer_product_list')

@login_required
def checkout(request):
    """
    Complete a sale with cash / partial payment / full credit (udhaar).
    All money and stock updates run inside a single atomic transaction.
    """
    purchase_info = request.session.get('purchase_info')
    if not purchase_info:
        messages.error(request, "No purchase information found. Please select a product first.")
        return redirect('customer_product_list')

    product = get_object_or_404(Product, pk=purchase_info['product_id'])
    quantity = int(purchase_info['quantity'])
    try:
        total_cost = Decimal(purchase_info['total_cost']).quantize(Decimal('0.01'))
    except (InvalidOperation, TypeError, ValueError):
        messages.error(request, "Invalid cart total. Please try again.")
        del request.session['purchase_info']
        return redirect('customer_product_list')

    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        try:
            payment_amount = Decimal(str(request.POST.get('payment_amount', '0') or '0')).quantize(Decimal('0.01'))
        except (InvalidOperation, TypeError, ValueError):
            messages.error(request, "Invalid payment amount.")
            return render(request, 'inventory/checkout.html', {
                'product': product,
                'quantity': quantity,
                'total_cost': total_cost,
                'currency': CURRENCY_SYMBOL,
                'profile': profile,
                'change': None,
            })

        if payment_amount < 0:
            messages.error(request, "Payment amount cannot be negative.")
            return render(request, 'inventory/checkout.html', {
                'product': product,
                'quantity': quantity,
                'total_cost': total_cost,
                'currency': CURRENCY_SYMBOL,
                'profile': profile,
                'change': None,
            })

        credit_needed = (total_cost - payment_amount).quantize(Decimal('0.01'))
        if credit_needed < 0:
            credit_needed = Decimal('0.00')
            change = (payment_amount - total_cost).quantize(Decimal('0.01'))
            amount_paid = total_cost
        else:
            change = Decimal('0.00')
            amount_paid = payment_amount

        if credit_needed > 0 and not profile.can_take_credit(credit_needed):
            messages.error(
                request,
                f"Credit limit exceeded. Available credit: {CURRENCY_SYMBOL}{profile.available_credit}. "
                f"Outstanding balance: {CURRENCY_SYMBOL}{profile.balance}."
            )
            return render(request, 'inventory/checkout.html', {
                'product': product,
                'quantity': quantity,
                'total_cost': total_cost,
                'currency': CURRENCY_SYMBOL,
                'profile': profile,
                'change': None,
            })

        if credit_needed == 0:
            payment_method = Purchase.PAYMENT_CASH if amount_paid > 0 else Purchase.PAYMENT_CASH
        elif amount_paid == 0:
            payment_method = Purchase.PAYMENT_CREDIT
        else:
            payment_method = Purchase.PAYMENT_SPLIT

        try:
            with transaction.atomic():
                product = Product.objects.select_for_update().get(pk=product.pk)
                if product.is_expired():
                    raise ValueError(f"{product.name} is expired and cannot be sold.")

                # FEFO: allocate from earliest-expiring non-expired batches
                has_batches = product.batches.filter(is_active=True, quantity__gt=0).exists()
                plan = []
                if has_batches:
                    plan = product.allocate_fefo(quantity)
                    for batch, take in plan:
                        batch.quantity -= take
                        if batch.quantity == 0:
                            batch.is_active = False
                        batch.save(update_fields=['quantity', 'is_active'])
                    product.sync_quantity_from_batches()
                else:
                    # Legacy path: product has no batches yet — use product.quantity
                    if product.quantity < quantity:
                        raise ValueError(
                            f"Not enough {product.name} in stock. Available: {product.quantity}."
                        )
                    product.quantity -= quantity
                    product.save(update_fields=['quantity'])

                sale = Purchase.objects.create(
                    product=product,
                    customer=request.user,
                    quantity=quantity,
                    total_price=total_cost,
                    amount_paid=amount_paid,
                    amount_on_credit=credit_needed,
                    payment_method=payment_method,
                )
                for batch, take in plan:
                    SaleBatchAllocation.objects.create(sale=sale, batch=batch, quantity=take)

                if credit_needed > 0:
                    profile = CustomerProfile.objects.select_for_update().get(user=request.user)
                    profile.balance = (profile.balance + credit_needed).quantize(Decimal('0.01'))
                    profile.save(update_fields=['balance', 'updated_at'])
        except ValueError as exc:
            messages.error(request, str(exc))
            if 'purchase_info' in request.session:
                del request.session['purchase_info']
            return redirect('customer_product_list')
        except Exception:
            messages.error(request, "Sale could not be completed. Please try again.")
            return redirect('customer_product_list')

        if credit_needed > 0 and change == 0:
            msg = (
                f"Sale successful. Paid {CURRENCY_SYMBOL}{amount_paid}, "
                f"on credit (udhaar) {CURRENCY_SYMBOL}{credit_needed}. "
                f"New balance: {CURRENCY_SYMBOL}{(profile.balance)}."
            )
        elif change > 0:
            msg = f"Purchase successful! Your change is {CURRENCY_SYMBOL}{change}."
        else:
            msg = f"Purchase successful! Paid {CURRENCY_SYMBOL}{amount_paid}."

        messages.success(request, msg)
        if 'purchase_info' in request.session:
            del request.session['purchase_info']
        return redirect('customer_product_list')

    return render(request, 'inventory/checkout.html', {
        'product': product,
        'quantity': quantity,
        'total_cost': total_cost,
        'currency': CURRENCY_SYMBOL,
        'profile': profile,
        'change': None,
    })


@admin_required
def supplier_list(request):
    suppliers = Supplier.objects.all()
    return render(request, 'inventory/supplier_list.html', {'suppliers': suppliers})

@admin_required
def supplier_create(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('supplier_list')
    else:
        form = SupplierForm()
    return render(request, 'inventory/supplier_form.html', {'form': form, 'action': 'Add'})

@admin_required
def supplier_update(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            return redirect('supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'inventory/supplier_form.html', {'form': form, 'action': 'Edit'})

@admin_required
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        supplier.delete()
        return redirect('supplier_list')
    return render(request, 'inventory/supplier_confirm_delete.html', {'supplier': supplier})

@admin_required
def sales_forecast(request):
    purchases = Purchase.objects.all().values('product__name', 'purchase_date', 'quantity')
    if not purchases:
        return render(request, 'inventory/sales_forecast.html', {'forecast': {}})

    df = pd.DataFrame(list(purchases))
    df['purchase_date'] = pd.to_datetime(df['purchase_date'])
    df = df.set_index('purchase_date')

    forecast = {}
    for product_name, group in df.groupby('product__name'):
        daily_sales = group['quantity'].resample('D').sum()
        moving_average = daily_sales.rolling(window=7).mean().iloc[-1]
        forecast[product_name] = moving_average if not pd.isna(moving_average) else 0

    return render(request, 'inventory/sales_forecast.html', {'forecast': forecast})

@login_required
def request_return(request):
    if request.method == 'POST':
        form = ReturnForm(request.POST)
        if form.is_valid():
            return_request = form.save(commit=False)
            return_request.customer = request.user
            return_request.save()
            messages.success(request, "Return request submitted successfully.")
            return redirect('customer_product_list')
    else:
        form = ReturnForm()
    return render(request, 'inventory/request_return.html', {'form': form})

@admin_required
def manage_returns(request):
    returns = Return.objects.all()
    return render(request, 'inventory/manage_returns.html', {'returns': returns})

@admin_required
def process_return(request, pk, status):
    return_request = get_object_or_404(Return, pk=pk)
    if status in ["Approved", "Rejected"]:
        return_request.status = status
        if status == "Approved":
            product = return_request.product
            product.quantity += return_request.quantity
            product.save()
        return_request.save()
        messages.success(request, f"Return request {status.lower()}.")
    else:
        messages.error(request, "Invalid status.")
    return redirect('manage_returns')

def view_barcode(request, pk):
    product = get_object_or_404(Product, pk=pk)
    EAN = barcode.get_barcode_class('ean13')
    ean = EAN(f'{product.pk:012d}', writer=ImageWriter())
    response = HttpResponse(content_type='image/png')
    ean.write(response)
    return response

@admin_required
def process_return(request, pk, status):
    if status not in ["Approved", "Rejected"]:
        messages.error(request, "Invalid status.")
        return redirect('manage_returns')

    try:
        with transaction.atomic():
            return_request = Return.objects.select_for_update().get(pk=pk)
            if return_request.status != "Pending":
                messages.error(request, "This return has already been processed.")
                return redirect('manage_returns')

            return_request.status = status
            if status == "Approved":
                product = Product.objects.select_for_update().get(pk=return_request.product_id)
                product.quantity += return_request.quantity
                product.save(update_fields=['quantity'])
            return_request.save(update_fields=['status'])
        messages.success(request, f"Return request {status.lower()}.")
    except Exception:
        messages.error(request, "Could not process return. Please try again.")
    return redirect('manage_returns')


def view_barcode(request, pk):
    product = get_object_or_404(Product, pk=pk)
    EAN = barcode.get_barcode_class('ean13')
    ean = EAN(f'{product.pk:012d}', writer=ImageWriter())
    response = HttpResponse(content_type='image/png')
    ean.write(response)
    return response


@login_required
def my_ledger(request):
    """Customer views their own sales and outstanding balance."""
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    sales = Purchase.objects.filter(customer=request.user).select_related('product')[:50]
    payments = CustomerPayment.objects.filter(customer=request.user)[:30]
    return render(request, 'inventory/my_ledger.html', {
        'profile': profile,
        'sales': sales,
        'payments': payments,
        'currency': CURRENCY_SYMBOL,
    })


@admin_required
def customer_ledger_list(request):
    """Staff: list all customers with outstanding balances."""
    profiles = (
        CustomerProfile.objects.select_related('user')
        .order_by('-balance', 'user__username')
    )
    return render(request, 'inventory/customer_ledger_list.html', {
        'profiles': profiles,
        'currency': CURRENCY_SYMBOL,
    })


@admin_required
def customer_ledger_detail(request, user_id):
    """Staff: one customer ledger + record payment against udhaar."""
    customer = get_object_or_404(User, pk=user_id)
    profile, _ = CustomerProfile.objects.get_or_create(user=customer)
    sales = Purchase.objects.filter(customer=customer).select_related('product')[:50]
    payments = CustomerPayment.objects.filter(customer=customer)[:30]

    if request.method == 'POST':
        try:
            amount = Decimal(str(request.POST.get('amount', '0'))).quantize(Decimal('0.01'))
        except (InvalidOperation, TypeError, ValueError):
            messages.error(request, "Invalid amount.")
            return redirect('customer_ledger_detail', user_id=user_id)

        if amount <= 0:
            messages.error(request, "Payment amount must be greater than zero.")
            return redirect('customer_ledger_detail', user_id=user_id)

        method = request.POST.get('payment_method', 'cash')
        notes = (request.POST.get('notes') or '')[:255]

        try:
            with transaction.atomic():
                profile = CustomerProfile.objects.select_for_update().get(user=customer)
                if amount > profile.balance:
                    amount = profile.balance
                if amount <= 0:
                    messages.info(request, "No outstanding balance to collect.")
                    return redirect('customer_ledger_detail', user_id=user_id)

                profile.balance = (profile.balance - amount).quantize(Decimal('0.01'))
                profile.save(update_fields=['balance', 'updated_at'])

                CustomerPayment.objects.create(
                    customer=customer,
                    amount=amount,
                    payment_method=method if method in ('cash', 'card', 'other') else 'cash',
                    received_by=request.user,
                    notes=notes,
                )
            messages.success(
                request,
                f"Received {CURRENCY_SYMBOL}{amount}. New balance: {CURRENCY_SYMBOL}{profile.balance}."
            )
        except Exception:
            messages.error(request, "Could not record payment. Please try again.")
        return redirect('customer_ledger_detail', user_id=user_id)

    return render(request, 'inventory/customer_ledger_detail.html', {
        'customer': customer,
        'profile': profile,
        'sales': sales,
        'payments': payments,
        'currency': CURRENCY_SYMBOL,
    })



@admin_required
def batch_list(request, product_id=None):
    """List batches; optional filter by product."""
    batches = ProductBatch.objects.select_related('product', 'supplier').order_by('expiry_date')
    product = None
    if product_id:
        product = get_object_or_404(Product, pk=product_id)
        batches = batches.filter(product=product)
    return render(request, 'inventory/batch_list.html', {
        'batches': batches,
        'product': product,
        'today': timezone.now().date(),
        'currency': CURRENCY_SYMBOL,
    })


@admin_required
def receive_batch(request, product_id=None):
    """
    Receive new stock as a batch (goods receipt).
    Creates/updates ProductBatch and syncs Product.quantity.
    """
    product = None
    if product_id:
        product = get_object_or_404(Product, pk=product_id)

    if request.method == 'POST':
        try:
            pid = int(request.POST.get('product_id') or (product.id if product else 0))
            product = Product.objects.get(pk=pid)
            batch_number = (request.POST.get('batch_number') or '').strip()
            qty = int(request.POST.get('quantity', 0))
            expiry = request.POST.get('expiry_date')
            cost = Decimal(str(request.POST.get('purchase_cost') or '0')).quantize(Decimal('0.01'))
            supplier_id = request.POST.get('supplier_id') or None
            notes = (request.POST.get('notes') or '')[:255]
        except Exception:
            messages.error(request, "Invalid form data.")
            return redirect('receive_batch')

        if not batch_number or qty <= 0 or not expiry:
            messages.error(request, "Batch number, quantity > 0 and expiry date are required.")
            return redirect('receive_batch', product_id=product.id)

        try:
            with transaction.atomic():
                product = Product.objects.select_for_update().get(pk=product.pk)
                batch, created = ProductBatch.objects.select_for_update().get_or_create(
                    product=product,
                    batch_number=batch_number,
                    defaults={
                        'quantity': 0,
                        'expiry_date': expiry,
                        'purchase_cost': cost,
                        'notes': notes,
                        'is_active': True,
                    }
                )
                if not created:
                    # same batch number: add quantity, keep earliest expiry if already set
                    batch.quantity += qty
                    if cost > 0:
                        batch.purchase_cost = cost
                    if notes:
                        batch.notes = notes
                    batch.is_active = True
                    batch.save()
                else:
                    batch.quantity = qty
                    batch.expiry_date = expiry
                    batch.purchase_cost = cost
                    batch.notes = notes
                    if supplier_id:
                        batch.supplier_id = int(supplier_id)
                    batch.save()

                if supplier_id and not batch.supplier_id:
                    batch.supplier_id = int(supplier_id)
                    batch.save(update_fields=['supplier'])

                # Also bump legacy product.quantity and optionally update product expiry to earliest batch
                product.quantity = product.total_batch_quantity()
                # Keep product.expiry_date as nearest upcoming expiry for alerts
                nearest = (
                    product.batches.filter(is_active=True, quantity__gt=0)
                    .order_by('expiry_date').values_list('expiry_date', flat=True).first()
                )
                if nearest:
                    product.expiry_date = nearest
                product.save(update_fields=['quantity', 'expiry_date'])

            messages.success(
                request,
                f"Received {qty} of {product.name} batch {batch_number}. "
                f"Stock now {product.quantity}."
            )
            return redirect('batch_list_product', product_id=product.id)
        except Exception as e:
            messages.error(request, f"Could not receive batch: {e}")
            return redirect('receive_batch', product_id=product.id if product else None)

    products = Product.objects.all().order_by('name')
    suppliers = Supplier.objects.all().order_by('name')
    return render(request, 'inventory/receive_batch.html', {
        'product': product,
        'products': products,
        'suppliers': suppliers,
        'currency': CURRENCY_SYMBOL,
    })


def custom_404(request, exception=None):
    return render(request, 'inventory/404.html', status=404)


def custom_500(request):
    return render(request, 'inventory/500.html', status=500)
