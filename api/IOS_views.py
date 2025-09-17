#IOS app APIs:
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db.models import Count, Q
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


def raise_error(prob=0.3):
    """
    Simulates various kinds of errors with a given probability (0 <= prob <= 1).
    Call this at the beginning of a Django view to randomly raise an error.
    """
    if random.random() > prob:
        return  # No error this time

    error_type = random.choice([
        'http404',
        'permission_denied',
        'auth_failed',
        'not_authenticated',
        'validation_error',
        'value_error',
        'key_error',
        'type_error',
        'zero_division',
        'json_decode_error',
        'timeout',
        'generic_exception',
        'internal_server_error',
    ])

    if error_type == 'http404':
        raise Http404("Simulated 404: Not Found")

    elif error_type == 'permission_denied':
        raise PermissionDenied("Simulated Permission Denied")

    elif error_type == 'auth_failed':
        raise AuthenticationFailed("Simulated Authentication Failure")

    elif error_type == 'not_authenticated':
        raise NotAuthenticated("Simulated Not Authenticated")

    elif error_type == 'validation_error':
        raise ValidationError("Simulated Validation Error")

    elif error_type == 'value_error':
        raise ValueError("Simulated Value Error")

    elif error_type == 'key_error':
        raise KeyError("Simulated Key Error: 'missing_key'")

    elif error_type == 'type_error':
        raise TypeError("Simulated Type Error: expected int, got str")

    elif error_type == 'zero_division':
        _ = 1 / 0  # Will raise ZeroDivisionError

    elif error_type == 'json_decode_error':
        import json
        json.loads("INVALID_JSON")

    elif error_type == 'timeout':
        time.sleep(10)  # Simulate timeout — let frontend timeout

    elif error_type == 'generic_exception':
        raise Exception("Simulated generic exception")

    elif error_type == 'internal_server_error':
        raise RuntimeError("Simulated Internal Server Error")

    else:
        raise Exception("Unexpected error type in raise_error()")
# END #




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


@method_decorator(csrf_exempt, name='dispatch')
class MyTokenObtainPairView(TokenObtainPairView):
    """
    Custom view that uses our email-based serializer.
    """
    serializer_class = MyTokenObtainPairSerializer


class UserRegistrationView(APIView):
    """
    API endpoint for user registration.
    """
    permission_classes = []  # No permissions required to register a new user
    authentication_classes = [] # No authentication required

    def post(self, request, format=None):
        try:
            serializer = UserRegistrationSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.save()
                if getattr(serializer, 'verification_email_sent', False):
                    d1 = "Er is een link verstuurd naar uw e-mailadres om uw account te activeren."
                    d2 = "Volg de link in die e-mail om je registratie te voltooien."
                    d3 = "Als je de e-mail niet ziet, controleer dan je spammap."
                    d4 = "Neem contact met ons op als je de e-mail binnen enkele minuten niet ontvangt."
                    return Response(
                        
                        {"message": f"{d1} {d2}\n{d3} {d4}"},
                        status=status.HTTP_201_CREATED
                    )
                else:
                    API_Errors.objects.create(
                        task= "Send email",
                        error = f"No email sent to {user.email}"
                    )
                    return Response(
                        {"message": "Er is iets misgegaan met het versturen van de verificatie link, neem alstublieft contact op met ons."},
                        status=status.HTTP_201_CREATED
                    )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            API_Errors.objects.create(
                task= "Registration",
                error = str(e)
            )
            return JsonResponse({'error': 'Er ging iets mis.'}, status=500)


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def IOS_API_delete_account(request):
    try:
        user = request.user
        user.delete()
        return JsonResponse({'success': True, 'message': 'Account deleted.'})
    except Exception as e:
        API_Errors.objects.create(
            task= "Delete user",
            error= str(e)
        )
        return JsonResponse({'error': "Er is iets misgegaan."}, status=500)


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def IOS_API_fetch_my_feed(request):
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

    sleep(SLEEP_TIME)
    try:
        raise_error(ERR_PROB)
        if request.method == 'POST':
            data = json.loads(request.body)
            page_number = int(data.get('page', 1))
            user = request.user

            subscribed_stores = deals_models.Store.objects.filter(subscriptions=user)
            three_weeks_ago = timezone.now() - timedelta(days=21)

            # --- GENDER FILTERING ---
            gender_of_user = getattr(user.extrauserinformation, 'gender', None)
            if gender_of_user == 0:
                gender_filters = Q(message__email_to="gijsgprojects@gmail.com") | Q(message__store__genderPreferenceSet=False)
            elif gender_of_user == 1:
                gender_filters = Q(message__email_to="donnapatrona79@gmail.com") | Q(message__store__genderPreferenceSet=False)
            elif gender_of_user == 2:
                gender_filters = Q()
            else:
                gender_filters = Q()

            # Get all GmailMessages related to those stores
            sales = list(deals_models.GmailSaleAnalysis.objects.filter(
                is_sale_mail=True,
                is_personal_deal=False,
                deal_probability__gt=settings.THRESHOLD_DEAL_PROBABILITY,
                message__received_date__gte=three_weeks_ago,
                message__store__isnull=False
            ).filter(
                message__store__in=subscribed_stores
            ).filter(
                gender_filters
            ).select_related('message').order_by('-message__received_date'))

            # we also want to include new stores added to the database
            gender_preference_user = ["M", "F", "B"][user.extrauserinformation.gender]
            acceptable_genders = ['B']
            three_days_ago = timezone.now() - timedelta(days=3)

            if gender_preference_user != "B":
                acceptable_genders.append(gender_preference_user)
                new_stores = list(deals_models.Store.objects.filter(
                    gender__in=acceptable_genders,
                    dateIssued__gte=three_days_ago
                ))
            else:
                new_stores = list(deals_models.Store.objects.filter(dateIssued__gte=three_days_ago))

            feed_items = sales + new_stores
            feed_items.sort(
                key=lambda item: item.message.received_date if hasattr(item, 'message') else item.dateIssued,
                reverse=True
            )

            paginator = Paginator(feed_items, ITEMS_PER_PAGE)

            try:
                page_obj = paginator.page(page_number)
            except PageNotAnInteger:
                page_obj = paginator.page(1)
                page_number = 1
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages)
                page_number = paginator.num_pages

            response = []
            for analysis in page_obj:
                if hasattr(analysis, 'message'):
                    a: deals_models.GmailSaleAnalysis = analysis
                    a: deals_models.GmailSaleAnalysis = analysis
                    s = "Er is een nieuwe deal beschikbaar!"
                    d = "Bekijk jouw nieuwe deal door op de knop te klikken."
                    data = {
                        'type': 'sale',
                        'title': a.title,
                        'grabber': a.grabber if a.grabber != "N/A" else s,
                        'description': a.description if a.description != "N/A" else d,
                        'storeName': a.message.store.name,
                        'mainLink': f"deals/visit/{a.id}/{user.id}/",
                        'messageId': a.message.id,
                        'dateReceived': a.message.received_date,
                        'parsedDateReceived': parse_date_received(a.message.received_date),
                    }
                    response.append(data)
                else:
                    a: deals_models.Store = analysis
                    data = {
                        'type': 'new_store',
                        'id': a.id,
                        'name': a.name,
                        'image_url': a.image_url if a.mayUseContent else get_store_logo(a.name),
                        'is_subscribed': a.is_subscribed(user),
                    }
                    response.append(data)

            return JsonResponse({
                'success': True,
                'items': response,
                'has_next_page': page_obj.has_next(),
                'page': page_number,
                'total_pages': paginator.num_pages,
            })

    except Exception as e:
        API_Errors.objects.create(
            task="Fetch my feed",
            error=str(e)
        )
        return JsonResponse({'error': 'Er ging iets mis.'}, status=500)



@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def IOS_API_fetch_my_sales(request):
    sleep(SLEEP_TIME)

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

    if request.method == 'POST':
        raise_error(ERR_PROB)
        try:
            data = json.loads(request.body)
            page_number = int(data.get('page', 1))
            user = request.user

            subscribed_stores = deals_models.Store.objects.filter(subscriptions=user)
            three_weeks_ago = timezone.now() - timedelta(days=21)

            # --- GENDER FILTERING (same as website) ---
            gender_of_user = getattr(user.extrauserinformation, 'gender', None)
            if gender_of_user == 0:
                gender_filters = Q(message__email_to="gijsgprojects@gmail.com") | Q(message__store__genderPreferenceSet=False)
            elif gender_of_user == 1:
                gender_filters = Q(message__email_to="donnapatrona79@gmail.com") | Q(message__store__genderPreferenceSet=False)
            elif gender_of_user == 2:
                gender_filters = Q()
            else:
                gender_filters = Q()

            analyses = deals_models.GmailSaleAnalysis.objects.filter(
                is_sale_mail=True,
                is_personal_deal=False,
                deal_probability__gt=settings.THRESHOLD_DEAL_PROBABILITY,
                message__received_date__gte=three_weeks_ago,
                message__store__isnull=False
            ).filter(
                message__store__in=subscribed_stores
            ).filter(
                gender_filters
            ).select_related('message').order_by('-message__received_date')

            paginator = Paginator(analyses, ITEMS_PER_PAGE)

            try:
                page_obj = paginator.page(page_number)
            except PageNotAnInteger:
                page_obj = paginator.page(1)
                page_number = 1
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages)
                page_number = paginator.num_pages

            response = []
            for analysis in page_obj:
                a: deals_models.GmailSaleAnalysis = analysis
                s = "Er is een nieuwe deal beschikbaar!"
                d = "Bekijk jouw nieuwe deal door op de knop te klikken."
                data = {
                    'title': a.title,
                    'grabber': a.grabber if a.grabber != "N/A" else s,
                    'storeName': a.message.store.name,
                    'mainLink': f"deals/visit/{a.id}/{user.id}/",
                    'description': a.description if a.description != "N/A" else d,
                    'messageId': a.message.id,
                    'dateReceived': a.message.received_date,
                    'parsedDateReceived': parse_date_received(a.message.received_date),
                }
                response.append(data)

            return JsonResponse({
                'success': True,
                'deals': response,
                'has_next_page': page_obj.has_next(),
                'page': page_number,
                'total_pages': paginator.num_pages,
            })

        except Exception as e:
            API_Errors.objects.create(
                task="IO Fetch my sales",
                error=str(e)
            )
            return JsonResponse({'error': 'Er ging iets mis.'}, status=500)



@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def IOS_API_fetch_account_details(request):
    sleep(SLEEP_TIME)
    try:
        raise_error(ERR_PROB)
        user = request.user
        extra_info = user.extrauserinformation
        user_data = {
            'userId': user.id,
            'email': user.email,
            'gender': extra_info.gender
        }
        subscriptions = deals_models.Store.objects.filter(subscriptions=user).order_by('name')
        store_data = []
        for store in subscriptions:

            store_data.append({
                'storeId': store.id,
                'storeName': store.name,
                'imageUrl': store.image_url if store.mayUseContent else get_store_logo(store.name)
            })

        return JsonResponse({'success': True, 'user': user_data, 'stores': store_data})
    except Exception as e:
        API_Errors.objects.create(
            task= "Fetch account details",
            error = str(e)
        )
        return JsonResponse({'error': 'Er ging iets mis.'}, status=500) 


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def IOS_API_subscribe_to_store(request):
    # url = subscribe-to-store-api/
    sleep(SLEEP_TIME)
    try:
        raise_error(ERR_PROB)
        data = json.loads(request.body)
        store_id = data.get('storeId')
        user = request.user
        store = deals_models.Store.objects.get(id=store_id)

        if store.is_subscribed(user):
            return JsonResponse({'error': 'Je bent al geabboneerd op deze winkel.'}, status=400)
        store.add_subscriber(user)
        response = {
            'success': True,
            'message': 'Geabboneerd!',
            'storeName': store.name,
            'storeId': store.id,
            'imageUrl': store.image_url if store.mayUseContent else get_store_logo(store.name)
        }
        return JsonResponse(response)
    except deals_models.Store.DoesNotExist:
        return JsonResponse({'error': 'Winkel niet gevonden.'}, status=404)
    except Exception as e:
        API_Errors.objects.create(
            task= "Subscribe to store",
            error = str(e)
        )
        return JsonResponse({'error': 'Er ging iets mis.'}, status=500)



@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def IOS_API_un_subscribe_to_store(request):
    #url = un-subscribe-to-store-api/
    sleep(SLEEP_TIME)
    try:
        raise_error(ERR_FOCUS)
        data = json.loads(request.body)
        store_id = data.get('storeId')
        user = request.user
        store = deals_models.Store.objects.get(id=store_id)
        if not store.is_subscribed(user):
            return JsonResponse({'error': 'Je bent niet geabboneerd op deze winkel.'}, status=400)
        store.remove_subscriber(user)
        return JsonResponse({'success': True,'message': 'Afgemeld.'})
    except Exception as e:
        API_Errors.objects.create(
            task= "Un-subscribe to store",
            error = str(e)
        )
        return JsonResponse({'error': 'Er ging iets mis.'}, status=500
                            )


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def IOS_API_send_recommendation(request):
    # url = request-recommendation-api/
    sleep(SLEEP_TIME)
    try:
        raise_error(ERR_PROB)
        data = json.loads(request.body)
        store = data.get('store', '')
        if len(store) == 0:
            return JsonResponse({'error': 'Voer een geldige winkel in.'}, status=400)
        new_rec = pages_models.recommendation.objects.create(
            user=request.user,
            store=store
        )
        new_rec.save()
        return JsonResponse({'success': True,'message': 'Bedankt! Wij proberen deze winkel zo snel mogelijk toe te voegen.'})
    except Exception as e:
        API_Errors.objects.create(
            task= "Send recommendation",
            error = str(e)
        )
        return JsonResponse({'error': 'Er ging iets mis.'}, status=500)


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def IOS_API_search_stores(request):
    # url = search-stores-api/
    sleep(SLEEP_TIME)
    try:
        raise_error(ERR_PROB)
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        page_number = int(data.get('page', 1))

        # Search stores using your custom search method
        results = deals_models.Store.objects.search(query=query).order_by('name')

        # Paginate results (e.g., 10 per page)
        paginator = Paginator(results, ITEMS_PER_PAGE)
        page_obj = paginator.get_page(page_number)

        stores = []
        for store in page_obj:
            stores.append({
                'id': store.id,
                'name': store.name,
                'image_url': store.image_url if store.mayUseContent else get_store_logo(store.name),
                'is_subscribed': store.is_subscribed(request.user)
            })

        return JsonResponse({
            'stores': stores,
            'totalFound': len(results),
            'hasNextPage': page_obj.has_next()
        })

    except Exception as e:
        API_Errors.objects.create(
            task= "Search stores",
            error = str(e)
        )
        return JsonResponse({'error': "Er ging iets mis."}, status=400)


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def IOS_API_change_user_gender_preference(request):
    # url = change-user-gender-preference/
    sleep(SLEEP_TIME)
    try:
        raise_error(ERR_FOCUS)
        data = json.loads(request.body)
        gender = data.get('gender', '')
        if gender not in [0, 1, 2]:
            return JsonResponse({'error': 'Invalid gender preference.'}, status=400)
        user = request.user
        extra_info = user.extrauserinformation
        extra_info.gender = gender
        extra_info.save()
        return JsonResponse({'success': True,'message': 'Succesvol aangepast.'})

    except Exception as e:
        API_Errors.objects.create(
            task= "Change user gender preference",
            error = str(e)
        )
        return JsonResponse({'error': 'Er ging iets mis.'}, status=500)
    


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def IOS_API_fetch_popular_stores(request):
    # url = fetch-popular-stores/
    sleep(SLEEP_TIME)
    try:
        raise_error(ERR_PROB)
        data = json.loads(request.body)
        preference = request.user.extrauserinformation.gender
        
        page_number = int(data.get('page', 1))
        # Base queryset
        if preference == 2: # Gender BOTH => all stores matter
            queryset = deals_models.Store.objects.all()
        else:
            # Include both gender-specific and general-interest stores
            queryset = deals_models.Store.objects.filter(
                Q(gender=preference) | Q(gender="B")
            )

        results = queryset.annotate(
            subscriber_count=Count('subscriptions')
        ).order_by('-subscriber_count')

        # Paginate results (e.g., 10 per page)
        paginator = Paginator(results, ITEMS_PER_PAGE)
        page_obj = paginator.get_page(page_number)

        stores = []
        for store in page_obj:
            stores.append({
                'id': store.id,
                'name': store.name,
                'image_url': store.image_url if store.mayUseContent else get_store_logo(store.name),
                # Pass request.user to is_subscribed method
                'is_subscribed': store.is_subscribed(request.user),
            })

        return JsonResponse({
            'stores': stores,
            'totalFound': len(results),
            'hasNextPage': page_obj.has_next()
        })

    except Exception as e:
        API_Errors.objects.create(
            task= "Fetch popular stores",
            error = str(e)
        )
        return JsonResponse({'error': "Er ging iets mis."}, status=400)



@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def IOS_API_save_expo_push_token(request):
    """
    Save Expo Push Token for the logged-in user.
    Expected JSON body: { "token": "<expo_push_token>" }
    """
    try:
        data = json.loads(request.body)
        token = data.get('expo_token')

        if not token:
            return JsonResponse({'error': 'Token not provided.'}, status=400)

        user = request.user
        user.extrauserinformation.expoToken = token
        user.extrauserinformation.save()
        return JsonResponse({'success': True, 'message': 'Push token saved.'})

    except Exception as e:
        API_Errors.objects.create(
            task= "Save expo push token",
            error = str(e)
        )
        return JsonResponse({'error': 'Er ging iets mis bij het opslaan van het token.'}, status=500)



@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def IOS_API_delete_expo_push_token(request):
    """
    Delete Expo Push Token for the logged-in user.
    """
    try:
        user = request.user
        user.extrauserinformation.expoToken = None
        user.extrauserinformation.save()
        return JsonResponse({'success': True, 'message': 'Push token saved.'})

    except Exception as e:
        API_Errors.objects.create(
            task= "Delete expo push token",
            error = str(e)
        )
        return JsonResponse({'error': 'Er ging iets mis bij het verwijderen van het token.'}, status=500)


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_analysis_detail(request):
    try:
        analysis_id = json.loads(request.body).get('analysisId')
        analysis = deals_models.GmailSaleAnalysis.objects.get(id=analysis_id)
    except deals_models.GmailSaleAnalysis.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)
    except Exception as e:
        API_Errors.objects.create(
            task= "Get analysis detail",
            error = str(e)
        )
        return JsonResponse({'error': str(e)}, status=500)
    
    s = "Er is een nieuwe deal beschikbaar!"
    d = "Bekijk jouw nieuwe deal door op de knop te klikken."
    return JsonResponse({
        'title': analysis.title,
        'grabber': analysis.grabber if analysis.grabber != "N/A" else s,
        'storeName': analysis.message.store.name,
        'mainLink': f"deals/visit/{analysis.id}/{request.user.id}/",  # consider if request.user.id is needed here
        'description': analysis.description if analysis.description != "N/A" else d,
        'messageId': analysis.message.id,
    })
