from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Workspace


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label='E-mail')
    first_name = forms.CharField(max_length=50, required=True, label='Nome')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'email')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Este e-mail já está cadastrado.')
        return email


class WorkspaceForm(forms.ModelForm):
    class Meta:
        model = Workspace
        fields = ['name', 'workspace_type']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none focus:bg-[#FFE600] font-bold uppercase',
                'placeholder': 'Ex: Loja de Celular, Barbearia...'
            }),
            'workspace_type': forms.Select(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none bg-white font-bold'
            }),
        }