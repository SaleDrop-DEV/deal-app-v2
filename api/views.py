import json
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Count, Q
from deals import models as deals_models
from pages import models as pages_models
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from time import sleep

from .models import API_Errors_Site


SLEEP_TIME = 0 #for testing 0 for production 

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



"""
API for website
"""
#search for stores, return at most 10 stores per page
def search_stores_api_view(request, results_per_page=10):
    sleep(SLEEP_TIME)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            query = data.get('query', '').strip()
            page_number = int(data.get('page', 1))

            # Search stores using your custom search method
            results = deals_models.Store.objects.search(query=query)

            # Paginate results (e.g., 10 per page)
            paginator = Paginator(results, results_per_page)
            page_obj = paginator.get_page(page_number)

            stores = []
            for store in page_obj:
                stores.append({
                    'id': store.id,
                    'name': store.name,
                    'image_url': store.image_url if store.mayUseContent else get_store_logo(store.name),
                    # Pass request.user to is_subscribed method
                    'is_subscribed': store.is_subscribed(request.user) if request.user.is_authenticated else False,
                })

            return JsonResponse({
                'stores': stores,
                'totalFound': len(results),
                'hasNextPage': page_obj.has_next()
            })

        except Exception as e:
            API_Errors_Site.objects.create(
                task= "Search stores",
                error = str(e)
            )
            return JsonResponse({'error': "Er ging iets mis."}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


def get_popular_stores_api_view(request, results_per_page=10):
    sleep(SLEEP_TIME)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            gender_preference = data.get('gender_preference', '')
            preference = None
            if gender_preference == '0':
                preference = "M"
            elif gender_preference == '1':
                preference = "F"
            elif gender_preference == '2':
                preference = "B"
            else:
                return JsonResponse({'error': 'Invalid gender preference.'}, status=400)

            page_number = int(data.get('page', 1))
            # Base queryset
            if preference == "B":
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
            paginator = Paginator(results, results_per_page)
            page_obj = paginator.get_page(page_number)

            stores = []
            for store in page_obj:
                stores.append({
                    'id': store.id,
                    'name': store.name,
                    'image_url': store.image_url if store.mayUseContent else get_store_logo(store.name),
                    # Pass request.user to is_subscribed method
                    'is_subscribed': store.is_subscribed(request.user) if request.user.is_authenticated else False,
                })

            return JsonResponse({
                'stores': stores,
                'totalFound': len(results),
                'hasNextPage': page_obj.has_next()
            })

        except Exception as e:
            API_Errors_Site.objects.create(
                task= "Get popular stores",
                error = str(e)
            )
            return JsonResponse({'error': "Er ging iets mis."}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)


#subscribe to a store
@login_required
def subscribe_to_store_api_view(request):
    sleep(SLEEP_TIME)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            store_id = data.get('store_id', '')
            store = deals_models.Store.objects.get(id=store_id)
            user = request.user

            # Check if the user is already subscribed to the store
            if store.is_subscribed(user):
                return JsonResponse({'error': 'Je bent al geabboneerd op deze winkel.'}, status=400)

            # Subscribe the user to the store
            store.add_subscriber(user)
            response = {
                'success': True,
                'message': 'Geabboneerd!',
                'store_name': store.name,
                'store_id': store.id,
                'image_url': store.image_url if store.mayUseContent else get_store_logo(store.name)
            }
            return JsonResponse(response)

        except deals_models.Store.DoesNotExist:
            return JsonResponse({'error': 'Winkel niet gevonden.'}, status=404)
        except Exception as e:
            API_Errors_Site.objects.create(
                task= "Subscribe to store",
                error = str(e)
            )
            return JsonResponse({'error': "Er ging iets mis."}, status=500)
        
@login_required   
def un_subscribe_to_store_api_view(request):
    sleep(SLEEP_TIME)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            store_id = data.get('store_id', '')
            store = deals_models.Store.objects.get(id=store_id)
            user = request.user

            # Check if the user is already subscribed to the store
            if not store.is_subscribed(user):
                return JsonResponse({'error': 'Je bent niet geabboneerd op deze winkel.'}, status=400)

            # Subscribe the user to the store
            store.remove_subscriber(user)
            return JsonResponse({'success': True,'message': 'Succesvol afgemeld.'})
        except deals_models.Store.DoesNotExist:
            return JsonResponse({'error': 'Winkel niet gevonden.'}, status=404)
        except Exception as e:
            API_Errors_Site.objects.create(
                task= "Un-subscribe to store",
                error = str(e)
            )
            return JsonResponse({'error': "Er ging iets mis."}, status=500)
        
@login_required        
def send_recommendation_api(request):
    sleep(SLEEP_TIME)
    if request.method == 'POST':
        try:
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
            API_Errors_Site.objects.create(
                task= "Send recommendation",
                error = str(e)
            )
            return JsonResponse({'error': 'Er ging iets mis.'}, status=500)
        


