from deals.models import GmailToken
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Refresh Gmail token'

    def handle(self, *args, **options):
        try:
            for token in GmailToken.objects.all():
                self.stdout.write(f"token.name: {str(token.name)}")
                token.update_token()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error refreshing tokens: {e}'))
        self.stdout.write(self.style.SUCCESS('Gmail token refreshed.'))
