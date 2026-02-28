from rest_framework import serializers
from accounts.models import *
from accounts.utils import *
from accounts.utils import * 
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError


class GovernorateSerializer(serializers.ModelSerializer):
    """
    محافظة:
    - الإرسال: name فقط
    - الإرجاع: id + name
    """
    class Meta:
        model = Governorate
        fields = ["id", "name"]

class AreaSerializer(serializers.ModelSerializer):
    #governorate_name = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = Area
        fields = ["id", "name", "governorate"]
        extra_kwargs = {
            "governorate": {"required": False}, 
        }

    def validate(self, attrs):
        gov_id = attrs.get("governorate", None)
        gov_name = attrs.get("governorate_name", None)

        if not gov_id and not gov_name:
            raise serializers.ValidationError(
                {"governorate": "Provide either governorate (id) or governorate_name."}
            )

        if gov_id and gov_name:
            raise serializers.ValidationError(
                {"governorate": "Use only one of governorate (id) or governorate_name."}
            )

        if gov_name:
            gov = Governorate.objects.filter(name__iexact=gov_name).first()
            if not gov:
                raise serializers.ValidationError({"governorate_name": "Governorate not found."})
            attrs["governorate"] = gov

        return attrs


class SubAreaSerializer(serializers.ModelSerializer):

    area = serializers.IntegerField(required=False, write_only=True)
    area_name = serializers.CharField(required=False, write_only=False)

    class Meta:
        model = SubArea
        fields = ["id", "name", "area", "area_name"]

    def validate(self, attrs):
        user = self.context["request"].user

        area_id = attrs.get("area")
        area_name = attrs.get("area_name")

        if (area_id is not None) or (area_name is not None):
            if not is_super_admin(user):
                raise serializers.ValidationError("لا يمكنك تحديد المنطقة يدويا")

            if area_id is not None and area_name is not None:
                raise serializers.ValidationError("يجب ان تحدد المنطقة التي تتبع لها الناحية")

            if area_id is not None:
                area_obj = Area.objects.filter(id=area_id).first()
                if not area_obj:
                    raise serializers.ValidationError({"area": "المنطقة غير موجودة"})
                attrs["area_obj"] = area_obj

            if area_name is not None:
                area_obj = Area.objects.filter(name__iexact=area_name).first()
                if not area_obj:
                    raise serializers.ValidationError({"area_name": "المنطقة غير موجودة"})
                attrs["area_obj"] = area_obj

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user

        if is_super_admin(user):
            area_obj = validated_data.pop("area_obj", None)
            if not area_obj:
                raise serializers.ValidationError("يجب ان تحدد المنطقة التي تتبع لها الناحية")
        else:
            if not user.area:
                raise serializers.ValidationError("حسابك غير مرتبط بمنطقة")
            area_obj = user.area

        validated_data.pop("area", None)
        validated_data.pop("area_name", None)

        return SubArea.objects.create(area=area_obj, **validated_data)


class VillageSerializer(serializers.ModelSerializer):

    subarea = serializers.IntegerField(required=False, write_only=True)
    subarea_name = serializers.CharField(required=False, write_only=True)

    subarea_id = serializers.IntegerField(read_only=True)
    subarea_display = serializers.CharField(source="subarea.name", read_only=True)

    class Meta:
        model = Village
        fields = [
            "id", "name", "type", "parent_name",
            "subarea_id", "subarea_display",
            "subarea", "subarea_name","code"
        ]


    def validate(self, attrs):
        user = self.context["request"].user

        subarea_id = attrs.get("subarea")
        subarea_name = attrs.get("subarea_name")

        # لازم واحد منهم على الأقل (لأن القرية لازم ترتبط بناحية)
        if subarea_id is None and subarea_name is None:
            raise serializers.ValidationError("يجب ارسال الرقم التعريفي للناحية او اسمها")

        # ممنوع الاثنين سوا
        if subarea_id is not None and subarea_name is not None:
          raise serializers.ValidationError("يجب ارسال الرقم التعريفي للناحية او اسمها")

        # جيب SubArea object
        if subarea_id is not None:
            subarea = SubArea.objects.select_related("area").filter(id=subarea_id).first()
            if not subarea:
                raise serializers.ValidationError({"subarea": "الناحية غير موجودة"})
        else:
            subarea = SubArea.objects.select_related("area").filter(name__iexact=subarea_name).first()
            if not subarea:
                raise serializers.ValidationError({"subarea_name": "الناحية غير موجودة"})

        # تحقق صلاحيات الربط
        if not is_super_admin(user):
            if not user.area:
                raise serializers.ValidationError("حسابك غير مرتبط بمنطقة")
            if subarea.area_id != user.area_id:
                raise serializers.ValidationError("لا يمكنك ربط القرية بناحية خارج منطقتك")

        # خزّنها كـ object لمرحلة create/update
        attrs["subarea_obj"] = subarea
        return attrs

    def create(self, validated_data):
        subarea_obj = validated_data.pop("subarea_obj")
        validated_data.pop("subarea", None)
        validated_data.pop("subarea_name", None)
        return Village.objects.create(subarea=subarea_obj, **validated_data)

    def update(self, instance, validated_data):
        user = self.context["request"].user

        # إذا في محاولة لتغيير الناحية (ID أو Name)
        if "subarea" in validated_data or "subarea_name" in validated_data:
            # استعمل نفس validate() ليطلع subarea_obj
            validated_data = self.validate(validated_data)
            new_subarea = validated_data.pop("subarea_obj")

            # تحقق صلاحيات النقل (نفس منطقك)
            if not is_super_admin(user):
                if not user.area:
                    raise serializers.ValidationError("حسابك غير مرتبط بمنطقة")
                if new_subarea.area_id != user.area_id:
                    raise serializers.ValidationError("لا يمكنك نقل القرية إلى ناحية خارج منطقتك")

            instance.subarea = new_subarea

            # نظّف مفاتيح الإدخال
            validated_data.pop("subarea", None)
            validated_data.pop("subarea_name", None)

        # حدّث باقي الحقول
        return super().update(instance, validated_data)

    

class PersonSerializer(serializers.ModelSerializer):

    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all(),error_messages={
            "required": "يجب إضافة القرية.",
            "does_not_exist": "القرية المحددة غير موجودة.",},)
    sect = serializers.PrimaryKeyRelatedField(queryset=Sect.objects.all(), required=False, allow_null=True)
    ethnicity = serializers.PrimaryKeyRelatedField(queryset=Ethnicity.objects.all(), required=False, allow_null=True)
    tribe = serializers.PrimaryKeyRelatedField(queryset=Tribe.objects.all(), required=False, allow_null=True)

    village_name = serializers.CharField(source="village.name", read_only=True)
    subarea_name = serializers.CharField(source="village.subarea.name", read_only=True)
    area_name = serializers.CharField(source="village.subarea.area.name", read_only=True)
    governorate_name = serializers.CharField(source="village.subarea.area.governorate.name", read_only=True)

    sect_name = serializers.CharField(source="sect.name", read_only=True, default=None)
    ethnicity_name = serializers.CharField(source="ethnicity.name", read_only=True, default=None)
    tribe_name = serializers.CharField(source="tribe.name", read_only=True, default=None)

    class Meta:
        model = Person
        fields = [
            "id",
            "name",

            # FK (IDs)
            "village",
            "sect",
            "ethnicity",
            "tribe",

            # optional display
            "village_name",
            "subarea_name",
            "area_name",
            "governorate_name",
            "sect_name",
            "ethnicity_name",
            "tribe_name",

            # info
            "phone",
            "address",
            "educational_qualifications",
            "work",
            "social_interests",
            "community_influence",
            "system_affiliation",
            "new_leadership",

            # system
            "locked",
            "created_by",
            "created_at",
        ]
        read_only_fields = ["locked", "created_by", "created_at"]

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user

        village = attrs.get("village") or getattr(self.instance, "village", None) 

        if not village:
            return attrs
           
        if is_super_admin(user):
            return attrs

        if is_area_manager(user) or is_data_entry(user):
            if (
                village.subarea.area != user.area
                or village.subarea.area.governorate != user.governorate
            ):
                raise serializers.ValidationError(
                    {"village": "لا يمكنك إضافة/تعديل أشخاص خارج منطقتك الإدارية."}
                )

        return attrs

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)

class SectSerializer(serializers.ModelSerializer):
    """
    API الطوائف:
    - الإرسال: name
    - الإرجاع: id + name
    """
    class Meta:
        model = Sect
        fields = ["id", "name"]

class EthnicitySerializer(serializers.ModelSerializer):
    """
    API القوميات:
    - الإرسال: name
    - الإرجاع: id + name
    """
    class Meta:
        model = Ethnicity
        fields = ["id", "name"]

class TribeSerializer(serializers.ModelSerializer):
    """
    API العشائر:
    - الإرسال: name
    - الإرجاع: id + name
    """

    class Meta:
        model = Tribe
        fields = ["id", "name"]
    

class VillageSectSerializer(serializers.ModelSerializer):
    # FK as IDs
    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())
    sect = serializers.PrimaryKeyRelatedField(queryset=Sect.objects.all())

    # optional display (إذا بدك)
    village_name = serializers.CharField(source="village.name", read_only=True)
    name = serializers.CharField(source="sect.name", read_only=True)

    class Meta:
        model = VillageSect
        fields = [
            "id",
            "village",
            "sect",
            "family_count",
            "individual_count",
            "village_name",
            "name",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user

        village = attrs.get("village") or getattr(self.instance, "village", None)
        sect = attrs.get("sect") or getattr(self.instance, "sect", None)

        # 1) تحقق نطاق المستخدم (متل ما عندك)
        if village and not is_super_admin(user) and (is_area_manager(user) or is_data_entry(user)):
            if (
                village.subarea.area != user.area
                or village.subarea.area.governorate != user.governorate
            ):
                raise serializers.ValidationError(
                    {"village": "لا يمكنك إدارة بيانات الطوائف خارج منطقتك."}
                )

        if self.instance is None and village and sect:
            exists = VillageSect.objects.filter(village=village, sect=sect).exists()
            if exists:
                raise serializers.ValidationError(
                    {"non_field_errors": ["هذه السجلات موجودة مسبقاً لنفس القرية ونفس الطائفة."]}
                )

        if self.instance is not None and village and sect:
            exists = VillageSect.objects.filter(village=village, sect=sect).exclude(id=self.instance.id).exists()
            if exists:
                raise serializers.ValidationError(
                    {"non_field_errors": ["لا يمكن تعديل السجل إلى قرية/طائفة موجودة مسبقاً."]}
                )

        return attrs

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)

    
class VillageEthnicitySerializer(serializers.ModelSerializer):

    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())
    ethnicity = serializers.PrimaryKeyRelatedField(queryset=Ethnicity.objects.all())

    village_name = serializers.CharField(source="village.name", read_only=True)
    name = serializers.CharField(source="ethnicity.name", read_only=True)

    class Meta:
        model = VillageEthnicity
        fields = [
            "id",
            "village",
            "ethnicity",
            "village_name",
            "name",
            "family_count",
            "individual_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        """
        1) منع تكرار (قرية + عرق)
        2) التحقق من الصلاحيات الجغرافية
        """
        request = self.context["request"]
        user = request.user
        instance = getattr(self, "instance", None)

        village = attrs.get("village") or (instance.village if instance else None)
        ethnicity = attrs.get("ethnicity") or (instance.ethnicity if instance else None)

        # 1️⃣ منع التكرار
        if village and ethnicity:
            qs = VillageEthnicity.objects.filter(
                village=village,
                ethnicity=ethnicity,
            )
            if instance:
                qs = qs.exclude(pk=instance.pk)

            if qs.exists():
                raise ValidationError(
                    {
                        "non_field_errors": (
                            "يوجد سجل لهذا العِرق في هذه القرية مسبقًا. "
                            "قم بتعديله بدل إنشاء سجل جديد."
                        )
                    }
                )

        # 2️⃣ الصلاحيات حسب المنطقة
        if not is_super_admin(user):
            if is_area_manager(user) or is_data_entry(user):
                if (
                    not village
                    or village.subarea.area != user.area
                    or village.subarea.area.governorate != user.governorate
                ):
                    raise ValidationError(
                        {
                            "village": "لا يمكنك إدارة بيانات الأعراق خارج منطقتك."
                        }
                    )
            else:
                raise ValidationError(
                    {"permission": "لا تملك صلاحية لإدارة هذه البيانات."}
                )

        return attrs

class VillageTribeSerializer(serializers.ModelSerializer):
    """
    توزيع قبلي داخل قرية 
    """
    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())
    tribe = serializers.PrimaryKeyRelatedField(queryset=Tribe.objects.all())

    # اختياري للعرض
    village_name = serializers.CharField(source="village.name", read_only=True)
    name = serializers.CharField(source="tribe.name", read_only=True)

    
    class Meta:
        model = VillageTribe
        fields = [
            "id",
            "village",
            "tribe",
            "village_name",
            "name",
            "individual_count",
            "family_count" ,
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        """
        1) منع تكرار (قرية + قبيلة)
        2) التحقق من الصلاحيات الجغرافية
        """
        request = self.context["request"]
        user = request.user
        instance = getattr(self, "instance", None)

        village = attrs.get("village") or (instance.village if instance else None)
        tribe = attrs.get("tribe") or (instance.tribe if instance else None)

        # 1️⃣ منع التكرار
        if village and tribe:
            qs = VillageTribe.objects.filter(
                village=village,
                tribe=tribe,
            )
            if instance:
                qs = qs.exclude(pk=instance.pk)

            if qs.exists():
                raise ValidationError(
                    {
                        "non_field_errors": (
                            "يوجد سجل لهذه القبيلة في هذه القرية مسبقًا. "
                            "قم بتعديله بدل إنشاء سجل جديد."
                        )
                    }
                )

        # 2️⃣ الصلاحيات حسب المنطقة
        if not is_super_admin(user):
            if is_area_manager(user) or is_data_entry(user):
                if (
                    not village
                    or village.subarea.area != user.area
                    or village.subarea.area.governorate != user.governorate
                ):
                    raise ValidationError(
                        {
                            "village": "لا يمكنك إدارة بيانات القبائل خارج منطقتك."
                        }
                    )
            else:
                raise ValidationError(
                    {"permission": "لا تملك صلاحية لإدارة هذه البيانات."}
                )

        return attrs

class IndustrialFacilitySerializer(serializers.ModelSerializer):
    """
    منشآت صناعية ضمن قرية وفي سنة معيّنة.
    """

    # إدخال بالاسم بدل ID
    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())
    village_name = serializers.CharField(source="village.name", read_only=True)

    person = serializers.PrimaryKeyRelatedField(queryset=Person.objects.all(), required=False, allow_null=True)
    person_name = serializers.CharField(source="person.name", read_only=True)  # عدّل الحقل حسب موديل Person


    class Meta:
        model = IndustrialFacility
        fields = [
            "id",
            "village",
            "village_name" ,
            "name",
            "type",
            "person",
            "person_name" ,
            "classification",
            "number_of_workers",
            "has_license",
            "license_type",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        """
        1) منع تكرار (قرية + سنة + اسم منشأة)
        2) التحقق من الصلاحيات الجغرافية (ضمن نفس المنطقة)
        3) (اختياري) التأكد أن الشخص من نفس القرية
        """
        request = self.context["request"]
        user = request.user
        instance = getattr(self, "instance", None)

        village = attrs.get("village") or (instance.village if instance else None)
       # year = attrs.get("year") or (instance.year if instance else None)
        name = attrs.get("name") or (instance.name if instance else None)
        person = attrs.get("person") or (instance.person if instance else None)
        qs = IndustrialFacility.objects.all()
        # 1️⃣ منع تكرار (قرية + سنة + اسم)
        if village and name:
            qs = IndustrialFacility.objects.filter(
                village=village,
                name=name,
            )
            
        if instance:
                qs = qs.exclude(pk=instance.pk)

        if qs.exists():
                raise ValidationError(
                    {
                        "non_field_errors": (
                            "يوجد منشأة صناعية بهذا الاسم في نفس القرية ونفس السنة."
                        )
                    }
                )

        # 2️⃣ الصلاحيات الجغرافية
        if not is_super_admin(user):
            if is_area_manager(user) or is_data_entry(user):
                if (
                    not village
                    or village.subarea.area != user.area
                    or village.subarea.area.governorate != user.governorate
                ):
                    raise ValidationError(
                        {
                            "village": "لا يمكنك إدارة منشآت صناعية خارج منطقتك."
                        }
                    )
            else:
                raise ValidationError(
                    {"permission": "لا تملك صلاحية لإدارة هذه البيانات."}
                )

        return attrs

    def create(self, validated_data):
        """
        نحدد created_by = المستخدم الحالي
        """
        request = self.context["request"]
        user = request.user
        validated_data["created_by"] = user
        return super().create(validated_data)
    
class LivestockSerializer(serializers.ModelSerializer):
    """
    بيانات الثروة الحيوانية لقرية معيّنة في سنة معيّنة.
    """

    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())
    village_name = serializers.CharField(source="village.name", read_only=True)

    class Meta:
        model = Livestock
        fields = [
            "id",
            "village",
            "village_name" ,

            "cows_count",
            "sheep_count",
            "poultry_count",
            "camels_count",
            "fish_count",

            "feeds",
            "grazing_areas",
            "grazing_areas_size",

            "meat_production",
            "milk_products",
            "egg_production",

            "breeders_count",
            "veterinarians_count",

            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at"]

    def validate(self, attrs):
        """
        1) منع تكرار (قرية + سنة)
        2) التحقق من الصلاحيات الجغرافية
        """
        request = self.context["request"]
        user = request.user
        instance = getattr(self, "instance", None)

        village = attrs.get("village") or (instance.village if instance else None)
        qs = Livestock.objects.all()
        #year = attrs.get("year") or (instance.year if instance else None)

        # 1️⃣ منع التكرار
        #if village and year:
         #   qs = Livestock.objects.filter(
          #      village=village,
           #     year=year,
           # )
        if instance:
                qs = qs.exclude(pk=instance.pk)

        if qs.exists():
                raise ValidationError(
                    {
                        "non_field_errors": (
                            "يوجد سجل للثروة الحيوانية لهذه القرية في هذه السنة مسبقًا. "
                            "قم بتعديله بدل إنشاء سجل جديد."
                        )
                    }
                )

        # 2️⃣ الصلاحيات الجغرافية
        if not is_super_admin(user):
            if is_area_manager(user) or is_data_entry(user):
                if (
                    not village
                    or village.subarea.area != user.area
                    or village.subarea.area.governorate != user.governorate
                ):
                    raise ValidationError(
                        {
                            "village": "لا يمكنك إدارة بيانات الثروة الحيوانية خارج منطقتك."
                        }
                    )
            else:
                raise ValidationError(
                    {"permission": "لا تملك صلاحية لإدارة هذه البيانات."}
                )

        return attrs

    def create(self, validated_data):
        """
        تعبئة created_by بالمستخدم الحالي.
        """
        request = self.context["request"]
        user = request.user
        validated_data["created_by"] = user
        return super().create(validated_data)
    
class GovernmentDepartmentSerializer(serializers.ModelSerializer):
    """
    دائرة حكومية ضمن قرية وفي سنة معيّنة.
    """

    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())
    village_name = serializers.CharField(source="village.name", read_only=True)
  
    class Meta:
        model = GovernmentDepartment
        fields = [
            "id",
            "village",
            "village_name",
            "ministry_name",
            "department_name",
            "address",
            "director_name",
            "contact_number",
            "staff_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
        validators = []

    
    def validate(self, attrs):
        request = self.context["request"]
        user = request.user
        instance = getattr(self, "instance", None)

        village = attrs.get("village") or (instance.village if instance else None)
        department_name = attrs.get("department_name") or (
            instance.department_name if instance else None
        )

        # 1) منع التكرار: (village + department_name)
        if village and department_name:
            qs = GovernmentDepartment.objects.filter(
                village=village,
                department_name__iexact=department_name,
            )
            if instance:
                qs = qs.exclude(pk=instance.pk)

            if qs.exists():
                raise ValidationError(
                    {"error": "يوجد دائرة حكومية بهذا الاسم في هذه القرية."}
                )

        # 2) صلاحيات جغرافية
        if not is_super_admin(user):
            if is_area_manager(user) or is_data_entry(user):
                if (
                    not village
                    or village.subarea.area != user.area
                    or village.subarea.area.governorate != user.governorate
                ):
                    raise ValidationError(
                        {"village": "لا يمكنك إدارة دوائر خارج منطقتك."}
                    )
            else:
                raise ValidationError(
                    {"permission": "لا تملك صلاحية لإدارة هذه البيانات."}
                )

        return attrs
    
class NaturalAssetSerializer(serializers.ModelSerializer):
    """
    مورد/معلم طبيعي داخل قرية في سنة معيّنة.
    """

    # إدخال وعرض القرية بالاسم
    village_name = serializers.CharField(source="village.name", read_only=True)
    owner_person_name = serializers.CharField(source="person_id_owner_name.name", read_only=True)
    investor_person_name = serializers.CharField(source="person_id_investor_name.name", read_only=True)

    village = serializers.PrimaryKeyRelatedField(
        queryset=Village.objects.all()
    )

    person_id_owner_name = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(),
        required=False,
        allow_null=True
    )

    person_id_investor_name = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = NaturalAsset
        fields = [
            "id",
            "village",
            "village_name" ,


            "type",
            "name",
            "classification",
            "important_level",
            "ownership",

            "person_id_owner_name",
            "owner_person_name" ,
            "supervising_authority",
            "person_id_investor_name",
             "investor_person_name" ,

            "average_visitors",
            "annual_revenue",

            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        """
        1)  منع تكرار (قرية + سنة + اسم)
        2) تحقق من الصلاحيات الجغرافية
        """
        request = self.context["request"]
        user = request.user
        instance = getattr(self, "instance", None)

        village = attrs.get("village") or (instance.village if instance else None)
        #year = attrs.get("year") or (instance.year if instance else None)
        name = attrs.get("name") or (instance.name if instance else None)
        qs = NaturalAsset.objects.all()

        owner_person = (
            attrs.get("person_id_owner_name")
            if "person_id_owner_name" in attrs
            else (instance.person_id_owner_name if instance else None)
        )
        investor_person = (
            attrs.get("person_id_investor_name")
            if "person_id_investor_name" in attrs
            else (instance.person_id_investor_name if instance else None)
        )

        # 1️⃣ (اختياري لكن مفيد): منع تكرار نفس المورد بنفس الاسم في نفس القرية ونفس السنة
        #if village and year and name:
        #    qs = NaturalAsset.objects.filter(
        #        village=village,
        #        year=year,
        #        name=name,
        #    )
        if village and name:
         qs = NaturalAsset.objects.filter(
            village=village,
            name__iexact=name,  # ✅ تجاهل فرق الحروف
        )
        if instance:
            qs = qs.exclude(pk=instance.pk)

        if qs.exists():
            raise ValidationError({
                "name": "يوجد مورد طبيعي بهذا الاسم في هذه القرية ."
            })

        # 2️⃣ الصلاحيات الجغرافية
        if not is_super_admin(user):
            if is_area_manager(user) or is_data_entry(user):
                if (
                    not village
                    or village.subarea.area != user.area
                    or village.subarea.area.governorate != user.governorate
                ):
                    raise ValidationError(
                        {"village": "لا يمكنك إدارة موارد طبيعية خارج منطقتك."}
                    )
            else:
                raise ValidationError(
                    {"permission": "لا تملك صلاحية لإدارة هذه البيانات."}
                )


        return attrs
    
class IndustrialZoneSerializer(serializers.ModelSerializer):
    """
    بيانات إحصائية عن المنطقة الصناعية في قرية وسنة معيّنة.
    """

    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())
    village_name = serializers.CharField(source="village.name", read_only=True)

    class Meta:
        model = IndustrialZone
        fields = [
            "id",
            "village",
            "village_name" ,
            "number_of_facilities",
            "number_of_shops",
            "number_of_workers",
            "annual_revenue",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at"]

    def validate(self, attrs):
        """
        1) منع تكرار (قرية + سنة)
        2) التحقق من أن المستخدم ضمن نفس المنطقة (إلا السوبر أدمن)
        """
        request = self.context["request"]
        user = request.user
        instance = getattr(self, "instance", None)

        village = attrs.get("village") or (instance.village if instance else None)
        qs = IndustrialZone.objects.all()
        #year = attrs.get("year") or (instance.year if instance else None)

        # 1️⃣ منع التكرار
        if village:
            qs = IndustrialZone.objects.filter(
                village=village,
            )
        if instance:
                qs = qs.exclude(pk=instance.pk)

        if qs.exists():
                raise ValidationError(
                    {
                        "non_field_errors": (
                            "يوجد سجل منطقة صناعية لهذه القرية في هذه السنة مسبقًا. "
                            "قم بتعديله بدل إنشاء سجل جديد."
                        )
                    }
                )

        # 2️⃣ صلاحيات جغرافية
        if not is_super_admin(user):
            if is_area_manager(user) or is_data_entry(user):
                if (
                    not village
                    or village.subarea.area != user.area
                    or village.subarea.area.governorate != user.governorate
                ):
                    raise ValidationError(
                        {"village": "لا يمكنك إدارة مناطق صناعية خارج منطقتك."}
                    )
            else:
                raise ValidationError(
                    {"permission": "لا تملك صلاحية لإدارة هذه البيانات."}
                )

        return attrs

    def create(self, validated_data):
        """
        تعبئة created_by بالمستخدم الحالي.
        """
        request = self.context["request"]
        validated_data["created_by"] = request.user
        return super().create(validated_data)
    
class ArchaeologicalSiteSerializer(serializers.ModelSerializer):
    """
    موقع أثري ضمن قرية وفي سنة معيّنة.
    """
    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())
    village_name = serializers.CharField(source="village.name", read_only=True)

    class Meta:
        model = ArchaeologicalSite
        fields = [
            "id",
            "village",
            "village_name",
            "name",
            "site_date",
            "archaeological_feature",
            "is_registered",
            "registered_organization",
            "registration_date",
            "average_visitors",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user
        instance = getattr(self, "instance", None)
        qs = ArchaeologicalSite.objects.all()
        village = attrs.get("village") or (instance.village if instance else None)
       # year = attrs.get("year") or (instance.year if instance else None)
        name = attrs.get("name") or (instance.name if instance else None)

        # 1️⃣ منع التكرار
        if village and name:
           qs = ArchaeologicalSite.objects.filter(
                village=village,
                name=name,
            )
        if instance:
                qs = qs.exclude(pk=instance.pk)

        if qs.exists():
                raise ValidationError(
                    {
                        "non_field_errors": (
                            "يوجد موقع أثري بهذا الاسم في هذه القرية لنفس السنة."
                        )
                    }
                )

        # 2️⃣ الصلاحيات الجغرافية
        if not is_super_admin(user):
            if is_area_manager(user) or is_data_entry(user):
                if (
                    not village
                    or village.subarea.area != user.area
                    or village.subarea.area.governorate != user.governorate
                ):
                    raise ValidationError(
                        {"village": "لا يمكنك إدارة مواقع أثرية خارج منطقتك."}
                    )
            else:
                raise ValidationError(
                    {"permission": "لا تملك صلاحية لإدارة هذه البيانات."}
                )

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["created_by"] = request.user
        return super().create(validated_data)
    
class TourismFacilitySerializer(serializers.ModelSerializer):
    """
    بيانات عن المنشأة السياحية في قرية وسنة معيّنة.
    """

    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())
    village_name = serializers.CharField(source="village.name", read_only=True)

    class Meta:
        model = TourismFacility
        fields = [
            "id",
            "name" ,
            "village",
            "village_name" ,
            "type",
            "is_invested",
            "is_private_property",
            "person_id_investor_name",
            "person_id_owner_name",
            "supervising_authority",
            "classification",
            "average_visitors",
            "annual_revenue",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user
        instance = getattr(self, "instance", None)

        village = attrs.get("village") or (instance.village if instance else None)
       # year = attrs.get("year") or (instance.year if instance else None)
        type = attrs.get("type") or (instance.type if instance else None)
        qs = TourismFacility.objects.all()

        # 1️⃣ منع التكرار
        """
        if village and type:
           qs = TourismFacility.objects.filter(
                village=village,
                type=type,
            )
           
        if instance:
                qs = qs.exclude(pk=instance.pk)

        if qs.exists():
                raise ValidationError(
                    {
                        "non_field_errors": (
                            "يوجد سجل لهذه المنشأة السياحية في هذه القرية ."
                        )
                    }
                )
        """

        # 2️⃣ الصلاحيات الجغرافية
        if not is_super_admin(user):
            if is_area_manager(user) or is_data_entry(user):
                if (
                    not village
                    or village.subarea.area != user.area
                    or village.subarea.area.governorate != user.governorate
                ):
                    raise ValidationError(
                        {"village": "لا يمكنك إدارة منشآت سياحية خارج منطقتك."}
                    )
            else:
                raise ValidationError(
                    {"permission": "لا تملك صلاحية لإدارة هذه البيانات."}
                )

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["created_by"] = request.user
        return super().create(validated_data)

   
class CommercialActivitySerializer(serializers.ModelSerializer):
    """
    بيانات عن الأنشطة التجارية في قرية وسنة معيّنة.
    """

    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())
    village_name = serializers.CharField(source="village.name", read_only=True)

    class Meta:
        model = CommercialActivity
        fields = [
            "id",
            "village" ,
            "village_name" ,
            "name",
            "activity_type",
            "address",
            "person",
            "is_licensed",
            "license_type",
            "license_date",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user
        instance = getattr(self, "instance", None)

        village = attrs.get("village") or (instance.village if instance else None)
        #year = attrs.get("year") or (instance.year if instance else None)
        name = attrs.get("name") or (instance.name if instance else None)
        qs = CommercialActivity.objects.all()
        # 1️⃣ منع التكرار
        if village and name:
            qs = CommercialActivity.objects.filter(
               village=village,
                name=name,
            )
        if instance:
                qs = qs.exclude(pk=instance.pk)
          
        """
            if qs.exists():
                raise ValidationError(
                    {
                        "non_field_errors": (
                            "يوجد سجل لهذا النشاط التجاري في هذه القرية لنفس السنة."
                        )
                    }
                )
            """
        # 2️⃣ الصلاحيات الجغرافية
        if not is_super_admin(user):
            if is_area_manager(user) or is_data_entry(user):
                if (
                    not village
                    or village.subarea.area != user.area
                    or village.subarea.area.governorate != user.governorate
                ):
                    raise ValidationError(
                        {"village": "لا يمكنك إدارة الأنشطة التجارية خارج منطقتك."}
                    )
            else:
                raise ValidationError(
                    {"permission": "لا تملك صلاحية لإدارة هذه البيانات."}
                )

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["created_by"] = request.user
        return super().create(validated_data)
    
class DemographicDataSerializer(serializers.ModelSerializer):
    """
    بيانات ديموغرافية عن قرية وسنة معيّنة.
    """

    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())
    village_name = serializers.CharField(source="village.name", read_only=True)

    class Meta:
        model = DemographicData
        fields = [
            "id",
            "village",
            "village_name" ,
            "administrative_boundaries",
            "area",
            "population",
            "number_of_families",
            "male_percentage",
            "female_percentage",
            "number_of_martyrs",
            "number_of_injured",
            "number_of_detainees",
            "displaced_percentage",
            "returned_percentage",
            "unemployment_percentage",
            "poverty_percentage",
            "wealth_percentage",
            "government_workers_percentage",
            "private_sector_workers_percentage",
            "elderly_percentage",
            "farmers_percentage",
            "industrial_workers_percentage",
            "traders_percentage",
            "craftsmen_percentage",
            "expatriates_percentage",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at"]

    def validate(self, attrs):
     request = self.context["request"]
     user = request.user
     instance = getattr(self, "instance", None)

     village = attrs.get("village") or (instance.village if instance else None)
     if not village:
        raise ValidationError({"village": "القرية مطلوبة."})

    # -----------------------
    # منع التكرار: سجل واحد فقط لكل قرية
    # -----------------------
     qs = DemographicData.objects.filter(village=village)
     if instance:
         qs = qs.exclude(pk=instance.pk)

     if qs.exists():
        raise ValidationError({
            "non_field_errors": "يوجد سجل ديموغرافي لهذه القرية مسبقًا ولا يمكن إضافة سجل آخر."
        })

    # -----------------------
    # صلاحيات/نطاق المنطقة
    # -----------------------
     if not is_super_admin(user):
        if is_area_manager(user) or is_data_entry(user):
            if (
                village.subarea.area != user.area
                or village.subarea.area.governorate != user.governorate
            ):
                raise ValidationError(
                    {"village": "لا يمكنك إدارة البيانات الديموغرافية خارج منطقتك."}
                )
        else:
            raise ValidationError(
                {"permission": "لا تملك صلاحية لإدارة هذه البيانات."}
            )

     return attrs
    def create(self, validated_data):
        request = self.context["request"]
        validated_data["created_by"] = request.user
        return super().create(validated_data)

class AgriculturalStatusSerializer(serializers.ModelSerializer):
    """
    حالة زراعية لقرية معيّنة (إجمالي المساحات، نسب الريّ، الموارد المائية، المحاصيل...).
    """

    # إدخال القرية بالاسم بدل الـ ID
    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())
    village_name = serializers.CharField(source="village.name", read_only=True)

    class Meta:
        model = AgriculturalStatus
        fields = [
            "id",
            "village",
            "village_name" ,
            "season",
            "total_agricultural_area",
            "irrigated_land_percentage",
            "rainfed_land_percentage",
            "critical_land_percentage",
            "state_owned_land_percentage",
            "water_resources",
            "crops",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        """
        1) منع تكرار (قرية + فصل) حسب الـ UniqueConstraint
        2) التأكد أن المستخدم له صلاحية على هاي القرية (نفس المنطقة)
        """
        request = self.context["request"]
        user = request.user
        instance = getattr(self, "instance", None)

        # لو عم نعمل create → القرية/الفصل من attrs
        # لو update وحقول ناقصة → نكمّل من instance
        village = attrs.get("village") or (instance.village if instance else None)
        season = (
            attrs.get("season")
            if "season" in attrs
            else (instance.season if instance else None)
        )

        # 1️⃣ منع التكرار لنفس (village, season)
        if village:
            qs = AgriculturalStatus.objects.filter(
                village=village,
                season=season,
            )
            if instance:
                qs = qs.exclude(pk=instance.pk)

            if qs.exists():
                raise ValidationError(
                    {
                        "non_field_errors": (
                            "يوجد سجل لحالة زراعية لهذه القرية وهذا الفصل مسبقًا. "
                            "قم بتعديل السجل الموجود بدل إنشاء واحد جديد."
                        )
                    }
                )

            # 2️⃣ صلاحيات حسب الموقع
            if not is_super_admin(user):
                if is_area_manager(user) or is_data_entry(user):
                    if (
                        village.subarea.area != user.area
                        or village.subarea.area.governorate != user.governorate
                    ):
                        raise ValidationError(
                            {
                                "village": "لا يمكنك إدارة البيانات الزراعية لقرى خارج منطقتك الإدارية."
                            }
                        )
                else:
                    raise ValidationError(
                        {"permission": "لا تملك صلاحية لإدارة هذه البيانات."}
                    )

        return attrs
