from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from .forms import UserRegisterForm, UserUpdateForm, CharacterCreateForm, \
    StatsCreateForm

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f"{username} has been created!")
            return redirect('login')
    else:
        form = UserRegisterForm()

    return render(request, 'users/register.html', {'form': form})


@login_required
def profile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        
        if "update-profile" in request.POST:
            if u_form.is_valid():
                u_form.save()
                messages.success(request, "Your account has been updated")
        elif "add-character" in request.POST:
            character_form = CharacterCreateForm()
            stats_form = StatsCreateForm()
            return render(request, 'users/character.html', 
                          {'character_form': character_form, "stats_form": stats_form})
    else:
        u_form = UserUpdateForm(instance=request.user)
    
    context = {
        'u_form': u_form
    }
    return render(request, 'users/profile.html', context)
