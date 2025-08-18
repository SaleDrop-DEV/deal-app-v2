from django.core.management.base import BaseCommand
from django.utils import timezone
from deals.models import GmailMessage, ScrapeData, GmailToken
import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
from email.utils import parseaddr


gmail_address = "gijsgprojects@gmail.com"


def fetch_and_save_emails(max_emails=10)->int:
    IMAP_SERVER = 'imap.gmail.com'
    IMAP_PORT = 993
    EMAIL_ACCOUNT = 'gijsgprojects@gmail.com'
    APP_PASSWORD = GmailToken.objects.get(name='GENERAL-IMAP').credentials_json['password']

    # Connect to Gmail
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mail.login(EMAIL_ACCOUNT, APP_PASSWORD)
    mail.select('inbox')  # Select the inbox folder

    # Search emails (ALL = every email)
    status, data = mail.search(None, 'ALL')
    mail_ids = list(reversed(data[0].split()))

    def decode_email_header(header_value):
        decoded_parts = decode_header(header_value)
        decoded_string = ''
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_string += part.decode(encoding or 'utf-8', errors='ignore')
            else:
                decoded_string += part
        return decoded_string

    def correct_sender(sender):
        name, email = parseaddr(sender)[1]
        return f"{name} <{email}>"
        

    def extract_bodies(msg):
        """
        Extracts both plain text and HTML bodies from an email message.
        Returns a tuple: (plain_text_body, html_body)
        """
        plain_text_body = None
        html_body = None

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition'))
                if 'attachment' in content_disposition:
                    continue
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                decoded = payload.decode(errors='ignore')

                if content_type == 'text/plain' and plain_text_body is None:
                    plain_text_body = decoded
                elif content_type == 'text/html' and html_body is None:
                    html_body = decoded
        else:
            content_type = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            if payload:
                decoded = payload.decode(errors='ignore')
                if content_type == 'text/plain':
                    plain_text_body = decoded
                elif content_type == 'text/html':
                    html_body = decoded

        return plain_text_body, html_body

    def get_email(msg):
        plain_text, html = extract_bodies(msg)
        return {
            'gmail_message_id': msg.get('Message-ID', ''),
            'sender': correct_sender(decode_email_header(msg.get('From', ''))),
            'subject': decode_email_header(msg.get('Subject', '')),
            'received_date': msg.get('Date', ''),
            'body': html or plain_text,  # prefer HTML if available
        }

    count = 0
    for num in mail_ids[:max_emails]:
        status, msg_data = mail.fetch(num, '(RFC822)')
        
        # msg_data can contain multiple parts; find the one with the actual email
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                raw_email = response_part[1]
                msg = email.message_from_bytes(raw_email)
                data = get_email(msg)
                
                # Parse date safely
                received_date = parsedate_to_datetime(msg.get('Date'))
                if timezone.is_naive(received_date):
                    received_date = timezone.make_aware(received_date, timezone.get_current_timezone())
                
                # Deduplication & saving
                if not GmailMessage.objects.filter(subject=data['subject'], received_date=received_date, email_to=gmail_address).exists():
                    print(f"NEW: Email from {data['sender']} with subject '{data['subject']}'.")
                    GmailMessage.objects.create(
                        gmail_message_id=data['gmail_message_id'],
                        sender = data['sender'] or "Unknown sender",
                        subject=data['subject'] or "No Subject",
                        body=data['body'],
                        received_date=received_date,
                        email_to=gmail_address
                    )
                    count += 1
    mail.close()
    mail.logout()
    return count


class Command(BaseCommand):
    help = 'Fetch and save emails from Gmail using GmailToken model'

    def handle(self, *args, **options):
        task_name = 'Fetch Gmail Emails'
        execution_time = timezone.now()
        
        fetch_and_save_emails()
        try:
            count = fetch_and_save_emails()
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
