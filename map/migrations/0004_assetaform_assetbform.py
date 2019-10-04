# Generated by Django 2.0.7 on 2019-09-28 18:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('map', '0003_auto_20190917_2010'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssetAForm',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_location', models.CharField(blank=True, max_length=255, null=True)),
                ('end_location', models.CharField(blank=True, max_length=255, null=True)),
                ('asset_name', models.CharField(blank=True, max_length=255, null=True)),
                ('func_class', models.CharField(blank=True, max_length=50, null=True)),
                ('pavement_surface', models.CharField(blank=True, max_length=50, null=True)),
                ('install_date', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.IntegerField(blank=True, null=True)),
                ('updated_by', models.IntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'form_asset_a',
            },
        ),
        migrations.CreateModel(
            name='AssetBForm',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(blank=True, max_length=255, null=True)),
                ('code', models.CharField(blank=True, max_length=255, null=True)),
                ('support_structure', models.CharField(blank=True, max_length=50, null=True)),
                ('install_date', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.IntegerField(blank=True, null=True)),
                ('updated_by', models.IntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'form_asset_b',
            },
        ),
    ]