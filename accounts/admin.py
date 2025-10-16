from django.contrib import admin

from .models import CustomUser, ExtraUserInformation, Device

admin.site.register(CustomUser)
admin.site.register(ExtraUserInformation)


# Register your models here.
