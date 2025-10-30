from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import get_user_model, login, authenticate
from django.core.mail import EmailMessage
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers.json import DjangoJSONEncoder
from django.template.loader import render_to_string
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models.functions import Coalesce
from django.utils import timezone # Import timezone

from deals.models import Store, Click, ClickNoAuth, GmailSaleAnalysis # Keep GmailSaleAnalysis for best_sales
from .models import BusinessProfile, BusinessLoginCode, SaleMessage # Import SaleMessage
from .forms import StoreProfileEditForm, SaleMessageForm # Import SaleMessageForm
from api.models import API_Errors_Site
from pages.models import StaticContent

import random
from datetime import timedelta
import json

User = get_user_model()

def get_planned_date_str(sale_message: SaleMessage) -> str:
    """
    Generates a human-readable string for the scheduled date of a sale message.
    """
    now = timezone.now()
    msg = sale_message
    planned_date_str = ""

    if msg.scheduled_at:
        if msg.scheduled_at > now:
            one_week_from_now = now + timezone.timedelta(days=7)
            if msg.scheduled_at > one_week_from_now:
                # Format: 5 December 2025, 14:30
                planned_date_str = msg.scheduled_at.strftime("%-d %B %Y, %H:%M")
            else:
                planned_date_str = msg.scheduled_at.strftime("%A %H:%M")
                day_name_map = {
                    'Monday': 'Maandag', 'Tuesday': 'Dinsdag', 'Wednesday': 'Woensdag',
                    'Thursday': 'Donderdag', 'Friday': 'Vrijdag', 'Saturday': 'Zaterdag', 'Sunday': 'Zondag'
                }
                for eng, nl in day_name_map.items():
                    planned_date_str = planned_date_str.replace(eng, nl)
        else:
            # It has been sent in the past
            planned_date_str = f"{msg.scheduled_at.strftime('%d-%m-%Y %H:%M')}"
    else:
        # Not scheduled, depends on review/sent status
        if msg.sent_at:
            planned_date_str = f"{msg.sent_at.strftime('%d-%m-%Y %H:%M')}"
        else:
            planned_date_str = "Wacht op beoordeling voor verzending."
    
    return planned_date_str

def check_sale_limit_warning(store: Store) -> bool:
    """
    Checks if the store is *already* at the limit (3 or more sales) 
    in any existing 30-day sliding window.
    
    This is used to show a warning, not to enforce a new sale.
    """
    MAX_SALES_PER_30_DAYS = 3
    WINDOW_DURATION = timedelta(days=30)

    # 1. Get all "effective" sale dates.
    # We use Coalesce to prioritize scheduled_at if it exists,
    # otherwise we fall back to created_at for immediate sends.
    effective_dates = list(
        SaleMessage.objects.filter(store=store)
        .annotate(effective_date=Coalesce('scheduled_at', 'created_at'))
        .values_list('effective_date', flat=True)
        .order_by('effective_date') # Sorting is crucial
    )

    # 2. If there are fewer than 3 sales, a violation is impossible.
    if len(effective_dates) < MAX_SALES_PER_30_DAYS:
        return False

    # 3. Use the "sliding window" (two-pointer) algorithm
    i = 0  # Start pointer of the window
    for j in range(len(effective_dates)): # j is the end pointer
        
        # 4. While the window is 30 days or wider,
        #    move the start pointer 'i' to the right to shrink it.
        #    A window from Day 1 to Day 30 has a duration of 29 days.
        #    A window from Day 1 to Day 31 has a duration of 30 days.
        while effective_dates[j] - effective_dates[i] >= WINDOW_DURATION:
            i += 1

        # 5. Count the number of sales in the current, valid window [i..j]
        sales_in_window = (j - i) + 1

        # 6. If this window has 3 or more sales, a "full" period exists.
        if sales_in_window >= MAX_SALES_PER_30_DAYS:
            return True  # Violation found

    # 7. If we finish the loop, no "full" window was found.
    return False



# @csrf_exempt
def get_access_to_business_profile_page_view(request):
    """
    This view will handle the authenticate methods to login.

    There are two login processes:
        1: Code generation
            - Step 1: User selects a store and provides an email.
            - Step 2: If the email domain matches the store domain, a 6-digit code is sent.
            - Step 3: User submits the code for verification.
            - Step 4: On success, the user is logged in, and profiles are created if needed.

        2: Account
            - A standard email/password login for existing business users.
    """
    try:
        if request.method == 'GET':
            if request.user.is_authenticated and hasattr(request.user, 'businessprofile'):
                return redirect('business_dashboard')

            # For a GET request, we can render a page that shows the login form.
            # We'll pass the list of verified stores for the code generation flow.
            verified_stores = Store.objects.filter(isVerified=True)
            
            stores_data = []
            for store in verified_stores:
                display_domains = []
                if store.domain_list:
                    # Filter domains to only include those with one dot (e.g., 'domain.com')
                    display_domains = [domain for domain in store.domain_list if domain.count('.') == 1]
                
                stores_data.append({'id': store.id, 'name': store.name, 'domains': display_domains})

            stores_json = json.dumps(stores_data, cls=DjangoJSONEncoder)

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

            promoPhoto = StaticContent.objects.get(content_name="businessAccessPromotie")

            return render(request, 'business/access.html', {
                'stores_json': stores_json, 
                'trusted_stores': stores_data, 
                'premium_stores_count': premium_stores_count, 
                'promoPhoto': promoPhoto,
                'statCard': statCard
                })

        if request.method == 'POST':
            data = json.loads(request.body)
            access_method = data.get('access_method')

            if access_method == 'code':
                return handle_code_login(request, data)
            elif access_method == 'account':
                return handle_account_login(request, data)
            else:
                return JsonResponse({'error': 'Invalid access method specified.'}, status=400)

    except Exception as e:
        print(e)
        return JsonResponse({'error': 'An unexpected server error occurred.'}, status=500)

    return JsonResponse({'error': 'Invalid request method.'}, status=405)


def handle_code_login(request, data):
    """Handles the multi-step code-based login flow."""
    def is_email_from_verified_domain(email: str, verified_domains: list[str]) -> tuple:
        """
        Secure and correct version to check for exact and subdomain matches.
        """
        try:
            validate_email(email)
        except ValidationError:
            return False, "Geen geldig e-mailadres."
        
        if not email or not verified_domains:
            return False, "Geen email of geverifieerde domeinen gevonden."

        email_domain = email.split('@')[-1].lower().strip()
        
        # Normalize verified domains
        normalized_verified = [d.lower().strip() for d in verified_domains]
        
        for verified_domain in normalized_verified:
            # 1. Check for exact match (e.g., "zara.com" == "zara.com")
            if email_domain == verified_domain:
                return True, ''
            
            # 2. Check for subdomain match (e.g., "mail.zara.com" ends with ".zara.com")
            if email_domain.endswith(f".{verified_domain}"):
                return True, ''

        # If no match was found after checking all verified domains:
        verified_domains_string = ', '.join(d for d in normalized_verified if d.count('.') == 1)
        return False, f"Email moet een geverifieerd domein hebben. Geverifieerde domeinen zijn:\n{verified_domains_string}\nVoor het aanvragen van een ander domein bezoek https://www.saledrop.app/for-business/."


    step = data.get('step')

    if step == 'send_code':
        email = data.get('email', '').strip().lower()
        store_id = data.get('store_id')

        if not email or not store_id:
            return JsonResponse({'error': 'Email en ID zijn verplicht.'}, status=400)

        try:
            store = Store.objects.get(id=store_id, isVerified=True)
        except Store.DoesNotExist:
            return JsonResponse({'error': 'Winkel niet gevonden of niet verifieerd.'}, status=404)

        # Check if email domain matches store domain
        # extract domain.com from mail@mails.domain.com or mail@domain.com
        # .com or whatever it is is also important to keep in the domain
        is_valid_domain, msg = is_email_from_verified_domain(email=email, verified_domains=store.domain_list)

        if not is_valid_domain:
            # msg = f"Email moet een geverifieerd domein hebben."
            return JsonResponse({'error': msg}, status=403)

        # Generate and send code
        code = str(random.randint(100000, 999999))
        BusinessLoginCode.objects.filter(email=email).delete() # Invalidate old codes
        BusinessLoginCode.objects.create(email=email, code=code)

        # Render the HTML email template
        html_content = render_to_string('email/business_login_code.html', {'code': code})

        # Create and send the email
        email_message = EmailMessage(
            subject='Jouw SaleDrop Login Code',
            body=html_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        email_message.content_subtype = "html"  # This is crucial for sending HTML emails
        # DEBUG FIX
        # email_message.send(fail_silently=False)
        print(f"Code: '{code}'")

        return JsonResponse({'success': True, 'message': 'Er is een 6-cijferige code verstuurd. Controleer je e-mailadres.'})

    elif step == 'verify_code':
        email = data.get('email', '').strip().lower()
        code = data.get('code')
        store_id = data.get('store_id')

        if not all([email, code, store_id]):
            return JsonResponse({'error': 'Email, code, and store ID are required.'}, status=400)

        try:
            login_code = BusinessLoginCode.objects.get(email=email, code=code)
            if not login_code.is_valid():
                login_code.delete()
                return JsonResponse({'error': 'Code is verlopen. Vraag een nieuwe aan.'}, status=400)

            store = Store.objects.get(id=store_id)
        except BusinessLoginCode.DoesNotExist:
            return JsonResponse({'error': 'Code is ongeldig of verlopen.'}, status=400)
        except Store.DoesNotExist:
            return JsonResponse({'error': 'Store not found.'}, status=404)

        # Code is valid, get or create user and profile
        user, created = User.objects.get_or_create(email=email)
        if created:
            user.set_unusable_password() # User can set a password later
            user.is_active = True
            user.save()

        BusinessProfile.objects.get_or_create(user=user, store=store)

        # Log the user in
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        login_code.delete() # Invalidate the code after use

        return JsonResponse({'success': True, 'message': 'Login successful!', 'redirect_url': '/business/dashboard/'}) # Or wherever they should go

    return JsonResponse({'error': 'Invalid step for code login.'}, status=400)


def handle_account_login(request, data):
    """Handles standard email/password login for business users."""
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return JsonResponse({'error': 'E-mailadres en wachtwoord zijn verplicht.'}, status=400)

    # Authenticate the user
    user = authenticate(request, username=email, password=password)

    if user is not None:
        # Check if the user has a business profile.
        if hasattr(user, 'businessprofile'):
            login(request, user)
            return JsonResponse({'success': True, 'message': 'Login successful!', 'redirect_url': '/business/dashboard/'})
        else:
            # User exists but is not a business user.
            return JsonResponse({'error': 'Dit account is niet gekoppeld aan een bedrijfsprofiel.'}, status=403)
    else:
        # Authentication failed
        return JsonResponse({'error': 'Ongeldige e-mail of wachtwoord.'}, status=401)


def business_dashboard_view(request):
    """
    Displays the dashboard for a logged-in business user.
    """
    def parse_date_issued(date_issued):
        month_map = {
            1: 'jan', 2: 'feb', 3: 'mrt', 4: 'apr', 5: 'mei', 6: 'jun', # Corrected 'mrt'
            7: 'jul', 8: 'aug', 9: 'sep', 10: 'okt', 11: 'nov', 12: 'dec' # Corrected 'sep'
        }
        # return 14 mei, 2024
        month_abbr = month_map.get(date_issued.month, '')
        return f"{date_issued.day} {month_abbr}, {date_issued.year}"
    
    def get_planned_sales(store):
        now = timezone.now()
        sales_messages = SaleMessage.objects.filter(store=store).order_by('scheduled_at')

        response = [
        ]
        for sale_message in sales_messages:
            ready = sale_message.publicReady
            review_status = "pending"
            reason = None

            if not ready:
                if sale_message.isManualReviewed:
                    review_status = "passed"
                    reason = sale_message.groq_data.reason if hasattr(sale_message, 'groq_data') else "Geen reden opgegeven."
            else:
                review_status = "approved"
            response.append({
                'id': sale_message.id,
                'title': sale_message.title,
                'grabber': sale_message.grabber,
                'planned_date': get_planned_date_str(sale_message),
                'isScheduled': True if sale_message.scheduled_at else False,
                'isSent': True if sale_message.sent_at else False,
                'review_status': review_status,
                'reason': reason,
            })

        return response

    if not request.user.is_authenticated:
        return redirect('business_access')
    user = request.user
    store = None
    try:
        # Ensure the user has a business profile and get the associated store
        if user.is_superuser:
            store_id = request.GET.get('store_id')
            if store_id:
                try:
                    store = Store.objects.get(id=store_id)
                except (Store.DoesNotExist, ValueError):
                    return redirect('business_access') # Or show an error
            else:
                # For a superuser without a store_id, show a selection page.
                stores_with_profiles = Store.objects.filter(employees__isnull=False).distinct().order_by('name')
                return render(request, 'business/dashboard_superuser_select.html', {'stores': stores_with_profiles})
        else:
            business_profile = BusinessProfile.objects.select_related('store').get(user=user)
            store = business_profile.store
    except BusinessProfile.DoesNotExist:
        # If no profile, they shouldn't be here. Redirect to the access page.
        return redirect('business_access')

    # 1. Get total clicks for the store (from both authenticated and anonymous users)
    auth_clicks = Click.objects.filter(store=store).count()
    no_auth_clicks = ClickNoAuth.objects.filter(store=store).count()
    total_clicks = auth_clicks + no_auth_clicks

    # 2. Get the top 3 best-performing sales based on clicks
    # We combine clicks from both models, group by sale analysis, and order by the total click count.
    top_sales_ids = list(Click.objects.filter(store=store).values('analysis_id').annotate(c=Count('id')).order_by('-c').values_list('analysis_id', flat=True))
    top_sales_ids += list(ClickNoAuth.objects.filter(store=store).values('analysis_id').annotate(c=Count('id')).order_by('-c').values_list('analysis_id', flat=True))
    
    # This is a simple way to get top unique IDs. For very large datasets, a more complex query might be better.
    # We get the top 3 unique analysis IDs based on their click frequency.
    from collections import Counter
    top_3_analysis_ids = [item[0] for item in Counter(top_sales_ids).most_common(3)]

    # Fetch the actual sale analysis objects
    best_sales = GmailSaleAnalysis.objects.filter(id__in=top_3_analysis_ids).select_related('message')

    # Add click counts to each sale object
    for sale in best_sales:
        sale.clicks = Click.objects.filter(analysis=sale).count() + ClickNoAuth.objects.filter(analysis=sale).count()

    general_store_data = {
        'id': store.id,
        'name': store.name,
        'description': store.description,
        'onPlatformSince': f"Op SaleDrop sinds {parse_date_issued(store.dateIssued)}",
    }

    user_data = {
        'user_email': request.user.email,
        'passWordSet': request.user.has_usable_password(),
    }

    store_actions_container = {
        'may_use_content': False if not store.mayUseContent else True,
    }

    # Calculate the number of pending actions for the user
    pending_actions_count = 0
    if not store.mayUseContent:
        pending_actions_count += 1
    if not request.user.has_usable_password():
        pending_actions_count += 1

    # Add the edit form to the context
    edit_form = StoreProfileEditForm(instance=store) # For editing store profile
    sale_message_form = SaleMessageForm() # For creating new sale messages

    best_sales = sorted(best_sales, key=lambda s: s.clicks, reverse=True)
    best_sales_data = []
    for sale in best_sales:
        data = {
            # Ensure all fields expected by showProductDetails are present
            'id': sale.id,
            'title': sale.title,
            'description': sale.description,
            'main_link': sale.main_link,
            'clicks': sale.clicks,
            'grabber': sale.grabber,
            'received_date': parse_date_issued(sale.message.received_date),
            'store': { # Nested store data for consistency with API
                'id': sale.message.store.id,
                'name': sale.message.store.name,
                'id': sale.message.store.id,
                'image_url': sale.message.store.image_url
            }
        }
        best_sales_data.append(data)

    best_sales_data_json = json.dumps(best_sales_data, cls=DjangoJSONEncoder)
    

    parse_date_issued(store.dateIssued)

    context = {
        'general_store_data': general_store_data,
        'user_data': user_data,
        'store_actions_container': store_actions_container,
        'store': store,
        'total_clicks': total_clicks,
        'best_sales': best_sales_data,
        'best_sales_data_json': best_sales_data_json,
        'edit_form': edit_form, # For editing store profile
        'pending_actions_count': pending_actions_count,
        'sale_message_form': sale_message_form, # For creating new sale messages

        'planned_sales': get_planned_sales(store=store),
        'plannedSalesCountWarningStyle': 'visible' if check_sale_limit_warning(store) else 'hidden'
    }

    return render(request, 'business/dashboard.html', context)


# POST endpoints for dashboard #

@login_required
def edit_store_profile_view(request, store_id):
    """Handles the submission of the store profile edit form via AJAX."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    try:
        # Ensure the user has permission to edit this store
        if request.user.is_superuser:
            store = Store.objects.get(id=store_id)
        else:
            profile = BusinessProfile.objects.get(user=request.user, store_id=store_id)
            store = profile.store

        form = StoreProfileEditForm(request.POST, request.FILES, instance=store)
        if form.is_valid():
            updated_store = form.save()
            return JsonResponse({
                'success': True,
                'message': 'Profiel is bijgewerkt.',
                'new_description': updated_store.description,
                'new_image_url': updated_store.image_url.url if updated_store.image_url else ''
            })
        else:
            errors = {field: error[0] for field, error in form.errors.items()}
            return JsonResponse({'error': 'Validatiefout.', 'errors': errors}, status=400)

    except (Store.DoesNotExist, BusinessProfile.DoesNotExist):
        return JsonResponse({'error': 'Winkel niet gevonden of geen permissie.'}, status=404)
    except Exception as e:
        API_Errors_Site.objects.create(task="edit_store_profile_view", error=str(e))
        return JsonResponse({'error': 'Er is een onverwachte serverfout opgetreden.'}, status=500)


def allow_logo_use_view(request, id):
    if request.method == 'POST':
        store_id = id
        if store_id:
            try:
                store = Store.objects.get(id=store_id)
                store.mayUseContent = True
                store.save()
            except Exception as e:
                API_Errors_Site.objects.create(
                    task = "allow_logo_use_view",
                    error = str(e)
                )
                return JsonResponse({'error': True})
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'error': True})


@login_required
def create_sale_message_view(request):
    """
    Handles the creation of a new SaleMessage object via AJAX.
    Enforces "max 3 sales per 30-day sliding window" rule based on effective dates.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    try:
        user = request.user
        store = None  # Initialize store variable

        # Determine the store for which the message is being created
        if user.is_superuser:
            store_id = request.POST.get('store_id')
            if not store_id:
                return JsonResponse({'error': 'Store ID is vereist voor supergebruikers.'}, status=400)
            store = Store.objects.get(id=store_id)
        else:
            business_profile = BusinessProfile.objects.select_related('store').get(user=user)
            store = business_profile.store

        # --- START: Corrected Rate Limiting Logic ---

        # 1. Validate the form FIRST to get the cleaned scheduled_at date
        form = SaleMessageForm(request.POST)
        if not form.is_valid():
            errors = {field: error[0] for field, error in form.errors.items()}
            return JsonResponse({'error': 'Validatiefout.', 'errors': errors}, status=400)

        # 2. Determine the "effective date" of the new sale being submitted
        new_scheduled_at_date = form.cleaned_data.get('scheduled_at')
        if new_scheduled_at_date is None:
            new_effective_date = timezone.now() # It's an immediate send
        else:
            new_effective_date = new_scheduled_at_date

        # The rule is "no more than 3 sales", so the violation happens at the 4th sale.
        MAX_SALES_ALLOWED = 3
        VIOLATION_THRESHOLD = MAX_SALES_ALLOWED + 1
        WINDOW_DURATION = timedelta(days=30)

        # 3. Get all *existing* effective sale dates (using Coalesce, just like the warning function)
        effective_dates = list(
            SaleMessage.objects.filter(store=store)
            .annotate(effective_date=Coalesce('scheduled_at', 'created_at'))
            .values_list('effective_date', flat=True)
        )

        # 4. Add the new potential sale's date to the list
        effective_dates.append(new_effective_date)
        # 5. Sort the combined list
        effective_dates.sort()

        # 6. Run the sliding window algorithm on the combined list
        if len(effective_dates) >= VIOLATION_THRESHOLD:
            # Check every possible window of 4 sales
            for i in range(len(effective_dates) - (VIOLATION_THRESHOLD - 1)):
                # A window is from index i to i + 3 (for a limit of 4)
                window_start_date = effective_dates[i]
                window_end_date = effective_dates[i + VIOLATION_THRESHOLD - 1]

                if (window_end_date - window_start_date) < WINDOW_DURATION:
                    return JsonResponse({
                        'error': 'Limiet bereikt. U kunt niet meer dan 3 sales binnen een periode van 30 dagen inplannen.'
                    }, status=400)

        # --- END: Corrected Rate Limiting Logic ---

        # 7. If we are here, no violation was found. Save the object.
        # The form is already validated.
        sale_message = form.save(commit=False)
        sale_message.store = store
        sale_message.created_by = user
        sale_message.save()

        # Determine review_status and reason for the newly created sale
        ready = sale_message.publicReady
        review_status = "pending"
        reason = None

        if not ready:
            if sale_message.isManualReviewed:
                review_status = "passed"
                # Check if groq_data exists before accessing its reason
                if hasattr(sale_message, 'groq_data') and sale_message.groq_data:
                    reason = sale_message.groq_data.reason
                else:
                    reason = "Geen reden opgegeven." # Default if groq_data or reason is missing
        else:
            review_status = "approved"

        # Check if the user should be shown the limit warning *after* this creation
        show_warning = check_sale_limit_warning(store) # This function is already correct
        return JsonResponse({
            'success': True,
            'message': 'Sale bericht aangemaakt. Wij controleren z.s.m. het bericht.',
            'showWarning': show_warning,
            'sale_message': { # Return data for immediate UI update
                'id': sale_message.id,
                'title': sale_message.title,
                'grabber': sale_message.grabber,
                'planned_date': get_planned_date_str(sale_message),
                'isScheduled': True if sale_message.scheduled_at else False,
                'isSent': True if sale_message.sent_at else False,
                'review_status': review_status,
                'reason': reason,
            },
        })
        
        # No 'else' block needed since we validated at the top

    except (Store.DoesNotExist, BusinessProfile.DoesNotExist):
        return JsonResponse({'error': 'Winkel niet gevonden of geen permissie.'}, status=404)
    except Exception as e:
        # API_Errors_Site.objects.create(task="create_sale_message_view", error=str(e))
        print(e)
        return JsonResponse({'error': 'Er is een onverwachte serverfout opgetreden.'}, status=500)


@login_required
def edit_sale_message_view(request, sale_id):
    """
    Handles fetching and updating a SaleMessage object.
    GET: Returns the data for a specific sale message to populate an edit form.
    POST: Updates the sale message with the submitted form data.
    """
    try:
        # Ensure the user has permission to edit this sale message
        if request.user.is_superuser:
            sale_message = SaleMessage.objects.get(id=sale_id)
        else:
            profile = BusinessProfile.objects.get(user=request.user)
            sale_message = SaleMessage.objects.get(id=sale_id, store=profile.store)

    except (SaleMessage.DoesNotExist, BusinessProfile.DoesNotExist):
        return JsonResponse({'error': 'Sale bericht niet gevonden of geen permissie.'}, status=404)

    if request.method == 'GET':
        # Return the existing data to populate the form
        data = {
            'id': sale_message.id,
            'title': sale_message.title,
            'grabber': sale_message.grabber,
            'description': sale_message.description,
            'link': sale_message.link,
            # Format for datetime-local input
            'scheduled_at': sale_message.scheduled_at.strftime('%Y-%m-%dT%H:%M') if sale_message.scheduled_at else '',
            'isReviewed': sale_message.isReviewed,
            'isSuperuser': request.user.is_superuser,
        }
        return JsonResponse({'success': True, 'data': data})

    elif request.method == 'POST':
        form = SaleMessageForm(request.POST, instance=sale_message)
        if form.is_valid():
            # --- START: Rate Limiting Logic for Edit ---
            store = sale_message.store

            # 1. Determine the "effective date" of the edited sale
            new_scheduled_at_date = form.cleaned_data.get('scheduled_at')
            if new_scheduled_at_date is None:
                new_effective_date = sale_message.created_at # Fallback to creation if schedule is cleared
            else:
                new_effective_date = new_scheduled_at_date

            # 2. Define constants for the rule
            MAX_SALES_ALLOWED = 3
            VIOLATION_THRESHOLD = MAX_SALES_ALLOWED + 1
            WINDOW_DURATION = timedelta(days=30)

            # 3. Get all effective dates for the store, EXCLUDING the one being edited
            effective_dates = list(
                SaleMessage.objects.filter(store=store).exclude(id=sale_id)
                .annotate(effective_date=Coalesce('scheduled_at', 'created_at'))
                .values_list('effective_date', flat=True)
            )

            # 4. Add the new potential date and sort the list
            effective_dates.append(new_effective_date)
            effective_dates.sort()

            # 5. Run the sliding window algorithm
            if len(effective_dates) >= VIOLATION_THRESHOLD:
                for i in range(len(effective_dates) - (VIOLATION_THRESHOLD - 1)):
                    window_start_date = effective_dates[i]
                    window_end_date = effective_dates[i + VIOLATION_THRESHOLD - 1]

                    if (window_end_date - window_start_date) < WINDOW_DURATION:
                        return JsonResponse({
                            'error': 'Limiet bereikt. U kunt niet meer dan 3 sales binnen een periode van 30 dagen inplannen.'
                        }, status=400)
            # --- END: Rate Limiting Logic for Edit ---

            was_reviewed = sale_message.isReviewed
            oldTitle = sale_message.title
            oldGrabber = sale_message.grabber
            oldDescription = sale_message.description
            oldLink = sale_message.link
            oldScheduledAt = sale_message.scheduled_at
            updated_message = form.save(commit=False)

            if not oldTitle == updated_message.title and not request.user.is_superuser:
                updated_message.isReviewed = False
            if not oldGrabber == updated_message.grabber and not request.user.is_superuser:
                updated_message.isReviewed = False
            if not oldDescription == updated_message.description and not request.user.is_superuser:
                updated_message.isReviewed = False
            if not oldLink == updated_message.link and not request.user.is_superuser:
                updated_message.isReviewed = False
            
            # Logic for re-review
            # Superusers can edit without triggering re-review
            if was_reviewed and not request.user.is_superuser:
                changed_fields = form.changed_data
                print(changed_fields)
                # If only the schedule changed, keep it reviewed.
                if changed_fields == ['scheduled_at']:
                    updated_message.isReviewed = True
                    message = 'Verzenddatum is bijgewerkt.'
                # If content changed, it needs re-review.
                else:
                    updated_message.isReviewed = False
                    message = 'Sale bericht is bijgewerkt en wordt opnieuw beoordeeld.'
            else:
                # For new messages or superuser edits, use standard flow
                message = 'Sale bericht is bijgewerkt.'
                if not updated_message.isReviewed:
                    message = 'Sale bericht is bijgewerkt en wordt beoordeeld.'


            updated_message.save()

            show_warning = check_sale_limit_warning(store)

            return JsonResponse({
                'success': True,
                'message': message,
                'showWarning': show_warning,
                'sale_message': {
                    'id': updated_message.id,
                    'title': updated_message.title,
                    'grabber': updated_message.grabber,
                    'planned_date': get_planned_date_str(updated_message),
                    'isReviewed': updated_message.isReviewed,
                }
            })
        else:
            errors = {field: error[0] for field, error in form.errors.items()}
            return JsonResponse({'error': 'Validatiefout.', 'errors': errors}, status=400)

    return JsonResponse({'error': 'Invalid request method.'}, status=405)


@login_required
def delete_sale_message_view(request, sale_id):
    """
    Handles the deletion of a SaleMessage object via AJAX.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    try:
        if request.user.is_superuser:
            sale_message = SaleMessage.objects.get(id=sale_id)
        else:
            profile = BusinessProfile.objects.get(user=request.user)
            sale_message = SaleMessage.objects.get(id=sale_id, store=profile.store)

        sale_message.delete()
        return JsonResponse({'success': True, 'message': 'Sale bericht verwijderd.'})

    except (SaleMessage.DoesNotExist, BusinessProfile.DoesNotExist):
        return JsonResponse({'error': 'Sale bericht niet gevonden of geen permissie.'}, status=404)
    except Exception as e:
        print(e)
        return JsonResponse({'error': 'Er is een onverwachte serverfout opgetreden.'}, status=500)


# Change store email (easily)