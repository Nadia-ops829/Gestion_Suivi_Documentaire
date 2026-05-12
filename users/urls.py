from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('me/', views.me_view, name='me'),
    path('users/', views.users_list_create_view, name='users_list_create'),
    path('users/unlock/', views.unlock_user_view, name='unlock_user'),
]
