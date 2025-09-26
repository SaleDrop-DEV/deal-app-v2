from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Store

class StoreSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        """
        Returns a list of items to be included in the sitemap.
        Each item is a tuple: (Store object, 'gender_slug').
        Gender slugs can be 'mannen', 'vrouwen', or 'beide'.
        """
        # We only want to generate URLs for verified stores.
        stores = Store.objects.filter(isVerified=True)
        sitemap_items = []

        for store in stores:
            if store.genderPreferenceSet:
                # If the store has separate gender preferences, create a URL for each.
                sitemap_items.append((store, 'mannen'))
                sitemap_items.append((store, 'vrouwen'))
            else:
                # If no gender preference is set, use the store's default gender.
                if store.gender == 'M':
                    sitemap_items.append((store, 'mannen'))
                elif store.gender == 'F':
                    sitemap_items.append((store, 'vrouwen'))
                else: # 'B' for Both
                    sitemap_items.append((store, 'beide'))

        return sitemap_items

    def lastmod(self, item):
        store_obj, _ = item
        return store_obj.dateIssued

    def location(self, item):
        store_obj, code = item
        return reverse('search_stores_sale', args=[store_obj.id, code, store_obj.slug])