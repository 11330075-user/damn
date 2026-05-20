from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db import transaction
from .models import DeviceInventory, Booking, BookingDetail
import json

def booking_form(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        req_qty = int(data.get('quantity', 0))
        dev_type = data.get('device_type')
        
        with transaction.atomic():
            available_carts = DeviceInventory.objects.filter(
                device_type=dev_type, available_qty__gt=0
            ).order_by('cart_name')
            
            total_available = sum([c.available_qty for c in available_carts])
            if total_available < req_qty:
                return JsonResponse({'status': 'error', 'message': f'庫存不足！目前僅剩 {total_available} 台。'}, status=400)
            
            weeks_list = [v for k, v in data.items() if k.startswith('week_') and v != '']
            
            booking = Booking.objects.create(
                email=data.get('email'), agree_rules=data.get('agree_rules'),
                teacher_name=data.get('teacher_name'), phone=data.get('phone'),
                context=data.get('context', ''), course_name=data.get('course_name', ''),
                class_name=data.get('class_name', ''), location=data.get('location', ''),
                booking_type=data.get('booking_type'), single_date=data.get('single_date') or None,
                single_period=data.get('single_period', ''), agree_period=data.get('agree_period', ''),
                start_date=data.get('start_date') or None, end_date=data.get('end_date') or None,
                periods_json=json.dumps(weeks_list, ensure_ascii=False), exclude_date=data.get('exclude_date', ''),
                device_type=dev_type, required_quantity=req_qty, special_needs=data.get('special_needs', ''),
                pickup_person=data.get('pickup_person', '')
            )
            
            remaining_to_deduct = req_qty
            for cart in available_carts:
                if remaining_to_deduct <= 0: break
                if cart.available_qty >= remaining_to_deduct:
                    cart.available_qty -= remaining_to_deduct
                    BookingDetail.objects.create(booking=booking, inventory=cart, borrowed_qty=remaining_to_deduct)
                    cart.save()
                    remaining_to_deduct = 0
                else:
                    deduct_part = cart.available_qty
                    remaining_to_deduct -= deduct_part
                    cart.available_qty = 0
                    BookingDetail.objects.create(booking=booking, inventory=cart, borrowed_qty=deduct_part)
                    cart.save()
            
            return JsonResponse({'status': 'success', 'booking_id': booking.id})
            
    return render(request, 'booking_form.html')

def booking_success(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    details = booking.details.all()
    periods = json.loads(booking.periods_json) if booking.periods_json else []
    return render(request, 'booking_success.html', {'booking': booking, 'details': details, 'periods': periods})

def return_page(request):
    if request.method == 'POST':
        booking_id = request.POST.get('booking_id')
        with transaction.atomic():
            booking = get_object_or_404(Booking, id=booking_id, status='借用中')
            for detail in booking.details.all():
                inventory = detail.inventory
                inventory.available_qty += detail.borrowed_qty
                inventory.save()
            booking.status = '已歸還'
            booking.save()
        return redirect('return_page')
        
    active_bookings = Booking.objects.filter(status='借用中').order_by('-created_at')
    return render(request, 'return_page.html', {'bookings': active_bookings})