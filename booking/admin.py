from django.contrib import admin
from .models import DeviceInventory, Booking, BookingDetail

class BookingDetailInline(admin.TabularInline):
    model = BookingDetail
    extra = 0
    readonly_fields = ['inventory', 'borrowed_qty']

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['teacher_name', 'device_type', 'required_quantity', 'booking_type', 'status', 'created_at']
    list_filter = ['device_type', 'status', 'booking_type']
    inlines = [BookingDetailInline]

@admin.register(DeviceInventory)
class DeviceInventoryAdmin(admin.ModelAdmin):
    list_display = ['device_type', 'cart_name', 'capacity', 'available_qty']