from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, Purchase, Supplier, Return, CustomerProfile, CustomerPayment, ProductBatch, SaleBatchAllocation, SupplierPurchase, SupplierPurchaseLine, SupplierPayment
from datetime import timedelta
from django.utils import timezone
from django.contrib import messages
import pandas as pd
from django.contrib.auth.models import User
from django.http import HttpResponse, FileResponse, Http404
import barcode
from barcode.writer import ImageWriter

from datetime import date, datetime, timedelta

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
    """
    Approve/reject a return with full accounting:
    - restock to a RETURN batch (or existing nearest batch)
    - cash refund or credit to customer udhaar balance
    - link processed_by / processed_at
    """
    if status not in ["Approved", "Rejected"]:
        messages.error(request, "Invalid status.")
        return redirect('manage_returns')

    # Optional override from POST when approving from enhanced form
    if request.method == 'POST' and status == "Approved":
        refund_method = request.POST.get('refund_method', 'cash')
        restock = request.POST.get('restock', '1') == '1'
        try:
            refund_amount = Decimal(str(request.POST.get('refund_amount', '0') or '0')).quantize(Decimal('0.01'))
        except (InvalidOperation, TypeError, ValueError):
            refund_amount = None
    else:
        refund_method = None
        restock = True
        refund_amount = None

    try:
        with transaction.atomic():
            ret = Return.objects.select_for_update().select_related('product', 'customer', 'sale').get(pk=pk)
            if ret.status != "Pending":
                messages.error(request, "This return has already been processed.")
                return redirect('manage_returns')

            ret.status = status
            ret.processed_at = timezone.now()
            ret.processed_by = request.user

            if status == "Approved":
                if refund_method:
                    ret.refund_method = refund_method if refund_method in ('cash', 'credit', 'none') else 'cash'
                ret.restock = restock

                if refund_amount is None:
                    refund_amount = ret.suggested_refund()
                if ret.refund_method == Return.REFUND_NONE:
                    refund_amount = Decimal('0.00')
                ret.refund_amount = refund_amount

                # Restock
                if ret.restock and ret.quantity > 0:
                    product = Product.objects.select_for_update().get(pk=ret.product_id)
                    batch_number = f"RET-{ret.id}-{timezone.now().strftime('%Y%m%d')}"
                    # Prefer put back into a non-expired batch of same product if exists
                    today = timezone.now().date()
                    batch = (
                        product.batches.select_for_update()
                        .filter(is_active=True, expiry_date__gte=today)
                        .order_by('expiry_date')
                        .first()
                    )
                    if batch:
                        batch.quantity += ret.quantity
                        batch.save(update_fields=['quantity'])
                    else:
                        # Create a return batch; expiry from product or +1 year
                        from datetime import timedelta
                        exp = product.expiry_date if product.expiry_date >= today else today + timedelta(days=365)
                        batch = ProductBatch.objects.create(
                            product=product,
                            batch_number=batch_number,
                            quantity=ret.quantity,
                            expiry_date=exp,
                            purchase_cost=Decimal('0.00'),
                            notes=f'Restock from return #{ret.id}',
                            is_active=True,
                        )
                    product.quantity = product.total_batch_quantity()
                    # fallback if no batches sum
                    if product.quantity == 0 and not product.batches.exists():
                        product.quantity = ret.quantity
                    elif product.batches.exists():
                        product.quantity = product.total_batch_quantity()
                    else:
                        product.quantity += ret.quantity
                    product.save(update_fields=['quantity'])

                # Monetary refund
                if ret.refund_amount > 0 and ret.refund_method == Return.REFUND_CREDIT:
                    profile, _ = CustomerProfile.objects.select_for_update().get_or_create(user=ret.customer)
                    # Crediting udhaar = reduce what customer owes
                    profile.balance = (profile.balance - ret.refund_amount).quantize(Decimal('0.01'))
                    profile.save(update_fields=['balance', 'updated_at'])
                # cash refund is recorded on the return; actual cash drawer is operational

            ret.save()
        messages.success(
            request,
            f"Return {status.lower()}."
            + (f" Refund {CURRENCY_SYMBOL}{ret.refund_amount} via {ret.get_refund_method_display()}."
               if status == "Approved" else "")
        )
    except Exception as e:
        messages.error(request, f"Could not process return: {e}")
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



@admin_required
def supplier_purchase_list(request):
    purchases = (
        SupplierPurchase.objects.select_related('supplier')
        .order_by('-invoice_date', '-id')[:100]
    )
    return render(request, 'inventory/supplier_purchase_list.html', {
        'purchases': purchases,
        'currency': CURRENCY_SYMBOL,
    })


@admin_required
def supplier_purchase_create(request):
    """
    Create a supplier invoice with one or more lines.
    On save (status=received): create/update batches, increase supplier balance.
    Form posts repeated line fields: product_id[], batch_number[], quantity[], unit_cost[], expiry_date[]
    """
    products = Product.objects.all().order_by('name')
    suppliers = Supplier.objects.filter(is_active=True).order_by('name')

    if request.method == 'POST':
        try:
            supplier_id = int(request.POST.get('supplier_id'))
            invoice_number = (request.POST.get('invoice_number') or '').strip()
            invoice_date = request.POST.get('invoice_date') or timezone.now().date().isoformat()
            tax = Decimal(str(request.POST.get('tax') or '0')).quantize(Decimal('0.01'))
            notes = (request.POST.get('notes') or '')[:2000]
            amount_paid_now = Decimal(str(request.POST.get('amount_paid') or '0')).quantize(Decimal('0.01'))

            product_ids = request.POST.getlist('product_id')
            batch_numbers = request.POST.getlist('batch_number')
            quantities = request.POST.getlist('quantity')
            unit_costs = request.POST.getlist('unit_cost')
            expiries = request.POST.getlist('expiry_date')

            if not supplier_id or not invoice_number:
                raise ValueError('Supplier and invoice number are required.')
            if not product_ids:
                raise ValueError('Add at least one line item.')

            lines_data = []
            subtotal = Decimal('0.00')
            for i, pid in enumerate(product_ids):
                if not pid:
                    continue
                qty = int(quantities[i])
                cost = Decimal(str(unit_costs[i] or '0')).quantize(Decimal('0.01'))
                bn = (batch_numbers[i] or '').strip()
                exp = expiries[i]
                if qty <= 0 or not bn or not exp:
                    raise ValueError(f'Line {i+1}: batch number, quantity and expiry are required.')
                line_total = (Decimal(qty) * cost).quantize(Decimal('0.01'))
                subtotal += line_total
                lines_data.append({
                    'product_id': int(pid),
                    'batch_number': bn,
                    'quantity': qty,
                    'unit_cost': cost,
                    'expiry_date': exp,
                    'line_total': line_total,
                })

            if not lines_data:
                raise ValueError('Add at least one valid line item.')

            total = (subtotal + tax).quantize(Decimal('0.01'))
            if amount_paid_now < 0:
                amount_paid_now = Decimal('0.00')
            if amount_paid_now > total:
                amount_paid_now = total

            with transaction.atomic():
                supplier = Supplier.objects.select_for_update().get(pk=supplier_id)
                purchase = SupplierPurchase.objects.create(
                    supplier=supplier,
                    invoice_number=invoice_number,
                    invoice_date=invoice_date,
                    status=SupplierPurchase.STATUS_RECEIVED,
                    subtotal=subtotal,
                    tax=tax,
                    total=total,
                    amount_paid=amount_paid_now,
                    notes=notes,
                    created_by=request.user,
                )

                for ld in lines_data:
                    product = Product.objects.select_for_update().get(pk=ld['product_id'])
                    batch, created = ProductBatch.objects.select_for_update().get_or_create(
                        product=product,
                        batch_number=ld['batch_number'],
                        defaults={
                            'quantity': 0,
                            'expiry_date': ld['expiry_date'],
                            'purchase_cost': ld['unit_cost'],
                            'supplier': supplier,
                            'is_active': True,
                        }
                    )
                    batch.quantity += ld['quantity']
                    batch.expiry_date = ld['expiry_date']
                    batch.purchase_cost = ld['unit_cost']
                    batch.supplier = supplier
                    batch.is_active = True
                    batch.save()

                    line = SupplierPurchaseLine.objects.create(
                        purchase=purchase,
                        product=product,
                        batch_number=ld['batch_number'],
                        quantity=ld['quantity'],
                        unit_cost=ld['unit_cost'],
                        expiry_date=ld['expiry_date'],
                        line_total=ld['line_total'],
                        batch=batch,
                    )

                    product.quantity = product.total_batch_quantity()
                    nearest = (
                        product.batches.filter(is_active=True, quantity__gt=0)
                        .order_by('expiry_date').values_list('expiry_date', flat=True).first()
                    )
                    if nearest:
                        product.expiry_date = nearest
                    product.save(update_fields=['quantity', 'expiry_date'])

                # Increase supplier payable by unpaid portion
                payable = (total - amount_paid_now).quantize(Decimal('0.01'))
                if payable > 0:
                    supplier.balance = (supplier.balance + payable).quantize(Decimal('0.01'))
                    supplier.save(update_fields=['balance', 'updated_at'])

                if amount_paid_now > 0:
                    SupplierPayment.objects.create(
                        supplier=supplier,
                        amount=amount_paid_now,
                        payment_method='cash',
                        purchase=purchase,
                        paid_by=request.user,
                        notes=f'Paid with invoice {invoice_number}',
                    )

            messages.success(
                request,
                f"Purchase {invoice_number} received. Total {CURRENCY_SYMBOL}{total}. "
                f"Supplier balance now {CURRENCY_SYMBOL}{supplier.balance}."
            )
            return redirect('supplier_purchase_list')
        except Exception as e:
            messages.error(request, f"Could not save purchase: {e}")

    return render(request, 'inventory/supplier_purchase_form.html', {
        'products': products,
        'suppliers': suppliers,
        'currency': CURRENCY_SYMBOL,
        'today': timezone.now().date().isoformat(),
    })


@admin_required
def supplier_purchase_detail(request, pk):
    purchase = get_object_or_404(
        SupplierPurchase.objects.select_related('supplier').prefetch_related('lines__product'),
        pk=pk
    )
    return render(request, 'inventory/supplier_purchase_detail.html', {
        'purchase': purchase,
        'currency': CURRENCY_SYMBOL,
    })


@admin_required
def supplier_pay(request, supplier_id):
    supplier = get_object_or_404(Supplier, pk=supplier_id)
    if request.method == 'POST':
        try:
            amount = Decimal(str(request.POST.get('amount', '0'))).quantize(Decimal('0.01'))
            method = request.POST.get('payment_method', 'cash')
            reference = (request.POST.get('reference') or '')[:64]
            notes = (request.POST.get('notes') or '')[:255]
            purchase_id = request.POST.get('purchase_id') or None

            if amount <= 0:
                raise ValueError('Amount must be greater than zero.')

            with transaction.atomic():
                supplier = Supplier.objects.select_for_update().get(pk=supplier_id)
                if amount > supplier.balance:
                    amount = supplier.balance
                if amount <= 0:
                    messages.info(request, 'No outstanding balance.')
                    return redirect('supplier_list')

                purchase = None
                if purchase_id:
                    purchase = SupplierPurchase.objects.select_for_update().filter(
                        pk=purchase_id, supplier=supplier
                    ).first()
                    if purchase:
                        apply = min(amount, purchase.amount_due)
                        purchase.amount_paid = (purchase.amount_paid + apply).quantize(Decimal('0.01'))
                        purchase.save(update_fields=['amount_paid', 'updated_at'])

                supplier.balance = (supplier.balance - amount).quantize(Decimal('0.01'))
                supplier.save(update_fields=['balance', 'updated_at'])

                SupplierPayment.objects.create(
                    supplier=supplier,
                    amount=amount,
                    payment_method=method if method in ('cash', 'bank', 'cheque', 'other') else 'cash',
                    reference=reference,
                    purchase=purchase,
                    paid_by=request.user,
                    notes=notes,
                )
            messages.success(
                request,
                f"Paid {CURRENCY_SYMBOL}{amount} to {supplier.name}. "
                f"Balance now {CURRENCY_SYMBOL}{supplier.balance}."
            )
            return redirect('supplier_list')
        except Exception as e:
            messages.error(request, f"Payment failed: {e}")

    open_purchases = SupplierPurchase.objects.filter(
        supplier=supplier, status=SupplierPurchase.STATUS_RECEIVED
    ).order_by('-invoice_date')
    payments = SupplierPayment.objects.filter(supplier=supplier)[:30]
    return render(request, 'inventory/supplier_pay.html', {
        'supplier': supplier,
        'open_purchases': open_purchases,
        'payments': payments,
        'currency': CURRENCY_SYMBOL,
    })


@admin_required
def reports_dashboard(request):
    """
    Commercial snapshot: today/week sales, estimated gross profit,
    stock valuation, customer receivables, supplier payables.
    """
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)

    sales_qs = Purchase.objects.all()
    sales_today = sales_qs.filter(purchase_date__date=today)
    sales_week = sales_qs.filter(purchase_date__date__gte=week_ago)

    def sum_field(qs, field):
        total = Decimal('0.00')
        for row in qs.values_list(field, flat=True):
            if row is not None:
                total += Decimal(row)
        return total.quantize(Decimal('0.01'))

    revenue_today = sum_field(sales_today, 'total_price')
    revenue_week = sum_field(sales_week, 'total_price')
    revenue_all = sum_field(sales_qs, 'total_price')
    collected_today = sum_field(sales_today, 'amount_paid')
    credit_today = sum_field(sales_today, 'amount_on_credit')

    # Estimated COGS from sale batch allocations when available
    cogs = Decimal('0.00')
    for alloc in SaleBatchAllocation.objects.select_related('batch').filter(
        sale__purchase_date__date__gte=week_ago
    ):
        cogs += (Decimal(alloc.quantity) * Decimal(alloc.batch.purchase_cost or 0))
    cogs = cogs.quantize(Decimal('0.01'))
    gross_profit_week = (revenue_week - cogs).quantize(Decimal('0.01'))

    # Stock valuation at selling price and at cost
    stock_sell = Decimal('0.00')
    stock_cost = Decimal('0.00')
    for b in ProductBatch.objects.filter(is_active=True, quantity__gt=0).select_related('product'):
        stock_cost += Decimal(b.quantity) * Decimal(b.purchase_cost or 0)
        stock_sell += Decimal(b.quantity) * Decimal(b.product.price or 0)
    # products without batches
    for prod in Product.objects.all():
        if not prod.batches.filter(is_active=True, quantity__gt=0).exists():
            stock_sell += Decimal(prod.quantity) * Decimal(prod.price or 0)

    stock_cost = stock_cost.quantize(Decimal('0.01'))
    stock_sell = stock_sell.quantize(Decimal('0.01'))

    receivables = sum(
        (Decimal(p.balance) for p in CustomerProfile.objects.filter(balance__gt=0)),
        Decimal('0.00')
    ).quantize(Decimal('0.01'))
    payables = sum(
        (Decimal(s.balance) for s in Supplier.objects.filter(balance__gt=0)),
        Decimal('0.00')
    ).quantize(Decimal('0.01'))

    low_stock = sum(1 for p in Product.objects.all() if p.is_low_stock)
    expired = Product.objects.filter(expiry_date__lt=today).count()
    expiring = Product.objects.filter(
        expiry_date__gte=today, expiry_date__lte=today + timedelta(days=7)
    ).count()

    return render(request, 'inventory/reports_dashboard.html', {
        'currency': CURRENCY_SYMBOL,
        'today': today,
        'revenue_today': revenue_today,
        'collected_today': collected_today,
        'credit_today': credit_today,
        'revenue_week': revenue_week,
        'revenue_all': revenue_all,
        'cogs_week': cogs,
        'gross_profit_week': gross_profit_week,
        'stock_cost': stock_cost,
        'stock_sell': stock_sell,
        'receivables': receivables,
        'payables': payables,
        'low_stock': low_stock,
        'expired': expired,
        'expiring': expiring,
        'sales_today_count': sales_today.count(),
    })


@admin_required
def backup_database(request):
    """
    Download a consistent SQLite backup using the backup API when possible.
    """
    db_path = FilePath(settings.DATABASES['default']['NAME'])
    if not db_path.exists():
        messages.error(request, "Database file not found.")
        return redirect('reports_dashboard')

    backup_dir = FilePath(settings.BASE_DIR) / 'backups'
    backup_dir.mkdir(exist_ok=True)
    stamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    backup_path = backup_dir / f'pharmacy_backup_{stamp}.sqlite3'

    try:
        import sqlite3
        src = sqlite3.connect(str(db_path))
        dst = sqlite3.connect(str(backup_path))
        with dst:
            src.backup(dst)
        dst.close()
        src.close()
    except Exception:
        # Fallback: file copy (app should be quiet)
        shutil.copy2(db_path, backup_path)

    # Also keep a copy as latest
    latest = backup_dir / 'latest.sqlite3'
    shutil.copy2(backup_path, latest)

    response = FileResponse(
        open(backup_path, 'rb'),
        as_attachment=True,
        filename=backup_path.name,
    )
    return response


@admin_required
def restore_database(request):
    """
    Upload a .sqlite3 backup. Creates a safety backup of current DB first.
    User must restart the server after restore for full consistency.
    """
    if request.method == 'POST' and request.FILES.get('backup_file'):
        upload = request.FILES['backup_file']
        if not upload.name.endswith(('.sqlite3', '.db', '.sqlite')):
            messages.error(request, "Please upload a .sqlite3 database file.")
            return redirect('restore_database')

        db_path = FilePath(settings.DATABASES['default']['NAME'])
        backup_dir = FilePath(settings.BASE_DIR) / 'backups'
        backup_dir.mkdir(exist_ok=True)
        safety = backup_dir / f'safety_before_restore_{timezone.now().strftime("%Y%m%d_%H%M%S")}.sqlite3'

        try:
            # Safety backup of current
            if db_path.exists():
                shutil.copy2(db_path, safety)

            # Write upload to temp then replace
            temp_path = backup_dir / 'upload_restore_temp.sqlite3'
            with open(temp_path, 'wb') as out:
                for chunk in upload.chunks():
                    out.write(chunk)

            # Basic integrity check
            import sqlite3
            conn = sqlite3.connect(str(temp_path))
            try:
                conn.execute('PRAGMA integrity_check').fetchone()
            finally:
                conn.close()

            shutil.copy2(temp_path, db_path)
            messages.success(
                request,
                f"Database restored from {upload.name}. "
                f"Safety copy saved as {safety.name}. "
                f"Please restart the application server."
            )
            return redirect('reports_dashboard')
        except Exception as e:
            messages.error(request, f"Restore failed: {e}")
            return redirect('restore_database')

    backup_dir = FilePath(settings.BASE_DIR) / 'backups'
    existing = []
    if backup_dir.exists():
        existing = sorted(backup_dir.glob('*.sqlite3'), key=lambda p: p.stat().st_mtime, reverse=True)[:20]

    return render(request, 'inventory/restore_database.html', {
        'existing_backups': existing,
    })


@admin_required
def daily_closing(request):
    """Simple daily closing summary for the selected date (default today)."""
    day_str = request.GET.get('date') or timezone.now().date().isoformat()
    try:
        day = date.fromisoformat(day_str)
    except ValueError:
        day = timezone.now().date()

    sales = Purchase.objects.filter(purchase_date__date=day)
    payments = CustomerPayment.objects.filter(created_at__date=day)
    supplier_pays = SupplierPayment.objects.filter(paid_at__date=day)
    returns = Return.objects.filter(processed_at__date=day, status='Approved')

    sales_total = sum((s.total_price for s in sales), Decimal('0.00'))
    cash_in = sum((s.amount_paid for s in sales), Decimal('0.00'))
    credit_new = sum((s.amount_on_credit for s in sales), Decimal('0.00'))
    udhaar_collected = sum((p.amount for p in payments), Decimal('0.00'))
    supplier_paid = sum((p.amount for p in supplier_pays), Decimal('0.00'))
    refunds = sum((r.refund_amount for r in returns if r.refund_method == 'cash'), Decimal('0.00'))

    net_cash = (cash_in + udhaar_collected - supplier_paid - refunds).quantize(Decimal('0.01'))

    return render(request, 'inventory/daily_closing.html', {
        'day': day,
        'sales': sales,
        'sales_total': sales_total.quantize(Decimal('0.01')),
        'cash_in': cash_in.quantize(Decimal('0.01')),
        'credit_new': credit_new.quantize(Decimal('0.01')),
        'udhaar_collected': udhaar_collected.quantize(Decimal('0.01')),
        'supplier_paid': supplier_paid.quantize(Decimal('0.01')),
        'refunds': refunds.quantize(Decimal('0.01')),
        'net_cash': net_cash,
        'returns': returns,
        'currency': CURRENCY_SYMBOL,
    })

def custom_404(request, exception=None):
    return render(request, 'inventory/404.html', status=404)


def custom_500(request):
    return render(request, 'inventory/500.html', status=500)
