from django.db import models
from django.utils import timezone

class API_Errors(models.Model):
    task = models.CharField(max_length=255, blank=False, null=False)
    error = models.CharField(max_length=255, blank=False, null=False)
    execution_date = models.DateTimeField(default=timezone.now(), blank=False, null=False)

    def __str__(self):
        return f"{self.task} failed at {self.execution_date}"
    
    def to_dict(self):
        return {
            'task': self.task,
            'error': self.error,
            'execution_date': self.execution_date.strftime('%Y-%m-%d %H:%M:%S')
        }
    
class API_Errors_Site(models.Model):
    task = models.CharField(max_length=255, blank=False, null=False)
    error = models.CharField(max_length=255, blank=False, null=False)
    execution_date = models.DateTimeField(default=timezone.now(), blank=False, null=False)

    def __str__(self):
        return f"{self.task} failed at {self.execution_date}"
    
    def to_dict(self):
        return {
            'task': self.task,
            'error': self.error,
            'execution_date': self.execution_date.strftime('%Y-%m-%d %H:%M:%S')
        }