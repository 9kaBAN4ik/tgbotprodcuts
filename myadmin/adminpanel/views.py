from django.shortcuts import render
from .models import Product


def home(request):
    return render(request, 'adminpanel/home.html')

# Представление для отображения списка продуктов
def product_list(request):
    products = Product.objects.all()  # Получаем все продукты из базы данных
    return render(request, 'adminpanel/product_list.html', {'products': products})
