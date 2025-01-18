from django.contrib import admin
from django.urls import path
from adminpanel import views  # Импортируем views из adminpanel

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),  # Главная страница
    path('products/', views.product_list, name='product_list'),
]
