from django.contrib import admin
from django.db.models import Q

from .models import GmailMessage, GmailSaleAnalysis, Store, ScrapeData, SubscriptionData, Url, GmailToken, User, Click

# Register other models without custom admin
admin.site.register(GmailSaleAnalysis)
admin.site.register(SubscriptionData)
admin.site.register(GmailToken)
admin.site.register(Click)

# --- Store Admin Configuration ---
class HasNoDescriptionFilter(admin.SimpleListFilter):
    title = 'description status'
    parameter_name = 'has_description'

    def lookups(self, request, model_admin):
        return (
            ('no', 'Without Description'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'no':
            return queryset.filter(Q(description__isnull=True) | Q(description=''))
        return queryset

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'domain', 'isVerified', 'mayUseContent', 'gender', 'dateIssued')
    search_fields = ('name', 'domain', 'home_url', 'email_addresses')
    list_filter = ('isVerified', 'mayUseContent', 'gender', 'genderPreferenceSet', HasNoDescriptionFilter)
    readonly_fields = ('dateIssued', 'slug')
    fieldsets = (
        (None, {'fields': ('name', 'slug', 'description', 'home_url', 'sale_url', 'email_addresses')}),
        ('Configuration', {'fields': ('isVerified', 'genderPreferenceSet', 'gender', 'mayUseContent', 'isWeirdDomain')}),
        ('Media & Domain', {'fields': ('image_url', 'domain', 'domain_list', 'dateIssued')}),
    )

# --- GmailMessage Admin Configuration ---
class HasStoreFilter(admin.SimpleListFilter):
    title = 'Store linked'
    parameter_name = 'has_store'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'With Store'),
            ('no', 'Without Store'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(store__isnull=False)
        if self.value() == 'no':
            return queryset.filter(store__isnull=True)
        return queryset

class GmailMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'subject', 'received_date', 'store')
    search_fields = ('sender', 'subject', 'body')
    list_filter = (HasStoreFilter,)

if admin.site.is_registered(GmailMessage):
    admin.site.unregister(GmailMessage)
admin.site.register(GmailMessage, GmailMessageAdmin)


# --- ScrapeData Admin Configuration ---
class ScrapeDataAdmin(admin.ModelAdmin):
    list_display = ('task', 'succes', 'major_error', 'execution_date')
    search_fields = ('task', 'error')
    list_filter = ('task', 'succes', 'major_error', 'execution_date')

if admin.site.is_registered(ScrapeData):
    admin.site.unregister(ScrapeData)
admin.site.register(ScrapeData, ScrapeDataAdmin)


# --- Url Admin Configuration ---
@admin.register(Url)
class UrlAdmin(admin.ModelAdmin):
    # Columns to display in the list view
    list_display = ('general_url', 'last_scraped', 'user_visit_count')
    
    # Enable searching across these URL fields
    search_fields = ('url_ctrk', 'redirected_url', 'general_url')
    
    # Add a filter for the 'last_scraped' date
    list_filter = ('last_scraped',)
    
    # Improve the interface for the many-to-many field in the detail view
    filter_horizontal = ('visits_by_users',)

    # Use the @admin.display decorator for the custom column
    @admin.display(description='User Visits')
    def user_visit_count(self, obj):
        """Returns the number of users who have visited the URL."""
        return obj.visits_by_users.count()
