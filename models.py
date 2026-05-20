from django.db import models
from django.contrib.auth.models import User

# 1. 載具庫存資料表
class DeviceInventory(models.Model):
    DEVICE_CHOICES = [
        ('iPad', 'iPad'),
        ('Chromebook', 'Chromebook'),
        ('SurfaceGo', 'SurfaceGo'),
        ('Acer', 'Acer小筆電'),
    ]
    device_type = models.CharField('載具類型', max_length=20, choices=DEVICE_CHOICES)
    cart_name = models.CharField('車次/散裝名稱', max_length=20)  # 例如: A車, B車, 散裝
    capacity = models.IntegerField('總容量')
    available_qty = models.IntegerField('當前可用數量')

    def __str__(self):
        return f"{self.device_type} - {self.cart_name} (剩餘: {self.available_qty}/{self.capacity})"

# 2. 預約主檔資料表（對應你的 HTML 表單欄位）
class Booking(models.Model):
    email = models.EmailField('電子郵件')
    agree_rules = models.CharField('同意條款', max_length=100)
    teacher_name = models.CharField('借用教師姓名', max_length=50)
    phone = models.CharField('聯絡電話', max_length=50)
    context = models.CharField('使用情境', max_length=100, blank=True)
    course_name = models.CharField('課程名稱', max_length=100, blank=True)
    class_name = models.CharField('使用班級', max_length=50, blank=True)
    location = models.CharField('使用地點', max_length=100, blank=True)
    
    booking_type = models.CharField('預約類型', max_length=20)
    single_date = models.DateField('單次日期', null=True, blank=True)
    single_period = models.CharField('單次節次', max_length=50, blank=True)
    
    agree_period = models.CharField('同意週期規範', max_length=10, blank=True)
    start_date = models.DateField('週期開始', null=True, blank=True)
    end_date = models.DateField('週期結束', null=True, blank=True)
    periods_json = models.TextField('每週借用節次(JSON)', blank=True) # 儲存複選節次
    exclude_date = models.CharField('排除日期', max_length=200, blank=True)
    
    device_type = models.CharField('預約載具類型', max_length=20)
    required_quantity = models.IntegerField('需求總數量')
    special_needs = models.TextField('特殊需求', blank=True)
    pickup_person = models.CharField('預計取用人員', max_length=50, blank=True)
    
    created_at = models.DateTimeField('申請時間', auto_now_add=True)
    status = models.CharField('狀態', max_length=20, default='借用中')  # 借用中 / 已歸還

    def __str__(self):
        return f"{self.teacher_name} - {self.device_type}({self.required_quantity}台)"

# 3. 預約扣減明細表（紀錄這筆預約分別扣了哪幾部車）
class BookingDetail(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='details')
    inventory = models.ForeignKey(DeviceInventory, on_delete=models.CASCADE)
    borrowed_qty = models.IntegerField('借出數量')