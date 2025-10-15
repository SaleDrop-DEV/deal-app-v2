from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('contact/', views.contact, name='contact'),
    path('for-business/', views.for_business, name='for_business'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-of-service/', views.general_terms, name='general_terms'),
    path('alle-winkels/', views.all_stores, name='all_stores'),
    path('delete-account-policy/', views.delete_account_policy, name='delete_account_policy'),

    path('admin/static-content/', views.static_content_manager, name='static_content_manager'),
    path('admin/static-content/edit/', views.static_content_edit, name='static_content_edit'),
    path('admin/static-content/delete/<int:content_id>/', views.static_content_delete, name='static_content_delete'),

    path('test-notification/', views.test_notification, name='test_notification'),
    path('.well-known/apple-app-site-association/', views.apple_app_site_association, name='apple_app_site_association'),

    

]