from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from .forms import RegisterForm, UserProfileForm, CustomPasswordChangeForm
from .services import setup_new_user_workspaces
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            setup_new_user_workspaces(user)
            login(request, user)
            return redirect('dashboard')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def request_password_reset_view(request):
    reset_url = None
    user_found = False

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        user = User.objects.filter(email__iexact=email).first()

        if user:
            user_found = True
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            # Monta a URL completa de redefinição
            path = reverse('password_reset_confirm_direct', kwargs={'uidb64': uid, 'token': token})
            reset_url = request.build_absolute_uri(path)
        else:
            user_found = False

    return render(request, 'accounts/password_reset_request.html', {
        'reset_url': reset_url,
        'user_found': user_found,
        'submitted': request.method == 'POST'
    })


@login_required
def profile_view(request):
    profile_form = UserProfileForm(instance=request.user)
    password_form = CustomPasswordChangeForm(user=request.user)

    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = UserProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Perfil atualizado com sucesso!")
                return redirect('profile')

        elif 'change_password' in request.POST:
            password_form = CustomPasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                # Mantém o usuário logado após trocar a senha
                update_session_auth_hash(request, user)
                messages.success(request, "Senha alterada com sucesso!")
                return redirect('profile')

    return render(request, 'accounts/profile.html', {
        'profile_form': profile_form,
        'password_form': password_form
    })