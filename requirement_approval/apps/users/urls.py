from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'users'

urlpatterns = [
    path('', RedirectView.as_view(url='login/', permanent=False), name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('department-stats/', views.department_stats_view, name='department_stats'),
    path('reports/', views.reports_view, name='reports'),
    path('user-management/', views.user_management_view, name='user_management'),
    path('user/<int:user_id>/edit/', views.user_edit_view, name='user_edit'),
    path('user/<int:user_id>/toggle-active/', views.user_toggle_active_view, name='user_toggle_active'),
    path('user/<int:user_id>/delete/', views.user_delete_view, name='user_delete'),
]
