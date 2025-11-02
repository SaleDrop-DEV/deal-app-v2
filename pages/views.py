from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.utils import timezone

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
    search_stores_image = StaticContent.objects.get(content_name="Home: Zoek je favoriete winkels")
    example_sale_image = StaticContent.objects.get(content_name="Home: Voorbeeld sale")
    logo_name_image = StaticContent.objects.get(content_name="Logo + SaleDrop")
    appStoreImage = StaticContent.objects.get(content_name="Download In Appstore")

    sharingPhoto = StaticContent.objects.get(content_name="sharingPhoto")
    
    all_stores = list(Store.objects.all().values_list('name', flat=True).order_by('name'))
    premium_stores_count = len(all_stores)
    statCard = StaticContent.objects.get(content_name="statistiekKaart")

    # Distribute store names for the three marquees
    total_stores_for_marquee = len(all_stores)
    third = total_stores_for_marquee // 3
    other_stores_marquee = all_stores[:third]
    females_stores_marquee = all_stores[third:2*third]
    males_stores_marquee = all_stores[2*third:]

    return render(request, 'pages/index.html', {
        'page': 'index',
        'notifications': json.dumps(notifications),
        'search_stores_image': search_stores_image.to_dict(),
        'featured_stores': Store.objects.filter(isVerified=True).order_by('?')[:12], # Keep some featured stores for the old section if it's still used elsewhere or for fallback
        'other_stores_marquee': other_stores_marquee,
        'females_stores_marquee': females_stores_marquee,
        'males_stores_marquee': males_stores_marquee,
        'example_sale_image': example_sale_image.to_dict(),
        'appStoreImage': appStoreImage.to_dict(),
        'logo_name_image': logo_name_image.to_dict(),
        'premium_stores_count': premium_stores_count,
        'statCard': statCard,
        'sharingPhoto': sharingPhoto.to_dict()
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
    sharingPhoto = StaticContent.objects.get(content_name="sharingPhoto")
    return render(request, 'pages/contact.html', {
        'page': 'contact',
        'email': settings.EMAIL_HOST_USER,
        'instagram': settings.INSTA_URL,
        'sharingPhoto': sharingPhoto
    })

def delete_account_policy(request):
    return render(request, 'pages/delete_account_policy.html', {
        'page': 'delete_account_policy',
        'email': settings.EMAIL_HOST_USER
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
        # For GET requests, fetch the data needed for the 'trusted-by' section
        trusted_stores = Store.objects.filter(mayUseContent=True)
        stores_data = []
        for store in trusted_stores:
            data = {
                'id': store.id,
                'name': store.name,
                'image_url': store.image_url,
            }
            if store.name != "SaleDrop":
                stores_data.append(data)

        premium_stores_count = Store.objects.all().count()
        statCard = StaticContent.objects.get(content_name="statistiekKaart")

        # For GET requests, render the page with the context
        return render(request, 'pages/request_store.html', {
            'page': 'request_store',
            'trusted_stores': stores_data,
            'premium_stores_count': premium_stores_count,
            'statCard': statCard
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
            [print(c.required) for c in static_content]
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
        required = content.required
        
        form = StaticContentForm(request.POST, request.FILES, instance=content)
        if form.is_valid():
            old_image_path = None
            if 'image_url' in request.FILES:
                old_image_path = content.image_url

            # Prevent changing the name if the content is required
            if content.required and 'content_name' in request.POST and request.POST.get('content_name') != content.content_name:
                # You might want to add a message here to inform the user
                return redirect('static_content_manager')

            edited_content = form.save(commit=False)
            edited_content.required = required
            edited_content.date_modified = timezone.now()

            if 'image_url' in request.FILES:
                print("Image is updated")
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
                    # Handle absolute paths from the new image modal
                    if 'saledrop.app' in relative_path:
                        relative_path = relative_path.split('saledrop.app/media/', 1)[-1]

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

    # Prevent deletion if the content is marked as required
    if content.required:
        # You can add a Django message here to inform the admin
        return redirect('static_content_manager')

    content.delete()
    return redirect('static_content_manager')


import requests
import time # Needed for synchronous delay

# --- Configuration ---
EXPO_PUSH_URL = 'https://exp.host/--/api/v2/push/send'
EXPO_RECEIPTS_URL = 'https://exp.host/--/api/v2/push/getReceipts'
RECEIPT_CHECK_DELAY_SECONDS = 5 # Recommended minimum delay

@login_required
def test_notification(request):

    def send_batch_notifications(token, title, body, data):
        """
        Sends notifications to the Expo Push API and returns the ticket response.
        """
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        messages = [{'to': token, 'title': title, 'body': body, 'data': data}]
        
        try:
            response = requests.post(EXPO_PUSH_URL, json=messages, headers=headers)
            response.raise_for_status()
            return True, response.json()
        except requests.exceptions.RequestException as e:
            try:
                error_details = e.response.json()
            except (AttributeError, ValueError):
                error_details = {'detail': str(e)}
            return False, error_details


    def check_receipts(ticket_ids):
        """
        Polls the Expo API for the final receipt status.
        """
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        payload = {'ids': ticket_ids}

        try:
            # Wait a few seconds for Expo to process the tickets into receipts
            time.sleep(RECEIPT_CHECK_DELAY_SECONDS) 
            
            response = requests.post(EXPO_RECEIPTS_URL, json=payload, headers=headers)
            response.raise_for_status()
            return True, response.json()
        except requests.exceptions.RequestException as e:
            try:
                error_details = e.response.json()
            except (AttributeError, ValueError):
                error_details = {'detail': str(e)}
            return False, error_details


    if request.user.is_superuser:
        user = request.user
        try:
            push_token = user.extrauserinformation.expoToken
        except AttributeError:
            return JsonResponse({'error': 'User model or related object structure is incorrect.'}, status=500)
            
        if not push_token:
            return JsonResponse({'error': 'No push token found'}, status=400)
        
        
        # 1. SEND NOTIFICATION AND GET TICKET
        success, ticket_response = send_batch_notifications(
            token=push_token, 
            title="Test Notificatie", 
            body="Dit is een test notificatie van SaleDrop!", 
            data={"test": "data"}
        )
        
        if not success:
            return JsonResponse({'status': 'Ticket Request Failed', 'error_details': ticket_response}, status=500)

        
        # 2. EXTRACT TICKET ID(S)
        ticket_ids = []
        for ticket in ticket_response.get('data', []):
            if ticket.get('status') == 'ok' and 'id' in ticket:
                ticket_ids.append(ticket['id'])

        if not ticket_ids:
             # This means the ticket request succeeded but all tickets immediately failed (status: error)
             return JsonResponse({'status': 'Tickets sent but all failed immediately', 'tickets': ticket_response['data']}, status=500)


        # 3. CHECK RECEIPT STATUS
        receipt_success, receipt_response = check_receipts(ticket_ids)

        if not receipt_success:
            return JsonResponse({'status': 'Receipt Check Failed', 'error_details': receipt_response}, status=500)
            
        
        # 4. PARSE AND RETURN FINAL RESULT
        
        # Extract the detailed receipt for the single token we sent
        receipt_details = receipt_response.get('data', {}).get(ticket_ids[0]) if ticket_ids else None
        
        if receipt_details and receipt_details.get('status') == 'error':
            # This is the crucial information! The error from Apple.
            return JsonResponse({
                'status': 'Final Receipt Error', 
                'token': push_token,
                'receipt': receipt_details,
                'message': f"Notification failed delivery to APNs. Reason: {receipt_details.get('details', {}).get('error', 'Unknown Error')}"
            }, status=200)

        return JsonResponse({
            'status': 'Notification Check Complete', 
            'token': push_token,
            'ticket_id': ticket_ids[0] if ticket_ids else 'N/A',
            'receipt_status': receipt_details.get('status') if receipt_details else 'Pending/Unknown',
            'full_receipt': receipt_details,
            'advice': 'If receipt status is "ok" but the notification was not received on the App Store version, the problem is usually a local device issue (settings, connectivity) or a race condition where the token was invalid at the moment of send, or a build/entitlement mismatch on the device itself.'
        })

    else:
        return JsonResponse({'error': 'Forbidden'}, status=403)



def apple_app_site_association(request):
    data = {
        "applinks": {
            "apps": [],
            "details": [
                {
                    "appID": "TSUTXHU596.com.SaleDrop.SaleDrop",
                    # Add paths you want your app to handle
                    "paths": []
                }
            ]
        },
        "webcredentials": {
            "apps": ["TSUTXHU596.com.SaleDrop.SaleDrop"]
        }
    }
    return JsonResponse(data)


