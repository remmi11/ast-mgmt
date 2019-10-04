# Generated by Django 2.0.7 on 2019-10-01 09:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('map', '0006_auto_20190928_1905'),
    ]

    operations = [
        migrations.AddField(
            model_name='assetaform',
            name='assetId',
            field=models.CharField(default='asset-1', max_length=255, unique=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='assetbform',
            name='assetId',
            field=models.CharField(default='asset-2', max_length=255, unique=True),
            preserve_default=False,
        ),
    ]
