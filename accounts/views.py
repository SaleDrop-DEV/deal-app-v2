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
        if source == 'app':
            return redirect('complete_profile')
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
            
            # Redirect to the main page after successful submission
            return redirect(f"{reverse('stores')}?succesfuly_activated=1")
        else:
            # If the submission is invalid, show an error.
            error = "Selecteer een geldige optie."
            return render(request, 'account/gender_form.html', {'error': error})

    # This part handles the initial GET request.
    return render(request, 'account/gender_form.html')
