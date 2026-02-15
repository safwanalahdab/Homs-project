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
    governorate_name = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Area
        fields = ["id", "name", "governorate", "governorate_name"]
        extra_kwargs = {
            "governorate": {"required": False},  # نخليها اختيارية لأن ممكن يجي الاسم بدلها
        }

    def validate(self, attrs):
        gov_id = attrs.get("governorate", None)
        gov_name = attrs.get("governorate_name", None)

        # لازم واحد منهم فقط
        if not gov_id and not gov_name:
            raise serializers.ValidationError(
                {"governorate": "Provide either governorate (id) or governorate_name."}
            )

        if gov_id and gov_name:
            raise serializers.ValidationError(
                {"governorate": "Use only one of governorate (id) or governorate_name."}
            )

        # إذا بعت اسم، جيب الـ Governorate من الداتابيز وحطّه مكان governorate
        if gov_name:
            gov = Governorate.objects.filter(name__iexact=gov_name).first()
            if not gov:
                raise serializers.ValidationError({"governorate_name": "Governorate not found."})
            attrs["governorate"] = gov

        return attrs


class SubAreaSerializer(serializers.ModelSerializer):
    # نقبل ID بالـ area (PrimaryKey) أو name بالـ area_name
    area = serializers.IntegerField(required=False, write_only=True)
    area_name = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = SubArea
        fields = ["id", "name", "area", "area_name"]

    def validate(self, attrs):
        user = self.context["request"].user

        area_id = attrs.get("area")
        area_name = attrs.get("area_name")

        # السوبر أدمن فقط يقدر يحدد المنطقة يدويًا (ID أو Name)
        if (area_id is not None) or (area_name is not None):
            if not is_super_admin(user):
                raise serializers.ValidationError("لا يمكنك تحديد المنطقة يدويًا")

            # لازم واحد فقط (ID أو Name)
            if area_id is not None and area_name is not None:
                raise serializers.ValidationError("استخدم area (id) أو area_name (name) فقط")

            # حوّل إلى Area object
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

        # إذا سوبر أدمن: يستخدم المنطقة المحددة
        if is_super_admin(user):
            area_obj = validated_data.pop("area_obj", None)
            if not area_obj:
                raise serializers.ValidationError("يجب تحديد area أو area_name للسوبر أدمن")
        else:
            # مدير منطقة/مدخل بيانات: المنطقة من user.area
            if not user.area:
                raise serializers.ValidationError("حسابك غير مرتبط بمنطقة")
            area_obj = user.area

        # شيل المفاتيح الكتابية حتى ما تنحفظ كمجالات
        validated_data.pop("area", None)
        validated_data.pop("area_name", None)

        return SubArea.objects.create(area=area_obj, **validated_data)


class VillageSerializer(serializers.ModelSerializer):
    # input
    subarea = serializers.IntegerField(required=False, write_only=True)
    subarea_name = serializers.CharField(required=False, write_only=True)

    # output
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
            raise serializers.ValidationError("يجب إرسال subarea (id) أو subarea_name (name)")

        # ممنوع الاثنين سوا
        if subarea_id is not None and subarea_name is not None:
          raise serializers.ValidationError("استخدم subarea (id) أو subarea_name (name) فقط")

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
    # ====== FK FIELDS AS IDS ======
    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())
    sect = serializers.PrimaryKeyRelatedField(queryset=Sect.objects.all(), required=False, allow_null=True)
    ethnicity = serializers.PrimaryKeyRelatedField(queryset=Ethnicity.objects.all(), required=False, allow_null=True)
    tribe = serializers.PrimaryKeyRelatedField(queryset=Tribe.objects.all(), required=False, allow_null=True)

    # ====== READ-ONLY DISPLAY FIELDS (اختياري للعرض) ======
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
    # FK as IDs
    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())
    sect = serializers.PrimaryKeyRelatedField(queryset=Sect.objects.all())

    # optional display (إذا بدك)
    village_name = serializers.CharField(source="village.name", read_only=True)
    sect_name = serializers.CharField(source="sect.name", read_only=True)

    class Meta:
        model = VillageSect
        fields = [
            "id",
            "village",
            "sect",
            "family_count",
            "individual_count",
            "village_name",
            "sect_name",
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

    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())
    ethnicity = serializers.PrimaryKeyRelatedField(queryset=Ethnicity.objects.all())

    village_name = serializers.CharField(source="village.name", read_only=True)
    ethnicity_name = serializers.CharField(source="ethnicity.name", read_only=True)

    class Meta:
        model = VillageEthnicity
        fields = [
            "id",
            "village",
            "village_name",
            "ethnicity",
            "ethnicity_name",
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
    tribe_name = serializers.CharField(source="tribe.name", read_only=True)

    
    class Meta:
        model = VillageTribe
        fields = [
            "id",
            "village",
            "village_name",
            "tribe",
            "tribe_name",
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
            "year",
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

    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())
    village_name = serializers.CharField(source="village.name", read_only=True)

    class Meta:
        model = Livestock
        fields = [
            "id",
            "village",
            "village_name" ,
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

    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())
    village_name = serializers.CharField(source="village.name", read_only=True)

    class Meta:
        model = GovernmentDepartment
        fields = [
            "id",
            "village",
            "village_name",
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

            "year",

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

    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())
    village_name = serializers.CharField(source="village.name", read_only=True)

    class Meta:
        model = IndustrialZone
        fields = [
            "id",
            "village",
            "village_name" ,
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
    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())
    village_name = serializers.CharField(source="village.name", read_only=True)

    class Meta:
        model = ArchaeologicalSite
        fields = [
            "id",
            "village",
            "village_name",
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

    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())
    village_name = serializers.CharField(source="village.name", read_only=True)

    class Meta:
        model = TourismFacility
        fields = [
            "id",
            "village",
            "village_name" ,
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

    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())
    village_name = serializers.CharField(source="village.name", read_only=True)

    class Meta:
        model = CommercialActivity
        fields = [
            "id",
            "village" ,
            "village_name" ,
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

    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())
    village_name = serializers.CharField(source="village.name", read_only=True)

    class Meta:
        model = DemographicData
        fields = [
            "id",
            "village",
            "village_name" ,
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
    
class AgriculturalStatusSerializer(serializers.ModelSerializer):
    """
    بيانات الحالة الزراعية لقرية ضمن سنة (سنوي أو موسمي).
    """

    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all())
    village_name = serializers.CharField(source="village.name", read_only=True)

    subarea_id = serializers.IntegerField(source="village.subarea_id", read_only=True)
    subarea_name = serializers.CharField(source="village.subarea.name", read_only=True)

    area_id = serializers.IntegerField(source="village.subarea.area_id", read_only=True)
    area_name = serializers.CharField(source="village.subarea.area.name", read_only=True)

    governorate_id = serializers.IntegerField(
        source="village.subarea.area.governorate_id", read_only=True
    )
    governorate_name = serializers.CharField(
        source="village.subarea.area.governorate.name", read_only=True
    )

    class Meta:
        model = AgriculturalStatus
        fields = [
            "id",
            "village",
            "village_name",
            "subarea_id",
            "subarea_name",
            "area_id",
            "area_name",
            "governorate_id",
            "governorate_name",
            "year",
            "season",
            "total_agricultural_area",
            "irrigated_land_percentage",
            "rainfed_land_percentage",
            "critical_land_percentage",
            "state_owned_land_percentage",
            "water_resources",
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
        season = attrs.get("season") if "season" in attrs else (instance.season if instance else None)

        # 1️⃣ منع التكرار (قرية + سنة + موسم)
        if village and year is not None:
            qs = AgriculturalStatus.objects.filter(
                village=village,
                year=year,
                season=season,  # ممكن تكون NULL (سنوي)
            )
            if instance:
                qs = qs.exclude(pk=instance.pk)

            """
            if qs.exists():
                raise ValidationError(
                    {"non_field_errors": ("يوجد سجل حالة زراعية لهذه القرية في نفس السنة ونفس الموسم.")}
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
                    raise ValidationError({"village": "لا يمكنك إدارة البيانات الزراعية خارج منطقتك."})
            else:
                raise ValidationError({"permission": "لا تملك صلاحية لإدارة هذه البيانات."})

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["created_by"] = request.user
        return super().create(validated_data)


class AgriculturalCropSerializer(serializers.ModelSerializer):
    """
    بيانات المحاصيل ضمن حالة زراعية معيّنة (بدون جدول Crop مستقل).
    """

    agricultural_status = serializers.PrimaryKeyRelatedField(
        queryset=AgriculturalStatus.objects.all()
    )

    # معلومات مفيدة للفرونت من الـ AgriculturalStatus
    village = serializers.IntegerField(source="agricultural_status.village_id", read_only=True)
    village_name = serializers.CharField(source="agricultural_status.village.name", read_only=True)
    year = serializers.IntegerField(source="agricultural_status.year", read_only=True)
    season = serializers.CharField(source="agricultural_status.season", read_only=True)

    class Meta:
        model = AgriculturalCrop
        fields = [
            "id",
            "agricultural_status",
            "village",
            "village_name",
            "year",
            "season",
            "crop_name",
            "area",
            "is_strategic",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user
        instance = getattr(self, "instance", None)

        agricultural_status = attrs.get("agricultural_status") or (
            instance.agricultural_status if instance else None
        )
        crop_name = attrs.get("crop_name") or (instance.crop_name if instance else None)

        # 1️⃣ منع التكرار (نفس الحالة الزراعية + نفس اسم المحصول)
        if agricultural_status and crop_name:
            qs = AgriculturalCrop.objects.filter(
                agricultural_status=agricultural_status,
                crop_name=crop_name,
            )
            if instance:
                qs = qs.exclude(pk=instance.pk)

            """
            if qs.exists():
                raise ValidationError(
                    {"non_field_errors": ("يوجد هذا المحصول مسبقاً ضمن نفس الحالة الزراعية.")}
                )
            """

        # 2️⃣ الصلاحيات الجغرافية (من خلال قرية الحالة الزراعية)
        if not is_super_admin(user):
            if is_area_manager(user) or is_data_entry(user):
                village = getattr(agricultural_status, "village", None)
                if (
                    not village
                    or village.subarea.area != user.area
                    or village.subarea.area.governorate != user.governorate
                ):
                    raise ValidationError({"agricultural_status": "لا يمكنك إدارة المحاصيل خارج منطقتك."})
            else:
                raise ValidationError({"permission": "لا تملك صلاحية لإدارة هذه البيانات."})

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["created_by"] = request.user
        return super().create(validated_data)