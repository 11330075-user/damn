from django.urls import path
from django.contrib import admin
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),  # 管理員登入與查看網址
    path('', views.booking_form, name='booking_form'),  # 預約表單頁面
    path('success/<int:booking_id>/', views.booking_success, name='booking_success'),  # 自動填入的新表格頁
    path('return/', views.return_page, name='return_page'),  # 歸還網頁
]