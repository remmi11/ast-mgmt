# Generated by Django 2.0.7 on 2019-10-01 18:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('map', '0007_auto_20191001_0931'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assetaform',
            name='assetId',
            field=models.CharField(max_length=255, unique=True, verbose_name='asset_id'),
        ),
        migrations.AlterField(
            model_name='assetaform',
            name='end_location',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='end'),
        ),
        migrations.AlterField(
            model_name='assetaform',
            name='install_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='install'),
        ),
        migrations.AlterField(
            model_name='assetaform',
            name='pavement_surface',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='pavement'),
        ),
        migrations.AlterField(
            model_name='assetaform',
            name='start_location',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='start'),
        ),
        migrations.AlterField(
            model_name='assetbform',
            name='assetId',
            field=models.CharField(max_length=255, unique=True, verbose_name='asset_id'),
        ),
        migrations.AlterField(
            model_name='assetbform',
            name='install_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='install'),
        ),
        migrations.AlterField(
            model_name='assetbform',
            name='support_structure',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='support'),
        ),
    ]