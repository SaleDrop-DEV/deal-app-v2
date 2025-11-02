from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings

from deals.models import Store, ScrapeData
from business.models import SaleMessage

import requests

EXPO_PUSH_URL = 'https://exp.host/--/api/v2/push/send'


def sendPushNotifications(message: SaleMessage):
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

    def send_batch_notifications(tokens, title, subtitle, body, data):
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
                'subtitle': subtitle,
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

    if message.store:
        store = message.store
        subscribers = store.subscriptions.filter(email = "support@saledrop.app")

        device_expo_tokens = list(
            subscribers.prefetch_related('devices')
            .filter(devices__expo_token__isnull=False)
            .exclude(devices__expo_token='')
            .values_list('devices__expo_token', flat=True)
        )
        emoji = "🔥"  # Fire emoji for sales
        if device_expo_tokens:
            title = store.name
            subtitle = f"{emoji} {message.title}"
            grabber = message.grabber if message.grabber != 'N/A' else "Nieuwe deal beschikbaar!"
            body = grabber
            data = {
                "page": "SaleDetail",
                "analysisId": -message.id,
            }
            send_batch_notifications(device_expo_tokens, title, subtitle, body, data)


class Command(BaseCommand):
    help = 'Disperse SaleMessages that are marked as publicReady and not yet sent.'

    def handle(self, *args, **options):
        self.stdout.write("Starting to disperse ready SaleMessages...")
        for salemessage in SaleMessage.objects.filter(publicReady=True, sent_at__isnull=True).order_by('scheduled_at', 'created_at'):
            #check if we need to send
            if timezone.now() >= (salemessage.scheduled_at or timezone.now()):
                sendPushNotifications(salemessage)
                salemessage.sent_at = timezone.now()
                salemessage.save()
            self.stdout.write(self.style.SUCCESS(f"Dispersed SaleMessage ID {salemessage.id} and marked as sent."))