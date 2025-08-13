from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.conf import settings

from collections import defaultdict, OrderedDict

from deals.models import Store
from .forms import BusinessRequestForm
from .models import recommendation, Notification
#import user model
User = get_user_model()

import json

def index(request):
    notifications = Notification.objects.all()
    notifications = [n.to_dict() for n in notifications]
    return render(request, 'pages/index.html', {
        'page': 'index',
        'notifications': json.dumps(notifications)
    })


def privacy_policy(request):
    return render(request, 'pages/privacy_policy.html', {
        'page': 'privacy_policy',
        'email': settings.EMAIL_HOST_USER
    })

def general_terms(request):
    return render(request, 'pages/general_terms.html', {
        'page': 'general_terms',
        'email': settings.EMAIL_HOST_USER
    })

def contact(request):
    return render(request, 'pages/contact.html', {
        'page': 'contact',
        'email': settings.EMAIL_HOST_USER,
        'instagram': settings.INSTA_URL
    })

@csrf_exempt
def for_business(request):
    """
    Handles both GET and POST requests for the store request page.
    """
    if request.method == 'POST':
        try:
            # Decode the JSON data from the request body
            data = json.loads(request.body)
        except json.JSONDecodeError:
            # Return an error if the JSON is malformed
            return JsonResponse({'message': 'Invalid JSON data.'}, status=400)

        # Create a form instance with the submitted data
        form = BusinessRequestForm(data)

        # Validate the form
        if form.is_valid():
            # If the form is valid, save the new BusinessRequest instance
            form.save()
            return JsonResponse({'message': 'Bedankt! Uw verzoek is ontvangen.'}, status=200)
        else:
            # If the form is not valid, return the form errors
            return JsonResponse({'message': form.errors}, status=400)
    else:
        # For GET requests, render the page with the context
        return render(request, 'pages/request_store.html', {
            'page': 'request_store'
        })

def custom_404_view(request, exception):
    return render(request, '404.html', {}, status=404)

def custom_500_view(request):
    return render(request, '500.html', status=500)


def theme_designer(request):
    return render(request, 'pages/theme_v2.html', {
        'page': 'theme_designer'
    })


def all_stores(request):
    # Get all store names sorted alphabetically
    store_names = Store.objects.values_list('name', flat=True).order_by('name')

    # Group by first letter
    grouped_stores = defaultdict(list)
    for name in store_names:
        first_letter = name[0].upper()
        grouped_stores[first_letter].append(name)

    # Sort letters alphabetically
    grouped_stores = OrderedDict(sorted(grouped_stores.items()))

    return render(request, 'pages/all_stores.html', {
        'page': 'all_stores',
        'grouped_stores': grouped_stores
    })