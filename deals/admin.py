from django.contrib import admin

from .models import GmailMessage, GmailSaleAnalysis, Store, ScrapeData, SubscriptionData



admin.site.register(GmailSaleAnalysis)
admin.site.register(Store)
admin.site.register(ScrapeData)
admin.site.register(SubscriptionData)
admin.site.register(Url)
admin.site.register(GmailToken)

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

