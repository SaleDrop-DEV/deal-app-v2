#IOS app APIs:
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import render
from django.utils import timezone
from django.conf import settings


from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from time import sleep
import json

from .serializers import MyTokenObtainPairSerializer, UserRegistrationSerializer
from .models import API_Errors
from deals import models as deals_models
from pages import models as pages_models
from accounts.models import OneTimeLoginToken

SLEEP_TIME = 0
ITEMS_PER_PAGE = 15

ERR_PROB = 0
ERR_FOCUS = 0


# ERROR TESTING #
import random
import time
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.utils.timezone import now
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, ValidationError


from datetime import timedelta

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



# Example lists (could also come from DB or external service)
sponsors = [
    {
        'id': 1,
        'type': 'sponsor',
        'name': 'Sponsor 1',
        'image_url': 'https://www.saledrop.app/media/store_logos/07b02bd9-bf59-4fe0-8dab-059209c61542.png',
        'title': 'Sponsor 1 Title',
        'grabber': 'Check out Sponsor 1!',
        'description': 'This is Sponsor 1',
        'link': 'https://sponsor1.com',
    },
    {
        'id': 2,
        'type': 'sponsor',
        'storeName': 'Sponsor 2',
        'image_url': 'https://www.saledrop.app/media/store_logos/07b02bd9-bf59-4fe0-8dab-059209c61542.png',
        'title': 'Sponsor 2 Title',
        'grabber': 'Check out Sponsor 2!',
        'description': 'This is Sponsor 2',
        'link': 'https://sponsor2.com',
    },
]


sponsors = []

highlighted_sales = [
    {
        'type': 'highlighted_sale',
        'title': 'Herfst sale nu online',
        'grabber': 'Pak tot 70% korting!',
        'description': 'Beschrijving van de uitgelichte deal.',
        'storeName': 'Zara',
        'mainLink': "deals/public/",
        'messageId': 1,
        'dateReceived': "",
        'parsedDateReceived': '1m geleden',
    },
    {
        'type': 'highlighted_sale',
        'title': 'Some title',
        'grabber': 'Some grabber text',
        'description': 'Some description text',
        'storeName': 'Store name',
        'mainLink': "deals/public/",
        'messageId': 1,
        'dateReceived': "",
        'parsedDateReceived': '1m geleden',
    }
]

def get_highlighted_sales(user):
    """
    Fetch highlighted sales from the database.
    For simplicity, we return a static list here.
    """
    try:
        # Use filter to fetch all existing sales with the given IDs in one query.
        # This is more efficient and avoids errors if an ID doesn't exist.
        id_s = [2234, 2246] # Example IDs
        # sales_qs = deals_models.GmailSaleAnalysis.objects.filter(id__in=id_s)
        # print(f"Fetched {sales_qs.count()} highlighted sales from DB.")

        highlighted_sales = []
        for id in id_s:
            message = deals_models.GmailMessage.objects.get(id=id)
            analysis = message.analysis
            if message and message.store:
                data = {
                    'type': 'highlighted_sale',
                    'title': analysis.title,
                    'grabber': analysis.grabber,
                    'description': analysis.description,
                    'storeName': analysis.message.store.name,
                    'mainLink': f"deals/visit/{analysis.id}/{user.id}/" if user else f"deals/visit/{analysis.id}/0/",
                    'messageId': analysis.message.id,
                    'analysisId': analysis.id,
                    'dateReceived': analysis.message.received_date,
                    'parsedDateReceived': parse_date_received(analysis.message.received_date),
                }
                highlighted_sales.append(data)
            else:
                print(f"Skipping sale ID {analysis.id} due to missing related objects.")
        return highlighted_sales
    except Exception as e:
        print(e)
        return []

def get_sponsors():
    via_appia = deals_models.Store.objects.get(id=44)
    data = {
        'id': via_appia.id,
        'type': 'sponsor',
        'name': via_appia.name,
        'image_url': f"https://saledrop.app/{via_appia.image_url}",
        'title': 'Ontvang 10% korting bij Via Appia',
        'grabber': 'Bekijk de nieuwe collectie!',
        'description': 'Ontvang 10% korting op je eerste bestelling bij Via Appia met de code "SALE10".',
        'link': via_appia.home_url
    }
    return [data]


ITEMS_PER_PAGE = 10
SLEEP_TIME = 0


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
        days = int(delta.total_seconds() / 86400)
        return f"{days} dag{'en' if days > 1 else ''} geleden"


def serialize_feed_item(item, user):
    """
    Turns a GmailSaleAnalysis or Store into a dict suitable for the feed response.
    """
    if hasattr(item, 'message'):  # GmailSaleAnalysis
        a = item
        s = "Er is een nieuwe deal beschikbaar!"
        d = "Bekijk jouw nieuwe deal door op de knop te klikken."
        return {
            'type': 'sale',
            'title': a.title,
            'grabber': a.grabber if a.grabber != "N/A" else s,
            'description': a.description if a.description != "N/A" else d,
            'storeName': a.message.store.name,
            'mainLink': f"deals/visit/{a.id}/{user.id}/" if user else f"deals/visit/{a.id}/0/",
            'messageId': a.message.id,
            'dateReceived': a.message.received_date,
            'parsedDateReceived': parse_date_received(a.message.received_date),
        }
    else:  # Store
        a = item
        return {
            'type': 'new_store',
            'id': a.id,
            'name': a.name,
            'image_url': a.image_url if a.mayUseContent else get_store_logo(a.name),
            'is_subscribed': a.is_subscribed(user) if user else False,
        }


def inject_extras(response, page_number, new_stores_to_inject, sponsors_to_inject, highlighted_sales_to_inject):
    """
    Insert sponsors, highlighted sales, or other special items into the feed.
    Items are inserted in reverse index order to avoid shifting indices.
    """
    # New store at index 7
    # A simple way to get a different store for the second slot if available
    second_new_store_index = (page_number - 1) * 2 + 1
    if second_new_store_index < len(new_stores_to_inject):
        new_store = new_stores_to_inject[second_new_store_index]
        insert_index = min(7, len(response))
        response.insert(insert_index, new_store)

    # Highlighted sale at index 5
    if page_number - 1 < len(highlighted_sales_to_inject):
        highlighted_sale = highlighted_sales_to_inject[page_number - 1]
        insert_index = min(5, len(response))
        response.insert(insert_index, highlighted_sale)

    # New store at index 3
    first_new_store_index = (page_number - 1) * 2
    if first_new_store_index < len(new_stores_to_inject):
        new_store = new_stores_to_inject[first_new_store_index]
        insert_index = min(3, len(response))
        response.insert(insert_index, new_store)

    # Sponsor at index 2 (as it was originally)
    if page_number - 1 < len(sponsors_to_inject):
        sponsor = sponsors_to_inject[page_number - 1]
        insert_index = min(2, len(response))
        response.insert(insert_index, sponsor)

    return response


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def IOS_API_fetch_my_feed(request):
    """
    Returns a feed for the authenticated user, including sales, new stores,
    optional sponsors, and highlighted sales.
    """
    from time import sleep
    sleep(SLEEP_TIME)

    try:
        data = json.loads(request.body)
        page_number = int(data.get('page', 1))
        user = request.user

        # Subscribed stores
        subscribed_stores = deals_models.Store.objects.filter(subscriptions=user)
        three_weeks_ago = timezone.now() - timedelta(days=21)

        # Gender filters
        gender_of_user = getattr(user.extrauserinformation, 'gender', None)
        if gender_of_user == 0:
            gender_filters = Q(message__email_to="gijsgprojects@gmail.com") | Q(message__store__genderPreferenceSet=False)
        elif gender_of_user == 1:
            gender_filters = Q(message__email_to="donnapatrona79@gmail.com") | Q(message__store__genderPreferenceSet=False)
        else:
            gender_filters = Q()

        # Sales
        sales_qs = deals_models.GmailSaleAnalysis.objects.filter(
            is_sale_mail=True,
            is_personal_deal=False,
            deal_probability__gt=settings.THRESHOLD_DEAL_PROBABILITY,
            message__received_date__gte=three_weeks_ago,
            message__store__isnull=False,
            message__store__in=subscribed_stores,
            is_new_deal_better=True
        ).filter(
            gender_filters
        ).select_related('message').order_by('-message__received_date')

        # New stores
        gender_preference_user = ["M", "F", "B"][user.extrauserinformation.gender]
        acceptable_genders = ['B']
        seven_days_ago = timezone.now() - timedelta(days=7)
        if gender_preference_user != "B":
            acceptable_genders.append(gender_preference_user)
            new_stores = list(deals_models.Store.objects.filter(
                gender__in=acceptable_genders,
                dateIssued__gte=seven_days_ago
            ).order_by('-dateIssued'))
        else:
            new_stores = list(deals_models.Store.objects.filter(dateIssued__gte=seven_days_ago).order_by('-dateIssued'))

        # Paginate
        paginator = Paginator(sales_qs, ITEMS_PER_PAGE)
        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
            page_number = 1
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
            page_number = paginator.num_pages

        # Serialize
        response = [serialize_feed_item(item, user) for item in page_obj.object_list]
        serialized_new_stores = [serialize_feed_item(item, user) for item in new_stores]

        # Inject extras - passing all potential items to the injection function
        response = inject_extras(response, page_number, serialized_new_stores, get_sponsors(), get_highlighted_sales(user))

        return Response({
            'success': True,
            'items': response,
            'has_next_page': page_obj.has_next(),
            'page': page_number,
            'total_pages': paginator.num_pages,
        })

    except Exception as e:
        API_Errors.objects.create(task="Fetch my feed", error=str(e))
        return Response({'error': 'Er ging iets mis.'}, status=500)



# NEEDS MODIFY LIKE ABOVE #
# --- MODIFIED AND IMPROVED FUNCTION USING INJECTION LOGIC --- #
@api_view(['POST'])
@csrf_exempt
def IOS_API_fetch_feed_no_auth(request, max_preview_pages=2):
    """
    Returns a generic feed for non-authenticated users.
    This version now paginates only sales and then injects new stores,
    mirroring the structure of the authenticated feed.
    """

    try:
        data = json.loads(request.body)
        page_number = int(data.get('page', 1))

        if page_number > max_preview_pages:
            return Response({
                'success': True,
                'items': [],
                'has_next_page': False,
                'page': page_number,
                'total_pages': max_preview_pages,
            })

        three_weeks_ago = timezone.now() - timedelta(days=21)

        # 1. Fetch all potential sales items
        sales = list(deals_models.GmailSaleAnalysis.objects.filter(
            is_sale_mail=True,
            is_personal_deal=False,
            deal_probability__gt=settings.THRESHOLD_DEAL_PROBABILITY,
            message__received_date__gte=three_weeks_ago,
            message__store__isnull=False,
            is_new_deal_better=True
        ).select_related('message', 'message__store').order_by('-message__received_date'))
        
        # 2. Filter to one unique sale per store per day (retained from original logic)
        unique_sales = []
        seen_store_days = set()
        for sale in sales:
            if sale.message and sale.message.store:
                store_id = sale.message.store.id
                sale_date = sale.message.received_date.date()
                if (store_id, sale_date) not in seen_store_days:
                    unique_sales.append(sale)
                    seen_store_days.add((store_id, sale_date))
        
        # 3. Fetch all potential items for injection (new stores)
        seven_days_ago = timezone.now() - timedelta(days=7)
        new_stores = list(deals_models.Store.objects.filter(dateIssued__gte=seven_days_ago).order_by('-dateIssued'))

        # 4. Paginate ONLY the main feed content (the unique sales)
        paginator = Paginator(unique_sales, ITEMS_PER_PAGE)
        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
            page_number = 1
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
            page_number = paginator.num_pages if paginator.num_pages > 0 else 1

        # 5. Serialize the items for the current page and the items to be injected
        # Note: Pass `user=None` as there is no authenticated user.
        serialized_sales = [serialize_feed_item(item, None) for item in page_obj.object_list]
        serialized_new_stores = [serialize_feed_item(item, None) for item in new_stores]
        
        # For the non-auth feed, we don't have sponsors or highlighted sales.
        sponsors = []
        highlighted_sales = []

        # 6. Inject the extra items into the serialized list of sales
        response_items = inject_extras(
            serialized_sales, 
            page_number, 
            serialized_new_stores, 
            sponsors, 
            highlighted_sales
        )

        return Response({
            'success': True,
            'items': response_items,
            'has_next_page': page_obj.has_next(),
            'page': page_number,
            'total_pages': paginator.num_pages,
        })

    except Exception as e:
        API_Errors.objects.create(task="Fetch my feed no auth", error=str(e))
        return Response({'error': 'Er ging iets mis.'}, status=500)


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def IOS_API_fetch_stores(request):
    try:
        data = json.loads(request.body)
        user = request.user
        preference = user.extrauserinformation.gender

        page_number = int(data.get('page', 1))
        search_query = data.get('query', '').strip()
        sort = data.get('sort', 'popular')
        if sort not in ['popular', 'new', 'name', 'with_sales']:
            return JsonResponse({'error': "Ongeldige sorteermethode."}, status=400)

        # Base queryset based on user's gender preference for stores
        if preference == 2:  # Gender BOTH => all stores matter
            queryset = deals_models.Store.objects.all()
        else:
            gender_char = 'M' if preference == 0 else 'F'
            queryset = deals_models.Store.objects.filter(Q(gender=gender_char) | Q(gender="B"))

        if search_query:
            queryset = queryset.filter(name__icontains=search_query)

        # --- REFACTORED ANNOTATION LOGIC ---

        # 1. Define gender filters for sales emails, relative to Store
        gender_of_user = getattr(user.extrauserinformation, 'gender', None)
        gender_sales_filter = Q()
        if gender_of_user == 0: # Male
            gender_sales_filter = Q(gmailmessage__email_to="gijsgprojects@gmail.com") | Q(gmailmessage__store__genderPreferenceSet=False)
        elif gender_of_user == 1: # Female
            gender_sales_filter = Q(gmailmessage__email_to="donnapatrona79@gmail.com") | Q(gmailmessage__store__genderPreferenceSet=False)
            
        # 2. Define the main filter for active sales, relative to Store
        three_weeks_ago = timezone.now() - timedelta(days=21)
        active_sales_filter = Q(
            gmailmessage__analysis__is_sale_mail=True,
            gmailmessage__analysis__is_personal_deal=False,
            gmailmessage__analysis__is_new_deal_better=True,
            gmailmessage__analysis__deal_probability__gt=settings.THRESHOLD_DEAL_PROBABILITY,
            gmailmessage__received_date__gte=three_weeks_ago
        )

        # 3. Combine filters and annotate the count onto the main queryset
        final_sales_filter = active_sales_filter & gender_sales_filter
        queryset = queryset.annotate(
            active_sales_count=Count('gmailmessage', filter=final_sales_filter, distinct=True)
        )

        # Apply sorting
        if sort == 'new':
            results = queryset.order_by('-dateIssued')
        elif sort == 'name':
            results = queryset.order_by('name')
        elif sort == 'with_sales':
            # We already have the count, just filter and order by it
            results = queryset.filter(active_sales_count__gt=0)#.order_by('-active_sales_count')
        else:  # Default to 'popular'
            results = queryset.annotate(
                subscriber_count=Count('subscriptions')
            ).order_by('-subscriber_count')

        # Paginate results
        paginator = Paginator(results, ITEMS_PER_PAGE)
        page_obj = paginator.get_page(page_number)

        stores = []
        for store in page_obj:
            stores.append({
                'id': store.id,
                'name': store.name,
                'image_url': store.image_url if store.mayUseContent else get_store_logo(store.name),
                'active_sales_count': store.active_sales_count, # Use the annotated value
                'is_subscribed': store.is_subscribed(user),
            })

        return JsonResponse({
            'stores': stores,
            'totalFound': results.count(), # Use .count() for efficiency
            'hasNextPage': page_obj.has_next()
        })

    except Exception as e:
        API_Errors.objects.create(
            task="Fetch popular stores",
            error=str(e)
        )
        return JsonResponse({'error': "Er ging iets mis."}, status=400)


@api_view(['POST'])
@csrf_exempt
def IOS_API_fetch_stores_no_auth(request):
    try:
        data = json.loads(request.body)
        page_number = int(data.get('page', 1))
        search_query = data.get('query', '').strip()
        sort = data.get('sort', 'popular')
        if sort not in ['popular', 'new', 'name', 'with_sales']:
            return JsonResponse({'error': "Ongeldige sorteermethode."}, status=400)

        queryset = deals_models.Store.objects.all()

        if search_query:
            queryset = queryset.filter(name__icontains=search_query)

        # --- REFACTORED ANNOTATION LOGIC ---

        # 1. Define the filter for active sales, relative to Store
        three_weeks_ago = timezone.now() - timedelta(days=21)
        active_sales_filter = Q(
            gmailmessage__analysis__is_sale_mail=True,
            gmailmessage__analysis__is_personal_deal=False,
            gmailmessage__analysis__is_new_deal_better=True,
            gmailmessage__analysis__deal_probability__gt=settings.THRESHOLD_DEAL_PROBABILITY,
            gmailmessage__received_date__gte=three_weeks_ago
        )

        # 2. Annotate the count onto every store in the queryset
        queryset = queryset.annotate(
            active_sales_count=Count(
                TruncDate('gmailmessage__received_date'), filter=active_sales_filter, distinct=True
            )
        )

        # Apply sorting
        if sort == 'new':
            results = queryset.order_by('-dateIssued')
        elif sort == 'name':
            results = queryset.order_by('name')
        elif sort == 'with_sales':
            results = queryset.filter(active_sales_count__gt=0)#.order_by('-active_sales_count')
        else:  # Default to 'popular'
            results = queryset.annotate(subscriber_count=Count('subscriptions')).order_by('-subscriber_count')

        # Paginate results
        paginator = Paginator(results, ITEMS_PER_PAGE)
        page_obj = paginator.get_page(page_number)

        stores = []
        for store in page_obj:
            stores.append({
                'id': store.id,
                'name': store.name,
                'image_url': store.image_url if store.mayUseContent else get_store_logo(store.name),
                'active_sales_count': store.active_sales_count, # Use the annotated value
                'is_subscribed': False
            })

        return JsonResponse({
            'stores': stores,
            'totalFound': results.count(), # Use .count() for efficiency
            'hasNextPage': page_obj.has_next()
        })

    except Exception as e:
        API_Errors.objects.create(
            task="Fetch popular stores",
            error=str(e)
        )
        return JsonResponse({'error': "Er ging iets mis."}, status=400)


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def IOS_API_fetch_public_sales(request):
    sleep(SLEEP_TIME)
    try:
        data = json.loads(request.body)
        page_number = int(data.get('page', 1))
        user = request.user

        # Gender filters
        gender_of_user = getattr(user.extrauserinformation, 'gender', None)
        if gender_of_user == 0:
            gender_filters = Q(message__email_to="gijsgprojects@gmail.com") | Q(message__store__genderPreferenceSet=False)
        elif gender_of_user == 1:
            gender_filters = Q(message__email_to="donnapatrona79@gmail.com") | Q(message__store__genderPreferenceSet=False)
        else:
            gender_filters = Q()

        three_weeks_ago = timezone.now() - timedelta(days=21)

        # Get all GmailMessages related to those stores
        sales_qs = deals_models.GmailSaleAnalysis.objects.filter(
            is_sale_mail=True,
            is_personal_deal=False,
            deal_probability__gt=settings.THRESHOLD_DEAL_PROBABILITY,
            message__received_date__gte=three_weeks_ago,
            message__store__isnull=False,
            is_new_deal_better=True
        ).filter(
            gender_filters
        ).select_related('message', 'message__store').order_by('-message__received_date')

        # If gender is 'both', filter to one sale per store per day.
        # Also fetch new stores based on gender preference for injection
        seven_days_ago = timezone.now() - timedelta(days=7)
        new_stores_qs = deals_models.Store.objects.filter(dateIssued__gte=seven_days_ago)

        if gender_of_user == 0: # Male
            new_stores_qs = new_stores_qs.filter(Q(gender='M') | Q(gender='B'))
        elif gender_of_user == 1: # Female
            new_stores_qs = new_stores_qs.filter(Q(gender='F') | Q(gender='B'))
        # For gender 'both' (2), we use all new stores without extra filtering.

        new_stores = list(new_stores_qs.order_by('-dateIssued'))
        serialized_new_stores = [serialize_feed_item(item, user) for item in new_stores]


        if gender_of_user == 2:
            unique_sales = []
            seen_store_days = set()
            for sale in sales_qs:
                if sale.message and sale.message.store:
                    store_id = sale.message.store.id
                    sale_date = sale.message.received_date.date()
                    if (store_id, sale_date) not in seen_store_days:
                        unique_sales.append(sale)
                        seen_store_days.add((store_id, sale_date))
            paginatable_items = unique_sales
        else:
            paginatable_items = sales_qs

        # Paginate
        paginator = Paginator(paginatable_items, ITEMS_PER_PAGE)
        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
            page_number = 1
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
            page_number = paginator.num_pages

        # Serialize
        response = []
        for analysis in page_obj:
            response.append(serialize_feed_item(analysis, user))

        response = inject_extras(response, page_number, serialized_new_stores, get_sponsors(), [])
        return Response({
            'success': True,
            'items': response,
            'has_next_page': page_obj.has_next(),
            'page': page_number,
            'total_pages': paginator.num_pages,
        })
    except Exception as e:
        API_Errors.objects.create(task="Fetch public sales", error=str(e))
        return Response({'error': 'Er ging iets mis.'}, status=500)




@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def IOS_API_fetch_account_details(request):
    sleep(SLEEP_TIME)
    try:
        data = json.loads(request.body)
        page_number = int(data.get('page', 1))

        user = request.user
        extra_info = user.extrauserinformation
        gender_map = {
            0: "Mannen",
            1: "Vrouwen",
            2: "Beide"
        }
        user_data = {
            'userId': user.id,
            'email': user.email,
            'gender': gender_map.get(extra_info.gender)
        }
        subscriptions_qs = deals_models.Store.objects.filter(subscriptions=user).order_by('name')

        # Gender filters for sales count
        gender_of_user = getattr(user.extrauserinformation, 'gender', None)
        if gender_of_user == 0:
            gender_filters = Q(message__email_to="gijsgprojects@gmail.com") | Q(message__store__genderPreferenceSet=False)
        elif gender_of_user == 1:
            gender_filters = Q(message__email_to="donnapatrona79@gmail.com") | Q(message__store__genderPreferenceSet=False)
        else:
            gender_filters = Q()

        def get_active_sales_count(store):
            one_month_ago = timezone.now() - timedelta(days=21)
            return deals_models.GmailSaleAnalysis.objects.filter(
                message__store=store, is_sale_mail=True, is_personal_deal=False,
                is_new_deal_better=True, deal_probability__gt=settings.THRESHOLD_DEAL_PROBABILITY,
                message__received_date__gte=one_month_ago
            ).filter(gender_filters).count()

        paginator = Paginator(subscriptions_qs, ITEMS_PER_PAGE)
        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
            page_number = 1
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
            page_number = paginator.num_pages

        store_data = []
        for store in page_obj.object_list:
            store_data.append({
                'id': store.id,
                'name': store.name,
                'image_url': store.image_url if store.mayUseContent else get_store_logo(store.name),
                'active_sales_count': get_active_sales_count(store),
                'isSubscribed': True
            })

        return Response({
            'success': True, 'user': user_data, 'stores': store_data,
            'has_next_page': page_obj.has_next(),
            'page': page_number,
        })
    except Exception as e:
        API_Errors.objects.create(
            task= "Fetch account details",
            error = str(e)
        )
        return JsonResponse({'error': 'Er ging iets mis.'}, status=500) 


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def IOS_API_fetch_all_subscribed_store_ids(request):
    """
    Fetches all store IDs the authenticated user is subscribed to.
    """
    try:
        user = request.user
        subscribed_store_ids = list(deals_models.Store.objects.filter(subscriptions=user).values_list('id', flat=True))
        return JsonResponse({
            'success': True,
            'subscribed_store_ids': subscribed_store_ids
        })
    except Exception as e:
        API_Errors.objects.create(
            task="Fetch all subscribed store IDs",
            error=str(e)
        )
        return JsonResponse({'error': 'Er ging iets mis.'}, status=500)


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def IOS_API_fetch_store_data(request):
    def parse_date_issued(date_issued):
        month_map = {
            1: 'jan', 2: 'feb', 3: 'mrt', 4: 'apr', 5: 'mei', 6: 'jun',
            7: 'jul', 8: 'aug', 9: 'sep', 10: 'okt', 11: 'nov', 12: 'dec'
        }
        # return 14 mei, 2024
        month_abbr = month_map.get(date_issued.month, '')
        return f"{date_issued.day} {month_abbr}, {date_issued.year}"

            
    try:
        data = json.loads(request.body)
        store_id = data.get('storeId')
        store = deals_models.Store.objects.get(id=store_id)
        user = request.user

        # Gender filters
        gender_of_user = getattr(user.extrauserinformation, 'gender', None)
        if gender_of_user == 0:
            gender_filters = Q(message__email_to="gijsgprojects@gmail.com") | Q(message__store__genderPreferenceSet=False)
        elif gender_of_user == 1:
            gender_filters = Q(message__email_to="donnapatrona79@gmail.com") | Q(message__store__genderPreferenceSet=False)
        else:
            gender_filters = Q()
        # get active sales
        three_weeks_ago = timezone.now() - timedelta(days=21)
        active_sales = deals_models.GmailSaleAnalysis.objects.filter(
            is_sale_mail=True,
            is_personal_deal=False,
            deal_probability__gt=settings.THRESHOLD_DEAL_PROBABILITY,
            message__received_date__gte=three_weeks_ago,
            message__store=store,
            is_new_deal_better=True
        ).filter(gender_filters).select_related('message').order_by('-message__received_date')
        serialized_sales = []
        for sale in active_sales:
            serialized_sales.append({
                'id': sale.id,
                'title': sale.title,
                'storeName': store.name,
                'grabber': sale.grabber if sale.grabber != "N/A" else "Er is een nieuwe deal beschikbaar!",
                'description': sale.description if sale.description != "N/A" else "Bekijk jouw nieuwe deal door op de knop te klikken.",
                'messageId': sale.message.id,
                'dateReceived': sale.message.received_date,
                'parsedDateReceived': parse_date_received(sale.message.received_date),
                'mainLink': f"deals/visit/{sale.id}/{user.id}/",
            })

        description = f"Op SaleDrop sinds {parse_date_issued(store.dateIssued)}"
        if store.description:
            description = store.description
        return Response({
            'success': True,
            'store_data': {
                'id': store.id,
                'name': store.name,
                'image_url': store.image_url if store.mayUseContent else get_store_logo(store.name),
                'isSubscribed': store.is_subscribed(user),
                'home_url': store.home_url,
                'description': description,
            },
            'active_sales': serialized_sales
        })
    except Exception as e:
        API_Errors.objects.create(
            task="Fetch store data",
            error=str(e)
        )
        return Response({'error': 'Er ging iets mis.'}, status=500)



@api_view(['POST'])
@csrf_exempt
def IOS_API_fetch_store_data_no_auth(request):
    # Helper function for human-readable dates, consistent with the feed
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
            days = int(delta.total_seconds() / 86400)
            return f"{days} dag{'en' if days > 1 else ''} geleden"

    def parse_date_issued(date_issued):
        month_map = {
            1: 'jan', 2: 'feb', 3: 'mrt', 4: 'apr', 5: 'mei', 6: 'jun',
            7: 'jul', 8: 'aug', 9: 'sep', 10: 'okt', 11: 'nov', 12: 'dec'
        }
        # return 14 mei, 2024
        month_abbr = month_map.get(date_issued.month, '')
        return f"{date_issued.day} {month_abbr}, {date_issued.year}"

    try:
        data = json.loads(request.body)
        store_id = data.get('storeId')
        page_number = int(data.get('page', 1)) # Read page number from request
        store = deals_models.Store.objects.get(id=store_id)
        
        three_weeks_ago = timezone.now() - timedelta(days=21)

        # Fetch all sales for the store, ordered by most recent first.
        active_sales_qs = deals_models.GmailSaleAnalysis.objects.filter(
            is_sale_mail=True,
            is_personal_deal=False,
            deal_probability__gt=settings.THRESHOLD_DEAL_PROBABILITY,
            message__received_date__gte=three_weeks_ago,
            message__store=store,
            is_new_deal_better=True
        ).select_related('message').order_by('-message__received_date')


        # Filter to one sale per day in Python to avoid database-specific features.
        unique_sales = []
        seen_dates = set()
        for sale in active_sales_qs:
            sale_date = sale.message.received_date.date()
            if sale_date not in seen_dates:
                unique_sales.append(sale)
                seen_dates.add(sale_date)
        print(f"Unique sales count: {len(unique_sales)}")


        # --- SERIALIZATION LOGIC ---
        serialized_sales = []
        for sale in unique_sales:
            serialized_sales.append({
                'id': sale.id,
                'storeName': store.name,
                'title': sale.title,
                'grabber': sale.grabber if sale.grabber != "N/A" else "Er is een nieuwe deal beschikbaar!",
                'description': sale.description if sale.description != "N/A" else "Bekijk jouw nieuwe deal door op de knop te klikken.",
                'messageId': sale.message.id,
                'dateReceived': sale.message.received_date,
                # Use the relative date parser for consistency
                'parsedDateReceived': parse_date_received(sale.message.received_date),
                'mainLink': f"deals/visit/{sale.id}/0/",
            })
            
        description = f"Op SaleDrop sinds {parse_date_issued(store.dateIssued)}"
        if store.description:
            description = store.description
        return Response({
            'success': True,
            'store_data': {
                'id': store.id,
                'name': store.name,
                'image_url': store.image_url if store.mayUseContent else get_store_logo(store.name),
                'isSubscribed': False,
                'home_url': store.home_url,
                'description': description,
            },
            # Nest the paginated sales and metadata in a 'sales' object
            'active_sales': serialized_sales
        })
    except deals_models.Store.DoesNotExist:
        return Response({'error': 'Winkel niet gevonden.'}, status=404)
    except Exception as e:
        API_Errors.objects.create(
            task="Fetch store data no auth",
            error=str(e)
        )
        return Response({'error': 'Er ging iets mis.'}, status=500)


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def IOS_API_save_expo_token(request):
    try:
        data = json.loads(request.body)
        expo_token = data.get('expoToken', '').strip()
        if not expo_token:
            return JsonResponse({'error': 'Ongeldig token.'}, status=405)

        user = request.user
        extra_info = user.extrauserinformation

        # Add the new token to the list if it's not already present
        if extra_info.expoTokens is None:
            extra_info.expoTokens = []
        if expo_token not in extra_info.expoTokens:
            extra_info.expoTokens.append(expo_token)
            extra_info.save()

        return JsonResponse({'success': True})
    except Exception as e:
        API_Errors.objects.create(
            task="Save Expo token",
            error=str(e)
        )
        return JsonResponse({'error': 'Er ging iets mis.'}, status=500)


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def IOS_API_delete_expo_token(request):
    try:
        data = json.loads(request.body)
        expo_token = data.get('expoToken', '').strip()
        if not expo_token:
            return JsonResponse({'error': 'Ongeldig token.'}, status=405)

        user = request.user
        extra_info = user.extrauserinformation

        # Remove the token from the list if it exists
        if extra_info.expoTokens and expo_token in extra_info.expoTokens:
            extra_info.expoTokens.remove(expo_token)
            if extra_info.expoToken == expo_token:
                extra_info.expoToken = None  # Clear the single token field if it matches
            extra_info.save()

        return JsonResponse({'success': True})
    except Exception as e:
        API_Errors.objects.create(
            task="Delete Expo token",
            error=str(e)
        )
        return JsonResponse({'error': 'Er ging iets mis.'}, status=500)


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def generate_auto_login_token(request):
    """
    Generates a short-lived, one-time token for a user to log into the web app.
    """
    try:
        user = request.user
        # Optional: Delete old tokens for this user to keep the table clean
        OneTimeLoginToken.objects.filter(user=user).delete()
        
        # Create a new token
        new_token = OneTimeLoginToken.objects.create(user=user)
        
        return Response({'token': str(new_token.token)})
    except Exception as e:
        API_Errors.objects.create(
            task="Generate auto login token",
            error=str(e)
        )
        return Response({'error': 'Er ging iets mis.'}, status=500)

# END OF FILE #