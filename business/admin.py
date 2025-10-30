from django.contrib import admin
from django.utils import timezone

from .models import BusinessProfile, BusinessLoginCode, SaleMessage, GroqAPIData

admin.site.register(BusinessProfile)
admin.site.register(BusinessLoginCode)
admin.site.register(GroqAPIData)

# Register your models here.

# Custom Admin Actions
@admin.action(description='Mark selected messages as Public Ready')
def make_public_ready(modeladmin, request, queryset):
    # When a message is marked public ready, it implies it has been reviewed
    # and no longer needs manual review. Also set sent_at for tracking.
    queryset.update(publicReady=True, needsManualReview=False, isReviewed=True, sent_at=timezone.now())
    modeladmin.message_user(request, f"{queryset.count()} messages marked as Public Ready.")

@admin.action(description='Mark selected messages for Manual Review')
def mark_for_manual_review(modeladmin, request, queryset):
    # This action flags messages for human attention. It explicitly sets publicReady to False.
    queryset.update(needsManualReview=True, publicReady=False)
    modeladmin.message_user(request, f"{queryset.count()} messages marked for Manual Review.")

@admin.action(description='Mark selected messages as Unreviewed (for re-moderation)')
def mark_as_unreviewed(modeladmin, request, queryset):
    # This action resets the review status, making it eligible for re-moderation by AI.
    # It also ensures it's not public ready or flagged for manual review.
    queryset.update(isReviewed=False, publicReady=False, needsManualReview=False)
    modeladmin.message_user(request, f"{queryset.count()} messages marked as Unreviewed.")


@admin.register(SaleMessage)
class SaleMessageAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'store',
        'created_by',
        'isReviewed',
        'needsManualReview',
        'publicReady',
        'scheduled_at',
        'sent_at',
        'created_at',
    )
    list_filter = (
        'isReviewed',
        'needsManualReview',
        'publicReady',
        'store',
        'created_by',
        'created_at',
        'scheduled_at',
    )
    search_fields = (
        'title',
        'grabber',
        'description',
        'link',
        'store__name',  # Allows searching by store name
        'created_by__email', # Allows searching by creator's email
    )
    readonly_fields = ('created_at', 'sent_at',) # These fields are set automatically or upon action
    fieldsets = (
        (None, {
            'fields': ('title', 'grabber', 'description', 'link')
        }),
        ('Status & Review', {
            'fields': ('isReviewed', 'needsManualReview', 'publicReady', 'isManualReviewed'),
            'description': 'Current moderation and publication status of the message.'
        }),
        ('Scheduling & Publication', {
            'fields': ('scheduled_at', 'sent_at'),
            'description': 'When the message is planned to be sent or was actually sent.'
        }),
        ('Origin', {
            'fields': ('store', 'created_by', 'created_at'),
            'classes': ('collapse',), # Makes this section collapsible by default
            'description': 'Information about the message\'s origin and creation.'
        }),
    )
    actions = [make_public_ready, mark_for_manual_review, mark_as_unreviewed]
    list_per_page = 25 # Display 25 items per page
