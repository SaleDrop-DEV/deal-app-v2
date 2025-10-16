from django.contrib import admin

from .models import CustomUser, ExtraUserInformation, Device

admin.site.register(CustomUser)
admin.site.register(ExtraUserInformation)
admin.site.register(Device)



# Register your models here.
