# from .fetch_emails import activate_gmail_watch as activate_gmail_watch_general
# from .fetch_emails_F import activate_gmail_watch as activate_gmail_watch_female
from .models import GmailToken
from django.core.management.base import BaseCommand

TOPIC_NAME_general = "projects/deals-app-465712/topics/gmail-notifications"
TOPIC_NAME_female = "projects/deals-app-468610/topics/Deal-App-notifications"

class Command(BaseCommand):
    help = 'Activate Gmail watch'

    def handle(self, *args, **options):
        try:
            GmailToken.objects.get(name="gijsgprojects@gmail.com").activate_gmail_watch(user_id="gijsgprojects@gmail.com", topic_name=TOPIC_NAME_general)
            GmailToken.objects.get(name="donnapatrona79@gmail.com").activate_gmail_watch(user_id="donnapatrona79@gmail.com", topic_name=TOPIC_NAME_female)
            # activate_gmail_watch_general(user_id='gijsgprojects@gmail.com', topic_name=TOPIC_NAME_general)
            # activate_gmail_watch_female(user_id='donnapatrona79@gmail.com', topic_name=TOPIC_NAME_female)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error activating Gmail watch: {e}'))
        else:
            self.stdout.write(self.style.SUCCESS('Gmail watch activated successfully.'))
            
