from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.models import Governorate, Area, SubArea, Village
from accounts.utils import is_super_admin, is_area_manager, is_data_entry
from .serializers import * 
from .mixins import * 
from .permissions import IsSuperAdmin, IsLocationStaff


class GovernorateViewSet(viewsets.ModelViewSet):
    """
    إدارة المحافظات:
    - الأمن الأساسي فقط
    """
    serializer_class = GovernorateSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get_queryset(self):
        return Governorate.objects.all().order_by("id")


class AreaViewSet(viewsets.ModelViewSet):
    """
    إدارة المناطق:
    - الأمن الأساسي فقط
    - فلترة:
        ?governorate=<اسم المحافظة>
        ?name=<اسم المنطقة>
    """
    serializer_class = AreaSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get_queryset(self):
        qs = Area.objects.select_related("governorate").all().order_by("id")
        params = self.request.query_params

        gov_name = params.get("governorate")
        area_name = params.get("name")

        if gov_name:
            qs = qs.filter(governorate__name__iexact=gov_name)
        if area_name:
            qs = qs.filter(name__iexact=area_name)

        return qs


class SubAreaViewSet(viewsets.ModelViewSet):
    """
    إدارة النواحي:
    - الأمن الأساسي: يشوف/يضيف/يعدّل/يحذف الكل
    - مدير المنطقة + مدخل البيانات:
        يشوف/يضيف/يعدّل/يحذف فقط النواحي ضمن منطقته (user.area)
    """
    serializer_class = SubAreaSerializer
    permission_classes = [IsAuthenticated, IsLocationStaff]

    def get_queryset(self):
        qs = SubArea.objects.select_related("area", "area__governorate").all().order_by("id")
        params = self.request.query_params
        user = self.request.user

        # تقييد حسب الدور
        if is_super_admin(user):
            pass
        elif is_area_manager(user) or is_data_entry(user):
            if not user.area:
                return SubArea.objects.none()
            qs = qs.filter(area=user.area)
        else:
            return SubArea.objects.none()

        # فلاتر اختيارية بالأسماء
        area_name = params.get("area")
        gov_name = params.get("governorate")
        subarea_name = params.get("name")

        if area_name:
            qs = qs.filter(area__name__iexact=area_name)
        if gov_name:
            qs = qs.filter(area__governorate__name__iexact=gov_name)
        if subarea_name:
            qs = qs.filter(name__iexact=subarea_name)

        return qs


class VillageViewSet(viewsets.ModelViewSet):
    """
    إدارة القرى:
    - الأمن الأساسي: يشوف/يضيف/يعدّل/يحذف كل القرى
    - مدير المنطقة + مدخل البيانات:
        يشوف/يضيف/يعدّل/يحذف فقط القرى ضمن منطقته (subarea.area = user.area)
    """
    serializer_class = VillageSerializer
    permission_classes = [IsAuthenticated, IsLocationStaff]

    def get_queryset(self):
        qs = Village.objects.select_related(
            "subarea", "subarea__area", "subarea__area__governorate"
        ).all().order_by("id")

        params = self.request.query_params
        user = self.request.user

        # تقييد حسب الدور
        if is_super_admin(user):
            pass
        elif is_area_manager(user) or is_data_entry(user):
            if not user.area:
                return Village.objects.none()
            qs = qs.filter(subarea__area=user.area)
        else:
            return Village.objects.none()

        # فلاتر اختيارية بالأسماء
        subarea_name = params.get("subarea")
        area_name = params.get("area")
        gov_name = params.get("governorate")
        village_name = params.get("name")

        if subarea_name:
            qs = qs.filter(subarea__name__iexact=subarea_name)
        if area_name:
            qs = qs.filter(subarea__area__name__iexact=area_name)
        if gov_name:
            qs = qs.filter(subarea__area__governorate__name__iexact=gov_name)
        if village_name:
            qs = qs.filter(name__iexact=village_name)

        return qs

class PersonViewSet(LocationScopedQuerysetMixin, viewsets.ModelViewSet):
    """
    إدارة الأشخاص:
    - super_admin: يشوف الكل
    - area_manager / data_entry: فقط ضمن منطقته
    """

    queryset = Person.objects.select_related(
        "village",
        "village__subarea",
        "village__subarea__area",
        "sect",
        "ethnicity",
        "tribe",
    ).all()
    serializer_class = PersonSerializer
    permission_classes = [ IsAuthenticated, IsLocationStaff ]
    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        village_name = params.get("village")
        sect_name = params.get("sect")
        ethnicity_name = params.get("ethnicity")
        tribe_name = params.get("tribe")

        if village_name:
            qs = qs.filter(village__name__iexact=village_name)

        if sect_name:
            qs = qs.filter(sect__name__iexact=sect_name)

        if ethnicity_name:
            qs = qs.filter(ethnicity__name__iexact=ethnicity_name)

        if tribe_name:
            qs = qs.filter(tribe__name__iexact=tribe_name)
        return qs

    
class SectViewSet(viewsets.ModelViewSet):
    """
    إدارة الطوائف:
    - super_admin
    - area_manager
    - data_entry
    """

    queryset = Sect.objects.all().order_by("id")
    serializer_class = SectSerializer
    permission_classes = [IsAuthenticated,IsLocationStaff]

class EthnicityViewSet(viewsets.ModelViewSet):
    """
    إدارة القوميات:
    - super_admin
    - area_manager
    - data_entry
    """

    queryset = Ethnicity.objects.all().order_by("id")
    serializer_class = EthnicitySerializer
    permission_classes = [IsAuthenticated,IsLocationStaff]

class TribeViewSet(viewsets.ModelViewSet):
    """
    إدارة العشائر:
    - super_admin
    - area_manager
    - data_entry
    """

    queryset = Tribe.objects.all().order_by("id")
    serializer_class = TribeSerializer
    permission_classes = [IsAuthenticated,IsLocationStaff]


class VillageSectViewSet(viewsets.ModelViewSet):
    """
    API لإدارة بيانات الطوائف في القرى:

    - list    GET    /api/village-sects/
    - retrieve GET   /api/village-sects/{id}/
    - create  POST   /api/village-sects/
    - update  PUT    /api/village-sects/{id}/
    - partial_update PATCH /api/village-sects/{id}/
    - destroy DELETE /api/village-sects/{id}/
    """

    queryset = VillageSect.objects.select_related(
        "village",
        "village__subarea",
        "village__subarea__area",
        "village__subarea__area__governorate",
        "sect",
    ).all()

    serializer_class = VillageSectSerializer
    permission_classes = [IsAuthenticated, IsLocationStaff]

    def get_queryset(self):
        """
        فلترة النتائج حسب دور وموقع المستخدم:
        - super_admin: يشوف كل شيء
        - area_manager / data_entry: يشوف فقط القرى ضمن محافظته ومنطقته
        """
        user = self.request.user
        qs = super().get_queryset()

        if not user or not user.is_authenticated:
            return qs.none()

        if is_super_admin(user):
            return qs

        if is_area_manager(user) or is_data_entry(user):
            return qs.filter(
                village__subarea__area=user.area,
                village__subarea__area__governorate=user.governorate,
            )

        return qs.none()

    
class VillageSectKeyFigureViewSet(viewsets.ModelViewSet):
    """
    شخصيات رئيسية حسب (القرية، الطائفة):

    - list        GET    /api/village-sect-key-figures/
    - retrieve    GET    /api/village-sect-key-figures/{id}/
    - create      POST   /api/village-sect-key-figures/
    - update      PUT    /api/village-sect-key-figures/{id}/
    - partial_update PATCH /api/village-sect-key-figures/{id}/
    - destroy     DELETE /api/village-sect-key-figures/{id}/
    """

    queryset = VillageSectKeyFigure.objects.select_related(
        "village_sect",
        "village_sect__village",
        "village_sect__village__subarea",
        "village_sect__village__subarea__area",
        "village_sect__village__subarea__area__governorate",
        "village_sect__sect",
        "person",
        "created_by",
    ).all()

    serializer_class = VillageSectKeyFigureSerializer
    permission_classes = [IsAuthenticated, IsLocationStaff]

    def get_queryset(self):
        """
        - super_admin: يشوف كل الشخصيات
        - area_manager / data_entry: فقط الشخصيات ضمن منطقته
        """
        user = self.request.user
        qs = super().get_queryset()

        if not user or not user.is_authenticated:
            return qs.none()

        if is_super_admin(user):
            return qs

        if is_area_manager(user) or is_data_entry(user):
            return qs.filter(
                village_sect__village__subarea__area=user.area,
                village_sect__village__subarea__area__governorate=user.governorate,
            )

        return qs.none()
    
class VillageEthnicityViewSet(viewsets.ModelViewSet) :

    """
    إدارة التوزيع العِرقي للقرى.
    """

    queryset = VillageEthnicity.objects.select_related(
        "village",
        "village__subarea",
        "village__subarea__area",
        "village__subarea__area__governorate",
        "ethnicity",
    ).all().order_by("-id")

    serializer_class = VillageEthnicitySerializer
    permission_classes = [IsAuthenticated, IsLocationStaff]

    def get_queryset(self):
        """
        - super_admin: يرى كل السجلات
        - area_manager / data_entry: فقط ضمن منطقته
        """
        user = self.request.user
        qs = super().get_queryset()

        if not user or not user.is_authenticated:
            return qs.none()

        if is_super_admin(user):
            return qs

        if is_area_manager(user) or is_data_entry(user):
            return qs.filter(
                village__subarea__area=user.area,
                village__subarea__area__governorate=user.governorate,
            )

        return qs.none()
    
class VillageTribeViewSet(viewsets.ModelViewSet):
    """
    إدارة التوزيع القبلي للقرى.
    """

    queryset = VillageTribe.objects.select_related(
        "village",
        "village__subarea",
        "village__subarea__area",
        "village__subarea__area__governorate",
        "tribe",
    ).all().order_by("-id")

    serializer_class = VillageTribeSerializer
    permission_classes = [IsAuthenticated, IsLocationStaff]

    def get_queryset(self):
        """
        - super_admin: يرى كل السجلات
        - area_manager / data_entry: فقط ضمن منطقته
        """
        user = self.request.user
        qs = super().get_queryset()

        if not user or not user.is_authenticated:
            return qs.none()

        if is_super_admin(user):
            return qs

        if is_area_manager(user) or is_data_entry(user):
            return qs.filter(
                village__subarea__area=user.area,
                village__subarea__area__governorate=user.governorate,
            )

        return qs.none()

class IndustrialFacilityViewSet(viewsets.ModelViewSet):
    """
    إدارة المنشآت الصناعية.
    """

    queryset = IndustrialFacility.objects.select_related(
        "village",
        "village__subarea",
        "village__subarea__area",
        "village__subarea__area__governorate",
        "person",
        "created_by",
    ).all().order_by("-year", "-id")

    serializer_class = IndustrialFacilitySerializer
    permission_classes = [IsAuthenticated, IsLocationStaff]

    def get_queryset(self):
        """
        - super_admin: يرى كل المنشآت
        - area_manager / data_entry: فقط ضمن منطقته
        """
        user = self.request.user
        qs = super().get_queryset()

        if not user or not user.is_authenticated:
            return qs.none()

        if is_super_admin(user):
            return qs

        if is_area_manager(user) or is_data_entry(user):
            return qs.filter(
                village__subarea__area=user.area,
                village__subarea__area__governorate=user.governorate,
            )

        return qs.none()
    
class LivestockViewSet(viewsets.ModelViewSet):
    """
    إدارة بيانات الثروة الحيوانية للقرى.
    """

    queryset = Livestock.objects.select_related(
        "village",
        "village__subarea",
        "village__subarea__area",
        "village__subarea__area__governorate",
        "created_by",
    ).all().order_by("-year", "village__name")

    serializer_class = LivestockSerializer
    permission_classes = [IsAuthenticated, IsLocationStaff]

    def get_queryset(self):
        """
        - super_admin: كل السجلات
        - area_manager / data_entry: فقط ضمن منطقته
        """
        user = self.request.user
        qs = super().get_queryset()

        if not user or not user.is_authenticated:
            return qs.none()

        if is_super_admin(user):
            return qs

        if is_area_manager(user) or is_data_entry(user):
            return qs.filter(
                village__subarea__area=user.area,
                village__subarea__area__governorate=user.governorate,
            )

        return qs.none()
    
class GovernmentDepartmentViewSet(viewsets.ModelViewSet):
    """
    إدارة الدوائر الحكومية.
    """

    queryset = GovernmentDepartment.objects.select_related(
        "village",
        "village__subarea",
        "village__subarea__area",
        "village__subarea__area__governorate",
    ).all().order_by("-year", "department_name")

    serializer_class = GovernmentDepartmentSerializer
    permission_classes = [IsAuthenticated, IsLocationStaff]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if not user or not user.is_authenticated:
            return qs.none()

        if is_super_admin(user):
            return qs

        if is_area_manager(user) or is_data_entry(user):
            return qs.filter(
                village__subarea__area=user.area,
                village__subarea__area__governorate=user.governorate,
            )

        return qs.none()
    
class NaturalAssetViewSet(viewsets.ModelViewSet):
    """
    إدارة الموارد/المعالم الطبيعية.
    """

    queryset = NaturalAsset.objects.select_related(
        "village",
        "village__subarea",
        "village__subarea__area",
        "village__subarea__area__governorate",
        "person_id_owner_name",
        "person_id_investor_name",
    ).all().order_by("-year", "village__name", "name")

    serializer_class = NaturalAssetSerializer
    permission_classes = [IsAuthenticated, IsLocationStaff]

    def get_queryset(self):
        """
        - super_admin: يرى كل السجلات
        - area_manager / data_entry: فقط ضمن منطقته
        """
        user = self.request.user
        qs = super().get_queryset()

        if not user or not user.is_authenticated:
            return qs.none()

        if is_super_admin(user):
            return qs

        if is_area_manager(user) or is_data_entry(user):
            return qs.filter(
                village__subarea__area=user.area,
                village__subarea__area__governorate=user.governorate,
            )

        return qs.none()
    
class IndustrialZoneViewSet(viewsets.ModelViewSet):
    """
    إدارة بيانات المناطق الصناعية (إحصائيات).
    """

    queryset = IndustrialZone.objects.select_related(
        "village",
        "village__subarea",
        "village__subarea__area",
        "village__subarea__area__governorate",
        "created_by",
    ).all().order_by("-year", "village__name")

    serializer_class = IndustrialZoneSerializer
    permission_classes = [IsAuthenticated, IsLocationStaff]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if not user or not user.is_authenticated:
            return qs.none()

        if is_super_admin(user):
            return qs

        if is_area_manager(user) or is_data_entry(user):
            return qs.filter(
                village__subarea__area=user.area,
                village__subarea__area__governorate=user.governorate,
            )

        return qs.none()
    
class ArchaeologicalSiteViewSet(viewsets.ModelViewSet):
    """
    إدارة المواقع الأثرية.
    """

    queryset = ArchaeologicalSite.objects.select_related(
        "village",
        "village__subarea",
        "village__subarea__area",
        "village__subarea__area__governorate",
        "created_by",
    ).all().order_by("-year", "name")

    serializer_class = ArchaeologicalSiteSerializer
    permission_classes = [IsAuthenticated, IsLocationStaff]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if not user or not user.is_authenticated:
            return qs.none()

        if is_super_admin(user):
            return qs

        if is_area_manager(user) or is_data_entry(user):
            return qs.filter(
                village__subarea__area=user.area,
                village__subarea__area__governorate=user.governorate,
            )

        return qs.none()
    

class TourismFacilityViewSet(viewsets.ModelViewSet):
    """
    إدارة المنشآت السياحية في القرى.
    """

    queryset = TourismFacility.objects.select_related(
        "village",
        "village__subarea",
        "village__subarea__area",
        "village__subarea__area__governorate",
        "created_by",
    ).all().order_by("-year", "type")

    serializer_class = TourismFacilitySerializer
    permission_classes = [IsAuthenticated, IsLocationStaff]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if not user or not user.is_authenticated:
            return qs.none()

        if is_super_admin(user):
            return qs

        if is_area_manager(user) or is_data_entry(user):
            return qs.filter(
                village__subarea__area=user.area,
                village__subarea__area__governorate=user.governorate,
            )

        return qs.none()

class CommercialActivityViewSet(viewsets.ModelViewSet):
    """
    إدارة الأنشطة التجارية في القرى.
    """

    queryset = CommercialActivity.objects.select_related(
        "village",
        "village__subarea",
        "village__subarea__area",
        "village__subarea__area__governorate",
        "created_by",
    ).all().order_by("-year", "name")

    serializer_class = CommercialActivitySerializer
    permission_classes = [IsAuthenticated, IsLocationStaff]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if not user or not user.is_authenticated:
            return qs.none()

        if is_super_admin(user):
            return qs

        if is_area_manager(user) or is_data_entry(user):
            return qs.filter(
                village__subarea__area=user.area,
                village__subarea__area__governorate=user.governorate,
            )

        return qs.none()

class DemographicDataViewSet(viewsets.ModelViewSet):
    """
    إدارة البيانات الديموغرافية للقرى.
    """

    queryset = DemographicData.objects.select_related(
        "village",
        "village__subarea",
        "village__subarea__area",
        "village__subarea__area__governorate",
        "created_by",
    ).all().order_by("-year", "village__name")

    serializer_class = DemographicDataSerializer
    permission_classes = [IsAuthenticated, IsLocationStaff]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if not user or not user.is_authenticated:
            return qs.none()

        if is_super_admin(user):
            return qs

        if is_area_manager(user) or is_data_entry(user):
            return qs.filter(
                village__subarea__area=user.area,
                village__subarea__area__governorate=user.governorate,
            )

        return qs.none()
