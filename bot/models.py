from django.db import models


class PurchasedDomain(models.Model):
    """Модель для хранения выкупленный доменных имен"""
    domain = models.CharField(max_length=255, unique=True, verbose_name='Имя домена')
    purchased_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата покупки домена')
