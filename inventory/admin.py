from django.contrib import admin
from .models import Product, Purchase, Supplier, Return, CustomerProfile, CustomerPayment, ProductBatch, SaleBatchAllocation, SupplierPurchase, SupplierPurchaseLine, SupplierPayment, CashbookEntry, MedicineMaster, AppNotification, CreditDue


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


@admin.register(CashbookEntry)
class CashbookEntryAdmin(admin.ModelAdmin):
    list_display = ('entry_date', 'entry_type', 'expense_category', 'amount', 'payment_channel', 'description')
    list_filter = ('entry_type', 'expense_category', 'entry_date')


@admin.register(MedicineMaster)
class MedicineMasterAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'brand_name', 'company', 'pack_size', 'current_mrp', 'legacy_retail_price')
    search_fields = ('product_name', 'brand_name', 'company')


@admin.register(AppNotification)
class AppNotificationAdmin(admin.ModelAdmin):
    list_display = ('kind', 'title', 'is_read', 'created_at')
    list_filter = ('kind', 'is_read')


@admin.register(CreditDue)
class CreditDueAdmin(admin.ModelAdmin):
    list_display = ('customer', 'amount', 'due_date', 'phone', 'is_settled')
    list_filter = ('is_settled', 'due_date')
