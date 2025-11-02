from django.db import models
from django.conf import settings
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils import timezone

from deals.models import Store



class BusinessProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, 
                                on_delete=models.CASCADE, 
                                related_name='businessprofile')
    store = models.ForeignKey(Store, 
                              on_delete=models.CASCADE, 
                              related_name='employees')

    def __str__(self):
        return f"{self.user.email} @ {self.store.name}"
    
class EditProfileRequest(models.Model):
    business_profile = models.ForeignKey(BusinessProfile,
                                         on_delete=models.CASCADE,
                                         related_name='edit_requests')
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    is_processed = models.BooleanField(default=False)

    # fields to be edited in the store profile
    description = models.TextField(max_length=175, null=True, blank=True)
    image_url = models.CharField(max_length=255, blank=True, null=False)

class SaleMessage(models.Model):
    store = models.ForeignKey(Store, 
                              on_delete=models.CASCADE, 
                              related_name='salemessages')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.CASCADE,
                                   related_name='salemessages')
    link = models.URLField(blank=False, null=False)
    title = models.CharField(max_length=50)
    grabber = models.CharField(max_length=50)
    description = models.TextField(max_length= 300)
    created_at = models.DateTimeField(auto_now_add=True)
    isReviewed = models.BooleanField(default=False) # done by AI
    needsManualReview = models.BooleanField(default=False)
    isManualReviewed = models.BooleanField(default=False)
    publicReady = models.BooleanField(default=False) # after manual review or AI approval

    scheduled_at = models.DateTimeField(db_index=True, null=True, blank=True,
                                        help_text="If null, send immediately. If set, send at this time.")
    sent_at = models.DateTimeField(null=True, blank=True, 
                                   help_text="Timestamp of when this was successfully sent.")
    
    def __str__(self):
        return f"{self.store.name} - {self.title}"

@receiver(pre_delete, sender=SaleMessage)
def delete_related_groq_data(sender, instance, **kwargs):
    """
    Ensures that the related GroqAPIData object is deleted before
    the SaleMessage is deleted to prevent IntegrityError on OneToOneField.
    """
    if hasattr(instance, 'groq_data'):
        instance.groq_data.delete()

    
class SaleMessageClick(models.Model):
    salemessage = models.ForeignKey(SaleMessage, 
                                    on_delete=models.CASCADE, 
                                    related_name='clicks')
    clicked_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.SET_NULL,
                             null=True,
                             blank=True,
                             related_name='brand_made_salemessage_clicks')
    
class GroqAPIData(models.Model):
    salemessage = models.OneToOneField(SaleMessage, 
                                       on_delete=models.CASCADE, 
                                       related_name='groq_data')
    is_safe = models.BooleanField()
    reason = models.TextField()
    category = models.CharField(max_length=100)
    moderated_at = models.DateTimeField(auto_now_add=True)

class BusinessLoginCode(models.Model):
    email = models.EmailField(db_index=True)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        """Checks if the code is still valid (e.g., within 10 minutes)."""
        return timezone.now() < self.created_at + timezone.timedelta(minutes=10)
