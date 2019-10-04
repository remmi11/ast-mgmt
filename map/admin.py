from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib import auth
from map.models import Company

class CustomUserAdmin(UserAdmin):
    fieldsets = (
        (None, {
            'fields': ('username', 'password', 'company')
        }),
        ('Advanced options', {
            'fields': ('is_active', 'is_superuser'),
        }),
    )
    list_display = ('username', 'company', 'last_login', 'date_joined', 'is_active', 'is_superuser')
    list_filter = ('last_login', 'date_joined', 'is_active')
    search_fields = ('username', 'email')
    ordering = ('-last_login',)

class CompanyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    list_filter = ('name', )
    search_fields = ('name', )
    ordering = ('name',)

admin.site.register(get_user_model(), CustomUserAdmin)
admin.site.register(Company, CompanyAdmin)
admin.site.unregister(auth.models.Group)