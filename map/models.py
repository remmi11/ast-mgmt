from django.db import models
from django.contrib.auth.models import AbstractUser

from myapp import settings

class Company(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'company'

class CustomUser(AbstractUser):
    company = models.ForeignKey('Company', on_delete=models.CASCADE, default=1)

    def save(self, *args, **kwargs):
        super(CustomUser, self).save(*args, **kwargs)

class AssetAForm(models.Model):
    assetId = models.CharField(db_column='asset_id', max_length=255, unique=True)
    start_location = models.CharField(db_column='start', max_length=255, blank=True, null=True)
    end_location = models.CharField(db_column='end', max_length=255, blank=True, null=True)
    asset_name = models.CharField(max_length=255, blank=True, null=True)
    length = models.FloatField(blank=True, null=True)
    wide = models.FloatField(blank=True, null=True)
    func_class = models.CharField(max_length=50, blank=True, null=True)
    pavement_surface = models.CharField(db_column='pavement', max_length=50, blank=True, null=True)
    install_date = models.DateTimeField(db_column='install', blank=True, null=True)

    created_by = models.IntegerField(blank=True, null=True)
    updated_by = models.IntegerField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'form_asset_a'

class AssetBForm(models.Model):
    assetId = models.CharField(db_column='asset_id', max_length=255, unique=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    code = models.CharField(max_length=255, blank=True, null=True)
    support_structure = models.CharField(db_column='support', max_length=50, blank=True, null=True)
    install_date = models.DateTimeField(db_column='install', blank=True, null=True)

    created_by = models.IntegerField(blank=True, null=True)
    updated_by = models.IntegerField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'form_asset_b'