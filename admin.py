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
    search_fields = ['teacher_name', 'email']
    inlines = [BookingDetailInline]  # 讓管理員點進去就能看到這筆單分別扣了哪幾台車

@admin.register(DeviceInventory)
class DeviceInventoryAdmin(admin.ModelAdmin):
    list_display = ['device_type', 'cart_name', 'capacity', 'available_qty']
    list_editable = ['available_qty']  # 允許管理員直接在後台手動校正每台車的數量