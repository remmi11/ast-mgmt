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
from datetime import date
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

    return render(request, 'map.html', {
        'assetAList': assetAList, 'FUNC_CLASS': FUNC_CLASS,
        'PAVEMENT_SURFACE': PAVEMENT_SURFACE,
        'SUPPORT_STRUCTURE': SUPPORT_STRUCTURE, 
        'assetAMaxID': '%04d' % maxA if maxA != None else maxA,
        'assetBMaxID': '%04d' % maxB if maxB != None else maxB
    })

@login_required
@csrf_exempt
def apiForm(request, type):
    search_key = request.POST.get('search')

    temp = []
    users = CustomUser.objects.filter(company_id=request.user.company_id)
    user_names = {tp.pk:tp.username for tp in users}

    if type == "formA":
        if search_key == "" or search_key == None:
            assetAList = AssetAForm.objects.filter(created_by__in=user_names.keys()).order_by('assetId')
        else:
            codition = (Q(assetId__icontains=search_key) | \
                Q(start_location__icontains=search_key) | \
                Q(end_location__icontains=search_key) | \
                Q(asset_name__icontains=search_key) | \
                Q(func_class__icontains=search_key) | \
                Q(pavement_surface__icontains=search_key))
            assetAList = AssetAForm.objects.filter(Q(created_by__in=user_names.keys()) & codition).order_by('assetId')
        assetAList = json.loads(serializers.serialize('json', assetAList))

        for item in assetAList:
            asset = item['fields']
            asset['id'] = item['pk']

            asset['user_id'] = asset['created_by']
            asset['created_by'] = user_names[asset['created_by']]

            try:
                asset['area'] = float(asset['length']) * float(asset['wide'])
            except:
                asset['area'] = 0

            for tp in asset:
                asset[tp] = "" if asset[tp] == "None" or asset[tp] == None else asset[tp]

            temp.append(asset)
    else:
        if search_key == "" or search_key == None:
            assetBList = AssetBForm.objects.filter(created_by__in=user_names.keys()).order_by('assetId')
        else:
            codition = (Q(assetId__icontains=search_key) | \
                Q(type__icontains=search_key) | \
                Q(code__icontains=search_key) | \
                Q(support_structure__icontains=search_key))
            assetBList = AssetBForm.objects.filter(Q(created_by__in=user_names.keys()) & codition).order_by('assetId')
        
        assetBList = json.loads(serializers.serialize('json', assetBList))

        for item in assetBList:
            asset = item['fields']
            asset['id'] = item['pk']
            asset['user_id'] = asset['created_by']
            asset['created_by'] = user_names[asset['created_by']]

            for tp in asset:
                asset[tp] = "" if asset[tp] == "None" or asset[tp] == None else asset[tp]

            temp.append(asset)

    users = [user.pk for user in users]
    filteredData = [asset for asset in temp if asset['user_id'] in users]

    return HttpResponse(json.dumps(filteredData), content_type='application/json')

# Controller for form view
@login_required
def formView(request):
    if request.method == "POST":
        asset_type = request.POST.get('asset_type')
        geometry = request.POST.get('geometry')
        print (asset_type)

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
        print (data)
        data['updated_by'] = request.user.pk

        form = AssetBDjForm(data, instance=asset)
        form.save()

    return render(request, 'asset/editB.html', 
        {'asset': asset, 'SUPPORT_STRUCTURE': SUPPORT_STRUCTURE})

@login_required
@csrf_exempt
def apiFormRemoveA(request, pk):
    asset = get_object_or_404(AssetAForm, pk=pk)
    if asset:
        asset.delete()

    return HttpResponse("OK")

@login_required
@csrf_exempt
def apiFormRemoveB(request, pk):
    asset = get_object_or_404(AssetBForm, pk=pk)
    if asset:
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

@login_required
@csrf_exempt
def apiGeoJson(request):
    res = dict()
    search_key = request.POST.get('search')

    users = CustomUser.objects.filter(company_id=request.user.company_id)
    user_names = {tp.pk:tp.username for tp in users}

    join_field = AssetAForm.objects.filter(Q(created_by__in=user_names.keys())).query

    if search_key != None and search_key != "":
        codition = (Q(assetId__icontains=search_key) | \
            Q(start_location__icontains=search_key) | \
            Q(end_location__icontains=search_key) | \
            Q(asset_name__icontains=search_key) | \
            Q(func_class__icontains=search_key) | \
            Q(pavement_surface__icontains=search_key))
        join_field = AssetAForm.objects.filter(Q(created_by__in=user_names.keys()) & codition).query
    join_field = str(join_field).split("WHERE")[1].strip()

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

    join_field = AssetBForm.objects.filter(Q(created_by__in=user_names.keys())).query

    if search_key != None and search_key != "":
        codition = (Q(assetId__icontains=search_key) | \
                Q(type__icontains=search_key) | \
                Q(code__icontains=search_key) | \
                Q(support_structure__icontains=search_key))
        join_field = AssetBForm.objects.filter(Q(created_by__in=user_names.keys()) & codition).query
    join_field = str(join_field).split("WHERE")[1].strip()

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

    print (shapefile)
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

        print ("start", asset_id)
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
                    sql = '''INSERT INTO form_asset_a (%s, "asset_id", "created_by", "created_at", "updated_at", "geom") 
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
                    sql = '''INSERT INTO form_asset_b (%s, "asset_id", "created_by", "created_at", "updated_at", "geom") 
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
            items = models_class.objects.filter(Q(created_by__in=user_names.keys()) & condition)
        else:
            items = models_class.objects.filter(Q(created_by__in=user_names.keys()))

        for obj in items:
            row = [getattr(obj, field) for field in field_names]
            row.append(user_names[obj.created_by])

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

    # create shape files for asset_a and asset_b
    if search_key != None and search_key != "":
        codition_a = (Q(assetId__icontains=search_key) | \
            Q(start_location__icontains=search_key) | \
            Q(end_location__icontains=search_key) | \
            Q(asset_name__icontains=search_key) | \
            Q(func_class__icontains=search_key) | \
            Q(pavement_surface__icontains=search_key))
        search_field = AssetAForm.objects.filter(Q(created_by__in=user_names.keys()) & codition_a).query
        search_field = str(search_field).split("WHERE")[1].strip()
        search_field = search_field.replace("LIKE UPPER(", "LIKE UPPER('").replace("(%", "('%").replace("%)", "%')")
        os.system('ogr2ogr -f "ESRI Shapefile" upload/%s/asset_a_shp/asset_a.shp %s "form_asset_a" -where "%s"' % (file_name, connection_string, search_field))

        codition_b = (Q(assetId__icontains=search_key) | \
                Q(type__icontains=search_key) | \
                Q(code__icontains=search_key) | \
                Q(support_structure__icontains=search_key))
        search_field = AssetBForm.objects.filter(Q(created_by__in=user_names.keys()) & codition_b).query
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