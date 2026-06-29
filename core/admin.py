import csv
from django.contrib import admin
from django.http import HttpResponse
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
    HouseholdMember,
)

# Register your models here.

class ExportCsvMixin:
    """
    Adds an "Export selected as CSV" action to any ModelAdmin that
    includes this mixin. Select rows in the admin list, pick this
    from the Action dropdown, get a CSV download. No extra setup,
    Django already had the pieces for this built in.
    """
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta.verbose_name_plural)
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])

        return response

    export_as_csv.short_description = "Export selected as CSV"


@admin.register(Landlord)
class LandlordAdmin(ExportCsvMixin, admin.ModelAdmin):
    list_display = ['full_name', 'phone_number', 'email', 'created_at']
    search_fields = ['full_name', 'email', 'phone_number']
    actions = ['export_as_csv']


class HousePhotoInline(admin.TabularInline):
    model = HousePhoto
    extra = 3
    fields = ['image', 'order']


@admin.register(House)
class HouseAdmin(ExportCsvMixin, admin.ModelAdmin):
    list_display = ['house_id', 'house_type', 'landlord', 'monthly_rent', 'deposit_amount', 'electricity_type', 'is_occupied']
    list_filter = ['house_type', 'electricity_type', 'is_occupied', 'landlord']
    search_fields = ['house_id']
    inlines = [HousePhotoInline]
    actions = ['export_as_csv']


class HouseholdMemberInline(admin.TabularInline):
    model = HouseholdMember
    extra = 2
    fields = ['full_name', 'relationship']
    inlines = ['HouseholdMemberInline']


@admin.register(Tenant)
class TenantAdmin(ExportCsvMixin, admin.ModelAdmin):
    list_display = ['full_name', 'house', 'phone_number', 'email', 'move_in_date', 'is_active']
    list_filter = ['is_active']
    search_fields = ['full_name', 'id_number', 'phone_number']
    actions = ['export_as_csv']


@admin.register(Payment)
class PaymentAdmin(ExportCsvMixin, admin.ModelAdmin):
    list_display = ['tenant', 'amount', 'month', 'status', 'date_paid', 'mpesa_reference']
    list_filter = ['status', 'month']
    search_fields = ['tenant__full_name', 'mpesa_reference']
    actions = ['export_as_csv']


@admin.register(WaterBill)
class WaterBillAdmin(ExportCsvMixin, admin.ModelAdmin):
    list_display = ['tenant', 'date', 'jerrican_type', 'quantity', 'amount', 'status', 'date_paid']
    list_filter = ['status', 'jerrican_type']
    search_fields = ['tenant__full_name', 'mpesa_reference']
    actions = ['export_as_csv']


@admin.register(ElectricityBill)
class ElectricityBillAdmin(ExportCsvMixin, admin.ModelAdmin):
    list_display = ['tenant', 'month', 'units_used', 'amount', 'status', 'date_paid']
    list_filter = ['status', 'month']
    search_fields = ['tenant__full_name', 'mpesa_reference']
    actions = ['export_as_csv']


@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(ExportCsvMixin, admin.ModelAdmin):
    list_display = ['tenant', 'category', 'status', 'created_at', 'updated_at']
    list_filter = ['status', 'category']
    search_fields = ['tenant__full_name', 'description']
    actions = ['export_as_csv']


@admin.register(ContactMessage)
class ContactMessageAdmin(ExportCsvMixin, admin.ModelAdmin):
    list_display = ['name', 'email', 'is_tenant', 'house_number', 'created_at', 'is_read']
    list_filter = ['is_tenant', 'is_read', 'created_at']
    search_fields = ['name', 'email', 'message', 'house_number']
    actions = ['export_as_csv']
  