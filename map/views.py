from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.db import connection

from .models import *
from .forms import *

from django.core import serializers
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q

import json
import zipfile
import osgeo.ogr
from datetime import date, datetime, timedelta
import uuid
import glob
import os
import shutil
import csv
from wsgiref.util import FileWrapper

FUNC_CLASS = [
    ['highways', 'Highways'],
    ['arterial', 'Arterial'],
    ['collector', 'Collector'],
    ['residential', 'Residential'],
    ['rural', 'Rural']
]

PAVEMENT_SURFACE = [
    ['asphalt', 'Asphalt'],
    ['pcc', 'PCC'],
    ['surface_treatment', 'Surface Treatment'],
    ['gravel', 'Gravel'],
    ['brick', 'Brick']
]

SUPPORT_STRUCTURE = [
    ['wood', 'Wood'],
    ['metal', 'Metal'],
    ['concrete', 'Concrete']
]

PAGE_SIZE = 10

# Controller for registering new user
def register(request):
    user_form = UserRegistrationForm()
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        if user_form.is_valid():
            new_user = user_form.save(commit=False)
            new_user.set_password(
                    user_form.cleaned_data['password'])
            new_user.save()

            return redirect("/")
        else:
            render(request,
                  'registration/register.html',
                  {'user_form': user_form})
    else:
        user_form = UserRegistrationForm()
    return render(request,
                  'registration/register.html',
                  {'user_form': user_form})

# Cutomuser user authentication
class AuthenticationUsernameBackend(object):
    def authenticate(self, username=None, password=None, **kwargs):
        try:
            user = CustomUser.objects.get(email=username)
        except CustomUser.DoesNotExist:
            return None
        else:
            if getattr(user, 'is_active', False) and user.check_password(password):
                return user
        return None

# Controller for map view
@login_required
def mapView(request):
    assetAList = AssetAForm.objects.all()
    maxA = AssetAForm.objects.all().aggregate(Max('pk'))['pk__max']
    maxB = AssetBForm.objects.all().aggregate(Max('pk'))['pk__max']
    param = dict()

    if request.POST:
        param = request.POST.dict()

    return render(request, 'map.html', {
        'assetAList': assetAList, 'FUNC_CLASS': FUNC_CLASS,
        'PAVEMENT_SURFACE': PAVEMENT_SURFACE,
        'SUPPORT_STRUCTURE': SUPPORT_STRUCTURE, 
        'assetAMaxID': '%04d' % maxA if maxA != None else maxA,
        'assetBMaxID': '%04d' % maxB if maxB != None else maxB,
        'param': param
    })

@login_required
def inspectionView(request, type):
    assetId = request.GET.get('assetId', '')

    if type == "assetA":
        asset = get_object_or_404(AssetAForm, assetId=assetId)
    else:
        asset = get_object_or_404(AssetBForm, assetId=assetId)

    created_user = CustomUser.objects.get(pk=asset.created_by)
    updated_user = CustomUser.objects.get(pk=asset.created_by)
    if created_user.company_id != request.user.company_id and updated_user.company_id != request.user.company_id:
        get_object_or_404(AssetAForm, assetId='')

    return render(request, 'inspection.html', {"assetType": type, "assetId": assetId})

@login_required
@csrf_exempt
def apiForm(request, type):
    search_key = request.POST.get('search')
    page = int(request.POST.get('page', 1))
    load_all = int(request.POST.get('loadAll', 0))

    filters = dict()
    params = json.loads(request.POST.get('filter'))
    for param in params:
        if param['name'] in ['asset_type', 'recent', 'pavement', 'structure', 'function']:
            if param['name'] not in filters.keys():
                filters[param['name']] = []
            filters[param['name']].append(param['value'])
        else:
            filters[param['name']] = param['value']

    temp = []
    users = CustomUser.objects.filter(company_id=request.user.company_id)
    user_names = {tp.pk:tp.username for tp in users}

    company_condition = Q(created_by__in=user_names.keys()) | \
            Q(updated_by__in=user_names.keys())

    condition = company_condition
    condition = commonSearch(condition, filters)

    if type == "formA":
        if 'pavement' in filters:
            condition = condition & Q(pavement_surface__in=filters['pavement'])
        if 'function' in filters:
            condition = condition & Q(func_class__in=filters['function'])
        if 'function_text' in filters and filters['function_text'] != "":
            condition = condition & Q(func_class__icontains=filters['function_text'])
        if 'start' in filters and filters['start'] != "":
            condition = condition & Q(start_location__iexact=filters['start'])
        if 'end' in filters and filters['end'] != "":
            condition = condition & Q(end_location__iexact=filters['end'])

        if search_key == "" or search_key == None:
            if load_all == 1:
                assetAList = AssetAForm.objects.filter(condition).order_by('assetId')[:page * PAGE_SIZE]
            else:
                assetAList = AssetAForm.objects.filter(condition).order_by('assetId')[(page-1) * PAGE_SIZE: page * PAGE_SIZE]
        else:
            global_search = (Q(assetId__icontains=search_key) | \
                Q(start_location__icontains=search_key) | \
                Q(end_location__icontains=search_key) | \
                Q(asset_name__icontains=search_key) | \
                Q(func_class__icontains=search_key) | \
                Q(pavement_surface__icontains=search_key))

            if load_all == 1:
                assetAList = AssetAForm.objects.filter(condition & global_search).order_by('assetId')[:page * PAGE_SIZE]
            else:
                assetAList = AssetAForm.objects.filter(condition & global_search).order_by('assetId')[(page-1) * PAGE_SIZE: page * PAGE_SIZE]

        assetAList = json.loads(serializers.serialize('json', assetAList))

        for item in assetAList:
            asset = item['fields']
            asset['id'] = item['pk']

            asset['user_id'] = asset['created_by']
            try:
                asset['created_by'] = user_names[asset['created_by']]
            except:
                asset['created_by'] = user_names[asset['updated_by']]

            try:
                asset['area'] = float(asset['length']) * float(asset['wide'])
            except:
                asset['area'] = 0

            for tp in asset:
                asset[tp] = "" if asset[tp] == "None" or asset[tp] == None else asset[tp]

            temp.append(asset)
    else:
        if 'structure' in filters:
            condition = condition & Q(support_structure__in=filters['structure'])

        if search_key == "" or search_key == None:
            if load_all == 1:
                assetBList = AssetBForm.objects.filter(condition).order_by('assetId')[:page * PAGE_SIZE]
            else:
                assetBList = AssetBForm.objects.filter(condition).order_by('assetId')[(page-1) * PAGE_SIZE: page * PAGE_SIZE]
        else:
            global_search = (Q(assetId__icontains=search_key) | \
                Q(type__icontains=search_key) | \
                Q(code__icontains=search_key) | \
                Q(support_structure__icontains=search_key))

            if load_all == 1:
                assetBList = AssetBForm.objects.filter(condition & global_search).order_by('assetId')[:page * PAGE_SIZE]
            else:
                assetBList = AssetBForm.objects.filter(condition & global_search).order_by('assetId')[(page-1) * PAGE_SIZE: page * PAGE_SIZE]            
        
        assetBList = json.loads(serializers.serialize('json', assetBList))

        for item in assetBList:
            asset = item['fields']
            asset['id'] = item['pk']
            asset['user_id'] = asset['created_by']
            try:
                asset['created_by'] = user_names[asset['created_by']]
            except:
                asset['created_by'] = user_names[asset['updated_by']]

            for tp in asset:
                asset[tp] = "" if asset[tp] == "None" or asset[tp] == None else asset[tp]

            temp.append(asset)

    return HttpResponse(json.dumps(temp), content_type='application/json')

# Controller for form view
@login_required
def formView(request):
    if request.method == "POST":
        asset_type = request.POST.get('asset_type')
        geometry = request.POST.get('geometry')

        if asset_type == "Asset A":
            assetA = AssetAForm()
            assetA.assetId = request.POST.get('asset_id_a')
            assetA.start_location = request.POST.get('start_location')
            assetA.end_location = request.POST.get('end_location')
            assetA.asset_name = request.POST.get('asset_name')
            assetA.length = float(request.POST.get('length'))
            assetA.wide = float(request.POST.get('wide'))
            assetA.func_class = request.POST.get('func_class')
            assetA.pavement_surface = request.POST.get('pavement_surface')
            assetA.install_date = request.POST.get('install_date_a')

            assetA.created_by = request.user.pk
            assetA.save()

            if geometry != None and geometry != "":
                sql = '''UPDATE form_asset_a SET "geom"=ST_GeometryFromText('%s', 4326), 
                    updated_by=%s, updated_at=now() WHERE asset_id = \'%s\';''' % \
                    (geometry, request.user.pk, assetA.assetId)

                with connection.cursor() as cursor:
                    cursor.execute(sql)

        else:
            assetB = AssetBForm()
            assetB.assetId = request.POST.get('asset_id_b')
            assetB.type = request.POST.get('type')
            assetB.code = request.POST.get('code')
            assetB.support_structure = request.POST.get('support_structure')
            assetB.install_date = request.POST.get('install_date_b')

            assetB.created_by = request.user.pk
            assetB.save()

            if geometry != None and geometry != "":
                sql = '''UPDATE form_asset_b SET "geom"=ST_GeometryFromText('%s', 4326), 
                    updated_by=%s, updated_at=now() WHERE asset_id = \'%s\';''' % \
                    (geometry, request.user.pk, assetB.assetId)

                with connection.cursor() as cursor:
                    cursor.execute(sql)

        return redirect("/map/")

    maxA = AssetAForm.objects.all().aggregate(Max('pk'))['pk__max']
    maxB = AssetBForm.objects.all().aggregate(Max('pk'))['pk__max']

    return render(request, 'asset/create.html', 
        {'FUNC_CLASS': FUNC_CLASS, 'PAVEMENT_SURFACE': PAVEMENT_SURFACE,
        'SUPPORT_STRUCTURE': SUPPORT_STRUCTURE, 
        'assetAMaxID': '%04d' % maxA if maxA != None else maxA,
        'assetBMaxID': '%04d' % maxB if maxB != None else maxB})

@login_required
def formEditA(request, pk):
    asset = get_object_or_404(AssetAForm, pk=pk)

    if request.method == "POST":
        data = request.POST.copy()
        data['updated_by'] = request.user.pk

        form = AssetADjForm(data, instance=asset)
        form.save()

        return redirect("/map/")

    return render(request, 'asset/editA.html', 
        {'asset': asset, 'FUNC_CLASS': FUNC_CLASS, 
        'PAVEMENT_SURFACE': PAVEMENT_SURFACE})

@login_required
def formEditB(request, pk):
    asset = get_object_or_404(AssetBForm, pk=pk)

    if request.method == "POST":
        data = request.POST.copy()
        data['updated_by'] = request.user.pk

        form = AssetBDjForm(data, instance=asset)
        form.save()

    return render(request, 'asset/editB.html', 
        {'asset': asset, 'SUPPORT_STRUCTURE': SUPPORT_STRUCTURE})

@login_required
@csrf_exempt
def apiInspection(request, type):
    assetId = request.GET.get("assetId", "")

    print (assetId, type)
    inspections = Inspection.objects.filter(asset_type=type, assetId=assetId)
    inspections = serializers.serialize('json', inspections)

    return HttpResponse(inspections, content_type='application/json')

@login_required
@csrf_exempt
def apiEditInspection(request, type):
    if request.POST:
        param = dict()
        data = json.loads(request.POST.get('data'))
        assetId = request.POST.get('assetId')
        for item in data:
            if item['name'] == "csrfmiddlewaretoken" or (item['name'] == "inspectionId" and item['value'] == ""):
                continue
            param[item['name']] = item['value']

        print (param)
        param['oci'] = float(param['oci'])
        param['assetId'] = assetId

        if 'inspectionId' not in param.keys():
            Inspection.objects.create(**param)
        else:
            inspection = Inspection.objects.get(pk=int(param['inspectionId']))
            del param['inspectionId']
            InspectionForm(param, instance=inspection).save()

    inspections = Inspection.objects.filter(asset_type=type, assetId=assetId)
    inspections = serializers.serialize('json', inspections)

    return HttpResponse(inspections, content_type='application/json')

@login_required
@csrf_exempt
def apiFormRemoveA(request, pk):
    asset = get_object_or_404(AssetAForm, pk=pk)
    if asset:
        Inspection.objects.filter(assetId=asset.assetId, asset_type='assetA').delete()
        asset.delete()

    return HttpResponse("OK")

@login_required
@csrf_exempt
def apiFormRemoveB(request, pk):
    asset = get_object_or_404(AssetBForm, pk=pk)
    if asset:
        Inspection.objects.filter(assetId=asset.assetId, asset_type='assetA').delete()
        asset.delete()

    return HttpResponse("OK")

@login_required
@csrf_exempt
def apiCheckAssetId(request, type):
    assetId = request.POST.get('assetId')
    if type == "asseta":
        asset = AssetAForm.objects.filter(assetId=assetId)
    else:
        asset = AssetBForm.objects.filter(assetId=assetId)

    if len(asset) > 0:
        return HttpResponse("True")
    return HttpResponse("False")

def commonSearch(condition, filters):
    if 'recent' in filters:
        created, updated = None, None
        if 'created' in filters['recent']:
            created = Q(created_at__gte=date.today()-timedelta(days=7))
        if 'updated' in filters['recent']:
            updated = Q(updated_at__gte=date.today()-timedelta(days=7))

        if created and updated:
            condition = condition & (created | updated)
        elif created:
            condition = condition & created
        elif updated:
            condition = condition & updated

    if 'install' in filters and filters['install'].strip() != "":
        install = filters['install'].split("-")
        install_start = datetime.strptime(install[0].strip(), '%m/%d/%Y')
        install_end = datetime.strptime(install[1].strip(), '%m/%d/%Y')
        condition = condition & Q(created_at__gte=install_start) & Q(created_at__lte=install_end)
    if 'update' in filters and filters['update'].strip() != "":
        update = filters['update'].split("-")
        update_start = datetime.strptime(update[0].strip(), '%m/%d/%Y')
        update_end = datetime.strptime(update[1].strip(), '%m/%d/%Y')
        condition = condition & Q(created_at__gte=update_start) & Q(created_at__lte=update_end)

    return condition

@login_required
@csrf_exempt
def apiGeoJson(request):
    res = dict()
    search_key = request.POST.get('search')
    page_a = int(request.POST.get('pageA', 1))
    page_b = int(request.POST.get('pageB', 1))

    filters = dict()
    params = json.loads(request.POST.get('filter'))
    for param in params:
        if param['name'] not in ['install', 'update', 'asset_type']:
            param['value'] = "\'%s\'" % param['value']

        if param['name'] in ['asset_type', 'recent', 'pavement', 'structure', 'function']:
            if param['name'] not in filters.keys():
                filters[param['name']] = []
            filters[param['name']].append(param['value'])
        else:
            filters[param['name']] = param['value']

    users = CustomUser.objects.filter(company_id=request.user.company_id)
    user_names = {tp.pk:tp.username for tp in users}

    company_condition = Q(created_by__in=user_names.keys()) | \
            Q(updated_by__in=user_names.keys())
    condition = company_condition

    if search_key != None and search_key != "":
        search_key = "\'%s\'" % search_key
        temp = (Q(assetId__icontains=search_key) | \
            Q(start_location__icontains=search_key) | \
            Q(end_location__icontains=search_key) | \
            Q(asset_name__icontains=search_key) | \
            Q(func_class__icontains=search_key) | \
            Q(pavement_surface__icontains=search_key))
        condition = condition & temp
    
    condition = commonSearch(condition, filters)

    if 'pavement' in filters:
        condition = condition & Q(pavement_surface__in=filters['pavement'])
    if 'function' in filters:
        condition = condition & Q(func_class__in=filters['function'])
    if 'function_text' in filters and filters['function_text'] != "''":
        condition = condition & Q(func_class__icontains=filters['function_text'])
    if 'start' in filters and filters['start'] != "''":
        condition = condition & Q(start_location__iexact=filters['start'])
    if 'end' in filters and filters['end'] != "''":
        condition = condition & Q(end_location__iexact=filters['end'])

    join_field = AssetAForm.objects.filter(condition)[(page_a-1) * PAGE_SIZE: page_a * PAGE_SIZE].query
    join_field = str(join_field).split("WHERE")[1].strip()
    join_field = join_field.replace('at" >= ', 'at" >= \'').replace('00:00:00+00:00', '00:00:00+00:00\'')
    join_field = join_field.replace('at" <= ', 'at" <= \'')

    sql = '''SELECT row_to_json(fc)
        FROM ( SELECT 'FeatureCollection' As type, array_to_json(array_agg(f)) As features
        FROM (SELECT 'Feature' As type, 
            ST_AsGeoJSON(form_asset_a.geom)::json As geometry,
            (
                select row_to_json(t) 
                from (select form_asset_a.asset_id As asset_id) t
            )
        As properties
        FROM form_asset_a WHERE '''+join_field+ ") As f ) As fc;"
    sql = sql.replace("LIKE UPPER(", "LIKE UPPER('").replace("(%", "('%").replace("%)", "%')")

    with connection.cursor() as cursor:
        cursor.execute(sql)
        row = cursor.fetchone()

        res['lines'] = row[0]

    condition = company_condition

    if search_key != None and search_key != "":
        search_key = "\'%s\'" % search_key
        temp = (Q(assetId__icontains=search_key) | \
            Q(start_location__icontains=search_key) | \
            Q(end_location__icontains=search_key) | \
            Q(asset_name__icontains=search_key) | \
            Q(func_class__icontains=search_key) | \
            Q(pavement_surface__icontains=search_key))
        condition = condition & temp
    
    condition = commonSearch(condition, filters)

    if 'structure' in filters:
        condition = condition & Q(support_structure__in=filters['structure'])

    join_field = AssetBForm.objects.filter(condition)[(page_b-1) * PAGE_SIZE: page_b * PAGE_SIZE].query
    join_field = str(join_field).split("WHERE")[1].strip()
    join_field = join_field.replace('at" >= ', 'at" >= \'').replace('00:00:00+00:00', '00:00:00+00:00\'')
    join_field = join_field.replace('at" <= ', 'at" <= \'')

    sql = '''SELECT row_to_json(fc)
        FROM ( SELECT 'FeatureCollection' As type, array_to_json(array_agg(f)) As features
        FROM (SELECT 'Feature' As type, 
            ST_AsGeoJSON(form_asset_b.geom)::json As geometry,
            (
                select row_to_json(t) 
                from (select form_asset_b.asset_id As asset_id) t
            )
        As properties
        FROM form_asset_b WHERE '''+join_field+ ") As f ) As fc;"
    sql = sql.replace("LIKE UPPER(", "LIKE UPPER('").replace("(%", "('%").replace("%)", "%')")

    with connection.cursor() as cursor:
        cursor.execute(sql)
        row = cursor.fetchone()

        res['points'] = row[0]

    if 'asset_type' in filters:
        if 'assetA' not in filters['asset_type']:
            res['lines'] = []
        if 'assetB' not in filters['asset_type']:
            res['points'] = []

    return HttpResponse(json.dumps(res), content_type='application/json')

# post api for importing shp file to postgis
@login_required
@csrf_exempt
def apiFileUpload(request):
    f = request.FILES['file']
    file_name = uuid.uuid4()

    # define constants
    FORMA_AVAILE = [
        'asset_name', 'func_class', 'length', 'wide', 'start', 
        'end', 'install'
    ]
    FORMB_AVAILE = [
        'type', 'code', 'support', 'install'
    ]

    # save uploaded file in the server side
    os.mkdir("upload/%s" % file_name)
    with open('upload/%s/%s.zip' % (file_name, file_name), 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)

    # extract zip file
    with zipfile.ZipFile("upload/%s/%s.zip" % (file_name, file_name),"r") as zip_ref:
        zip_ref.extractall("upload/%s" % file_name)

    # find .shp file and open it
    shapefile = None
    for file in glob.glob("upload/%s/*.shp" % file_name):
        shapefile = osgeo.ogr.Open(file)

    # if there is no shape file, return failed
    if shapefile == None:
        return HttpResponse("Failed")

    layer = shapefile.GetLayer(0)    
    for i in range(layer.GetFeatureCount()):
        feature = layer.GetFeature(i)

        names = [feature.GetFieldDefnRef(idx).GetName() for idx in range(0, feature.GetFieldCount())]

        try:
            wkt = feature.GetGeometryRef().ExportToWkt()
        except:
            wkt = None
        asset_id = feature.GetField("asset_id")

        if 'start' in names:
            asset = AssetAForm.objects.filter(assetId=asset_id)
            asset_data = {key:feature.GetField(key) for key in FORMA_AVAILE if key in names}

            if 'install' in asset_data and asset_data['install']:
                asset_data['install'] = asset_data['install'].replace("/", "-")
            else:
                asset_data['install'] = date.today().strftime("%Y-%m-%d");

            if len(asset) > 0:  # update existed asset
                asset = asset[0]
                data = ["\"%s\"='%s'" % (key, asset_data[key]) for key in asset_data]
                data = ", ".join(data)

                if wkt != None:
                    sql = '''UPDATE form_asset_a SET %s, "geom"=ST_GeometryFromText('%s', 4326), 
                        updated_by=%s, updated_at=now() WHERE asset_id = \'%s\';''' % \
                        (data, wkt, request.user.pk, asset.assetId)
                else:
                    sql = '''UPDATE form_asset_a SET %s, 
                        updated_by=%s, updated_at=now() WHERE asset_id = \'%s\';''' % \
                        (data, request.user.pk, asset.assetId)

                with connection.cursor() as cursor:
                    cursor.execute(sql)

                print ("updated", asset.assetId)
            else:               # create new asset
                if asset_id == None or asset_id == "":
                    asset_id = AssetAForm.objects.all().aggregate(Max('pk'))['pk__max']
                    asset_id = 'A-%04d' % asset_id \
                        if asset_id != None else "A-0001"

                fields = ", ".join(["\"%s\"" % key for key in asset_data])
                data = ", ".join(["'%s'" % asset_data[key] for key in asset_data])

                if wkt != None:
                    sql = '''INSERT INTO form_asset_a (%s, "asset_id", "created_by", "created_at", "updated_at", "geom") 
                        VALUES (%s, '%s', '%s', now(), now(), ST_GeometryFromText('%s', 4326))''' % (fields, data, asset_id, request.user.pk, wkt)
                else:
                    sql = '''INSERT INTO form_asset_a (%s, "asset_id", "created_by", "created_at", "updated_at") 
                        VALUES (%s, '%s', '%s', now(), now())''' % (fields, data, asset_id, request.user.pk)

                with connection.cursor() as cursor:
                    cursor.execute(sql)
                print ("created", asset_id)

        else:
            asset = AssetBForm.objects.filter(assetId=asset_id)
            asset_data = {key:feature.GetField(key) for key in FORMB_AVAILE if key in names}

            if 'install' in asset_data and asset_data['install']:
                asset_data['install'] = asset_data['install'].replace("/", "-")
            else:
                asset_data['install'] = date.today().strftime("%Y-%m-%d");

            if len(asset) > 0:  # update existed asset
                asset = asset[0]
                data = ["\"%s\"='%s'" % (key, asset_data[key]) for key in asset_data]
                data = ", ".join(data)

                if wkt != None:
                    sql = '''UPDATE form_asset_b SET %s, "geom"=ST_GeometryFromText('%s', 4326), 
                        updated_by=%s, updated_at=now() WHERE asset_id = \'%s\';''' % \
                        (data, wkt, request.user.pk, asset.assetId)
                else:
                    sql = '''UPDATE form_asset_b SET %s, 
                        updated_by=%s, updated_at=now() WHERE asset_id = \'%s\';''' % \
                        (data, request.user.pk, asset.assetId)
                with connection.cursor() as cursor:
                    cursor.execute(sql)

                print ("updated", asset.assetId)
            else:               # create new asset
                if asset_id == None or asset_id == "":
                    asset_id = AssetBForm.objects.all().aggregate(Max('pk'))['pk__max']
                    asset_id = 'B-%04d' % asset_id \
                        if asset_id != None else "B-0001"

                fields = ", ".join(["\"%s\"" % key for key in asset_data])
                data = ", ".join(["'%s'" % asset_data[key] for key in asset_data])

                if wkt != None:
                    sql = '''INSERT INTO form_asset_b (%s, "asset_id", "created_by", "created_at", "updated_at", "geom") 
                        VALUES (%s, '%s', '%s', now(), now(), ST_GeometryFromText('%s', 4326))''' % (fields, data, asset_id, request.user.pk, wkt)
                else:
                    sql = '''INSERT INTO form_asset_b (%s, "asset_id", "created_by", "created_at", "updated_at") 
                        VALUES (%s, '%s', '%s', now(), now())''' % (fields, data, asset_id, request.user.pk)

                with connection.cursor() as cursor:
                    cursor.execute(sql)
                print ("created", asset_id)

    shutil.rmtree("upload/%s" % file_name)

    return HttpResponse("OK")

# function to generate csv file
def createCsv(file_path, field_names, user_names, models_class, condition):
    with open(file_path, "w") as fp:
        writer = csv.writer(fp)
        writer.writerow(field_names + ['user'])

        if condition:
            items = models_class.objects.filter((Q(created_by__in=user_names.keys()) | \
                        Q(updated_by__in=user_names.keys())) & condition)
        else:
            items = models_class.objects.filter(Q(created_by__in=user_names.keys()) | \
                Q(updated_by__in=user_names.keys()))

        for obj in items:
            row = [getattr(obj, field) for field in field_names]

            try:
                row.append(user_names[obj.created_by])
            except:
                row.append(user_names[obj.updated_by])

            writer.writerow(row)

@login_required
@csrf_exempt
def apiFileDownload(request):
    connection_string = 'PG:"host=13.82.41.95 user=postgres dbname=ananya password=gdipass1"'
    users = CustomUser.objects.filter(company_id=request.user.company_id)
    user_names = {tp.pk:tp.username for tp in users}

    search_key = request.GET.get('search')

    users = CustomUser.objects.filter(company_id=request.user.company_id)
    user_names = {tp.pk:tp.username for tp in users}

    file_name = uuid.uuid4()
    # create a directory for wrapping all data
    os.mkdir("upload/%s" % file_name)
    os.mkdir("upload/%s/asset_a_shp" % file_name)
    os.mkdir("upload/%s/asset_b_shp" % file_name)

    codition_a, codition_b = None, None
    company_condition = Q(created_by__in=user_names.keys()) | \
            Q(updated_by__in=user_names.keys())

    # create shape files for asset_a and asset_b
    if search_key != None and search_key != "":
        codition_a = (Q(assetId__icontains=search_key) | \
            Q(start_location__icontains=search_key) | \
            Q(end_location__icontains=search_key) | \
            Q(asset_name__icontains=search_key) | \
            Q(func_class__icontains=search_key) | \
            Q(pavement_surface__icontains=search_key))
        search_field = AssetAForm.objects.filter(company_condition & codition_a).query
        search_field = str(search_field).split("WHERE")[1].strip()
        search_field = search_field.replace("LIKE UPPER(", "LIKE UPPER('").replace("(%", "('%").replace("%)", "%')")
        os.system('ogr2ogr -f "ESRI Shapefile" upload/%s/asset_a_shp/asset_a.shp %s "form_asset_a" -where "%s"' % (file_name, connection_string, search_field))

        codition_b = (Q(assetId__icontains=search_key) | \
                Q(type__icontains=search_key) | \
                Q(code__icontains=search_key) | \
                Q(support_structure__icontains=search_key))
        search_field = AssetBForm.objects.filter(company_condition & codition_b).query
        search_field = str(search_field).split("WHERE")[1].strip()
        search_field = search_field.replace("LIKE UPPER(", "LIKE UPPER('").replace("(%", "('%").replace("%)", "%')")
        os.system('ogr2ogr -f "ESRI Shapefile" upload/%s/asset_b_shp/asset_b.shp %s "form_asset_b" -where "%s"' % (file_name, connection_string, search_field))
    else:
        os.system('ogr2ogr -f "ESRI Shapefile" upload/%s/asset_a_shp/asset_a.shp %s "form_asset_a"' % (file_name, connection_string))
        os.system('ogr2ogr -f "ESRI Shapefile" upload/%s/asset_b_shp/asset_b.shp %s "form_asset_b"' % (file_name, connection_string))

    # create csv files for asset_a and asset_b
    field_names = ['assetId', 'start_location', 'end_location', 'asset_name',
        'length', 'wide', 'func_class', 'pavement_surface', 'install_date']
    createCsv("upload/%s/asset_a.csv" % file_name,
        field_names, user_names, AssetAForm, codition_a)
    field_names = ['assetId', 'type', 'code', 'support_structure', 'install_date']
    createCsv("upload/%s/asset_b.csv" % file_name,
        field_names, user_names, AssetBForm, codition_b)

    files_path = "upload/%s" % file_name
    path_to_zip = shutil.make_archive(files_path, "zip", files_path)
    response = HttpResponse(FileWrapper(open(path_to_zip,'rb')), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="data.zip"'.format(
        filename = "data.zip"
    )

    shutil.rmtree("upload/%s" % file_name)
    os.remove("upload/%s.zip" % file_name)

    return response

# Controller for updating a user
@login_required
def update_profile(request, pk):
    if not request.user.pk != pk: 
        return redirect('/')
    
    users = CustomUser.objects.all()
    user = get_object_or_404(CustomUser, pk=pk)

    if request.method == "POST":
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save(commit=False)
            if request.POST.get('new_password') != "":
                user.set_password(request.POST.get('new_password'))
            user.save()
            return redirect('/map/')
    else:
        form = UserEditForm(instance=user)
    return render(request, 'registration/update_profile.html', {'user_form': form})