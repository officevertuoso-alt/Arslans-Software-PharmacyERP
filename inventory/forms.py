from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Product, Supplier, Return


class SignUpForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name',
            'generic_name',
            'category',
            'quantity',
            'expiry_date',
            'price',
            'barcode_number',
            'units_per_pack',
            'allow_loose',
            'is_controlled',
            'requires_rx',
        ]
        # include optional fields only if model has them - listed ones exist after migrations


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = '__all__'


class ReturnForm(forms.ModelForm):
    class Meta:
        model = Return
        fields = ['product', 'sale', 'quantity', 'reason']
