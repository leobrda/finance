from django import forms
from .models import Transaction, Category, MonthlyGoal, RecurringExpense


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'category_type']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none focus:bg-[#FFE600] font-bold uppercase',
                'placeholder': 'Ex: Alimentação, Serviços, Freelance...'
            }),
            'category_type': forms.Select(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none bg-white font-bold'
            }),
        }


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['description', 'amount', 'transaction_date', 'category', 'payment_method', 'status', 'notes']
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none focus:bg-[#FFE600] font-bold',
                'placeholder': 'Ex: Pagamento Fornecedor, Corte de Cabelo...'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm font-mono outline-none focus:bg-[#FFE600] font-bold',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'transaction_date': forms.DateInput(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none focus:bg-[#FFE600]',
                'type': 'date'
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
                'rows': 2,
                'placeholder': 'Observações adicionais...'
            }),
        }

    def __init__(self, *args, **kwargs):
        workspace = kwargs.pop('workspace', None)
        super().__init__(*args, **kwargs)
        if workspace:
            self.fields['category'].queryset = Category.objects.filter(workspace=workspace).order_by('category_type', 'name')
            self.fields['category'].empty_label = "Sem Categoria"


class MonthlyGoalForm(forms.ModelForm):
    class Meta:
        model = MonthlyGoal
        fields = ['revenue_goal', 'expense_limit']
        widgets = {
            'revenue_goal': forms.NumberInput(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none focus:bg-[#FFE600] font-mono font-bold',
                'step': '0.01',
                'placeholder': 'Ex: 8000.00'
            }),
            'expense_limit': forms.NumberInput(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none focus:bg-[#FFE600] font-mono font-bold',
                'step': '0.01',
                'placeholder': 'Ex: 3500.00'
            }),
        }


class RecurringExpenseForm(forms.ModelForm):
    class Meta:
        model = RecurringExpense
        fields = ['description', 'amount', 'due_day', 'category', 'payment_method', 'auto_pay', 'notes']
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none focus:bg-[#FFE600] font-bold uppercase',
                'placeholder': 'Ex: NETFLIX, SPOTIFY, INTERNET, ALUGUEL...'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm font-mono font-bold outline-none focus:bg-[#FFE600]',
                'step': '0.01',
                'placeholder': 'Ex: 55.90'
            }),
            'due_day': forms.NumberInput(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm font-mono font-bold outline-none focus:bg-[#FFE600]',
                'min': '1',
                'max': '31',
                'placeholder': 'Ex: 10'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none bg-white font-bold'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none bg-white font-bold'
            }),
            'auto_pay': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 border-2 border-black accent-[#FFE600] cursor-pointer'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none focus:bg-[#FFE600]',
                'rows': 2,
                'placeholder': 'Ex: Cartão Nubank final 1234'
            })
        }

    def __init__(self, *args, **kwargs):
        workspace = kwargs.pop('workspace', None)
        super().__init__(*args, **kwargs)
        if workspace:
            self.fields['category'].queryset = Category.objects.filter(workspace=workspace, category_type='EXPENSE').order_by('name')
            self.fields['category'].empty_label = "Selecione uma Categoria"
        # Define o valor inicial como marcado
        if 'auto_pay' in self.fields and self.instance.pk is None:
                self.fields['auto_pay'].initial = True