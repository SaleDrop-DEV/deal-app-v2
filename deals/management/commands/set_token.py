import json
import os
from django.core.management.base import BaseCommand
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from deals.models import GmailToken # Ensure this is the correct import path

class Command(BaseCommand):
    help = 'Initiates the Gmail API authentication flow and stores the token in the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--name',
            type=str,
            help='A unique name (the email address to authenticate with) to identify the GmailToken in the database.',
            required=True
        )

    def handle(self, *args, **options):
        name = options['name']
        
        # Check if the token name already exists
        if GmailToken.objects.filter(name=name).exists():
            self.stdout.write(self.style.ERROR(f'A GmailToken with the name "{name}" already exists. Please choose a different name.'))
            return
        if name == "gijsgprojects@gmail.com":
            credentials_file_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'credentials_g.json'
            )
        elif name == "donnapatrona79@gmail.com":
            credentials_file_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'credentials_d.json'
            )

        # Nieuwe logica om credentials.json aan te maken als deze niet bestaat
        if not os.path.exists(credentials_file_path):
            self.stderr.write(self.style.WARNING(f'Waarschuwing: "credentials.json" file niet gevonden op {credentials_file_path}'))
            self.stderr.write(self.style.WARNING('Er is een placeholder-bestand aangemaakt. Vul de client_id en client_secret in van je Google Cloud project en voer het commando opnieuw uit.'))
            
            placeholder_data = {
                "installed": {
                    "client_id": "JOUW_CLIENT_ID_HIER",
                    "client_secret": "JOUW_CLIENT_SECRET_HIER",
                    "redirect_uris": ["http://localhost"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://accounts.google.com/o/oauth2/token"
                }
            }
            
            with open(credentials_file_path, 'w') as f:
                json.dump(placeholder_data, f, indent=4)
            return

        self.stdout.write(f'Starting authentication flow for email: {name}')
        self.stdout.write('Please follow the instructions in your browser.')
            
        try:
            # The SCOPES are defined in the GmailToken model
            scopes = GmailToken.SCOPES
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file_path, scopes)
            creds = flow.run_local_server(port=0, prompt='consent')

            token_data = json.loads(creds.to_json())
            
            # Create a new GmailToken object and save it
            gmail_token = GmailToken.objects.create(
                name=name,
                token_json=token_data,
                credentials_json=json.load(open(credentials_file_path, 'r'))
            )
            
            self.stdout.write(self.style.SUCCESS(f'Successfully created GmailToken with name "{name}".'))
            self.stdout.write(self.style.SUCCESS('You can now use this token to activate the watch process.'))

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR('credentials.json not found. Please ensure it is in the same directory as this command file.'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'An unexpected error occurred during authentication: {e}'))

