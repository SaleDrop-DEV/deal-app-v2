from django.urls import path
from . import views

urlpatterns = [
    path('personal/', views.personal_deals_view, name='personal_deals'),
    path('public/', views.public_deals_view, name='public_deals'),
    path('all/', views.all_deals_view, name='all_deals'),
    path('my-sales/', views.client_deals_view, name='client_deals'),

    path('visit/<int:gmail_analysis_id>/<int:user_id>/', views.visit_sale_view, name='visit_sale'),

    path('stores-manager/', views.stores_manager_view, name='stores_manager'),
    path('stores-manager/edit/<int:store_id>/', views.edit_store_view, name='edit_store'),
    path('stores-manager/delete/<int:store_id>/', views.delete_store_view, name='delete_store'),

    path('stores-subscriptions/', views.stores_view, name='stores'),
    path('toggle-subscription/', views.toggle_subscription, name='toggle_subscription'),

    path('store/<int:store_id>/', views.store_sales_view, name='store_sales'),

]