from django.contrib import admin
from .models import recommendation, Notification, BusinessRequest, StaticContent


# Create a ModelAdmin class to customize the admin interface
class RecommendationAdmin(admin.ModelAdmin):

    list_filter = ('handled',)

    # Optional: You can also add 'handled' to the list_display to show the
    # status directly in the table view.
    list_display = ('store', 'user', 'handled', 'date_sent')


# Register the recommendation model with the custom admin class
admin.site.register(recommendation, RecommendationAdmin)
admin.site.register(Notification)
admin.site.register(BusinessRequest)
admin.site.register(StaticContent)

