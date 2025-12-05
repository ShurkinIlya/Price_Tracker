# parsers/views.py
from django.shortcuts import render
from django.http import HttpResponse

def index(request):
    return render(request, 'parsers/index.html')

def amazon_parser(request):
    return HttpResponse("Парсер Amazon - в разработке")

def wildberries_parser(request):
    return HttpResponse("Парсер Wildberries - в разработке")

def ozon_parser(request):
    return HttpResponse("Парсер OZON - в разработке")