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
    """
    منطقة:
    - الإرسال:
        name
        governorate  (اسم المحافظة، مو الـ id)
    - الإرجاع:
        id
        name
        governorate      (اسم المحافظة)
        governorate_id   (id المحافظة – للقراءة فقط)
    """
    governorate = serializers.SlugRelatedField(
        slug_field="name",           # نستخدم حقل name كـ slug
        queryset=Governorate.objects.all(),
    )
    governorate_id = serializers.IntegerField(
        source="governorate.id", read_only=True
    )

    class Meta:
        model = Area
        fields = ["id", "name", "governorate", "governorate_id"]


class SubAreaSerializer(serializers.ModelSerializer):
    area = serializers.CharField(required=False)

    class Meta:
        model = SubArea
        fields = ["id", "name", "area"]

    def validate_area(self, value):
        """
        السوبر أدمن فقط يقدر يحدد المنطقة بالاسم
        """
        user = self.context["request"].user

        if not is_super_admin(user):
            raise serializers.ValidationError("لا يمكنك تحديد المنطقة يدويًا")

        try:
            return Area.objects.get(name__iexact=value)
        except Area.DoesNotExist:
            raise serializers.ValidationError("المنطقة غير موجودة")

    def create(self, validated_data):
        user = self.context["request"].user

        if is_super_admin(user):
            # السوبر أدمن يحدد المنطقة
            area = validated_data.pop("area")
        else:
            # مدير المنطقة / مدخل البيانات
            if not user.area:
                raise serializers.ValidationError("حسابك غير مرتبط بمنطقة")
            area = user.area

        return SubArea.objects.create(area=area, **validated_data)

class VillageSerializer(serializers.ModelSerializer):
    subarea = serializers.CharField()

    class Meta:
        model = Village
        fields = [
            "id",
            "name",
            "type",
            "subarea",
            "parent_name",
        ]

    # -----------------------
    # تحويل اسم الناحية إلى object
    # -----------------------
    def validate_subarea(self, value):
        user = self.context["request"].user

        try:
            subarea = SubArea.objects.select_related("area").get(
                name__iexact=value
            )
        except SubArea.DoesNotExist:
            raise serializers.ValidationError("الناحية غير موجودة")

        # سوبر أدمن: مسموح كل شي
        if is_super_admin(user):
            return subarea

        # مدير منطقة / مدخل بيانات
        if not user.area:
            raise serializers.ValidationError("حسابك غير مرتبط بمنطقة")

        if subarea.area_id != user.area_id:
            raise serializers.ValidationError(
                "لا يمكنك ربط القرية بناحية خارج منطقتك"
            )

        return subarea

    # -----------------------
    # CREATE
    # -----------------------
    def create(self, validated_data):
        return Village.objects.create(**validated_data)

    # -----------------------
    # UPDATE
    # -----------------------
    def update(self, instance, validated_data):
        user = self.context["request"].user

        # إذا حاول يغير الناحية
        new_subarea = validated_data.get("subarea")

        if new_subarea:
            # سوبر أدمن: حر
            if not is_super_admin(user):
                if not user.area:
                    raise serializers.ValidationError(
                        "حسابك غير مرتبط بمنطقة"
                    )

                if new_subarea.area_id != user.area_id:
                    raise serializers.ValidationError(
                        "لا يمكنك نقل القرية إلى ناحية خارج منطقتك"
                    )

        return super().update(instance, validated_data)
    

class PersonSerializer(serializers.ModelSerializer):
    # ====== READ-ONLY DISPLAY FIELDS ======
    village_name = serializers.CharField(source="village.name", read_only=True)
    subarea_name = serializers.CharField(
        source="village.subarea.name", read_only=True
    )
    area_name = serializers.CharField(
        source="village.subarea.area.name", read_only=True
    )
    governorate_name = serializers.CharField(
        source="village.subarea.area.governorate.name", read_only=True
    )

    sect_name = serializers.CharField(source="sect.name", read_only=True)
    ethnicity_name = serializers.CharField(source="ethnicity.name", read_only=True)
    tribe_name = serializers.CharField(source="tribe.name", read_only=True)

    # ====== INPUT FIELDS (NAMES INSTEAD OF IDS) ======
    village = serializers.SlugRelatedField(
        queryset=Village.objects.all(),
        slug_field="name"
    )

    sect = serializers.SlugRelatedField(
        queryset=Sect.objects.all(),
        slug_field="name",
        required=False,
        allow_null=True
    )

    ethnicity = serializers.SlugRelatedField(
        queryset=Ethnicity.objects.all(),
        slug_field="name",
        required=False,
        allow_null=True
    )

    tribe = serializers.SlugRelatedField(
        queryset=Tribe.objects.all(),
        slug_field="name",
        required=False,
        allow_null=True
    )

    class Meta:
        model = Person
        fields = [
            "id",
            "name",

            # input
            "village",
            "sect",
            "ethnicity",
            "tribe",

            # output (display)
            "village_name",
            "subarea_name",
            "area_name",
            "governorate_name",
            "sect_name",
            "ethnicity_name",
            "tribe_name",

            # person info
            "phone",
            "address",
            "educational_qualifications",
            "work",
            "social_interests",
            "community_influence",
            "system_affiliation",
            "new_leadership",

            # system fields
            "locked",
            "created_by",
            "created_at",
        ]
        read_only_fields = ["locked", "created_by", "created_at"]

    # ====== LOCATION VALIDATION ======
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
                    {"village": "لا يمكنك إضافة أو تعديل أشخاص خارج منطقتك الإدارية."}
                )

        return attrs

    # ====== AUTO CREATED_BY ======
    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


# locations/serializers.py

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
    # حقول للعرض فقط (اسم القرية واسم الطائفة)
    village = serializers.SlugRelatedField(
        queryset=Village.objects.all(),
        slug_field="name"
    )
    sect = serializers.SlugRelatedField(
        queryset=Sect.objects.all(),
        slug_field="name"
    )

    class Meta:
        model = VillageSect
        fields = [
            "id",
            "village",
            "sect",
            "family_count",
            "individual_count",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at"]

    def validate(self, attrs):
        """
        منطق الصلاحيات حسب الموقع:
        - super_admin: حر، ما منقيّده بالموقع
        - area_manager / data_entry: لازم القرية تكون ضمن محافظته + منطقته
        """
        request = self.context["request"]
        user = request.user

        # القرية اللي عم نشتغل عليها
        village = attrs.get("village") or getattr(self.instance, "village", None)
        if not village:
            return attrs  # لو ما في قرية بالداتا، منرجّع attrs كما هي

        # الأمن الأساسي: حر
        if is_super_admin(user):
            return attrs

        # مدير منطقة أو مدخل بيانات: مقيّد بمنطقته
        if is_area_manager(user) or is_data_entry(user):
            if (
                village.subarea.area != user.area
                or village.subarea.area.governorate != user.governorate
            ):
                raise serializers.ValidationError(
                    {"village": "لا يمكنك إدارة بيانات الطوائف في قرية خارج منطقتك الإدارية."}
                )

        return attrs

    def create(self, validated_data):
        """
        نضيف created_by أوتوماتيكياً من المستخدم الحالي.
        """
        request = self.context["request"]
        validated_data["created_by"] = request.user
        return super().create(validated_data)


class VillageSectKeyFigureSerializer(serializers.ModelSerializer):
    """
    هذا الـ Serializer مسؤول عن:
    ربط شخص معيّن كشخصية مؤثرة (Key Figure)
    ضمن طائفة معيّنة
    داخل قرية معيّنة
    """

    # ===============================
    # حقول الإدخال (WRITE ONLY)
    # ===============================

    # اسم القرية يُرسل كنص (مثلاً: "الغنطو")
    # ويتم تحويله داخليًا إلى Village object
    village = serializers.SlugRelatedField(
        queryset=Village.objects.all(),
        slug_field="name",
        write_only=True,
        help_text="اسم القرية، مثلاً: الغنطو"
    )

    # اسم الطائفة يُرسل كنص (مثلاً: "سني")
    # ويتم تحويله داخليًا إلى Sect object
    sect = serializers.SlugRelatedField(
        queryset=Sect.objects.all(),
        slug_field="name",
        write_only=True,
        help_text="اسم الطائفة، مثلاً: سني"
    )

    # اسم الشخص (يتم ربطه مباشرة بجدول Person)
    person = serializers.SlugRelatedField(
        queryset=Person.objects.all(),
        slug_field="name",
        help_text="اسم الشخص (الشخصية المؤثرة)"
    )

    # ===============================
    # حقول العرض (READ ONLY)
    # ===============================

    # اسم القرية للعرض (مستخرج من العلاقة VillageSect → Village)
    village_name = serializers.CharField(
        source="village_sect.village.name",
        read_only=True
    )

    # اسم الطائفة للعرض
    sect_name = serializers.CharField(
        source="village_sect.sect.name",
        read_only=True
    )

    # اسم الشخص للعرض
    person_name = serializers.CharField(
        source="person.name",
        read_only=True
    )

    # اسم المستخدم الذي أضاف هذه الشخصية
    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True
    )

    # ===============================
    # إعدادات عامة
    # ===============================

    class Meta:
        model = VillageSectKeyFigure
        fields = [
            "id",

            # للإدخال
            "village",
            "sect",
            "person",

            # للعرض
            "village_name",
            "sect_name",
            "person_name",
            "created_by_username",

            "created_at",
            "updated_at",
        ]

        # هذه الحقول لا يمكن تعديلها من المستخدم
        read_only_fields = [
            "created_by_username",
            "created_at",
            "updated_at"
        ]

    # ===============================
    # التحقق المنطقي (VALIDATION)
    # ===============================

    def validate(self, attrs):
        """
        منطق التحقق:
        1️⃣ التأكد أن (القرية + الطائفة) موجودة مسبقًا في VillageSect
        2️⃣ التأكد أن المستخدم لديه صلاحية إدارية على هذه القرية
        3️⃣ التأكد أن الشخص تابع لنفس القرية (اختياري لكن منطقي)
        """

        request = self.context["request"]
        user = request.user

        village = attrs.get("village")
        sect = attrs.get("sect")
        person = attrs.get("person") or getattr(self.instance, "person", None)

        # 1️⃣ التأكد أن VillageSect موجود
        # (لا يمكن إضافة شخصية لطائفة غير مسجّلة إحصائيًا في القرية)
        try:
            village_sect = VillageSect.objects.select_related(
                "village",
                "village__subarea",
                "village__subarea__area",
                "village__subarea__area__governorate",
                "sect",
            ).get(village=village, sect=sect)
        except ObjectDoesNotExist:
            raise serializers.ValidationError(
                {
                    "non_field_errors":
                    "لا توجد بيانات إحصائية لهذه الطائفة في هذه القرية (VillageSect غير موجود)."
                }
            )

        # 2️⃣ التحقق من الصلاحيات الجغرافية
        # السوبر أدمن غير مقيّد
        if not is_super_admin(user):
            # مدير منطقة أو مدخل بيانات
            if is_area_manager(user) or is_data_entry(user):
                # يجب أن تكون القرية ضمن نفس منطقة المستخدم
                if (
                    village_sect.village.subarea.area != user.area
                    or village_sect.village.subarea.area.governorate != user.governorate
                ):
                    raise serializers.ValidationError(
                        {
                            "village":
                            "لا يمكنك إضافة شخصيات رئيسية خارج نطاق منطقتك الإدارية."
                        }
                    )
            else:
                raise serializers.ValidationError(
                    {"permission": "لا تملك صلاحية لإضافة شخصيات رئيسية."}
                )

        # 3️⃣ التأكد أن الشخص من نفس القرية
        if person and person.village and person.village != village_sect.village:
            raise serializers.ValidationError(
                {
                    "person":
                    "هذا الشخص مسجّل في قرية مختلفة عن القرية المحددة."
                }
            )

        # نمرّر VillageSect مؤقتًا لاستخدامه في create/update
        attrs["__village_sect_instance"] = village_sect

        return attrs

    # ===============================
    # CREATE
    # ===============================

    def create(self, validated_data):
        """
        عند الإنشاء:
        - نحذف village و sect (لأنهما ليسا حقولًا في الموديل)
        - نربط VillageSect الصحيح
        - نضيف created_by تلقائيًا
        """

        request = self.context["request"]
        user = request.user

        # هذه القيم استخدمت فقط للتحقق
        validated_data.pop("village", None)
        validated_data.pop("sect", None)

        village_sect = validated_data.pop("__village_sect_instance")

        validated_data["village_sect"] = village_sect
        validated_data["created_by"] = user

        return super().create(validated_data)

    # ===============================
    # UPDATE
    # ===============================

    def update(self, instance, validated_data):
        """
        عند التعديل:
        - إذا تغيّرت القرية أو الطائفة
          نعيد حساب VillageSect
        """

        village = validated_data.pop("village", None)
        sect = validated_data.pop("sect", None)

        if village and sect:
            village_sect = validated_data.pop("__village_sect_instance", None)
            if village_sect:
                validated_data["village_sect"] = village_sect

        return super().update(instance, validated_data)
    
class VillageEthnicitySerializer(serializers.ModelSerializer):
    """
    توزيع عِرقي داخل قرية (بدون بعد زمني).
    """

    # إدخال بالاسم بدل ID
    village = serializers.SlugRelatedField(
        queryset=Village.objects.all(),
        slug_field="name",
        help_text="اسم القرية"
    )
    ethnicity = serializers.SlugRelatedField(
        queryset=Ethnicity.objects.all(),
        slug_field="name",
        help_text="اسم العِرق"
    )

    class Meta:
        model = VillageEthnicity
        fields = [
            "id",
            "village",
            "ethnicity",
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

    # إدخال بالاسم بدل ID
    village = serializers.SlugRelatedField(
        queryset=Village.objects.all(),
        slug_field="name",
        help_text="اسم القرية"
    )
    tribe = serializers.SlugRelatedField(
        queryset=Tribe.objects.all(),
        slug_field="name",
        help_text="اسم القبيلة"
    )

    class Meta:
        model = VillageTribe
        fields = [
            "id",
            "village",
            "tribe",
            "individual_count",
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
    village = serializers.SlugRelatedField(
        queryset=Village.objects.all(),
        slug_field="name",
        help_text="اسم القرية"
    )

    person = serializers.SlugRelatedField(
        queryset=Person.objects.all(),
        slug_field="name",
        required=False,
        allow_null=True,
        help_text="اسم الشخص المرتبط بالمنشأة (صاحب/مستثمر...)"
    )

    class Meta:
        model = IndustrialFacility
        fields = [
            "id",
            "village",
            "year",
            "name",
            "type",
            "person",
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
        year = attrs.get("year") or (instance.year if instance else None)
        name = attrs.get("name") or (instance.name if instance else None)
        person = attrs.get("person") or (instance.person if instance else None)

        # 1️⃣ منع تكرار (قرية + سنة + اسم)
        if village and year and name:
            qs = IndustrialFacility.objects.filter(
                village=village,
                year=year,
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

    # إدخال/عرض بالاسم بدل ID
    village = serializers.SlugRelatedField(
        queryset=Village.objects.all(),
        slug_field="name",
        help_text="اسم القرية (مثلاً: الغنطو)"
    )

    class Meta:
        model = Livestock
        fields = [
            "id",
            "village",
            "year",

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
        year = attrs.get("year") or (instance.year if instance else None)

        # 1️⃣ منع التكرار
        if village and year:
            qs = Livestock.objects.filter(
                village=village,
                year=year,
            )
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

    village = serializers.SlugRelatedField(
        queryset=Village.objects.all(),
        slug_field="name",
        help_text="اسم القرية"
    )

    class Meta:
        model = GovernmentDepartment
        fields = [
            "id",
            "village",
            "year",
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

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user
        instance = getattr(self, "instance", None)

        village = attrs.get("village") or (instance.village if instance else None)
        year = attrs.get("year") or (instance.year if instance else None)
        department_name = (
            attrs.get("department_name")
            or (instance.department_name if instance else None)
        )

        # 1️⃣ منع التكرار
        if village and year and department_name:
            qs = GovernmentDepartment.objects.filter(
                village=village,
                year=year,
                department_name=department_name,
            )
            if instance:
                qs = qs.exclude(pk=instance.pk)

            if qs.exists():
                raise ValidationError(
                    {
                        "non_field_errors": (
                            "يوجد سجل لهذه الدائرة في هذه القرية ونفس السنة."
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
    village = serializers.SlugRelatedField(
        queryset=Village.objects.all(),
        slug_field="name",
        help_text="اسم القرية (مثلاً: الغنطو)"
    )

    # إدخال المالك بالاسم (يرتبط بحقل person_id_owner_name في الموديل)
    owner_person = serializers.SlugRelatedField(
        source="person_id_owner_name",
        queryset=Person.objects.all(),
        slug_field="name",
        required=False,
        allow_null=True,
        help_text="اسم المالك (إن وجد)"
    )

    # إدخال المستثمر بالاسم (يرتبط بحقل person_id_investor_name)
    investor_person = serializers.SlugRelatedField(
        source="person_id_investor_name",
        queryset=Person.objects.all(),
        slug_field="name",
        required=False,
        allow_null=True,
        help_text="اسم المستثمر (إن وجد)"
    )

    class Meta:
        model = NaturalAsset
        fields = [
            "id",
            "village",
            "year",

            "type",
            "name",
            "classification",
            "important_level",
            "ownership",

            "owner_person",
            "supervising_authority",
            "investor_person",

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
        year = attrs.get("year") or (instance.year if instance else None)
        name = attrs.get("name") or (instance.name if instance else None)

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
        if village and year and name:
            qs = NaturalAsset.objects.filter(
                village=village,
                year=year,
                name=name,
            )
            if instance:
                qs = qs.exclude(pk=instance.pk)

            if qs.exists():
                raise ValidationError(
                    {
                        "non_field_errors": (
                            "يوجد مورد طبيعي بهذا الاسم في هذه القرية لنفس السنة."
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

    village = serializers.SlugRelatedField(
        queryset=Village.objects.all(),
        slug_field="name",
        help_text="اسم القرية (مثلاً: الغنطو)"
    )

    class Meta:
        model = IndustrialZone
        fields = [
            "id",
            "village",
            "year",
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
        year = attrs.get("year") or (instance.year if instance else None)

        # 1️⃣ منع التكرار
        if village and year:
            qs = IndustrialZone.objects.filter(
                village=village,
                year=year,
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
    
    village = serializers.SlugRelatedField(
        queryset=Village.objects.all(),
        slug_field="name",
        help_text="اسم القرية"
    )

    class Meta:
        model = ArchaeologicalSite
        fields = [
            "id",
            "village",
            "year",
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

        village = attrs.get("village") or (instance.village if instance else None)
        year = attrs.get("year") or (instance.year if instance else None)
        name = attrs.get("name") or (instance.name if instance else None)

        # 1️⃣ منع التكرار
        if village and year and name:
            qs = ArchaeologicalSite.objects.filter(
                village=village,
                year=year,
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

    village = serializers.SlugRelatedField(
        queryset=Village.objects.all(),
        slug_field="name",
        help_text="اسم القرية (مثلاً: الغنطو)"
    )

    class Meta:
        model = TourismFacility
        fields = [
            "id",
            "village",
            "year",
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
        year = attrs.get("year") or (instance.year if instance else None)
        type = attrs.get("type") or (instance.type if instance else None)

        # 1️⃣ منع التكرار
        if village and year and type:
            qs = TourismFacility.objects.filter(
                village=village,
                year=year,
                type=type,
            )
            if instance:
                qs = qs.exclude(pk=instance.pk)

            if qs.exists():
                raise ValidationError(
                    {
                        "non_field_errors": (
                            "يوجد سجل لهذه المنشأة السياحية في هذه القرية لنفس السنة."
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

    village = serializers.SlugRelatedField(
        queryset=Village.objects.all(),
        slug_field="name",
        help_text="اسم القرية"
    )

    class Meta:
        model = CommercialActivity
        fields = [
            "id",
            "village",
            "year",
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
        year = attrs.get("year") or (instance.year if instance else None)
        name = attrs.get("name") or (instance.name if instance else None)

        # 1️⃣ منع التكرار
        if village and year and name:
            qs = CommercialActivity.objects.filter(
                village=village,
                year=year,
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

    village = serializers.SlugRelatedField(
        queryset=Village.objects.all(),
        slug_field="name",
        help_text="اسم القرية (مثلاً: الغنطو)"
    )

    class Meta:
        model = DemographicData
        fields = [
            "id",
            "village",
            "year",
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
        year = attrs.get("year") or (instance.year if instance else None)

        # 1️⃣ منع التكرار
        if village and year:
            qs = DemographicData.objects.filter(
                village=village,
                year=year,
            )
            if instance:
                qs = qs.exclude(pk=instance.pk)

            if qs.exists():
                raise ValidationError(
                    {
                        "non_field_errors": (
                            "يوجد سجل ديموغرافي لهذه القرية لنفس السنة."
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