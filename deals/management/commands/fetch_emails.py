from django.core.management.base import BaseCommand
from django.utils import timezone
from deals.models import GmailMessage, ScrapeData, GmailToken
from googleapiclient.errors import HttpError
from datetime import datetime
import base64


def get_email_parts(msg):
    plain_text_body = None
    html_body = None

    if 'parts' in msg['payload']:
        for part in msg['payload']['parts']:
            if part['mimeType'] == 'text/plain' and 'body' in part and 'data' in part['body']:
                plain_text_body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
            elif part['mimeType'] == 'text/html' and 'body' in part and 'data' in part['body']:
                html_body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
            if 'parts' in part:
                nested_plain, nested_html = get_email_parts({'payload': part})
                if nested_plain and not plain_text_body:
                    plain_text_body = nested_plain
                if nested_html and not html_body:
                    html_body = nested_html
    elif 'body' in msg['payload'] and 'data' in msg['payload']['body']:
        if msg['payload']['mimeType'] == 'text/plain':
            plain_text_body = base64.urlsafe_b64decode(msg['payload']['body']['data']).decode('utf-8', errors='ignore')
        elif msg['payload']['mimeType'] == 'text/html':
            html_body = base64.urlsafe_b64decode(msg['payload']['body']['data']).decode('utf-8', errors='ignore')
    return plain_text_body, html_body


def fetch_and_save_emails(service, gmail_address, max_emails=10, label_ids=['INBOX']):
    messages_fetched = 0
    try:
        results = service.users().messages().list(
            userId='me',
            labelIds=label_ids,
            maxResults=max_emails
        ).execute()

        messages = results.get('messages', [])
        for msg in messages:
            msg_id = msg['id']
            msg_data = service.users().messages().get(
                userId='me',
                id=msg_id,
                format='full'
            ).execute()

            headers = msg_data['payload'].get('headers', [])
            sender = subject = None
            for header in headers:
                if header['name'].lower() == 'from':
                    sender = header['value']
                elif header['name'].lower() == 'subject':
                    subject = header['value']

            plain_text_body, html_body = get_email_parts(msg_data)

            timestamp = int(msg_data.get('internalDate', 0)) / 1000.0
            received_date = timezone.make_aware(datetime.fromtimestamp(timestamp), timezone.utc)

            if not GmailMessage.objects.filter(sender=sender, subject=subject, received_date=received_date).exists():
                GmailMessage.objects.create(
                    gmail_message_id=msg_id,
                    sender=sender or "Unknown sender",
                    subject=subject or "No Subject",
                    body=html_body or plain_text_body,
                    received_date=received_date,
                    email_to=gmail_address
                )
                messages_fetched += 1
                print(f"NEW: Email from {sender} with subject '{subject}'.")

        return True, None, messages_fetched

    except HttpError as error:
        return False, str(error), messages_fetched


class Command(BaseCommand):
    help = 'Fetch and save emails from Gmail using GmailToken model'

    def handle(self, *args, **options):
        task_name = 'Fetch Gmail Emails'
        execution_time = timezone.now()

        try:
            token_obj = GmailToken.objects.get(name="gijsgprojects@gmail.com")  # adjust name
        except GmailToken.DoesNotExist:
            self.stdout.write(self.style.ERROR("No GmailToken found for 'female_account'"))
            return

        try:
            service = token_obj.get_gmail_service()
            success, error_message, count = fetch_and_save_emails(service, gmail_address="gijsgprojects@gmail.com", max_emails=50)

            if not success:
                ScrapeData.objects.create(
                    task=task_name,
                    succes=False,
                    major_error=True,
                    error=error_message or "",
                    execution_date=execution_time
                )
                self.stdout.write(self.style.ERROR(f'Failed to fetch emails: {error_message}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Emails fetched and saved successfully. Total new: {count}'))

        except Exception as e:
            ScrapeData.objects.create(
                task=task_name,
                succes=False,
                major_error=True,
                error=str(e),
                execution_date=execution_time
            )
            self.stdout.write(self.style.ERROR(f'Unexpected error: {e}'))
