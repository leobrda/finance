from django.shortcuts import render, redirect
from django.contrib.auth import login
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