# Generated by Django 2.0.7 on 2019-09-28 19:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('map', '0005_auto_20190928_1830'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assetaform',
            name='length',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='assetaform',
            name='wide',
            field=models.FloatField(blank=True, null=True),
        ),
    ]