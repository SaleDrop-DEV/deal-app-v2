from .fetch_emails import refresh_gmail_token as refresh_gmail_token_general
from .fetch_emails_F import refresh_gmail_token as refresh_gmail_token_female
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Refresh Gmail token'

    def handle(self, *args, **options):
        refresh_gmail_token_general()
        refresh_gmail_token_female()
        self.stdout.write(self.style.SUCCESS('Gmail token refreshed.'))