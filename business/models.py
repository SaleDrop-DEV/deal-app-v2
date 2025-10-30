from django.db import models
from django.conf import settings
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
    
class SaleMessage(models.Model):
    store = models.ForeignKey(Store, 
                              on_delete=models.CASCADE, 
                              related_name='salemessages')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.CASCADE,
                                   related_name='salemessages')
    link = models.URLField(blank=False, null=False)
    title = models.CharField(max_length=255)
    grabber = models.CharField(max_length=255)
    description = models.TextField(max_length= 2500)
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
