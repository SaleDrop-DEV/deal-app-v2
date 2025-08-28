from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

from deals.models import GmailMessage, GmailSaleAnalysis, ScrapeData, Url

import os
import json
import requests
from time import sleep
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse

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

def analyze_email_with_gemini_refined(email_html, sender, subject):
    """
    Analyseer e-mailinhoud met Gemini API en retourneer data passend bij GmailSaleAnalysis model.
    """

    prompt = (
        f"Analyseer de onderstaande e-mailinhoud en bepaal of het een uitverkoop betreft. "
        f"Negeer welkomsmails en algemene reclame. "
        f"Extraheer de volgende velden nauwkeurig:\n\n"
        f"- is_sale_mail: true/false\n"
        f"- is_personal_deal: true/false\n"
        f"- title: string (Een **zeer korte titel** van maximaal 5 woorden, bijv. 'SALE MANGO' of 'Nieuwe collectie'. Gebruik geen kortingspercentages hier.)\n"
        f"- grabber: string (Een **korte, pakkende kortingszin**, zoals '-70% korting' of 'Tot 50% korting'. Dit is de belangrijkste promotiezin.)\n"
        f"- description: string (Een **neutrale, redactionele beschrijving** van de aanbieding. Dit mag langere details bevatten. \
          Vermijd bezittelijke voornaamwoorden, persoonlijke verwijzingen en directe marketing-taal. Geef een korte en duidelijke samenvatting van de aanbieding, geschreven in een casual toon.)\n"
        f"- main_link: string (URL naar de sale)\n"
        f"- highlighted_products: array van objecten met {{title, new_price, old_price, product_image_url, link}}\n"
        f"- deal_probability: float (tussen 0 en 1, met hoe zeker je bent dat dit een echte sale is)\n\n"
        f"Als een variabele er niet is, gebruik dan 'N/A'.\n"
        f"Geef de output als een JSON object dat het gevraagde schema volgt.\n"
        # f"Sender: {sender}\n"
        # f"Subject: {subject}\n"
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
    
    # ... (rest of the function, including API call, remains the same)

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

    # API call and data processing
    response = requests.post(GEMINI_API_URL, headers=HEADERS, data=json.dumps(payload))
    response.raise_for_status()
    result = response.json()

    parts = result.get('candidates', [{}])[0].get('content', {}).get('parts', [])
    if not parts:
        return None

    json_text = parts[0].get('text', '{}')
    parsed = json.loads(json_text)

    # Normalize and validate values
    return {
        "is_sale_mail": parsed.get("is_sale_mail", False),
        "is_personal_deal": parsed.get("is_personal_deal", False),
        "title": parsed.get("title"),
        "grabber": parsed.get("grabber"),
        "description": parsed.get("description"),
        "main_link": parsed.get("main_link"),
        "highlighted_products": parsed.get("highlighted_products", []),
        "deal_probability": float(parsed.get("deal_probability", 0.0))
    }


def get_unanalyzed_gmail_messages():
    """
    Returns all GmailMessages that do NOT have any related analysis.
    """
    return GmailMessage.objects.filter(analysis__isnull=True).order_by('-received_date')

def get_response(url, retries=4):
    response = None
    for _ in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=10)
            if response.status_code == 200:
                return response
            else:
                sleep(1.5)
        except:
            sleep(1.5)
    raise RuntimeError(f"Max retries exceeded.")
            
def scrape_and_save_general_url(url):
    def strip_query_params(url):
        parsed = urlparse(url)
        clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
        return clean_url
    try:
        does_url_exist = Url.objects.filter(url_ctrk=url).exists()
        if does_url_exist:
            return
        response = get_response(url)#requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=10)
        if response.status_code == 200:
            redirected_url = response.url
            general_url = strip_query_params(redirected_url)
            Url.objects.create(url_ctrk=url.strip(), redirected_url=redirected_url.strip(), general_url=general_url.strip(), last_scraped=timezone.now())
            return
        else:
            print(f"[ERROR] Statuscode: {response.status_code}")
            return
    except Exception as e:
        ScrapeData.objects.create(
            task="Scrape General URL",
            succes=False,
            major_error=True,
            error=str(e),
            execution_date=timezone.now()
        )
        print(f"Error scraping {url}: {e}")

def sendPushNotifications(analysis: GmailSaleAnalysis):
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

    if analysis.is_sale_mail and not analysis.is_personal_deal and analysis.deal_probability > 0.925:
        if analysis.message.store:
            store = analysis.message.store
            subscribers = filter_subscribers_by_store_gender(
                store, store.subscriptions.all(), target_email=analysis.message.email_to
            )
            expo_tokens = [
                subscriber.extrauserinformation.expoToken
                for subscriber in subscribers
                if hasattr(subscriber, 'extrauserinformation') and subscriber.extrauserinformation.expoToken
            ]

            if expo_tokens:
                title = f"{store.name}: {analysis.title}"
                body = f"{analysis.grabber}"
                data = {
                    "page": "SaleDetail",
                    "analysisId": analysis.id,
                }
                send_batch_notifications(expo_tokens, title, body, data)

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
    messages_to_analyse = get_unanalyzed_gmail_messages()
    messages_subset = messages_to_analyse[:max_analyses]
    num_messages = len(messages_subset)
    for i, message in enumerate(messages_subset):
        in_analysis = message.in_analysis
        if not in_analysis:
            message.in_analysis = True
            message.save()
            cleaned_html_body = shorten_email_html(message.body)
            analysis_data = analyze_email_with_gemini(cleaned_html_body, message.sender, message.subject)
            if analysis_data is None:
                print("Error occured with fetching the data from gemini.")
                ScrapeData.objects.create(
                    task="Analyze Gmail Messages",
                    succes=False,
                    major_error=False,
                    error="Error occured with fetching the data from gemini.",
                    execution_date=timezone.now()
                )
                message.in_analysis = False
                message.save()
                continue
            if analysis_data["is_sale_mail"]:
                scrape_and_save_general_url(analysis_data["main_link"])
            if analysis_data:
                analysis = GmailSaleAnalysis.objects.create(
                    message=message,
                    is_sale_mail=analysis_data["is_sale_mail"],
                    is_personal_deal=analysis_data["is_personal_deal"],
                    title=analysis_data["title"],
                    grabber=analysis_data["grabber"],
                    description=analysis_data["description"],
                    main_link=analysis_data["main_link"],
                    highlighted_products=analysis_data["highlighted_products"],
                    deal_probability=analysis_data["deal_probability"]
                )
                sendPushNotifications(analysis=analysis)
                if i < num_messages - 1: # If it's not the last message
                    sleep(1.5)
        #else:
        #    raise ValueError(f"Failed to analyze email (id={message.id}).")




class Command(BaseCommand):
    help = 'Analyse gmails with gemini'

    def handle(self, *args, **options):
        execution_date = timezone.now()
        task_name = "Gemini Gmail Analysis"

        try:
            analyze_gmail_messages(max_analyses=10)
            # Log success
            # ScrapeData.objects.create(
            #     task=task_name,
            #     succes=True,
            #     major_error=False,
            #     error=None,
            #     execution_date=execution_date
            # )
            self.stdout.write(self.style.SUCCESS('Successfully analyzed up to 10 Gmail messages.'))
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
