from celery import shared_task
from api.models import API_Errors_Site
from django.core.management import call_command


@shared_task
def moderate_created_sale_messages():
    try:
        call_command('moderate')
    except Exception as e:
        API_Errors_Site.objects.create(
            task="moderate_created_sale_messages",
            error=str(e)
        )

@shared_task
def disperse_ready_sale_messages():
    try:
        call_command('disperse_sales')
    except Exception as e:
        API_Errors_Site.objects.create(
            task="disperse_ready_sale_messages",
            error=str(e)
        )