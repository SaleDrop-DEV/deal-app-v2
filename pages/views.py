from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.conf import settings


from collections import defaultdict, OrderedDict
import json
import os
import uuid

from deals.models import Store
from .forms import BusinessRequestForm, StaticContentForm
from .models import recommendation, Notification, StaticContent
#import user model
User = get_user_model()





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
    return render(request, 'pages/404.html', {}, status=404)

def custom_500_view(request):
    return render(request, 'pages/500.html', status=500)


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




@login_required
def static_content_manager(request):
    if request.user.is_superuser:
        if request.method == 'POST':
            form = StaticContentForm(request.POST, request.FILES)
            if form.is_valid():
                content: StaticContent = form.save(commit=False)
                if 'image_url' in request.FILES:
                    image = request.FILES['image_url']
                    ext = image.name.split('.')[-1].lower()
                    allowed_extensions = ['jpg', 'jpeg', 'png', 'gif']

                    if ext not in allowed_extensions:
                        return JsonResponse({'error': 'Invalid extension: Only JPG, JPEG, PNG and GIF are allowed.'}, status=400)
                    else:
                        # Define the directory where images will be saved
                        upload_dir = os.path.join(settings.MEDIA_ROOT, 'static_content')
                        os.makedirs(upload_dir, exist_ok=True)

                        filename = f"{uuid.uuid4()}.{ext}"
                        full_path = os.path.join(upload_dir, filename)

                        try:
                            with open(full_path, 'wb+') as destination:
                                for chunk in image.chunks():
                                    destination.write(chunk)
                            content.image_url = f"/media/static_content/{filename}"
                        except IOError as e:
                            return JsonResponse({'error': f'Error: {e}'}, status=405)
                content.save()
                return redirect('static_content_manager')
        else:
            static_content = StaticContent.objects.all()
            form = StaticContentForm()
        return render(request, 'admin_templates/static_content_manager.html', {'form': form, 'static_content': static_content, 'page': 'static-content-manager'})

    else:
        return redirect('account_view')


@login_required
def static_content_edit(request):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    if request.method == 'POST':
        content_id = request.POST.get('content_id')
        content = get_object_or_404(StaticContent, id=content_id)
        
        form = StaticContentForm(request.POST, request.FILES, instance=content)
        if form.is_valid():
            old_image_path = None
            if 'image_url' in request.FILES:
                old_image_path = content.image_url

            edited_content = form.save(commit=False)

            if 'image_url' in request.FILES:
                image = request.FILES['image_url']
                ext = image.name.split('.')[-1].lower()
                allowed_extensions = ['jpg', 'jpeg', 'png', 'gif']

                if ext not in allowed_extensions:
                    return JsonResponse({'error': 'Invalid extension'}, status=400)

                upload_dir = os.path.join(settings.MEDIA_ROOT, 'static_content')
                os.makedirs(upload_dir, exist_ok=True)
                filename = f"{uuid.uuid4()}.{ext}"
                full_path = os.path.join(upload_dir, filename)

                with open(full_path, 'wb+') as destination:
                    for chunk in image.chunks():
                        destination.write(chunk)
                edited_content.image_url = f"/media/static_content/{filename}"

                if old_image_path:
                    # remove leading slash if present
                    relative_path = old_image_path.lstrip('/').replace('media/', '', 1)
                    absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)
                    if os.path.exists(absolute_path):
                        os.remove(absolute_path)

            edited_content.save()
            return redirect('static_content_manager')
    return redirect('static_content_manager')

@login_required
def static_content_delete(request, content_id):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    content = get_object_or_404(StaticContent, id=content_id)
    content.delete()
    return redirect('static_content_manager')

