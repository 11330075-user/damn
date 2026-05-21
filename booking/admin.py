from django.contrib import admin
from .models import DeviceInventory, Booking, BookingAssignment

class BookingAssignmentInline(admin.TabularInline):
    model = BookingAssignment
    extra = 0
    readonly_fields = ['inventory', 'assigned_qty']

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    # 顯示欄位包含日期、開始節次、結束節次
    list_display = ['teacher_name', 'device_type', 'required_quantity', 'single_date', 'start_period', 'end_period', 'status', 'created_at']
    list_filter = ['single_date', 'device_type', 'status']
    search_fields = ['teacher_name']
    inlines = [BookingAssignmentInline]  # 點進去就能看到系統自動分配哪台車給他

@admin.register(DeviceInventory)
class DeviceInventoryAdmin(admin.ModelAdmin):
    list_display = ['device_type', 'cart_name', 'capacity']