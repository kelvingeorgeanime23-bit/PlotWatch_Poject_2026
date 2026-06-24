from django.contrib import admin
from .models import (
    Landlord,
    House,
    HousePhoto,
    Tenant,
    Payment,
    WaterBill,
    ElectricityBill,
    MaintenanceRequest,
    ContactMessage,
)

# Register your models here.

@admin.register(Landlord)
class LandlordAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone_number', 'email', 'created_at']
    search_fields = ['full_name', 'email', 'phone_number']


class HousePhotoInline(admin.TabularInline):
    model = HousePhoto
    extra = 3
    fields = ['image', 'order']


@admin.register(House)
class HouseAdmin(admin.ModelAdmin):
    list_display = ['house_id', 'house_type', 'landlord', 'monthly_rent', 'deposit_amount', 'electricity_type', 'is_occupied']
    list_filter = ['house_type', 'electricity_type', 'is_occupied', 'landlord']
    search_fields = ['house_id']
    inlines = [HousePhotoInline]


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'house', 'phone_number', 'email', 'move_in_date', 'is_active']
    list_filter = ['is_active']
    search_fields = ['full_name', 'id_number', 'phone_number']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'amount', 'month', 'status', 'date_paid', 'mpesa_reference']
    list_filter = ['status', 'month']
    search_fields = ['tenant__full_name', 'mpesa_reference']


@admin.register(WaterBill)
class WaterBillAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'date', 'jerrican_type', 'quantity', 'amount', 'status', 'date_paid']
    list_filter = ['status', 'jerrican_type']
    search_fields = ['tenant__full_name', 'mpesa_reference']


@admin.register(ElectricityBill)
class ElectricityBillAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'month', 'units_used', 'amount', 'status', 'date_paid']
    list_filter = ['status', 'month']
    search_fields = ['tenant__full_name', 'mpesa_reference']


@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'category', 'status', 'created_at', 'updated_at']
    list_filter = ['status', 'category']
    search_fields = ['tenant__full_name', 'description']


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'is_tenant', 'house_number', 'created_at', 'is_read']
    list_filter = ['is_tenant', 'is_read', 'created_at']
    search_fields = ['name', 'email', 'message', 'house_number']