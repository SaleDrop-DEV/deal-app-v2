from celery import shared_task
from django.core.mail import send_mail
from .models import API_Errors_Site # Assuming this model is in the same app

@shared_task
def send_new_recommendation_email(store_name):
    """
    Sends a notification email to admins about a new store recommendation.
    This task runs in the background.
    """
    subject = 'SaleDrop Admin | Nieuwe winkel aanvraag is binnengekomen!'
    message = f"Er is een nieuwe winkel aanvraag binnengekomen: {store_name}"
    from_email = 'support@saledrop.app'
    recipient_list = ['u4987625257@gmail.com']

    try:
        send_mail(subject, message, from_email, recipient_list)
    except Exception as e:
        # Log the specific error that occurred
        API_Errors_Site.objects.create(
            task="send_new_recommendation_email",
            error=f"Failed to send recommendation email for '{store_name}'. Error: {str(e)}"
        )
