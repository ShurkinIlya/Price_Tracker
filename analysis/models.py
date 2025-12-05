from django.db import models


class CurrencyRate(models.Model):
    code = models.CharField(max_length=8, unique=True)
    rate = models.DecimalField(max_digits=16, decimal_places=6)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code}: {self.rate}"


class SaleEvent(models.Model):
    name = models.CharField(max_length=120)
    start_date = models.DateField()
    end_date = models.DateField()
    discount_hint = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def __str__(self):
        return self.name
