from django.urls import path
from . import views

urlpatterns = [
	path('', views.home, name='home'),
	path('houses/', views.houses_list, name='houses_list'),
	path('houses/<str:house_id>/', views.house_detail, name='house_detail'),
	path('dashboard/', views.dashboard, name='dashboard'),
	path('tenant/', views.tenant_dashboard, name='tenant_dashboard'),
	path('landlord/', views.landlord_dashboard, name='landlord_dashboard'),
	path('api/role/', views.role_check_api, name='role_check_api'),
	path('api/tenant/dashboard/', views.tenant_dashboard_api, name='tenant_dashboard_api'),
	path('api/tenant/maintenance/', views.tenant_maintenance_api, name='tenant_maintenance_api'),
	path('api/landlord/dashboard/', views.landlord_dashboard_api, name='landlord_dashboard_api'),
	path('api/contact/', views.contact_message_api, name='contact_message_api'),
]