from django.db import models
from django.db.models import Q
from django.conf import settings
import tldextract
import os
from django.utils import timezone

# Create your models here.
User = settings.AUTH_USER_MODEL
# User = get_user_model() 

class GmailMessage(models.Model):
    gmail_message_id = models.CharField(max_length=255)
    sender = models.CharField(max_length=255)
    subject = models.CharField(max_length=1024)
    body = models.TextField()
    received_date = models.DateTimeField()
    email_to = models.CharField(max_length=255, blank=False, null=False)
    in_analysis = models.BooleanField(default=False)

    store = models.ForeignKey('Store', null=True, blank=False, on_delete=models.SET_NULL)

    def save(self, *args, **kwargs):
        if self.sender and not self.store:
            try:
                email = self.sender.split('<')[1].split('>')[0].strip()
            except IndexError:
                email = self.sender.strip()
            
            full_domain, registered_domain, domain_root = self.extract_domain_parts_email(email)
            domain_candidates = [d.lower() for d in [full_domain, registered_domain, domain_root] if d]

            match = None
            for domain in domain_candidates:
                for store in Store.objects.all():
                    if domain in store.domain_list:
                        match = store
                        self.store = match
                        break
                if match:
                    break


        super().save(*args, **kwargs)


    def extract_domain_parts_email(self, email):
        """
        Returns a tuple:
        (full_domain, registered_domain, domain_root)

        e.g., for 'info@mail.example.co.uk':
        -> ('mail.example.co.uk', 'example.co.uk', 'example')
        """
        try:
            # Get domain from email
            full_domain = email.split('@')[-1].strip()
            if full_domain.startswith("www."):
                full_domain = full_domain[4:]

            extracted = tldextract.extract(full_domain)
            registered_domain = f"{extracted.domain}.{extracted.suffix}" if extracted.suffix else extracted.domain
            domain_root = extracted.domain

            return full_domain, registered_domain, domain_root
        except Exception:
            return '', '', ''

    def is_analysed(self) -> bool:
        return self.analysis.exists()

    def __str__(self):
        return f"From: {self.sender}, Subject: {self.subject}"
    
    def to_dict(self):
        def get_domain(sender):
            return sender.split('@')[1]

        def extract_domain_from_email(email_address: str) -> str:
                if '@' not in email_address:
                    raise ValueError("Invalid email address: Missing '@' symbol.")
                # Split the email address into local part and domain part
                _, domain_part = email_address.split('@', 1)
                # Split the domain part by '.'
                domain_components = domain_part.split('.')
                # The main domain and TLD are typically the last two components
                # For example, in "news.carhartt-wip.com", it's "carhartt-wip.com"
                # In "example.com", it's "example.com"
                if len(domain_components) < 2:
                    raise ValueError(f"Invalid domain format: '{domain_part}'. Not enough components.")

                # Combine the second-to-last component (main domain) and the last component (TLD)
                return f"{domain_components[-2]}.{domain_components[-1]}".replace(">", "")
        
        return {
            'gmail_message_id': self.gmail_message_id,
            'sender': self.sender,
            'domain': extract_domain_from_email(self.sender),
            'subject': self.subject,
            'body': self.body,
            'received_date': self.received_date.strftime('%Y-%m-%d %H:%M:%S')
        }
    
class GmailSaleAnalysis(models.Model):
    message = models.OneToOneField(GmailMessage, on_delete=models.CASCADE, related_name="analysis")
    is_sale_mail = models.BooleanField(null=False, blank=False)
    is_personal_deal = models.BooleanField(null=False, blank=False)
    title = models.TextField(null=True, blank=True)
    grabber = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    main_link = models.TextField(null=True, blank=True)
    highlighted_products = models.JSONField(null=True, blank=True)
    deal_probability = models.FloatField()


    def __str__(self):
        return f"Analysis for Message ID {self.message.id} - Probability: {self.deal_probability}"
    
    def to_dict(self):
        data = {
            'gmail_data': self.message.to_dict(),
            'is_sale_mail': self.is_sale_mail,
            'is_personal_deal': self.is_personal_deal,
            'title': self.title,
            'grabber': self.grabber,
            'description': self.description,
            'main_link': self.main_link,
            'highlighted_products': self.highlighted_products,
            'deal_probability': self.deal_probability
        }
        # Attempt to find a matching store
        if self.message.store:
            data['store'] = self.message.store.to_dict()
        else:
            data['store'] = None  # fallback, should be rare given your queryset

        return data
    
class StoreQuerySet(models.QuerySet):
    def search(self, query):
        if not query:
            return self.none()
        # Assuming you add a description field, or just search on name for now
        return self.filter(Q(name__icontains=query))  # Add description__icontains if description exists

class StoreManager(models.Manager):
    def get_queryset(self):
        return StoreQuerySet(self.model, using=self._db)
    
    def search(self, query):
        return self.get_queryset().search(query)

class Store(models.Model):
    GENDER_CHOICES = (
        ('M', 'Male'), # use gijsgprojects@gmail.com
        ('F', 'Female'), # use .......
        ('B', 'Both'), # here only one email needs to be given (gijsgprojects@gmail.com)
    )

    name = models.CharField(max_length=255, verbose_name="Store Name", help_text="Full store name")
    email_addresses = models.TextField(blank=False, null=False) # Store emails like: "email1@example.com,email2@example.com"
    domain = models.CharField(max_length=255, blank=True, null=False) # from website
    subscriptions = models.ManyToManyField(User, related_name='subscribed_stores', blank=True)
    home_url = models.URLField(blank=False, null=False)
    sale_url = models.URLField(blank=True, null=True)
    image_url = models.CharField(max_length=255, blank=True, null=False)

    domain_list = models.JSONField(blank=True, null=True) # stores at least the domain created at new. later we can add more.
    isVerified = models.BooleanField(default=False)
    genderPreferenceSet = models.BooleanField(default=False) # False: Newsletter didn't ask for gender
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True) # only filled in if gender preference is not set
    mayUseContent = models.BooleanField(default=False)

    # NEW FIELD #
    dateIssued = models.DateTimeField(default=timezone.now(), null=False)



    objects = StoreManager()

    def __str__(self):
        return self.name
    
    def search(self, query):
        return self.get_queryset().filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    
    def is_subscribed(self, user):
        return self.subscriptions.filter(id=user.id).exists()
    
    def add_subscriber(self, user):
        self.subscriptions.add(user)
    
    def remove_subscriber(self, user):
        self.subscriptions.remove(user)
    
    def get_subscribers(self):
        return self.subscriptions.all()
    
    def delete(self, *args, **kwargs):
        # Build the full filesystem path to the file
        old_image_path = os.path.join(settings.BASE_DIR, self.image_url.lstrip('/'))
    
        if os.path.exists(old_image_path):
            os.remove(old_image_path)
    
        # Call the parent delete method to remove the model
        super().delete(*args, **kwargs)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email_addresses.split(','),
            'email_addresses_comma': self.email_addresses,
            'domain': self.domain,
            'home_url': self.home_url,
            'sale_url': self.sale_url,
            'image_url': self.image_url,
            'domain_list': self.domain_list,
            'isVerified': self.isVerified,
            'genderPreferenceSet': self.genderPreferenceSet,
            'gender': self.gender,
            'mayUseContent': self.mayUseContent
        }

class SubscriptionData(models.Model):
    """
    Stores user subscriptions to specific stores.
    Each user can have one subscription entry which contains a list of store IDs.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription_data')
    stores = models.JSONField(default=list, help_text="JSON list of subscribed store IDs")

    def __str__(self):
        return f"Subscription for {self.user.username} (ID: {self.user.id})"

    def to_dict(self):
        return {
            'user_id': self.user.id,
            'subscribed_store_ids': self.stores
        }

class ScrapeData(models.Model):
    task = models.CharField(max_length=255, blank=False, null=False)
    succes = models.BooleanField(blank=False, null=False)
    major_error = models.BooleanField(blank=False, null=False)
    error = models.TextField(blank=True, null=True)
    execution_date = models.DateTimeField(blank=False, null=False)
    
    def __str__(self):
        if self.succes:
            return f"{self.task} succesfully executed at {self.execution_date}"
        else:
            return f"{self.task} failed at {self.execution_date}"

    def to_dict(self):
        return {
            'task': self.task,
            'succes': self.succes,
            'major_error': self.major_error,
            'error': self.error,
            'execution_date': self.execution_date.strftime('%Y-%m-%d %H:%M:%S')
        }
    
class Url(models.Model):
    url_ctrk = models.URLField(unique=True)
    redirected_url = models.URLField()
    general_url = models.URLField()
    last_scraped = models.DateTimeField(null=True, blank=True)

    # NEW #
    visits_by_users = models.ManyToManyField(User, related_name='visited_urls')

    def add_visit(self, user):
        self.visits_by_users.add(user) if user not in self.visits_by_users.all() else None

    def get_users(self):
        return self.visits_by_users.all()
    
    def __str__(self):
        return self.url
    
    def to_dict(self):
        return {
            'url_ctrk': self.url_ctrk,
            'redirected_url': self.redirected_url,
            'general_url': self.general_url,
            'last_scraped': self.last_scraped
        }
    


from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from django.utils import timezone
import json

class GmailToken(models.Model):
    name = models.CharField(max_length=50, unique=True)
    token_json = models.JSONField()
    credentials_json = models.JSONField()  # Fixed typo: credentials_jsonm → credentials_json
    updated_at = models.DateTimeField(auto_now=True)

    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

    def __str__(self):
        return self.name

    def refresh_token(self):
        """Refresh this Gmail token and update it in the database."""
        creds = Credentials.from_authorized_user_info(info=self.token_json, scopes=self.SCOPES)

        if creds and creds.refresh_token:
            try:
                old_expiry = creds.expiry
                creds.refresh(Request())

                refreshed_data = json.loads(creds.to_json())
                if "refresh_token" not in refreshed_data:
                    refreshed_data["refresh_token"] = self.token_json.get("refresh_token")

                self.token_json = refreshed_data
                self.save(update_fields=["token_json", "updated_at"])

                print(f"[{self.name}] Token refreshed. Old expiry: {old_expiry}, New expiry: {creds.expiry}")
                return True

            except Exception as e:
                print(f"[{self.name}] Error refreshing token: {e}")
                return False
        else:
            print(f"[{self.name}] No refresh token available — cannot refresh.")
            return False

    def get_gmail_service(self):
        """
        Returns an authenticated Gmail API service object using stored tokens.
        If token is invalid, refresh or do full auth flow.
        """
        creds = None

        if self.token_json:
            creds = Credentials.from_authorized_user_info(info=self.token_json, scopes=self.SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print(f"[{self.name}] Token expired — refreshing...")
                self.refresh_token()
                creds = Credentials.from_authorized_user_info(info=self.token_json, scopes=self.SCOPES)
            else:
                print(f"[{self.name}] No valid token — running full authentication flow...")
                flow = InstalledAppFlow.from_client_config(self.credentials_json, self.SCOPES)
                creds = flow.run_local_server(port=0)

                self.token_json = json.loads(creds.to_json())
                self.save(update_fields=["token_json", "updated_at"])

        return build('gmail', 'v1', credentials=creds)
    
    def activate_gmail_watch(self, user_id, topic_name):
        """
        Sends a 'watch' request to the Gmail API for a given user and Pub/Sub topic.
        If unauthorized, attempts token refresh and retries.
        """
        try:
            service = self.get_gmail_service()

            request_body = {
                'topicName': topic_name,
                'labelIds': ['INBOX']
            }

            return service.users().watch(userId=user_id, body=request_body).execute()

        except HttpError as error:
            if error.resp.status in [401, 403]:
                print(f"[{self.name}] Token might be expired. Refreshing and retrying...")
                if self.refresh_token():
                    service = self.get_gmail_service()
                    request_body = {
                        'topicName': topic_name,
                        'labelIds': ['INBOX']
                    }
                    return service.users().watch(userId=user_id, body=request_body).execute()
            raise error

    def to_dict(self):
        return {
            'name': self.name,
            'token_json': self.token_json,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }

