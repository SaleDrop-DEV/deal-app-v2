# my_app/views.py (replace 'my_app' with your actual app name)
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, GenderPreferenceForm
from .models import ExtraUserInformation, CustomUser
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.urls import reverse

from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage
from django.conf import settings
from django.contrib.auth.views import LoginView
from .forms import CustomAuthenticationForm
from django.http import HttpResponseRedirect
from rest_framework_simplejwt.tokens import RefreshToken



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


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Wachtwoord is aangepast.')
            return redirect('account_view')
        else:
            messages.error(request, 'Er is iets misgegaan. Probeer het opnieuw.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'account/password_change_form.html', {
        'form': form
    })

@login_required
def account_view(request):
    user = request.user
    try:
        extra_info = user.extrauserinformation
    except ExtraUserInformation.DoesNotExist:
        extra_info = ExtraUserInformation.objects.create(user=user, gender=0)

    # Handle POST
    if request.method == 'POST':
        form = GenderPreferenceForm(request.POST, instance=extra_info)
        if form.is_valid():
            form.save()
            return redirect('account_view')
    else:
        form = GenderPreferenceForm(instance=extra_info)

    # Assuming user has a `subscribed_stores` relationship
    subscribed_stores = user.subscribed_stores.order_by('name').all()
    for store in subscribed_stores:
        store.logo_url = store.image_url if store.mayUseContent else get_store_logo(store.name)



    context = {
        'page': 'account',
        'user': user,
        'extra_info': extra_info,
        'form': form,
        'subscribed_stores': subscribed_stores,
    }
    return render(request, 'account/account.html', context)


def logout_view(request):
    logout(request)
    return redirect('login')


class CustomLoginView(LoginView):
    authentication_form = CustomAuthenticationForm
    template_name = 'account/login.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # Add your custom context variables
        context['page'] = 'login'
        return context


def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # user.is_active = False
            # user.save()

            current_site = get_current_site(request)
            mail_subject = 'Activeer je account.'

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            # You must include the protocol (http or https)
            base_activation_url = reverse('activate', kwargs={'uidb64': uid, 'token': token})
            activation_link = f"{settings.CURRENT_URL}{base_activation_url}?source=web"

            message = render_to_string('email/validation_email.html', {
                'user': user,
                'uid': uid,
                'token': token,
                'activation_link': activation_link,  # Pass the new variable
            })
            to_email = form.cleaned_data.get('email')
            email = EmailMessage(
                mail_subject, message, to=[to_email]
            )
            email.content_subtype = "html"
            email.send()

            d1 = "Er is een link verstuurd naar uw e-mailadres om uw account te activeren."
            d2 = "Volg de link in die e-mail om je registratie te voltooien."
            d3 = "Als je de e-mail niet ziet, controleer dan je spammap."
            d4 = "Neem contact met ons op als je de e-mail binnen enkele minuten niet ontvangt."
            data = {
                'title': "Verificatie link is verstuurd.",
                'description': f"{d1} {d2}\n{d3} {d4}"
            }
            return render(request, 'account/message_template.html', context=data)
    else:
        form = CustomUserCreationForm()

    return render(request, 'account/signup.html', {'form': form, 'page': 'signup'})


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, ExtraUserInformation.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        source = request.GET.get('source')
        if source == 'app' or source == 'appV2':
            return redirect(f"{reverse('complete_profile')}?source=app")
        else:
            return redirect(f"{reverse('stores')}?succesfuly_activated=1")
    else:
        data = {
            'title': "Verificatie link is niet geldig.",
            'description': "De link is niet geldig of is verbruikt."
        }
        return render(request, 'account/message_template.html', context=data)


@login_required
def complete_profile(request):
    """
    Handles both displaying the gender form and processing its submission.
    """
    try:
        user = request.user
        # --- FIX 2: Handle the POST request from the form submission ---
        if request.method == 'POST':
            gender_str = request.POST.get('gender')
            valid_genders = ['man', 'vrouw', 'anders']

            if gender_str in valid_genders:
                gender_map = {'man': 0, 'vrouw': 1, 'anders': 2}
                gender_int = gender_map.get(gender_str)
                
                # Use get_or_create to safely create the record.
                extra_info, created = ExtraUserInformation.objects.get_or_create(user=user)
                
                # Now, 'extra_info' is the actual object, not a tuple
                extra_info.gender = gender_int
                extra_info.save()
                
                source = request.GET.get('source')
                if source == 'appV2':
                    # Generate a one-time token for the app to log the user in.
                    refresh = RefreshToken.for_user(user)
                    return redirect(f"{reverse('stores')}?succesfuly_activated=1&token={str(refresh)}")
                else:
                    return redirect(f"{reverse('stores')}?succesfuly_activated=1")
            else:
                # If the submission is invalid, show an error.
                error = "Selecteer een geldige optie."
                return render(request, 'account/gender_form.html', {'error': error})

        # This part handles the initial GET request.
        return render(request, 'account/gender_form.html')
    except Exception as e:
        # Log the error and show a generic error message.
        API_Errors_Site.objects.create(
            task = "Completing profile.",
            error = str(e)
        )
        error = "Er is iets misgegaan. Probeer het later opnieuw."
        return render(request, 'account/gender_form.html', {'error': error})


from django.http import JsonResponse
@login_required
def get_refresh_token(request):
    """
    Endpoint to get a new refresh token for the logged-in user.
    """
    user = request.user
    if not user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    refresh = RefreshToken.for_user(user)
    return JsonResponse({
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    })


from deals.models import GmailToken, Click, Store
from pages.models import recommendation, BusinessRequest
from api.models import API_Errors_Site
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import requests
from django.db.models import Count
import json



@login_required
def admin_dashboard(request):
    def get_google_search_console_data(token_name="googleSearchConsole"):
        def get_data(credentials_info, property_url, days=-14):
            """
            Haalt GSC data op voor een specifieke website met een credentials dictionary.
            """
            SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']

            try:
                # Authenticatie direct vanuit het dictionary object
                credentials = service_account.Credentials.from_service_account_info(
                    credentials_info, scopes=SCOPES)

                # Bouw de service
                service = build('searchconsole', 'v1', credentials=credentials)

                # Definieer de API-request
                request_body = {
                    'startDate': (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d'),
                    'endDate': datetime.now().strftime('%Y-%m-%d'),
                    'dimensions': ['date'],
                    'rowLimit': 100 # Ensure we get all recent data points
                }

                response = service.searchanalytics().query(
                    siteUrl=property_url,
                    body=request_body
                ).execute()
                return response.get('rows', [])
            except Exception as e:
                print(f"Fout bij ophalen GSC data: {e}")
                return None

        try:
            token_object = GmailToken.objects.get(name=token_name)
            json_token = token_object.token_json
            site_property = 'sc-domain:saledrop.app'
            gsc_data = get_data(json_token, site_property)
            return gsc_data
        except GmailToken.DoesNotExist:
            return None
        except Exception as e:
            API_Errors_Site.objects.create(
                task = "Fetching google search data.",
                error = str(e)
            )
            return None

    def get_bing_webmaster_data(token_name="bingWebmaster"):
        def fetch_bing_analytics(api_key, site_url):
            """
            Fetches query performance data from the Bing Webmaster API.
            """
            endpoint = f"https://ssl.bing.com/webmaster/api.svc/json/GetQueryStats?siteUrl={site_url}&apikey={api_key}"
            
            try:
                response = requests.get(endpoint)
                response.raise_for_status()
                data = response.json()
                return data.get('d', [])
            except requests.exceptions.RequestException as e:
                print(f"Fout bij ophalen Bing data: {e}")
                return None

        def get_dashboard_bing_data(site_url, token_name=token_name):
            """
            Retrieves the Bing API key from the database and fetches the analytics.
            """
            try:
                token_object = GmailToken.objects.get(name=token_name)
                api_key = token_object.token_json.get('key')
                if not api_key:
                    print("API key not found in token JSON.")
                    return None
                
                return fetch_bing_analytics(api_key, site_url)
                
            except GmailToken.DoesNotExist:
                print(f"Token with name '{token_name}' not found.")
                return None
            except Exception as e:
                print(f"An error occurred while getting Bing dashboard data: {e}")
                return None

        # It's more efficient to fetch data for the main domain once
        site_url = "https://saledrop.app/"
        bing_data = get_dashboard_bing_data(site_url)
        return bing_data

    def get_total_clicks():
        return Click.objects.count()

    def get_n_most_subscribed_stores(n=5):
        results = Store.objects.all().annotate(
            subscriber_count=Count('subscriptions')
        ).order_by('-subscriber_count')
        data = []
        for result in results[:n]:
            data.append({
                'name': result.name,
                'logo_url': result.image_url,
                'subscriber_count': result.subscriber_count,
            })
        return data

    def get_unhandled_recommendations():
        return [data.to_dict() for data in recommendation.objects.filter(handled=False).order_by('date_sent').all()]

    def get_six_latest_business_requests():
        seven_days_ago = datetime.now() - timedelta(days=7)
        recent_requests = BusinessRequest.objects.filter(date_sent__gte=seven_days_ago).order_by('-date_sent').all()[:6]
        return [data.to_dict() for data in recent_requests]

    if request.user.is_staff:
        gsc_data = get_google_search_console_data()
        bing_data = get_bing_webmaster_data()
        total_user_count = CustomUser.objects.count()

        context = {
            # Serialize data for JavaScript
            'gsc_data_json': json.dumps(gsc_data or []),
            'bing_data_json': json.dumps(bing_data or []),
            
            # Data for direct rendering
            'total_user_count': total_user_count,
            'total_clicks': get_total_clicks(),
            'most_subscribed_stores': get_n_most_subscribed_stores(),
            'unhandled_recommendations': get_unhandled_recommendations(),
            'latest_business_requests': get_six_latest_business_requests(),
        }
        return render(request, 'admin_templates/dashboard.html', context)
    else:
        return redirect('account_view')




from .models import OneTimeLoginToken
from django.utils import timezone
def auto_login_with_token(request, token):
    """
    Logs a user in using a one-time token and redirects them.
    """
    try:
        # Define how long the token is valid for
        TOKEN_VALIDITY_SECONDS = 60 
        
        login_token = OneTimeLoginToken.objects.get(token=token)
        
        # 1. Check if token is expired
        if login_token.created_at < timezone.now() - timedelta(seconds=TOKEN_VALIDITY_SECONDS):
            # Handle expired token (e.g., show an error page)
            login_token.delete() # Clean up
            return render(request, 'account/token_expired.html')

        # 2. If valid, log the user in
        user = login_token.user
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        # 3. Invalidate the token by deleting it
        login_token.delete()

        # 4. Redirect to the password change page
        return redirect('password_change') # Assumes you have a named URL 'password_change'

    except OneTimeLoginToken.DoesNotExist:
        # Handle invalid token
        return render(request, 'account/token_invalid.html')
