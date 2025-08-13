from celery import shared_task
from django.core.management import call_command




@shared_task
def fetch_and_process_gmail_messages_task_general():
    call_command('fetch_emails')
    call_command('analyse_emails')

@shared_task
def fetch_and_process_gmail_messages_task_female():
    call_command('fetch_emails_F')
    call_command('analyse_emails_F')

@shared_task
def refresh_tokens_task():
    """
    Calls the Django management command to refresh tokens.
    """
    call_command('refresh_tokens')