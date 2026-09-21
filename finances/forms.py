from django import forms
from .models import Transaction, Category

class TransactionForm(forms.ModelForm):
    transaction_date = forms.DateField(
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={
                'type': 'date',
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none focus:bg-[#FFE600] font-mono'
            }
        )
    )

    class Meta:
        model = Transaction
        fields = ['description', 'amount', 'category', 'payment_method', 'status', 'transaction_date', 'notes']
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none focus:bg-[#FFE600] font-bold'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none focus:bg-[#FFE600] font-mono font-bold',
                'step': '0.01'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none bg-white font-bold'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none bg-white font-bold'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none bg-white font-bold'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none focus:bg-[#FFE600]',
                'rows': 2
            }),
        }

    def __init__(self, *args, **kwargs):
        workspace = kwargs.pop('workspace', None)
        super().__init__(*args, **kwargs)
        if workspace:
            self.fields['category'].queryset = Category.objects.filter(workspace=workspace)


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'category_type']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none focus:bg-[#FFE600] font-bold uppercase',
                'placeholder': 'Ex: Capinhas, Películas, Manutenção...'
            }),
            'category_type': forms.Select(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none bg-white font-bold'
            }),
        }