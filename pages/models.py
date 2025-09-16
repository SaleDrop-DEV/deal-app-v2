from django.db import models
from django.conf import settings
from django.contrib.humanize.templatetags.humanize import naturaltime
import os

User = settings.AUTH_USER_MODEL 

class recommendation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    store = models.CharField(max_length=225, blank=False, null=False)
    handled = models.BooleanField(default=False)
    date_sent = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.store
    
    def to_dict(self):
        return {
            'id': self.id,
            'user': self.user.id,
            'store': self.store,
            'isHandled': self.handled,
            'date_sent': self.date_sent
        }

class Notification(models.Model):
    title = models.CharField(max_length=225, blank=False, null=False)
    description = models.CharField(max_length=225, blank=False, null=False)
    time_ago = models.CharField(max_length=225, blank=False, null=False)

    def __str__(self):
        return self.title
    
    def to_dict(self):
        return {
            'title': self.title,
            'description': self.description,
            'time': self.time_ago
        }
    
class BusinessRequest(models.Model):
    store_name = models.CharField(max_length=225, blank=False, null=False)
    store_email = models.CharField(max_length=225, blank=False, null=False)
    store_phone_number = models.CharField(max_length=225, blank=False, null=False)
    message = models.CharField(max_length=225, blank=False, null=False)
    date_sent = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.store_name

    def to_dict(self):
        return {
            'id': self.id,
            'store_name': self.store_name,
            'store_email': self.store_email,
            'store_phone_number': self.store_phone_number,
            'message': self.message,
            'date_sent': self.date_sent.strftime('%d %b %Y, %H:%M'),
            'date_sent_natural': naturaltime(self.date_sent)
        }
    

class StaticContent(models.Model):
    content_name = models.CharField(max_length=225, blank=False, null=False)
    dimensions = models.CharField(max_length=225, blank=False, null=False)
    image_url = models.CharField(max_length=255, blank=True, null=False)
    required = models.BooleanField(default=False)
    date_modified = models.DateTimeField(auto_now_add=True, null=False)

    def delete(self, *args, **kwargs):
        if self.image_url:
            # remove leading slash if present
            relative_path = self.image_url.lstrip('/').replace('media/', '', 1)
            old_image_path = os.path.join(settings.MEDIA_ROOT, relative_path)
            if os.path.exists(old_image_path):
                os.remove(old_image_path)
            else:
                print(f"File not found: {old_image_path}")
        super().delete(*args, **kwargs)

    def to_dict(self):
        return {
            'id': self.id,
            'content_name': self.content_name,
            'image_url': self.image_url,
            'date_modified': self.date_modified
        }