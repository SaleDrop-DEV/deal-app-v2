from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('sign-up/', views.signup_view, name='signup_view'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('complete-profile/', views.complete_profile, name='complete_profile'),
    path('log-out/', views.logout_view, name='logout'),
    path('log-in/', views.CustomLoginView.as_view(), name='login'),
    path('profile/', views.account_view, name='account_view'),
    path('change-password/', views.change_password, name='password_change'),
    path('account/change-password/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='registration/password_change_done.html'
    ), name='password_change_done'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
]
