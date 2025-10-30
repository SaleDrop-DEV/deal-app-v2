# /Users/gijs/saledrop/web_app_local/business/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('access/', views.get_access_to_business_profile_page_view, name='business_access'),
    path('dashboard/', views.business_dashboard_view, name='business_dashboard'),
    path('edit-store-profile/<int:store_id>/', views.edit_store_profile_view, name='edit_store_profile'),
    path('allow-logo-use/<int:id>/', views.allow_logo_use_view, name='allow_logo_use'),
    path('create-sale-message/', views.create_sale_message_view, name='create_sale_message'), # New URL
    path('edit-sale-message/<int:sale_id>/', views.edit_sale_message_view, name='edit_sale_message'),
    path('delete-sale-message/<int:sale_id>/', views.delete_sale_message_view, name='delete_sale_message'),
]