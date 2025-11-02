from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib.sitemaps.views import sitemap

from deals.sitemaps import StoreSitemap
from deals import views as deals_views
from pages import views as pages_views

sitemaps = {
    'stores': StoreSitemap,
    # U kunt hier meer sitemaps toevoegen voor andere content (bv. BlogSitemap)
}

urlpatterns = [
    path('admin-app/', admin.site.urls, name='admin'),
    path('', include('pages.urls')),
    path('accounts/', include('allauth.urls')),
    path('accounts/', include('accounts.urls')),  # Allauth routes
    path('deals/', include('deals.urls')),
    path('business/', include('business.urls')),
    path('api/', include('api.urls')),
    path("robots.txt", TemplateView.as_view(
        template_name="robots.txt",
        content_type="text/plain"
    )),

    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, 
         name='django.contrib.sitemaps.views.sitemap'),

    path('webhooks/gmail/', deals_views.gmail_webhook, name='gmail_webhook'),
    #path('test/<int:gender>/', deals_views.send_simple_html_email, name='test')
]

handler404 = pages_views.custom_404_view
handler500 = pages_views.custom_500_view


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
