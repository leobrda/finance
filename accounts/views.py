from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from .forms import RegisterForm
from .services import setup_new_user_workspaces

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