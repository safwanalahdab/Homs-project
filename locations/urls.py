# locations/urls.py
from django.urls import path , include 
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register("governorates", GovernorateViewSet, basename="governorates")
router.register("areas", AreaViewSet, basename="areas")
router.register("subareas", SubAreaViewSet, basename="subareas")
router.register("villages", VillageViewSet, basename="villages")
router.register("persons", PersonViewSet, basename="persons")
router.register("sect", SectViewSet , basename="sectViewSet")
router.register("ethnicity", EthnicityViewSet , basename="EthnicityViewSet")
router.register("tribe", TribeViewSet , basename="Tribe")
router.register("village-sects", VillageSectViewSet, basename="village-sects")
router.register("village-sect-key-figures",VillageSectKeyFigureViewSet,basename="village-sect-key-figures")
router.register("villageEthnicity",VillageEthnicityViewSet,basename="villageEthnicity")
router.register("village-tribes", VillageTribeViewSet, basename="village-tribe")
router.register("industrial-facilities",IndustrialFacilityViewSet,basename="industrial-facility")
router.register("livestock",LivestockViewSet,basename="livestock")
router.register("government-departments",GovernmentDepartmentViewSet,basename="government-department")
router.register("natural-assets",NaturalAssetViewSet,basename="natural-asset")
router.register("industrial-zones",IndustrialZoneViewSet,basename="industrial-zone")
router.register("archaeological-sites",ArchaeologicalSiteViewSet, basename="archaeological-site")
router.register("tourism-facilities",TourismFacilityViewSet,basename="tourism-facility")
router.register("commercial-activities",CommercialActivityViewSet,basename="commercial-activity")
router.register("demographic-data",DemographicDataViewSet,basename="demographic-data")


urlpatterns = [
    path('', include( router.urls ) ) ,
] 