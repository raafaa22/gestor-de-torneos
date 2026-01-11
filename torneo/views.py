from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def jugador_dashboard(request):
    return render(request, 'torneo/jugador_dashboard.html')

@login_required
def organizador_dashboard(request):
    return render(request, 'base.html')
