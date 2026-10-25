from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Home page for customers
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup_view, name='signup'),


    # Admin-only product 
    path('products/', views.product_list, name='product_list'),
    path('expired/', views.expired_products, name='expired_products'),
    path('expiring-soon/', views.expiring_soon_products, name='expiring_soon'),
    path('low-stock/', views.low_stock_products, name='low_stock'),
    path('income-report/', views.income_report, name='income_report'),
    path('add/', views.product_create, name='product_add'),
    path('edit/<int:pk>/', views.product_update, name='product_edit'),
    path('delete/<int:pk>/', views.product_delete, name='product_delete'),
    path('barcode/<int:pk>/', views.view_barcode, name='view_barcode'),

    # Supplier management
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/add/', views.supplier_create, name='supplier_add'),
    path('suppliers/edit/<int:pk>/', views.supplier_update, name='supplier_edit'),
    path('suppliers/delete/<int:pk>/', views.supplier_delete, name='supplier_delete'),

    # Sales forecast
    path('sales-forecast/', views.sales_forecast, name='sales_forecast'),

    # Product returns
    path('request-return/', views.request_return, name='request_return'),
    path('manage-returns/', views.manage_returns, name='manage_returns'),
    path('process-return/<int:pk>/<str:status>/', views.process_return, name='process_return'),

    # Customer shop (optional, can be removed if home.html is the shop)
    path('shop/', views.customer_product_list, name='customer_product_list'),
    path('buy/<int:pk>/', views.purchase_product, name='purchase_product'),
    path('checkout/', views.checkout, name='checkout'),

    # Customer credit / udhaar
    path('my-ledger/', views.my_ledger, name='my_ledger'),
    path('customers/ledger/', views.customer_ledger_list, name='customer_ledger_list'),
    path('customers/ledger/<int:user_id>/', views.customer_ledger_detail, name='customer_ledger_detail'),

    # Batches / FEFO
    path('batches/', views.batch_list, name='batch_list'),
    path('batches/product/<int:product_id>/', views.batch_list, name='batch_list_product'),
    path('batches/receive/', views.receive_batch, name='receive_batch'),
    path('batches/receive/<int:product_id>/', views.receive_batch, name='receive_batch'),

    # Supplier purchases & payments
    path('supplier-purchases/', views.supplier_purchase_list, name='supplier_purchase_list'),
    path('supplier-purchases/add/', views.supplier_purchase_create, name='supplier_purchase_create'),
    path('supplier-purchases/<int:pk>/', views.supplier_purchase_detail, name='supplier_purchase_detail'),
    path('suppliers/<int:supplier_id>/pay/', views.supplier_pay, name='supplier_pay'),

    # Reports & backup
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/daily-closing/', views.daily_closing, name='daily_closing'),
    path('backup/', views.backup_database, name='backup_database'),
    path('restore/', views.restore_database, name='restore_database'),

    # Cashbook, charts, master catalog, notifications
    path('cashbook/', views.cashbook_list, name='cashbook_list'),
    path('charts/', views.charts_dashboard, name='charts_dashboard'),
    path('api/charts-data/', views.charts_data_api, name='charts_data_api'),
    path('medicine-master/', views.medicine_master_list, name='medicine_master_list'),
    path('medicine-master/suggest/', views.medicine_master_suggest, name='medicine_master_suggest'),
    path('medicine-master/export/', views.medicine_master_export, name='medicine_master_export'),
    path('medicine-master/import/', views.medicine_master_import, name='medicine_master_import'),
    path('medicine-master/preload/', views.preload_medicines_ui, name='preload_medicines_ui'),
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('api/notifications/', views.notifications_poll, name='notifications_poll'),
    path('notifications/refresh/', views.refresh_alerts, name='refresh_alerts'),

    path('api/customer-suggest/', views.customer_suggest, name='customer_suggest'),

    # Fast POS
    path('pos/', views.pos_screen, name='pos_screen'),
    path('pos/search/', views.pos_search, name='pos_search'),
    path('pos/alternates/', views.pos_alternates, name='pos_alternates'),
    path('pos/help/', views.pos_product_help, name='pos_product_help'),
    path('pos/master-to-product/', views.master_to_product, name='master_to_product'),
    path('pos/scan/', views.pos_scan, name='pos_scan'),
    path('pos/add/', views.pos_add, name='pos_add'),
    path('pos/qty/', views.pos_qty, name='pos_qty'),
    path('pos/remove/', views.pos_remove, name='pos_remove'),
    path('pos/clear/', views.pos_clear, name='pos_clear'),
    path('pos/pay/', views.pos_pay, name='pos_pay'),

    path('pos/hold/', views.pos_hold, name='pos_hold'),
    path('pos/recall/<int:idx>/', views.pos_recall, name='pos_recall'),
    path('receipt/<str:bill_number>/', views.receipt_view, name='receipt_view'),
    path('stock-adjust/', views.stock_adjust, name='stock_adjust'),

    path('shift/open/', views.shift_open, name='shift_open'),
    path('shift/close/', views.shift_close, name='shift_close'),

    path('customers/parties/', views.customer_party_list, name='customer_party_list'),
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/<str:bill_number>/void/', views.invoice_void, name='invoice_void'),
    path('supplier-returns/', views.supplier_return_list, name='supplier_return_list'),
    path('supplier-returns/add/', views.supplier_return_create, name='supplier_return_create'),
    path('purchase-orders/auto/', views.auto_purchase_order, name='auto_purchase_order'),
    path('purchase-orders/<int:pk>/', views.purchase_order_detail, name='purchase_order_detail'),
    path('reports/controlled/', views.controlled_register, name='controlled_register'),
    path('reports/pnl/', views.simple_pnl, name='simple_pnl'),
    path('audit/', views.audit_log_list, name='audit_log_list'),

    path('messaging/', views.messaging_center, name='messaging_center'),
]
