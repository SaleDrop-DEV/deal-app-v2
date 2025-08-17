from django.urls import path
from . import views, IOS_views
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

urlpatterns = [
    # Open APIs #
    path('search-stores/', views.search_stores_api_view, name='search_stores_api'),
    path('get-popular-stores/', views.get_popular_stores_api_view, name='get_popular_stores_api'),

    # Login required APIs (for website) #
    path('subscribe-to-store/', views.subscribe_to_store_api_view, name='subscribe_to_store_api'),
    path('un-subscribe-to-store/', views.un_subscribe_to_store_api_view, name='un_subscribe_to_store_api'),
    path('request-recommendation/', views.send_recommendation_api, name='request_recommendation_api'),


    # API Authentication URLs (for JWT)
    path('get-token/', IOS_views.MyTokenObtainPairView.as_view(), name='token_obtain_pair'), #This endpoint accepts a POST request with a username and password and returns an access and refresh token pair
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'), # This endpoint accepts a POST request with a valid refresh token and returns a new access token
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'), # This endpoint accepts a POST request with an access token and returns a 200 OK status if the token is valid.

    # API register #
    path('register-new-user/', IOS_views.UserRegistrationView.as_view(), name='register_new_user'),

    # API endpoints for IOS app #
    path('fetch-my-sales/', IOS_views.IOS_API_fetch_my_sales, name='API_fetch_mysales'),
    path('fetch-my-feed/', IOS_views.IOS_API_fetch_my_feed, name='API_fetch_myfeed'),
    path('fetch-account-details/', IOS_views.IOS_API_fetch_account_details, name='API_fetch_account_details'),
    path('subscribe-to-store-api/', IOS_views.IOS_API_subscribe_to_store, name='API_subscribe_to_store'),
    path('un-subscribe-to-store-api/', IOS_views.IOS_API_un_subscribe_to_store, name='API_un_subscribe_to_store'),
    path('request-recommendation-api/', IOS_views.IOS_API_send_recommendation, name='API_request_recommendation'),
    path('search-stores-api/', IOS_views.IOS_API_search_stores, name='API_search_stores'),
    path('change-user-gender-preference/', IOS_views.IOS_API_change_user_gender_preference, name='API_change_user_gender_preference'),
    path('fetch-popular-stores/', IOS_views.IOS_API_fetch_popular_stores, name='API_fetch_popular_stores'),
    path('save-token/', IOS_views.IOS_API_save_expo_push_token, name='save-expo-push-token'),
    path('sale-details/', IOS_views.get_analysis_detail, name='get_analysis_detail'),
    path('delete-expo-push-token/', IOS_views.IOS_API_delete_expo_push_token, name='delete-expo-push-token'),
    path('delete-account/', IOS_views.IOS_API_delete_account, name='delete-account')


]
