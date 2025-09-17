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
        
from .tasks import send_new_recommendation_email

@login_required
def send_recommendation_api(request):
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

            send_new_recommendation_email.delay(store)
            return JsonResponse({'success': True,'message': 'Bedankt! Wij proberen deze winkel zo snel mogelijk toe te voegen.'})
        except Exception as e:
            API_Errors_Site.objects.create(
                task= "Send recommendation",
                error = str(e)
            )
            return JsonResponse({'error': 'Er ging iets mis.'}, status=500)
       
        
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from deals.models import Store, GmailToken

@login_required
def set_stores_in_sheets(request):
    def upload_to_sheets(to_sheets: list) -> bool:
        """
        Deze functie verwerkt de lijst met winkelobjecten en exporteert deze naar een Google Sheet.
        De authenticatie wordt gedaan met behulp van een service account.

        Args:
            to_sheets (list): Een lijst met dictionaries, waarbij elke dictionary de gegevens van een winkel bevat.

        Returns:
            bool: True bij succes, False bij een fout.
        """
        try:
            # Lees de onbewerkte data van de credentials uit de database
            credentials_data = GmailToken.objects.get(name="Sheets").credentials_json
            
            # Controleer of de data al een dictionary is.
            # Anders, probeer het te parsen als een JSON-string.
            if isinstance(credentials_data, str):
                info = json.loads(credentials_data)  # JSON string → dict
            else:
                info = credentials_data  # is al dict
            
            # Initialiseer de credentials met de service account info
            # De benodigde scopes (toegangsrechten) zijn hier ingesteld voor de Sheets API
            scopes = ['https://www.googleapis.com/auth/spreadsheets']
            credentials = Credentials.from_service_account_info(info, scopes=scopes)

            # Bouw de service voor de Sheets API
            service = build('sheets', 'v4', credentials=credentials)

            # De ID van de Google Sheet. Vervang 'YOUR_SPREADSHEET_ID' met de daadwerkelijke ID.
            # Je vindt de ID in de URL van je spreadsheet: https://docs.google.com/spreadsheets/d/YOUR_SPREADSHEET_ID/edit
            spreadsheet_id = '1TQ6vdAUFIOiOe48Rg-T_BiuxRrG30ygF9Mi0kLmZ57U'

            # De A1-notatie van het bereik om te updaten. Dit start bij de eerste cel in het eerste blad.
            range_name = 'AUTOMATED (NOT edit)!A1'

            # Converteer de lijst van dictionaries naar een lijst van lijsten (rijen) voor de API
            # Voeg een header-rij toe
            if not to_sheets:
                values = [[]]
            else:
                headers = list(to_sheets[0].keys())
                values = [headers] + [list(item.values()) for item in to_sheets]

            body = {
                'values': values
            }
            
            # Voer de API-aanvraag uit om de gegevens bij te werken
            result = service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()

            return True

        except Exception as e:
            # Log de fout in de database of naar de console voor debugging
            API_Errors_Site.objects.create(
                task="Upload to sheets (function)",
                error=str(e)
            )
            print(f"Fout bij het uploaden: {e}")
            return False

    if request.user.is_superuser:
        if request.method == 'POST':
            try:
                # Query de database voor alle 'Store' objecten
                stores = Store.objects.all()
                to_sheets = []
                for store in stores:
                    # Maak een dictionary van elke winkel met de gewenste velden
                    obj = {
                        'name': store.name,
                        'website': store.home_url,
                        'sale_url': store.sale_url,
                        'subscriptions': len(store.get_subscribers())
                    }
                    to_sheets.append(obj)
                
                # Roep de interne functie aan om de gegevens te uploaden
                success = upload_to_sheets(to_sheets=to_sheets)
                
                # Geef een JSON-response terug, afhankelijk van het resultaat
                if success:
                    return JsonResponse({'message': 'Gegevens succesvol geüpload naar Google Sheets.'})
                else:
                    return JsonResponse({'error': 'Fout bij het uploaden naar Google Sheets.'}, status=500)

            except Exception as e:
                API_Errors_Site.objects.create(
                    task="Set stores in sheets",
                    error=str(e)
                )
                return JsonResponse({'error': 'Er is een interne serverfout opgetreden.'}, status=500)
        else:
            # Als het geen POST-verzoek is, geef een HTTP 405 Method Not Allowed terug
            return JsonResponse({'error': 'Deze methode is niet toegestaan.'}, status=405)
    else:
        # Geen superuser, stuur een 403 Forbidden
        return JsonResponse({'error': 'Je hebt geen rechten om dit te doen.'}, status=403)

from deals.models import GmailMessage
from django.utils import timezone

from django.conf import settings
@login_required
def fetch_stores_for_admin(request):
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

    if request.user.is_superuser:
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                page_number = int(data.get('page', 1))
                sort_on = data.get('sort_on', None)
                order = data.get('order', None)
                search_name = data.get('search_name', None) # NEW: Get search term

                # Option lists for validation
                options_sort = ['verified', 'notVerified', 'mayUseContent', 'mayNotUseContent', 'isWeirdDomain', 'noEmailReceived', None]
                options_order = ['dateIssued', 'dateIssuedReverse', 'name', 'subscriptions', 'subscriptionsReverse', None]

                # Validate parameters
                if sort_on not in options_sort:
                    return JsonResponse({'error': 'Invalid sort_on parameter.'}, status=400)
                if order not in options_order:
                    return JsonResponse({'error': 'Invalid order parameter.'}, status=400)

                # Base QuerySet
                stores = deals_models.Store.objects.all()

                # NEW: Apply search filter if a search_name is provided
                if search_name:
                    stores = stores.filter(name__icontains=search_name)
                else:
                    print("no search name")

                # SORTING ON
                if sort_on == 'verified':
                    stores = stores.filter(isVerified=True)
                elif sort_on == 'notVerified':
                    stores = stores.filter(isVerified=False)
                elif sort_on == 'mayUseContent':
                    stores = stores.filter(mayUseContent=True)
                elif sort_on == 'mayNotUseContent':
                    stores = stores.filter(mayUseContent=False)
                elif sort_on == 'isWeirdDomain':
                    stores = stores.filter(isWeirdDomain=True)
                elif sort_on == 'noEmailReceived':
                    stores = stores.filter(gmailmessage__isnull=True)

                # ORDER
                if order == 'subscriptions':
                    stores = stores.annotate(
                            subscriber_count=Count('subscriptions')
                        ).order_by('-subscriber_count')
                elif order == 'subscriptionsReverse':
                    stores = stores.annotate(
                            subscriber_count=Count('subscriptions')
                        ).order_by('subscriber_count')  
                elif order == 'dateIssued':
                    stores = stores.order_by('-dateIssued')
                elif order == 'dateIssuedReverse':
                    stores = stores.order_by('dateIssued')
                else: # Default order by name if no other order is specified
                     stores = stores.order_by('name')


                totalFound = stores.count()

                paginator = Paginator(stores, 15)
                page_obj = paginator.get_page(page_number)
                
                response = []
                for store in page_obj:
                    # get the parsed date of last email
                    gmail_messages = GmailMessage.objects.filter(store=store).order_by('-received_date')
                    sales = gmail_messages.filter(analysis__is_sale_mail=True, analysis__deal_probability__gt=settings.THRESHOLD_DEAL_PROBABILITY)
                    last_received = "Er is nog geen mail ontvangen"
                    if len(gmail_messages) > 1:
                        latest_gmail = gmail_messages.first()
                        last_received = parse_date_received(latest_gmail.received_date)
                        last_received = f"Laatse mail: {last_received}"
                    response.append({
                        'id': store.id,
                        'name': store.name,
                        'home_url': store.home_url,
                        'sale_url': store.sale_url,
                        'verified': store.isVerified,
                        'mayUseContent': store.mayUseContent,
                        'dateIssued': store.dateIssued,
                        'email_addresses_comma': store.email_addresses,
                        'genderPreferenceSet': store.genderPreferenceSet,
                        'gender': store.gender,
                        'domain': store.domain,
                        'image_url': store.image_url,
                        'subscriptions': store.subscriptions.count(), # Use .count() for efficiency
                        'is_weird_domain': store.isWeirdDomain,
                        'last_received': last_received,
                        'amount_sales': len(sales)
                    })

                return JsonResponse({
                    'stores': response,
                    'totalFound': totalFound,
                    'hasNextPage': page_obj.has_next()
                })
        except Exception as e:
            API_Errors_Site.objects.create(
                task= "Fetch stores for admin",
                error = str(e)
            )
            return JsonResponse({'error': "Er ging iets mis."}, status=500)

    else:
        return JsonResponse({'error': 'Je hebt geen rechten om dit te doen.'}, status=403)

    return JsonResponse({'error': 'Invalid request method'})






#NEW#
# At the top of your views.py, make sure you have this import
from django.http import HttpResponseNotFound
from django.views.decorators.http import require_POST
from pages.models import recommendation

@login_required
@require_POST # Ensures this view only accepts POST requests
def check_recommendation(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    try:
        # 1. Read the raw request body and parse it as JSON
        data = json.loads(request.body)
        recommendation_id = data.get('recommendation_id')

        # 2. Check if the ID was provided in the JSON payload
        if recommendation_id is None:
            return JsonResponse({'error': 'recommendation_id not provided in request body'}, status=400)

        # 3. Safely get the recommendation object
        try:
            # We use int() here, now that we know recommendation_id is not None
            rec = recommendation.objects.get(id=int(recommendation_id))
        except recommendation.DoesNotExist:
            # This handles the case where the recommendation was already deleted/handled
            return HttpResponseNotFound(JsonResponse({'error': 'Recommendation not found.'}))
        except ValueError:
            # This handles if recommendation_id is not a valid number (e.g., "abc")
             return JsonResponse({'error': 'Invalid recommendation_id format.'}, status=400)


        # 4. Update the object and save it
        rec.handled = True
        rec.save()

        return JsonResponse({'success': True, 'message': 'Recommendation marked as handled.'})

    except json.JSONDecodeError:
        # This catches errors if the front-end sends malformed JSON
        return JsonResponse({'error': 'Invalid JSON format in request body.'}, status=400)
    except Exception as e:
        # General catch-all for any other unexpected errors
        print(e)
        API_Errors_Site.objects.create(
            task="Check recommendation",
            error=str(e)
        )
        return JsonResponse({'error': "Er ging iets mis op de server."}, status=500)

