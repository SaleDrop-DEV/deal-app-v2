from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import transaction

from deals.models import GmailMessage, GmailSaleAnalysis, ScrapeData, Url

import os
import json
import requests
from requests.adapters import HTTPAdapter
from time import sleep
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse
from urllib3.util.retry import Retry
import random

User = get_user_model()

PROXY_CAKE_USERNAME = settings.PROXY_CAKE_USERNAME
PROXY_CAKE_PASSWORD = settings.PROXY_CAKE_PASSWORD
PROXY_CAKE_IP = settings.PROXY_CAKE_IP
PROXY_CAKE_PORT = settings.PROXY_CAKE_PORT

PROXIES = {
    "http": f"http://{PROXY_CAKE_USERNAME}:{PROXY_CAKE_PASSWORD}@{PROXY_CAKE_IP}:{PROXY_CAKE_PORT}",
    "https": f"http://{PROXY_CAKE_USERNAME}:{PROXY_CAKE_PASSWORD}@{PROXY_CAKE_IP}:{PROXY_CAKE_PORT}",
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/114.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Connection": "keep-alive",
}

GEMINI_API_KEY = settings.GEMINI_API_KEY_GENERAL
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

EXPO_PUSH_URL = 'https://exp.host/--/api/v2/push/send'



def analyze_email_with_gemini(email_html, prompt_addition) -> dict:
    """
    Analyseer e-mailinhoud met Gemini API en retourneer data passend bij GmailSaleAnalysis model.
    """

    prompt = (
        f"Analyseer de onderstaande e-mailinhoud en bepaal of het een uitverkoop betreft. "
        f"Negeer welkomsmails en algemene reclame. "
        f"Extraheer de volgende velden nauwkeurig:\n\n"
        f"- is_sale_mail: true/false\n"
        f"- is_personal_deal: true/false\n"
        f"- title: string (Een **zeer korte titel** van maximaal 7 woorden, bijv. 'SALE MANGO' of 'Nieuwe collectie'. Gebruik geen kortingspercentages hier.)\n"
        f"- grabber: string (Een **korte, pakkende kortingszin**, zoals '-70% korting' of 'Tot 50% korting'. Dit is de belangrijkste promotiezin.)\n"
        f"- description: string (Een **neutrale, redactionele beschrijving** van de aanbieding. Dit mag langere details bevatten. \
          Vermijd bezittelijke voornaamwoorden, persoonlijke verwijzingen en directe marketing-taal. Geef een korte en duidelijke samenvatting van de aanbieding, geschreven in een casual toon.)"
        f" Start de beschrijving met: Bij 'merk' is nu/vanaf. De beschrijving moet niet overkomen alsof het uit een email komt, vermijd dus 'in deze email'.\n"
        f"- main_link: string (URL naar de sale)\n"
        f"- highlighted_products: array van objecten met {{title, new_price, old_price, product_image_url, link}}\n"
        f"- deal_probability: float (tussen 0 en 1, met hoe zeker je bent dat dit een echte sale is)\n\n"
        f"- is_new_deal_better: boolean \n{prompt_addition}\n\n"
        f"Als een variabele er niet is, gebruik dan 'N/A'.\n"
        f"Geef de output als een JSON object dat het gevraagde schema volgt.\n"
        f"Email HTML:\n{email_html}\n\n"
    )

    response_schema = {
        "type": "OBJECT",
        "properties": {
            "is_sale_mail": {"type": "BOOLEAN"},
            "is_personal_deal": {"type": "BOOLEAN"},
            "title": {"type": "STRING"},
            "grabber": {"type": "STRING"},
            "description": {"type": "STRING"},
            "main_link": {"type": "STRING"},
            "deal_probability": {"type": "NUMBER"},
            "is_new_deal_better": {"type": "BOOLEAN"},
            
            "highlighted_products": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "title": {"type": "STRING"},
                        "new_price": {"type": "STRING"},
                        "old_price": {"type": "STRING"},
                        "product_image_url": {"type": "STRING"},
                        "link": {"type": "STRING"}
                    },
                    "required": ["title", "new_price", "link"]
                }
            }
        },
        "required": ["is_sale_mail", "is_personal_deal", "deal_probability"]
    }

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": response_schema
        }
    }

    # 1. Define the retry strategy
    retry_strategy = Retry(
        total=5,  # Total number of retries
        status_forcelist=[500, 502, 503, 504],  # A set of HTTP status codes to retry on
        backoff_factor=1  # Will sleep for {backoff factor} * (2 ** ({number of total retries} - 1)) seconds
                        # e.g., 1s, 2s, 4s, 8s, 16s
    )

    # 2. Create an adapter and mount it to a session
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    try:
        response = session.post(GEMINI_API_URL, headers=HEADERS, data=json.dumps(payload), timeout=30)
        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        return {'success': False, 'error': str(e)}

    result = response.json()

    """
    Unsafe assumptions about Gemini response shape — 
    indexing into candidates[0] and parts[0] may raise IndexError when response is different; 
    code should guard.
    """

    candidates = result.get('candidates', [])
    if not candidates:
        return {'success': False, 'error': 'Gemini returned no candidates.'}

    # Now you can safely access the first element
    parts = candidates[0].get('content', {}).get('parts', [])
    if not parts:
        return {'success': False, 'error': "Gemini analysis returned no 'parts' in the content."}

    json_text = parts[0].get('text', '{}')
    parsed = json.loads(json_text)
    data = {
        "is_sale_mail": parsed.get("is_sale_mail", False),
        "is_personal_deal": parsed.get("is_personal_deal", False),
        "title": parsed.get("title"),
        "grabber": parsed.get("grabber"),
        "description": parsed.get("description"),
        "main_link": parsed.get("main_link"),
        "highlighted_products": parsed.get("highlighted_products", []),
        "deal_probability": float(parsed.get("deal_probability", 0.0)),

        "is_new_deal_better": parsed.get("is_new_deal_better", True)
    }
    return {'success': True, 'data': data}

def scrape_and_save_url(url: str):
    """
    Scrapes a URL, handles redirects, strips query parameters, and saves it.
    This function is designed to be robust, with automatic retries for
    transient network and server errors.
    """
    
    session = requests.Session()
    retry_strategy = Retry(
        total=5,  # Maximum number of retries
        status_forcelist=[429, 500, 502, 503, 504],  # Status codes to retry on
        backoff_factor=1  # Enables exponential backoff (e.g., waits 1s, 2s, 4s...)
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    def strip_query_params(u: str) -> str:
        parsed = urlparse(u)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

    # 2. Use a transaction to ensure the database operation is atomic.
    # This prevents partial data writes if an error occurs.
    try:
        with transaction.atomic():
            clean_url_key = url.strip()
            if Url.objects.filter(url_ctrk=clean_url_key).exists():
                return

            # 3. Make the request. The session handles retries automatically.
            # `raise_for_status()` will raise an HTTPError for non-2xx codes
            # after all retries are exhausted.
            response = session.get(
                clean_url_key, 
                headers=HEADERS, 
                proxies=PROXIES, 
                timeout=25
            )
            response.raise_for_status()

            redirected_url = response.url.strip()
            general_url = strip_query_params(redirected_url)

            Url.objects.create(
                url_ctrk=clean_url_key,
                redirected_url=redirected_url,
                general_url=general_url,
                last_scraped=timezone.now()
            )

    # 4. Catch specific exceptions for better error handling.
    except requests.exceptions.RequestException as e:
        # This catches connection errors, timeouts, and HTTP errors after retries fail.
        error_message = f"Network/HTTP error scraping {url}: {str(e)}"
        ScrapeData.objects.create(
            task="Scrape General URL",
            succes=False,
            major_error=False,
            error=error_message,
            execution_date=timezone.now()
        )
    except Exception as e:
        # Catch any other unexpected errors.
        error_message = f"An unexpected error occurred scraping {url}: {str(e)}"
        ScrapeData.objects.create(
            task="Scrape General URL",
            succes=False,
            major_error=False,
            error=error_message,
            execution_date=timezone.now()
        )

def sendPushNotifications(analysis: GmailSaleAnalysis, probability_threshold=0.925):
    """
    This function sends push notifications to users who have subscribed to the store,
    respecting the store's gender preference settings.
    """

    def chunk_tokens(token_list, chunk_size=100):
        """
        Yields chunks of a list.
        """
        for i in range(0, len(token_list), chunk_size):
            yield token_list[i:i + chunk_size]

    def send_batch_notifications(tokens, title, body, data):
        """
        Sends notifications in batches to the Expo Push API.
        """
        task_name = "Send Push Notifications"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }

        for token_chunk in chunk_tokens(tokens):
            messages = [{
                'to': token,
                'title': title,
                'body': body,
                'data': data
            } for token in token_chunk]

            try:
                response = requests.post(EXPO_PUSH_URL, json=messages, headers=headers)
                response.raise_for_status()
                # print("Batch sent:", response.json())
            except requests.exceptions.RequestException as e:
                print(f"Failed to send batch: {e}")
                ScrapeData.objects.create(
                    task=task_name,
                    succes=False,
                    major_error=True,
                    error=str(e),
                    execution_date=timezone.now()
                )
            else:
                print("Batch sent successfully.")

    def filter_subscribers_by_store_gender(store, subscribers_queryset, target_email=None):
        if store.genderPreferenceSet:
            if target_email and target_email.lower().strip() == "gijsgprojects@gmail.com":
                return subscribers_queryset.filter(extrauserinformation__gender__in=[0, 2])
            elif target_email and target_email.lower().strip() == "donnapatrona79@gmail.com":
                return subscribers_queryset.filter(extrauserinformation__gender__in=[1, 2])
            else:
                # Log unexpected mismatch
                ScrapeData.objects.create(
                    task="Gender filter",
                    succes=False,
                    major_error=False,
                    error=f"Unknown target email for gender-preferenced store: {target_email}",
                    execution_date=timezone.now()
                )
                return subscribers_queryset.none()
        else:
            return subscribers_queryset

    if analysis.is_sale_mail and not analysis.is_personal_deal and analysis.deal_probability > probability_threshold:
        if analysis.message.store:
            store = analysis.message.store
            subscribers = filter_subscribers_by_store_gender(
                store, store.subscriptions.all(), target_email=analysis.message.email_to
            )

            expo_tokens = list(
                subscribers.select_related('extrauserinformation')
                .filter(extrauserinformation__expoToken__isnull=False)
                .exclude(extrauserinformation__expoToken='')
                .values_list('extrauserinformation__expoToken', flat=True)
            )

            if expo_tokens:
                title = f"{store.name}: {analysis.title}"
                grabber = analysis.grabber if analysis.grabber != 'N/A' else "Nieuwe deal beschikbaar!"
                body = grabber
                data = {
                    "page": "SaleDetail",
                    "analysisId": analysis.id,
                }
                send_batch_notifications(expo_tokens, title, body, data)

def generate_analysis_from_gemini_data(message, data):

    def safe_parse_analysis(data) -> dict:
        parsed_data = data.copy() 
        if parsed_data.get('is_sale_mail') and parsed_data.get('deal_probability') > 0.85:
            # All the data points should be valid
            if parsed_data.get('title') == "N/A" or not parsed_data.get('title'):
                # No valid title returned by gemini
                parsed_data['is_sale_mail'] = False
        return parsed_data

    data = safe_parse_analysis(data=data)

    if data.get('is_sale_mail') and data.get('main_link'):
        # scrape the url
        scrape_and_save_url(url=data.get('main_link'))

    if len(data["title"].split()) > 7:
        ScrapeData.objects.create(
            task="Generating analysis from gemini data",
            succes=False,
            major_error=False,
            error = f"Title returned by gemini is false:\n{data['title']}",
            execution_date=timezone.now()
        )
        return None
    
    analysis = GmailSaleAnalysis.objects.create(
        message=message,
        is_sale_mail=data["is_sale_mail"],
        is_personal_deal=data["is_personal_deal"],
        title=data["title"],
        grabber=data["grabber"],
        description=data["description"],
        main_link=data["main_link"],
        highlighted_products=data["highlighted_products"],
        deal_probability=data["deal_probability"],
        is_new_deal_better=data["is_new_deal_better"]
    )

    return analysis

def analyze_gmail_messages(max_analyses=10):

    def shorten_email_html(full_html: str) -> str:
        """
        Extract and return only the <body> content from a full HTML email.
        This removes <head> and other non-body elements to reduce size.
        """
        soup = BeautifulSoup(full_html, "html.parser")
        body = soup.body
        if body:
            for tag in body.find_all(True):
                if tag.has_attr('style'):
                    del tag['style']
                if tag.has_attr('class'):
                    del tag['class']

            if len(str(body)) > 10000:
                dif = len(str(body)) - len(full_html)
                print(f"Waarschuwing: E-mail HTML is nog steeds erg lang ({len(str(body))} tekens).\n{dif} tekens zijn verloren")

            return str(body)
        else:
            return full_html
       
    messages_to_analyse = GmailMessage.objects.filter(analysis__isnull=True).order_by('-received_date')
    messages_subset = messages_to_analyse[:max_analyses]
    successfully_analyzed = 0

    with transaction.atomic():
        # Get a list of messages that are not currently locked by another process
        # and lock them for this transaction.
        messages_to_analyse = GmailMessage.objects.select_for_update(skip_locked=True).filter(
            analysis__isnull=True, 
            in_analysis=False
        ).order_by('-received_date')
        
        messages_subset = list(messages_to_analyse[:max_analyses])

        # Mark all messages in our subset as "in_analysis" in a single, efficient query
        message_ids = [msg.id for msg in messages_subset]
        GmailMessage.objects.filter(id__in=message_ids).update(in_analysis=True)

    num_messages = len(messages_subset)

    for i, message in enumerate(messages_subset):
        try:
            # Get a prompt addition: introduce the last two 'deals' in the same inbox
            # This will be used to determine if the deal is new 
            
            store = message.store
            email_to = message.email_to
            # only get analyses with the same store and inbox
            gmailMessages = GmailMessage.objects.filter(store=store, email_to=email_to, analysis__isnull=False).order_by('-received_date')
            prompts = []
            for old_message in gmailMessages:
                if old_message.analysis:
                    if hasattr(old_message, 'analysis') and old_message.analysis.is_sale_mail:
                        if not old_message.analysis.is_personal_deal and old_message.analysis.deal_probability > 0.925:
                            prompt_part = f"Titel: {old_message.analysis.title}\n"
                            prompt_part += f"Grabber: {old_message.analysis.grabber}\n"
                            prompts.append(prompt_part)
                            if len(prompts) >= 2:
                                break
            if len(prompts) == 0:
                prompt_addition = f"Er zijn nog geen eerdere analyses gemaakt dus graag is_new_deal_better True zetten."
            else:
                prompt_addition = f"De vorige analyses van dezelfde winkel zijn geweest:\n{''.join(prompts)}. Geef aan of in deze mail een nieuwe of een betere deal staat d.m.v. is_new_deal_better = True"
            
            cleaned_html_body = shorten_email_html(message.body)

            data = None
            error = None
            try:
                response = analyze_email_with_gemini(email_html=cleaned_html_body, prompt_addition=prompt_addition)
                if not response.get('success'):
                    error = response['error']
                    ScrapeData.objects.create(
                        task = "Error with function 'analyze_email_with_gemini'",
                        succes = False,
                        major_error = False,
                        error = error,
                        execution_date=timezone.now()
                    )
                else:
                    data = response['data']
            except Exception as e:
                error = str(e)
                ScrapeData.objects.create(
                    task = "Error with function 'analyze_email_with_gemini'",
                    succes = False,
                    major_error = False,
                    error = error,
                    execution_date=timezone.now()
                )
            if data:
                analysis = None
                try:
                    analysis = generate_analysis_from_gemini_data(message=message, data=data)
                except Exception as e:
                    ScrapeData.objects.create(
                        task = "Error with function 'analyze_email_with_gemini'",
                        succes = False,
                        major_error = False,
                        error = str(e),
                        execution_date=timezone.now()
                    )

                if analysis:
                    sendPushNotifications(analysis=analysis)
                    successfully_analyzed += 1

        except Exception as e:
            ScrapeData.objects.create(
                task="Critical error in message analysis loop",
                succes=False, major_error=True, error=str(e),
                execution_date=timezone.now()
            )

        finally:
            message.in_analysis = False
            message.save()
    
    return successfully_analyzed



class Command(BaseCommand):
    help = 'Analyse gmails with gemini'

    def handle(self, *args, **options):
        execution_date = timezone.now()
        task_name = "Gemini Gmail Analysis"

        try:
            successfully_analyzed = analyze_gmail_messages(max_analyses=10)
            self.stdout.write(self.style.SUCCESS(f'Successfully analyzed {successfully_analyzed} Gmail messages.'))
        except Exception as e:
            # Log failure with error message
            ScrapeData.objects.create(
                task=task_name,
                succes=False,
                major_error=True,
                error=str(e),
                execution_date=execution_date
            )
            self.stderr.write(self.style.ERROR(f'Error during analysis: {e}'))













# END #