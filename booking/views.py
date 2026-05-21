from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db import transaction
from .models import DeviceInventory, Booking, BookingAssignment
import json
from datetime import datetime, timedelta

# 輔助函式 1：判斷兩個單次時間區間是否重疊
def is_time_overlap(b1_date, b1_start, b1_end, b2_date, b2_start, b2_end):
    if b1_date != b2_date:
        return False
    return max(b1_start, b2_start) <= min(b1_end, b2_end)

# 輔助函式 2：將節次轉為數字
def period_to_num(p_str):
    if p_str == '午' or p_str == '4.5': return 4.5
    try:
        return float(p_str)
    except:
        return 0.0

def booking_form(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        req_qty = int(data.get('quantity', 0))
        dev_type = data.get('device_type')
        b_type = data.get('booking_type')
        
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        weeks_list = [k.replace('week_', '') for k, v in data.items() if k.startswith('week_') and v != '']

        with transaction.atomic():
            all_carts = DeviceInventory.objects.filter(device_type=dev_type)
            
            # 1. 解析本次申請要檢查的所有「具體日期與節次區間」
            check_dates_slots = []
            
            if b_type == '單次預約':
                target_date_str = data.get('single_date')
                s_period = float(data.get('start_period', 0))
                e_period = float(data.get('end_period', 0))
                
                if not target_date_str or s_period <= 0 or e_period <= 0:
                    return JsonResponse({'status': 'error', 'message': '請填寫正確的單次日期與起訖節次。'}, status=400)
                
                target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
                check_dates_slots.append((target_date, s_period, e_period))
            else: 
                if not start_date_str or not end_date_str or not weeks_list:
                    return JsonResponse({'status': 'error', 'message': '請填寫正確的週期起訖日期，並至少勾選一個借用節次！'}, status=400)
                
                s_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                e_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                if s_date > e_date:
                    return JsonResponse({'status': 'error', 'message': '週期開始日期不能大於結束日期。'}, status=400)
                
                weekday_name_map = {0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun'}
                curr = s_date
                while curr <= e_date:
                    w_name = weekday_name_map[curr.weekday()]
                    for p_slot in weeks_list:
                        # 支援 Mon_1 或 1 兩種前端格式
                        p_val = p_slot.split('_')[-1] 
                        p_num = period_to_num(p_val)
                        
                        # 如果當前日期符合勾選的星期（例如勾選 Mon_1，當前也是星期一）
                        if p_slot.startswith(w_name) or '_' not in p_slot:
                            exclude_str = data.get('exclude_date', '')
                            if curr.strftime("%m/%d") in exclude_str or curr.strftime("%Y-%m-%d") in exclude_str:
                                continue
                            check_dates_slots.append((curr, p_num, p_num))
                    curr += timedelta(days=1)
                
                if not check_dates_slots:
                    return JsonResponse({'status': 'error', 'message': '在此日期區間內找不到符合的星期節次。'}, status=400)

            # 2. 抓出所有「借用中」的舊預約
            existing_bookings = Booking.objects.filter(device_type=dev_type, status='借用中')
            
            # 用來紀錄在所有要檢查的時段中，每台車「最高被佔用幾台」的字典
            max_occupied_per_cart = {cart: 0 for cart in all_carts}
            
            worst_date = None
            worst_avail = 0
            
            # 開始橫巡所有申請的時段（不論是單次的一天，還是週期的幾十個時段）
            for (chk_date, chk_start, chk_end) in check_dates_slots:
                current_slot_occupied = {cart: 0 for cart in all_carts}
                
                for old_b in existing_bookings:
                    if old_b.booking_type == '單次預約':
                        if is_time_overlap(chk_date, chk_start, chk_end, old_b.single_date, old_b.start_period, old_b.end_period):
                            for assign in old_b.assignments.all():
                                if assign.inventory in current_slot_occupied:
                                    current_slot_occupied[assign.inventory] += assign.assigned_qty
                    else:
                        # 舊預約是週期，檢查 chk_date 是否在舊週期的生命週期內
                        if old_b.start_date <= chk_date <= old_b.end_date:
                            if chk_date.strftime("%m/%d") in old_b.exclude_date or chk_date.strftime("%Y-%m-%d") in old_b.exclude_date:
                                continue
                            
                            old_weeks = json.loads(old_b.periods_json) if old_b.periods_json else []
                            weekday_name_map = {0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun'}
                            current_w_name = weekday_name_map[chk_date.weekday()]
                            
                            for o_slot in old_weeks:
                                o_w_prefix = o_slot.split('_')[0]
                                o_val = o_slot.split('_')[-1]
                                o_num = period_to_num(o_val)
                                
                                # 必須舊週期的星期幾，跟現在檢查的星期幾一致
                                if o_w_prefix == current_w_name or '_' not in o_slot:
                                    if chk_start <= o_num <= chk_end:
                                        for assign in old_b.assignments.all():
                                            if assign.inventory in current_slot_occupied:
                                                current_slot_occupied[assign.inventory] += assign.assigned_qty
                                        break
                
                # 計算此單一時段的總可用量
                total_avail_in_slot = sum([cart.capacity - occupied for cart, occupied in current_slot_occupied.items()])
                
                # 🌟【核心修復點】不論單次或週期，都精準記錄每台車在這些被檢查時段中所面臨的「最大佔用高峰」
                for cart in all_carts:
                    if current_slot_occupied[cart] > max_occupied_per_cart[cart]:
                        max_occupied_per_cart[cart] = current_slot_occupied[cart]
                
                if total_avail_in_slot < req_qty:
                    worst_date = chk_date
                    worst_avail = total_avail_in_slot
                    break
            
            if worst_date:
                return JsonResponse({
                    'status': 'error', 
                    'message': f'預約失敗！在 {worst_date.strftime("%Y-%m-%d")} 該時段載具庫存不足，當節全校僅剩 {worst_avail} 台。'
                }, status=400)
            
            # 3. 檢查通過，建立預約主紀錄
            if b_type == '單次預約':
                booking = Booking.objects.create(
                    email=data.get('email'), agree_rules=data.get('agree_rules'),
                    teacher_name=data.get('teacher_name'), phone=data.get('phone'),
                    context=data.get('context', ''), course_name=data.get('course_name', ''),
                    class_name=data.get('class_name', ''), location=data.get('location', ''),
                    booking_type=b_type, 
                    single_date=datetime.strptime(data.get('single_date'), "%Y-%m-%d").date(), 
                    start_period=float(data.get('start_period')), end_period=float(data.get('end_period')),
                    device_type=dev_type, required_quantity=req_qty, 
                    special_needs=data.get('special_needs', ''), pickup_person=data.get('pickup_person', '')
                )
            else:
                booking = Booking.objects.create(
                    email=data.get('email'), agree_rules=data.get('agree_rules'),
                    teacher_name=data.get('teacher_name'), phone=data.get('phone'),
                    context=data.get('context', ''), course_name=data.get('course_name', ''),
                    class_name=data.get('class_name', ''), location=data.get('location', ''),
                    booking_type=b_type, 
                    start_date=datetime.strptime(start_date_str, "%Y-%m-%d").date(),
                    end_date=datetime.strptime(end_date_str, "%Y-%m-%d").date(),
                    periods_json=json.dumps(weeks_list, ensure_ascii=False),
                    exclude_date=data.get('exclude_date', ''),
                    device_type=dev_type, required_quantity=req_qty, 
                    special_needs=data.get('special_needs', ''), pickup_person=data.get('pickup_person', '')
                )

            # ----------------- 🌟 週期與單次共用：動態安全配車演算法 -----------------
            # 根據剛才在整個借用範圍掃描出的「最高佔用量」，算出每台車還有多少安全的「淨餘裕空間」
            cart_safe_available_list = []
            for cart in all_carts:
                safe_avail = cart.capacity - max_occupied_per_cart[cart]
                if safe_avail > 0:
                    cart_safe_available_list.append({
                        'cart_obj': cart,
                        'safe_qty': safe_avail
                    })
            
            # 嚴格按照車次名稱排序（A車 -> B車 -> C車 -> 散裝）
            cart_safe_available_list = sorted(cart_safe_available_list, key=lambda x: x['cart_obj'].cart_name)
            
            remaining_to_assign = req_qty
            for item in cart_safe_available_list:
                if remaining_to_assign <= 0: 
                    break
                
                cart = item['cart_obj']
                safe_qty = item['safe_qty']
                
                if safe_qty >= remaining_to_assign:
                    BookingAssignment.objects.create(booking=booking, inventory=cart, assigned_qty=remaining_to_assign)
                    remaining_to_assign = 0
                else:
                    BookingAssignment.objects.create(booking=booking, inventory=cart, assigned_qty=safe_qty)
                    remaining_to_assign -= safe_qty
                    
            return JsonResponse({'status': 'success', 'booking_id': booking.id})
            
    return render(request, 'booking_form.html')

def booking_success(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    assignments = booking.assignments.all()
    periods = json.loads(booking.periods_json) if booking.periods_json else []
    return render(request, 'booking_success.html', {'booking': booking, 'assignments': assignments, 'periods': periods})

def return_page(request):
    if request.method == 'POST':
        booking_id = request.POST.get('booking_id')
        booking = get_object_or_404(Booking, id=booking_id, status='借用中')
        booking.status = '已歸還'
        booking.save()
        return redirect('return_page')
        
    active_bookings = Booking.objects.filter(status='借用中').order_by('-created_at')
    return render(request, 'return_page.html', {'bookings': active_bookings})