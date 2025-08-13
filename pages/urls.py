from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('contact/', views.contact, name='contact'),
    path('for-business/', views.for_business, name='for_business'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-of-service/', views.general_terms, name='general_terms'),
    path('alle-winkels/', views.all_stores, name='all_stores')
    

]