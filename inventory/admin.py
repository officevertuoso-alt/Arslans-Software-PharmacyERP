from django.contrib import admin
from .models import Product, Purchase, Supplier, Return, CustomerProfile, CustomerPayment, ProductBatch, SaleBatchAllocation, SupplierPurchase, SupplierPurchaseLine, SupplierPayment


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'quantity', 'expiry_date', 'status', 'price')
    search_fields = ('name', 'category')


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('product', 'customer', 'quantity', 'total_price', 'amount_paid', 'amount_on_credit', 'payment_method', 'purchase_date')
    list_filter = ('purchase_date', 'payment_method', 'customer')
    search_fields = ('product__name', 'customer__username')


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone_number', 'balance', 'is_active')
    search_fields = ('name', 'contact_person')


@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
    list_display = ('product', 'customer', 'quantity', 'status', 'date_requested')
    list_filter = ('status', 'date_requested')


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'balance', 'credit_limit', 'updated_at')
    search_fields = ('user__username', 'phone')
    list_filter = ('updated_at',)


@admin.register(CustomerPayment)
class CustomerPaymentAdmin(admin.ModelAdmin):
    list_display = ('customer', 'amount', 'payment_method', 'received_by', 'created_at')
    list_filter = ('payment_method', 'created_at')
    search_fields = ('customer__username',)


@admin.register(ProductBatch)
class ProductBatchAdmin(admin.ModelAdmin):
    list_display = ('product', 'batch_number', 'quantity', 'expiry_date', 'purchase_cost', 'is_active', 'received_date')
    list_filter = ('is_active', 'expiry_date', 'product__category')
    search_fields = ('batch_number', 'product__name')
    raw_id_fields = ('product', 'supplier')


@admin.register(SaleBatchAllocation)
class SaleBatchAllocationAdmin(admin.ModelAdmin):
    list_display = ('sale', 'batch', 'quantity')
    raw_id_fields = ('sale', 'batch')


class SupplierPurchaseLineInline(admin.TabularInline):
    model = SupplierPurchaseLine
    extra = 0
    raw_id_fields = ('product', 'batch')


@admin.register(SupplierPurchase)
class SupplierPurchaseAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'supplier', 'invoice_date', 'total', 'amount_paid', 'status')
    list_filter = ('status', 'invoice_date')
    search_fields = ('invoice_number', 'supplier__name')
    inlines = [SupplierPurchaseLineInline]


@admin.register(SupplierPayment)
class SupplierPaymentAdmin(admin.ModelAdmin):
    list_display = ('supplier', 'amount', 'payment_method', 'paid_at', 'paid_by')
    list_filter = ('payment_method', 'paid_at')
