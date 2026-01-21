from django.urls import path , include
from .views import LoginView, RefreshView, LogoutView, MeView , ChangePasswordView , ProfileView , AccountManagementViewSet , IndustrialFacilityViewSet,LivestockViewSet,GovernmentDepartmentViewSet,NaturalAssetViewSet ,ArchaeologicalSiteViewSet,TourismFacilityViewSet,CommercialActivityViewSet,DemographicDataViewSet , IndustrialZoneViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register("accounts", AccountManagementViewSet, basename="accounts-management")
router.register("industrial-facilities", IndustrialFacilityViewSet, basename="industrialfacility")
router.register(r'livestock', LivestockViewSet)
router.register(r'government-departments', GovernmentDepartmentViewSet)
router.register(r'natural-assets', NaturalAssetViewSet)
router.register(r'industrial-zones', IndustrialZoneViewSet)
router.register(r'archaeological-sites', ArchaeologicalSiteViewSet)
router.register(r'tourism-facilities', TourismFacilityViewSet)
router.register(r'commercial-activities', CommercialActivityViewSet)
router.register(r'demographic-data', DemographicDataViewSet)


urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("profile/" , ProfileView.as_view() , name = "profile" ) ,
    path('', include( router.urls ) ) ,
]