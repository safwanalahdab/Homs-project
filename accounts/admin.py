from django.contrib import admin
from .models import * 
# Register your models here.

MODELS = [
    Governorate, Area, SubArea, Village,
    Role, Permission, PermissionRole,
    User,
    Sect, Ethnicity, Tribe,
    Person,
    VillageSect, VillageSectKeyFigure,
    VillageEthnicity, EthnicityKeyFigure,
    VillageTribe, VillageTribeKeyFigure,
    ModificationRequest, AuditLog, UserHistory,
    Livestock, GovernmentDepartment, NaturalAsset,
    IndustrialZone, TourismFacility, IndustrialFacility,
    ArchaeologicalSite, CommercialActivity,
    DemographicData, AgriculturalStatus,
    Crop, AgriculturalCrop,
]

admin.site.register(MODELS)
