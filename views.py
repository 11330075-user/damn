from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db import transaction
from .models import DeviceInventory, Booking, BookingDetail
import json

# 頁面 1：前端預約表單 (載入你提供的 HTML 樣式)
def booking_form(request):
    if request.method == 'POST':
        # 讀取前端 POST 來的 JSON 資料
        data = json.loads(request.body)
        
        req_qty = int(data.get('quantity', 0))
        dev_type = data.get('device_type')
        
        # 使用資料庫事務(Transaction)防止多人同時搶車造成的資料衝突
        with transaction.atomic():
            # 1. 抓出該載具有剩餘數量的車次，並按字母排序(A車->B車->C車->散裝)
            available_carts = DeviceInventory.objects.filter(
                device_type=dev_type, available_qty__gt=0
            ).order_style().order_by('cart_name')
            
            total_available = sum([c.available_qty for c in available_carts])
            if total_available < req_qty:
                return JsonResponse({'status': 'error', 'message': f'庫存不足！目前僅剩 {total_available} 台。'}, status=400)
            
            # 2. 建立預約主紀錄
            # 解析週節次複選方塊
            weeks_list = [v for k, v in data.items() if k.startswith('week_') and v != '']
            
            booking = Booking.objects.create(
                email=data.get('email'),
                agree_rules=data.get('agree_rules'),
                teacher_name=data.get('teacher_name'),
                phone=data.get('phone'),
                context=data.get('context', ''),
                course_name=data.get('course_name', ''),
                class_name=data.get('class_name', ''),
                location=data.get('location', ''),
                booking_type=data.get('booking_type'),
                single_date=data.get('single_date') or None,
                single_period=data.get('single_period', ''),
                agree_period=data.get('agree_period', ''),
                start_date=data.get('start_date') or None,
                end_date=data.get('end_date') or None,
                periods_json=json.dumps(weeks_list, ensure_ascii=False),
                exclude_date=data.get('exclude_date', ''),
                device_type=dev_type,
                required_quantity=req_qty,
                special_needs=data.get('special_needs', ''),
                pickup_person=data.get('pickup_person', '')
            )
            
            # 3. 自動扣減各車次數量 (核心演算法)
            remaining_to_deduct = req_qty
            for cart in available_carts:
                if remaining_to_deduct <= 0:
                    break
                
                if cart.available_qty >= remaining_to_deduct:
                    # 這部車夠扣
                    cart.available_qty -= remaining_to_deduct
                    BookingDetail.objects.create(booking=booking, inventory=cart, borrowed_qty=remaining_to_deduct)
                    cart.save()
                    remaining_to_deduct = 0
                else:
                    # 這部車不夠扣，把這步車扣到0，剩下的去扣下一部車
                    deduct_part = cart.available_qty
                    remaining_to_deduct -= deduct_part
                    cart.available_qty = 0
                    BookingDetail.objects.create(booking=booking, inventory=cart, borrowed_qty=deduct_part)
                    cart.save()
            
            return JsonResponse({'status': 'success', 'booking_id': booking.id})
            
    return render(request, 'booking_form.html')

# 頁面 2：新網頁 - 自動填入的新表格頁面 (顯示剛才提交成功的結果)
def booking_success(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    details = booking.details.all()
    periods = json.loads(booking.periods_json) if booking.periods_json else []
    return render(request, 'booking_success.html', {'booking': booking, 'details': details, 'periods': periods})

# 頁面 3：歸還網頁 (顯示所有「借用中」的清單，按歸還後自動把數量加回去)
def return_page(request):
    if request.method == 'POST':
        booking_id = request.POST.get('booking_id')
        with transaction.atomic():
            booking = get_object_or_404(Booking, id=booking_id, status='借用中')
            # 遍歷明細，把當初扣掉的數量各自加回對應的充電車
            for detail in booking.details.all():
                inventory = detail.inventory
                inventory.available_qty += detail.borrowed_qty
                inventory.save()
            
            # 變更借單狀態為已歸還
            booking.status = '已歸還'
            booking.save()
        return redirect('return_page')
        
    active_bookings = Booking.objects.filter(status='借用中').order_by('-created_at')
    return render(request, 'return_page.html', {'bookings': active_bookings})