from django import forms
from .models import Transaction, Category

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['description', 'amount', 'category', 'transaction_date', 'notes']
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border-gray-300 border p-2.5 text-sm focus:ring-indigo-500 focus:border-indigo-500',
                'placeholder': 'Ex: Corte e Escova, Tintura...'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'w-full rounded-lg border-gray-300 border p-2.5 text-sm focus:ring-indigo-500 focus:border-indigo-500',
                'placeholder': '0.00',
                'step': '0.01'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full rounded-lg border-gray-300 border p-2.5 text-sm focus:ring-indigo-500 focus:border-indigo-500'
            }),
            'transaction_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full rounded-lg border-gray-300 border p-2.5 text-sm focus:ring-indigo-500 focus:border-indigo-500'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 2,
                'class': 'w-full rounded-lg border-gray-300 border p-2.5 text-sm focus:ring-indigo-500 focus:border-indigo-500',
                'placeholder': 'Detalhes adicionais (opcional)'
            }),
        }

    def __init__(self, *args, workspace=None, **kwargs):
        super().__init__(*args, **kwargs)
        if workspace:
            self.fields['category'].queryset = Category.objects.filter(workspace=workspace)