from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.conf import settings
from urllib.parse import urlparse
from django.db.models import Q
from django.http import JsonResponse, JsonResponse, HttpResponseBadRequest, HttpResponse, Http404
from django.shortcuts import render, redirect
from django.core.serializers.json import DjangoJSONEncoder
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib.auth import get_user_model

import os
import base64
import uuid
import json
import tldextract
import time
from datetime import timedelta


from api.models import API_Errors_Site
from deals.models import GmailSaleAnalysis, Store, SubscriptionData, GmailMessage, Url, ScrapeData
from .forms import StoreForm
from .tasks import fetch_and_process_gmail_messages_task_general, fetch_and_process_gmail_messages_task_female

User = get_user_model()

def get_store_logo(store_name):
    """
    Returns the URL for a placeholder logo based on the store name.
    """
    if not store_name:
        return '/static/store_logos/placeholders/@.png'  # Generic fallback

    first_char = store_name[0].upper()
    if 'A' <= first_char <= 'Z':
        return f'/static/store_logos/placeholders/{first_char}.png'
    else:
        return '/static/store_logos/placeholders/@.png'

def parse_date_received(date_received):
    now = timezone.now()
    delta = now - date_received

    if delta.total_seconds() < 60:
        seconds = int(delta.total_seconds())
        return f"{seconds} seconde{'n' if seconds > 1 else ''} geleden"
    elif delta.total_seconds() < 3600:
        minutes = int(delta.total_seconds() / 60)
        return f"{minutes} minuut{'en' if minutes > 1 else ''} geleden"
    elif delta.total_seconds() < 86400:
        hours = int(delta.total_seconds() / 3600)
        return f"{hours} uur geleden"
    else:
        # Fallback for days or longer
        days = int(delta.total_seconds() / 86400)
        return f"{days} dag{'en' if days > 1 else ''} geleden"

def get_sale_page_url(store:Store, url:str):
    client_url = None
    if Url.objects.filter(url_ctrk=url.strip()).exists():
        client_url = Url.objects.get(url_ctrk=url).general_url
    if not client_url:
        client_url = store.sale_url if store.sale_url else store.home_url
    return client_url

# Deals display views
@login_required
def public_deals_view(request, sales_per_page=9):
    three_months_ago = timezone.now() - timedelta(days=90)
    user = request.user

    # The gender value should be an integer (0, 1, or 2)
    gender_of_user = getattr(user.extrauserinformation, 'gender', None)

    # Base query to filter for valid deals
    # We combine all non-gender-specific filters here for clarity and robustness
    base_filters = Q(
        is_sale_mail=True,
        is_personal_deal=False,
        deal_probability__gt=0.925,
        message__received_date__gt=three_months_ago,
        message__store__isnull=False  # This is the key change to ensure stores exist
    )

    if gender_of_user == 0:
        # User is male: want deals from stores with male email preference OR no preference
        gender_filters = Q(message__email_to="gijsgprojects@gmail.com") | Q(message__store__genderPreferenceSet=False)
    elif gender_of_user == 1:
        # User is female: want deals from stores with female email preference OR no preference
        gender_filters = Q(message__email_to="donnapatrona79@gmail.com") | Q(message__store__genderPreferenceSet=False)
    elif gender_of_user == 2:
        # User is non-binary: all deals with stores are relevant
        gender_filters = Q() # An empty Q object matches everything
    else:
        # Default or invalid gender: apply no gender-specific filtering
        gender_filters = Q() 

    # Combine all filters to create the final queryset
    analyses = GmailSaleAnalysis.objects.filter(base_filters & gender_filters).order_by('-message__received_date')

    # --- GET and POST logic remain the same, but use the new analyses queryset ---

    if request.method == 'GET':
        paginator = Paginator(analyses, sales_per_page)
        page_number = request.GET.get('page', 1)

        try:
            page_number = int(page_number)
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
            page_number = 1
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
            page_number = paginator.num_pages

        data = []
        for analysis in page_obj:
            deal = analysis.to_dict()
            data_deal = {
                'title': deal['title'],
                'grabber': deal['grabber'],
                'description': deal['description'],
                'main_link': f"/deals/visit/{analysis.id}/{request.user.id}/",
                'highlighted_products': None,#deal['highlighted_products'] if deal['store']['mayUseContent'] else None,
                'store': {
                    'name': deal['store']['name'],
                    'image_url': deal['store']['image_url'] if deal['store']['mayUseContent'] else get_store_logo(deal['store']['name']),
                },
                'date_received': deal['gmail_data']['received_date'],
                'parsed_date_received': parse_date_received(analysis.message.received_date),
            }
            data_deal['deal_json'] = json.dumps(data_deal, cls=DjangoJSONEncoder)
            data.append(data_deal)

        return render(request, 'deals/deals.html', {
            'title': "Bekijk alle deals",
            'deals': data,
            'page': 'public-deals',
            'url': 'public',
            'page_obj': page_obj,
            'has_next_page': page_obj.has_next(),
            'has_previous_page': page_obj.has_previous(),
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
        })
    
    elif request.method == 'POST':
        paginator = Paginator(analyses, sales_per_page)

        data = json.loads(request.body)
        page_number = data.get('page')

        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
            page_number = 1
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
            page_number = paginator.num_pages

        data = []
        for analysis in page_obj:
            deal = analysis.to_dict()
            data_deal = {
                'title': deal['title'],
                'grabber': deal['grabber'],
                'description': deal['description'],
                'main_link': f"/deals/{analysis.id}/{request.user.id}/",
                'highlighted_products': None,#deal['highlighted_products'] if deal['store']['mayUseContent'] else None,
                'store': {
                    'name': deal['store']['name'],
                    'image_url': deal['store']['image_url'] if deal['store']['mayUseContent'] else get_store_logo(deal['store']['name']),
                },
                'date_received': deal['gmail_data']['received_date'],
                'parsed_date_received': parse_date_received(analysis.message.received_date),
            }
            data_deal['deal_json'] = json.dumps(data_deal, cls=DjangoJSONEncoder)
            data.append(data_deal)

        return JsonResponse({
            'deals': data,
            'has_next_page': page_obj.has_next(),
        })

@login_required
def client_deals_view(request, sales_per_page=9):
    user = request.user
    three_months_ago = timezone.now() - timedelta(days=90)
    
    # Get the stores the user is subscribed to
    subscribed_stores = Store.objects.filter(subscriptions=user)
    
    # The gender value should be an integer (0, 1, or 2)
    gender_of_user = getattr(user.extrauserinformation, 'gender', None)

    # Base query to filter for valid deals, including subscribed stores and null check
    base_filters = Q(
        is_sale_mail=True,
        is_personal_deal=False,
        deal_probability__gt=0.925,
        message__received_date__gt=three_months_ago,
        message__store__isnull=False,  # Ensure store exists
        message__store__in=subscribed_stores # Ensure store is in the user's subscriptions
    )

    if gender_of_user == 0:
        # User is male
        gender_filters = Q(message__email_to="gijsgprojects@gmail.com") | Q(message__store__genderPreferenceSet=False)
    elif gender_of_user == 1:
        # User is female
        gender_filters = Q(message__email_to="donnapatrona79@gmail.com") | Q(message__store__genderPreferenceSet=False)
    elif gender_of_user == 2:
        # User is non-binary
        gender_filters = Q() # An empty Q object matches everything
    else:
        # Default or invalid gender: apply no gender-specific filtering
        gender_filters = Q()

    # Combine all filters to create the final queryset
    analyses = GmailSaleAnalysis.objects.filter(base_filters & gender_filters).select_related('message').order_by('-message__received_date')

    if request.method == 'GET':
        paginator = Paginator(analyses, sales_per_page)
        page_number = request.GET.get('page', 1)

        try:
            page_number = int(page_number)
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
            page_number = 1
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
            page_number = paginator.num_pages

        data = []
        for analysis in page_obj:
            try:
                deal = analysis.to_dict()
                data_deal = {
                    'title': deal['title'],
                    'grabber': deal['grabber'],
                    'description': deal['description'],
                    'main_link': f"/deals/visit/{analysis.id}/{request.user.id}/",
                    'highlighted_products': None,#deal['highlighted_products'] if deal['store']['mayUseContent'] else None,
                    'store': {
                        'name': deal['store']['name'],
                        'image_url': deal['store']['image_url'] if deal['store']['mayUseContent'] else get_store_logo(deal['store']['name']),
                    },
                    'date_received': deal['gmail_data']['received_date'],
                    'parsed_date_received': parse_date_received(analysis.message.received_date),
                }
                data_deal['deal_json'] = json.dumps(data_deal, cls=DjangoJSONEncoder)
                data.append(data_deal)
            except:
                print(f"store={deal['store']}")
                raise ValueError("error")

        return render(request, 'deals/deals.html', {
            'title': "Mijn sales",
            'deals': data,
            'page': 'client-deals',
            'url': 'my-sales',
            'page_obj': page_obj,
            'has_next_page': page_obj.has_next(),
            'has_previous_page': page_obj.has_previous(),
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
        })
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            page_number = data.get('page', 1)
        except Exception:
            page_number = 1

        paginator = Paginator(analyses, sales_per_page)

        try:
            page_number = int(page_number)
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        deals_data = []
        for analysis in page_obj:
            deal = analysis.to_dict()
            data_deal = {
                'title': deal['title'],
                'grabber': deal['grabber'],
                'description': deal['description'],
                'main_link': f"/deals/visit/{analysis.id}/{request.user.id}/",
                'highlighted_products': None,#deal['highlighted_products'] if deal['store']['mayUseContent'] else None,
                'store': {
                    'name': deal['store']['name'],
                    'image_url': deal['store']['image_url'] if deal['store']['mayUseContent'] else get_store_logo(deal['store']['name']),
                },
                'date_received': deal['gmail_data']['received_date'],
                'parsed_date_received': parse_date_received(analysis.message.received_date),
            }
            data_deal['deal_json'] = json.dumps(data_deal, cls=DjangoJSONEncoder)
            deals_data.append(data_deal)

        return JsonResponse({
            'deals': deals_data,
            'has_next_page': page_obj.has_next(),
        })


#admin#
@login_required
def all_deals_view(request, sales_per_page=9):
    if not request.user.is_superuser:
        return redirect('public_deals')
    if request.method == 'GET':
        analyses = GmailSaleAnalysis.objects.filter(
            is_sale_mail=True
        ).order_by('-message__received_date')

        paginator = Paginator(analyses, sales_per_page)

        page_number = request.GET.get('page', 1)

        try:
            page_number = int(page_number)
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
            page_number = 1
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
            page_number = paginator.num_pages

        data = []
        for analysis in page_obj:
            deal = analysis.to_dict()
            deal['personal'] = analysis.is_personal_deal
            deal['main_link'] = f"/deals/visit/{analysis.id}/{request.user.id}/"
            deal['deal_json'] = json.dumps(deal, cls=DjangoJSONEncoder)
            deal['date_received'] = deal['gmail_data']['received_date']
            deal['parsed_date_received'] = parse_date_received(analysis.message.received_date)

            data.append(deal)

        return render(request, 'deals/deals.html', {
            'title': "Alle deals",
            'deals': data,
            'page': 'all-deals',
            'url': 'all',
            'page_obj': page_obj,
            'has_next_page': page_obj.has_next(),
            'has_previous_page': page_obj.has_previous(),
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
        })

    else:
        try:
            data = json.loads(request.body)
            page_number = data.get('page', 1)
        except Exception:
            page_number = 1

        analyses = GmailSaleAnalysis.objects.filter(
            is_sale_mail=True
        ).order_by('-message__received_date')

        paginator = Paginator(analyses, sales_per_page)

        try:
            page_number = int(page_number)
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        data = []
        for analysis in page_obj:
            deal = analysis.to_dict()
            deal['main_link'] = f"/deals/visit/{analysis.id}/{request.user.id}/"
            deal['personal'] = analysis.is_personal_deal
            deal['deal_json'] = json.dumps(deal, cls=DjangoJSONEncoder)
            deal['date_received'] = deal['gmail_data']['received_date']
            deal['parsed_date_received'] = parse_date_received(analysis.message.received_date)

            data.append(deal)

        return JsonResponse({
            'deals': data,
            'has_next_page': page_obj.has_next(),
        })

#admin#
@login_required
def personal_deals_view(request, sales_per_page=9):
    if not request.user.is_superuser:
        return redirect('client_deals')
    if request.method == 'GET':
        analyses = GmailSaleAnalysis.objects.filter(
            is_sale_mail=True,
            is_personal_deal=True
        ).order_by('-message__received_date')

        paginator = Paginator(analyses, sales_per_page)

        page_number = request.GET.get('page', 1)

        try:
            page_number = int(page_number)
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
            page_number = 1
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
            page_number = paginator.num_pages

        data = []
        for analysis in page_obj:
            deal = analysis.to_dict()
            deal['main_link'] = f"/deals/visit/{analysis.id}/{request.user.id}/"
            deal['personal'] = analysis.is_personal_deal
            deal['deal_json'] = json.dumps(deal, cls=DjangoJSONEncoder)
            deal['date_received'] = deal['gmail_data']['received_date']
            deal['parsed_date_received'] = parse_date_received(analysis.message.received_date)

            data.append(deal)

        return render(request, 'deals/deals.html', {
            'title': "Persoonlijke sales",
            'deals': data,
            'page': 'personal-deals',
            'url': 'personal',
            'page_obj': page_obj,
            'has_next_page': page_obj.has_next(),
            'has_previous_page': page_obj.has_previous(),
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
        })
    else:
        try:
            data = json.loads(request.body)
            page_number = data.get('page', 1)
        except Exception:
            page_number = 1

        analyses = GmailSaleAnalysis.objects.filter(
            is_sale_mail=True,
            is_personal_deal=True
        ).order_by('-message__received_date')

        paginator = Paginator(analyses, sales_per_page)

        try:
            page_number = int(page_number)
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        data = []
        for analysis in page_obj:
            deal = analysis.to_dict()
            deal['main_link'] = f"/deals/visit/{analysis.id}/{request.user.id}/"
            deal['personal'] = analysis.is_personal_deal
            deal['deal_json'] = json.dumps(deal, cls=DjangoJSONEncoder)
            deal['date_received'] = deal['gmail_data']['received_date']
            deal['parsed_date_received'] = parse_date_received(analysis.message.received_date)

            data.append(deal)

        return JsonResponse({
            'deals': data,
            'has_next_page': page_obj.has_next(),
        })


# HELPER FUNCTIONS #
def extract_domain_parts_websitedomain(url):
    """
    Returns a tuple:
    (full_domain, registered_domain, domain_root)
    
    e.g., for 'http://news.example.com/nl':
    -> ('news.example.com', 'example.com', 'example')
    """
    try:
        parsed_url = urlparse(url)
        full_domain = parsed_url.netloc or parsed_url.path
        if full_domain.startswith("www."):
            full_domain = full_domain[4:]

        extracted = tldextract.extract(full_domain)
        registered_domain = f"{extracted.domain}.{extracted.suffix}" if extracted.suffix else extracted.domain
        domain_root = extracted.domain

        return full_domain.strip(), registered_domain.strip(), domain_root.strip()
    except Exception:
        return '', '', ''

def extract_domain_parts_email(email):
    """
    Returns a tuple:
    (full_domain, registered_domain, domain_root)

    e.g., for 'info@mail.example.co.uk':
    -> ('mail.example.co.uk', 'example.co.uk', 'example')
    """
    try:
        # Get domain from email
        full_domain = email.split('@')[-1].strip()
        if full_domain.startswith("www."):
            full_domain = full_domain[4:]

        extracted = tldextract.extract(full_domain)
        registered_domain = f"{extracted.domain}.{extracted.suffix}" if extracted.suffix else extracted.domain
        domain_root = extracted.domain

        return full_domain.strip(), registered_domain.strip(), domain_root.strip()
    except Exception:
        return '', '', ''


# Admin Views #
@login_required
def stores_manager_view(request):
    """
    Display all stores and handle POST requests for adding a new store.
    """
    if not request.user.is_superuser:
        return redirect('account_view')
    if request.method == 'POST':
        try:
            form = StoreForm(request.POST, request.FILES)
            if form.is_valid():
                store: Store = form.save(commit=False)

                if 'image_url' in request.FILES:
                    image = request.FILES['image_url']
                    ext = image.name.split('.')[-1].lower()
                    allowed_extensions = ['jpg', 'jpeg', 'png', 'gif']

                    if ext not in allowed_extensions:
                        return JsonResponse({'error': 'Ongeldig afbeeldingsbestand. Alleen JPG, JPEG, PNG en GIF zijn toegestaan.'}, status=400)
                    else:
                        # Define the directory where images will be saved
                        upload_dir = os.path.join(settings.MEDIA_ROOT, 'store_logos')
                        os.makedirs(upload_dir, exist_ok=True)

                        filename = f"{uuid.uuid4()}.{ext}"
                        full_path = os.path.join(upload_dir, filename)

                        try:
                            with open(full_path, 'wb+') as destination:
                                for chunk in image.chunks():
                                    destination.write(chunk)
                            store.image_url = os.path.join(settings.MEDIA_URL, 'media', 'store_logos', filename)
                        except IOError as e:
                            return JsonResponse({'error': f'Foutmelding bij opslaan van afbeelding: {e}'}, status=405)
                else:
                    return JsonResponse({'error': 'Voer een geldige afbeelding in.'}, status=400)
                full_domain, registered_domain, domain_root = extract_domain_parts_websitedomain(store.home_url)
                store.domain = registered_domain
                store.domain_list = [registered_domain, full_domain, domain_root]

                domain_set = set(store.domain_list)

                for email in store.email_addresses.split(','):
                    email_full_domain, email_registered_domain, email_domain_root = extract_domain_parts_email(email=email)
                    if (email_full_domain, email_registered_domain, email_domain_root) == ('', '', ''):
                        continue
                    # Check if the domains are not in the set before adding them
                    if email_full_domain not in domain_set:
                        store.domain_list.append(email_full_domain)
                        domain_set.add(email_full_domain)
                        
                    if email_registered_domain not in domain_set:
                        store.domain_list.append(email_registered_domain)
                        domain_set.add(email_registered_domain)

                    if email_domain_root not in domain_set:
                        store.domain_list.append(email_domain_root)
                        domain_set.add(email_domain_root)

                new_domain_list = [d.lower() for d in list(domain_set)]
                store.domain_list = new_domain_list

                store.save()
                return JsonResponse({'success': True, 'message' : 'Winkel toegevoegd!'})
            else:
                return JsonResponse({'error': 'Fout bij het toevoegen van de winkel. Controleer de formuliervelden.', 'message': form.errors.as_json()}, status=400)
        except Exception as e:
            return JsonResponse({'error': e}, status=502)
    else:
        form = StoreForm()

    all_stores = [s.to_dict() for s in Store.objects.all()]
    return render(request, 'deals_old/stores.html', {
        'stores': all_stores,
        'form': form,
        'page': 'store-manager'
    })

@login_required
def delete_store_view(request, store_id):
    store = get_object_or_404(Store, id=store_id)
    store.delete()
    return JsonResponse({'success': True, 'message': 'Store deleted successfully'})

@login_required
def edit_store_view(request, store_id):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'U heeft geen toegang tot deze functie.'}, status=403)
    
    store = get_object_or_404(Store, id=store_id)

    if request.method == 'POST':
        form = StoreForm(request.POST, request.FILES, instance=store)

        if form.is_valid():
            old_image_path = store.image_url if 'image_url' in request.FILES else None
            store: Store = form.save(commit=False)

            # Normalize and extract domain parts from home_url
            domain_set = set()
            new_domain_list = []

            if store.home_url:
                full_domain, registered_domain, domain_root = extract_domain_parts_websitedomain(store.home_url.strip())
                for d in [registered_domain, full_domain, domain_root]:
                    if d and d not in domain_set:
                        new_domain_list.append(d)
                        domain_set.add(d)
                store.domain = registered_domain  # Set primary domain

            # Normalize and extract from email addresses
            if store.email_addresses:
                for email in store.email_addresses.split(','):
                    email = email.strip()
                    email_full_domain, email_registered_domain, email_domain_root = extract_domain_parts_email(email)
                    for d in [email_full_domain, email_registered_domain, email_domain_root]:
                        if d and d not in domain_set:
                            new_domain_list.append(d)
                            domain_set.add(d)

            new_domain_list = [d.lower() for d in new_domain_list]

            store.domain_list = new_domain_list

            # Handle image upload
            if 'image_url' in request.FILES:
                image = request.FILES['image_url']
                ext = image.name.split('.')[-1].lower()
                allowed_extensions = ['jpg', 'jpeg', 'png', 'gif']

                if ext not in allowed_extensions:
                    return JsonResponse({'error': 'Ongeldig afbeeldingsbestand. Alleen JPG, JPEG, PNG en GIF zijn toegestaan.'}, status=400)

                upload_dir = os.path.join(settings.MEDIA_ROOT, 'media', 'store_logos')
                os.makedirs(upload_dir, exist_ok=True)
                filename = f"{uuid.uuid4()}.{ext}"
                full_path = os.path.join(upload_dir, filename)

                try:
                    with open(full_path, 'wb+') as destination:
                        for chunk in image.chunks():
                            destination.write(chunk)
                    store.image_url = os.path.join(settings.MEDIA_URL, 'store_logos', filename)
                except IOError as e:
                    return JsonResponse({'error': f'Foutmelding bij opslaan van afbeelding: {e}'}, status=500)

                # Delete old image if exists
                if old_image_path:
                    old_absolute_path = os.path.join(settings.BASE_DIR, old_image_path.lstrip('/'))
                    if os.path.exists(old_absolute_path):
                        try:
                            os.remove(old_absolute_path)
                        except OSError as e:
                            print(f"Error deleting old image file {old_absolute_path}: {e}")

            store.save()
            return JsonResponse({'success': True, 'message': 'Winkel succesvol bijgewerkt!'})
        else:
            return JsonResponse({'error': 'Fout bij het bijwerken van de winkel. Controleer de formuliervelden.', 'message': form.errors.as_json()}, status=400)

    return JsonResponse({'error': 'Ongeldige aanvraagmethode.'}, status=405)


#Store views
def stores_view(request):
    if request.user.is_authenticated:
        all_stores = Store.objects.all().order_by('name')
        try:
            subscription_obj = request.user.subscription_data
            current_subscriptions = subscription_obj.stores
        except SubscriptionData.DoesNotExist:
            current_subscriptions = []
        except Exception as e:
            raise ValueError(f"Error fetching subscription data: {e}")
        stores_with_subscription_status = []
        extra_info = request.user.extrauserinformation
        for store in all_stores:
            is_subscribed = store.is_subscribed(request.user)
            if is_subscribed:
                stores_with_subscription_status.append({
                    'id': store.id,
                    'name': store.name,
                    'domain': store.domain,
                    'home_url': store.home_url,
                    'sale_url': store.sale_url,
                    'image_url': store.image_url if store.mayUseContent else get_store_logo(store.name),
                    'is_subscribed': is_subscribed,
                })
        return render(request, 'deals/subscribed_stores.html', {
            'stores': stores_with_subscription_status,
            'page': 'subscribed_stores',
            'gender': extra_info.gender
        })
    else:
        return redirect('account_login')

@login_required
def toggle_subscription(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            store_id = data.get('store_id', '')

            if not store_id:
                return JsonResponse({'error': 'Geen winkel-ID opgegeven.'}, status=400)

            try:
                store_id = int(store_id)
                store = Store.objects.get(id=store_id)
                if store == None:
                    return JsonResponse({'error': 'Winkel niet gevonden.'}, status=404)
            except ValueError:
                return JsonResponse({'error': 'Ongeldige winkel-ID.'}, status=400)

            user = request.user

            if store.is_subscribed(user):
                # Unsubscribe
                store.remove_subscriber(user)
                message = 'Succesvol afgemeld.'
                subscribed = False
            else:
                # Subscribe
                store.add_subscriber(user)
                message = 'Geabboneerd!'
                subscribed = True

            return JsonResponse({
                'success': True,
                'message': message,
                'store_name': store.name,
                'store_id': store.id,
                'is_subscribed': subscribed,
                'image_url': store.image_url if store.mayUseContent else get_store_logo(store.name)
            })

        except Store.DoesNotExist:
            return JsonResponse({'error': 'Winkel niet gevonden.'}, status=404)
        except Exception as e:
            API_Errors_Site.objects.create(
                task="Toggle subscription",
                error=str(e)
            )
            return JsonResponse({'error': "Er ging iets mis."}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)




def visit_sale_view(request, gmail_analysis_id, user_id):
    user = get_object_or_404(User, id=user_id)
    gmail_message: GmailSaleAnalysis = get_object_or_404(GmailSaleAnalysis, id=gmail_analysis_id)
    if gmail_message.message.store and gmail_message.main_link:
        redirect_url = get_sale_page_url(gmail_message.message.store, gmail_message.main_link)
        if Url.objects.filter(url_ctrk=redirect_url).exists():
            Url.objects.get(url_ctrk=redirect_url).add_visit(user=user)
        return redirect(redirect_url)
    else:
        return Http404()


# Gmail webhook #
@csrf_exempt # Ensure this is the first decorator
@require_POST # Only allow POST requests
def gmail_webhook(request):
    """
    Receives push notifications from Google Cloud Pub/Sub for Gmail events.
    """
    try:
        # Pub/Sub sends notifications as a JSON payload in the request body
        # The actual message content is base64 encoded within the 'message' field
        data = json.loads(request.body)
        pubsub_message = data['message']

        # Decode the base64 encoded data from the Pub/Sub message
        # This data contains the email address of the user whose mailbox changed
        message_data_b64 = pubsub_message['data']
        message_data_decoded = base64.b64decode(message_data_b64).decode('utf-8')
        message_json = json.loads(message_data_decoded)

        user_email = message_json.get('emailAddress')
        messageId = pubsub_message['message_id']
        if user_email.lower().strip() == "gijsgprojects@gmail.com":
            print("MALE/GENERAL incoming email")
            fetch_and_process_gmail_messages_task_general.delay()
        elif user_email.lower().strip() == "donnapatrona79@gmail.com":
            print("FEMALE incoming email")
            fetch_and_process_gmail_messages_task_female.delay()
        else:
            print("ERROR: No matching email found")
            ScrapeData.objects.create(
                task = "Receiving gmail webhook",
                succes = False,
                major_error = True,
                error = "No matching email found",
                execution_date = timezone.now(),
            )
        return JsonResponse({"status": "success", "message": "Notification received and processed (conceptually)."})

    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON payload.")
    except KeyError as e:
        return HttpResponseBadRequest(f"Missing key in payload: {e}")
    except Exception as e:
        ScrapeData.objects.create(
            task = "Receiving gmail webhook",
            succes = False,
            major_error = True,
            error = str(e),
            execution_date = timezone.now(),
        )
        return HttpResponseBadRequest(f"An unexpected error occurred: {e}")


from django.core.mail import EmailMessage
from django.template.loader import render_to_string



def send_simple_html_email(request, gender):
    if gender == 0:
        recipient_email = "gijsgprojects@gmail.com"
    elif gender == 1:
        recipient_email = "donnapatrona79@gmail.com"
    elif gender == 2:
        recipient_email = "gijsgprojects@gmail.com"
    else:
        return HttpResponse("Invalid gender value, use 0, 1 or 2")
    # The HTML content of your email
    html_content = render_to_string('email/test_email.html')

    email = EmailMessage(
        subject='Summer sale',
        body=html_content,
        from_email='u4987625257@gmail.com',
        to=[recipient_email],
    )
    
    # This is the critical line! It tells the email client to render the body as HTML.
    email.content_subtype = "html"
    
    email.send()

    return HttpResponse(f"Test email is verzonden naar {recipient_email}")





 

