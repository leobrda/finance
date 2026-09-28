from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm, PasswordChangeForm
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


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none focus:bg-[#FFE600] font-bold uppercase',
                'placeholder': 'Seu primeiro nome'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none focus:bg-[#FFE600] font-bold uppercase',
                'placeholder': 'Seu sobrenome'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none focus:bg-[#FFE600] font-mono font-bold',
                'placeholder': 'seuemail@exemplo.com'
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Verifica se outro usuário já usa esse e-mail (excluindo o próprio usuário logado)
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Este e-mail já está em uso por outra conta.')
        return email


class CustomPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({
            'class': 'w-full border-2 border-black p-2.5 text-sm outline-none focus:bg-[#FFE600] font-mono font-bold',
            'placeholder': 'seuemail@exemplo.com'
        })

class CustomSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none focus:bg-[#FFE600] font-mono font-bold',
                'placeholder': '••••••••'
            })

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full border-2 border-black p-2.5 text-sm outline-none focus:bg-[#FFE600] font-mono font-bold',
                'placeholder': '••••••••'
            })