from django.db import models

# 1. 載具固定設備表（只記錄有哪些車，不直接在上面扣數字）
class DeviceInventory(models.Model):
    DEVICE_CHOICES = [
        ('iPad', 'iPad'),
        ('Chromebook', 'Chromebook'),
        ('SurfaceGo', 'SurfaceGo'),
        ('Acer', 'Acer小筆電'),
    ]
    device_type = models.CharField('載具類型', max_length=20, choices=DEVICE_CHOICES)
    cart_name = models.CharField('車次/散裝名稱', max_length=20)  # 例如: A車, B車, 散裝
    capacity = models.IntegerField('該車總台數')  # 例如: A車固定 42 台

    def __str__(self):
        return f"{self.device_type} - {self.cart_name} (總計: {self.capacity}台)"

# 2. 預約紀錄表
class Booking(models.Model):
    email = models.EmailField('電子郵件')
    agree_rules = models.CharField('同意條款', max_length=100)
    teacher_name = models.CharField('借用教師姓名', max_length=50)
    phone = models.CharField('聯絡電話', max_length=50)
    context = models.CharField('使用情境', max_length=100, blank=True)
    course_name = models.CharField('課程名稱', max_length=100, blank=True)
    class_name = models.CharField('使用班級', max_length=50, blank=True)
    location = models.CharField('使用地點', max_length=100, blank=True)
    
    booking_type = models.CharField('預約類型', max_length=20)  # 單次預約 / 週期預約
    
    # --- 單次預約欄位變更：改為起點與終點節次 ---
    single_date = models.DateField('單次日期', null=True, blank=True)
    start_period = models.IntegerField('開始節次', null=True, blank=True)  # 例如: 1 代表第一節
    end_period = models.IntegerField('結束節次', null=True, blank=True)    # 例如: 3 代表第三節
    
    # --- 週期預約欄位 ---
    agree_period = models.CharField('同意週期規範', max_length=10, blank=True)
    start_date = models.DateField('週期開始', null=True, blank=True)
    end_date = models.DateField('週期結束', null=True, blank=True)
    periods_json = models.TextField('每週借用節次(JSON)', blank=True) # 格式如: ["Mon_1", "Mon_2"]
    exclude_date = models.CharField('排除日期', max_length=200, blank=True)
    
    device_type = models.CharField('預約載具類型', max_length=20)
    required_quantity = models.IntegerField('需求總數量')
    special_needs = models.TextField('特殊需求', blank=True)
    pickup_person = models.CharField('預計取用人員', max_length=50, blank=True)
    
    created_at = models.DateTimeField('申請時間', auto_now_add=True)
    status = models.CharField('狀態', max_length=20, default='借用中')  # 借用中 / 已歸還

    def __str__(self):
        return f"{self.teacher_name} - {self.device_type}({self.required_quantity}台)"

# 3. 系統自動分配結果明細表（記錄哪筆預約、在什麼時間、佔用了哪台車多少台）
class BookingAssignment(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='assignments')
    inventory = models.ForeignKey(DeviceInventory, on_delete=models.CASCADE)
    assigned_qty = models.IntegerField('分配借出數量')