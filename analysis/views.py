from django.shortcuts import render

def index(request):
    return render(request, 'analysis/index.html')

def price_prediction(request):
    return render(request, 'analysis/predict.html') 