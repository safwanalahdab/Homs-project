from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password

from django.db.models import Q
from rest_framework import serializers

from .models import *
from .utils import *

User = get_user_model()

class LoginSerizlizer( serializers.Serializer ) : 
    """
    Login serializer:
    - Accepts a single identifier (username or email) + password.
    - Validates that both fields are provided.
    - Finds the user by username/email (case-insensitive).
    - Authenticates using Django's authenticate().
    - Blocks login if the account status is deactive.
    - Returns the authenticated user in validated_data["user"].
    """
    identifier = serializers.CharField() 
    password = serializers.CharField( write_only = True ) 

    def validate(self, attrs):
       identifier = ( attrs.get('identifier') or '' ).strip() 
       password = attrs.get('password') or '' 

       if not identifier or not password : 
           raise serializers.ValidationError({"error":"الرجاء ادخال الايميل وكلمة المرور"})

       user = User.objects.filter(
           Q( username__iexact = identifier) | Q( email__iexact = identifier )
        ).first()

       if not user : 
           raise serializers.ValidationError({"error" : "الايميل او المستخدم غير موجود" })
         
       auth_user = authenticate( username = user.username, password = password) 

       if not auth_user : 
           raise serializers.ValidationError({"error":"اسم المستخدم او كلمة المرور غير صحيحة"})
       
       if hasattr( auth_user , 'status') and auth_user.status == "deactive" :
           raise serializers.ValidationError({"error" : "هذا الحساب غير مفعل"}) 

       attrs['user'] = auth_user 
       return attrs 


class ChangePasswordSerializer( serializers.Serializer ) : 
    """
    Change Password serializer:
    - Requires old_password, new_password, and confirm_password.
    - Uses request.user from serializer context to verify old_password.
    - Ensures new_password matches confirm_password.
    - Validates password strength using Django's validate_password().
    - Returns validated data for use in ChangePasswordView.
    """
    old_password = serializers.CharField( write_only = True ) 
    new_password = serializers.CharField( write_only = True ) 
    confirm_password = serializers.CharField( write_only = True ) 
    
    def validate(self, attrs):
        user = self.context['request'].user
        old_password = attrs.get('old_password')
        new_password = attrs.get('new_password') 
        confirm_password = attrs.get("confirm_password") 

        if not user.check_password(old_password) : 
            raise serializers.ValidationError({"error" : "كلمة المررر القدية غير صحيحة"}) 
        
        if new_password != confirm_password:
            raise serializers.ValidationError({
                "confirm_password": "كلمتا المرور غير متطابقتين"
            })
        
        validate_password(new_password, user=user) 
        return attrs 
    

class ProfileSerializer(serializers.ModelSerializer):
    """
    Profile serializer:
    - Exposes user profile fields for viewing and updating.
    - Allows editing only basic personal info (first_name, last_name, phone, gender, birth_date).
    - Keeps account identity, role/status, location assignments, and timestamps read-only.
    """
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            'first_name',
            'last_name',
            "email",
            "phone",
            "gender",
            "birth_date",
            "governorate",
            "area",
            "subarea",
            "status",
            "role",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            'username' ,
            "email",
            "status",
            "role",
            "governorate",
            "area",
            "subarea",
            "created_at",
            "updated_at",
        ]


class AdminUserListSerializer(serializers.ModelSerializer):

   role = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all())
   role_name = serializers.CharField(source="role.name", read_only=True)

   governorate = serializers.PrimaryKeyRelatedField(queryset=Governorate.objects.all(), required=False, allow_null=True)
   governorate_name = serializers.CharField(source="governorate.name", read_only=True)

   area = serializers.PrimaryKeyRelatedField(queryset=Area.objects.all(), required=False, allow_null=True)
   area_name = serializers.CharField(source="area.name", read_only=True)

   class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "phone",
            "status",

            # FK ids
            "role",
            "role_name",
            "governorate",
            "governorate_name" ,
            "area",
            "area_name" ,

            # display names
            "role_name",
            "governorate_name",
            "area_name",

            "created_at",
            "updated_at",
        ]

class AdminUserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)
    role = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all())
    role_name = serializers.CharField(source="role.name", read_only=True)

    governorate = serializers.PrimaryKeyRelatedField(queryset=Governorate.objects.all(), required=False, allow_null=True)
    governorate_name = serializers.CharField(source="governorate.name", read_only=True)

    area = serializers.PrimaryKeyRelatedField(queryset=Area.objects.all(), required=False, allow_null=True)
    area_name = serializers.CharField(source="area.name", read_only=True)
    
    class Meta:
        model = User
        fields = [
            "email",
            "username",
            "first_name" ,
            "last_name" ,
            "phone",
            "gender",
            "birth_date",
            "role",
            "role_name" ,
            "status",
            "governorate",
            "governorate_name" ,
            "area",
            "area_name" ,
            "password",
            "confirm_password",
        ]

    def validate(self, attrs):
        request = self.context["request"]
        creator = request.user

        pw = attrs.get("password")
        cpw = attrs.get("confirm_password")
        if pw != cpw:
            raise serializers.ValidationError(
                {"confirm_password": "كلمتا المرور غير متطابقتين"}
            )

        validate_password(pw)

        # منطق الأدوار:
        # - super_admin: يمكنه إنشاء area_manager & data_entry
        # - area_manager: يمكنه إنشاء data_entry فقط وفي نفس منطقته

        target_role = attrs.get("role")

        # نفترض role.name موجودة
        target_role_name = (getattr(target_role, "name", "") or "").lower()

        from .utils import is_super_admin, is_area_manager

        if is_super_admin(creator):
            # super_admin حر: يسمح له بكل الأدوار اللي انت تعريفها
            if target_role_name not in ("area_manager", "data_entry"):
                raise serializers.ValidationError(
                    {"role": "الأمن الأساسي يمكنه إنشاء مدير منطقة أو مدخل بيانات فقط"}
                )

        elif is_area_manager(creator):
            # مدير المنطقة مسموح له فقط مدخل بيانات
            if target_role_name != "data_entry":
                raise serializers.ValidationError(
                    {"role": "مدير المنطقة يمكنه إنشاء مدخل بيانات فقط"}
                )

            # ويجب أن تكون نفس المنطقة تبعه
            if (
                attrs.get("governorate") != creator.governorate
                or attrs.get("area") != creator.area

            ):
                raise serializers.ValidationError(
                    {"location": "مدير المنطقة يمكنه إنشاء مستخدمين ضمن منطقته فقط"}
                )
        else:
            raise serializers.ValidationError(
                {"permission": "ليس لديك صلاحية لإنشاء مستخدمين"}
            )

        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data.pop("confirm_password", None)

        request = self.context["request"]
        creator = request.user

        # إن حابب تضيف created_by:
        # validated_
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

class AdminUserUpdateSerializer(serializers.ModelSerializer):
    role = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Role.objects.all(),
    )
    governorate = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Governorate.objects.all(),
    )
    area = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Area.objects.all(),
    )
    class Meta:
        model = User
        fields = [
            "username",
            "first_name" ,
            "last_name" ,
            "phone",
            "gender",
            "birth_date",
            "role",
            "status",
            "governorate",
            "area",
        ]

    def validate(self, attrs):
        request = self.context["request"]
        editor = request.user
        instance: "User" = self.instance

        target_role = attrs.get("role", instance.role)
        target_role_name = (getattr(target_role, "name", "") or "").lower()

        # super_admin: حر، بس ممكن تحط قواعد لو حابب (مثلاً ما ينزل مستخدم super_admin آخر إلا بشروط)
        if is_super_admin(editor):
            # مثال: نمنع تعديل دور super_admin لغيره إلا اذا كان هو نفسه
            # (اختياري، حسب شدة الأمان اللي بدك ياها)
            return attrs

        # area_manager:
        if is_area_manager(editor):
            # لا يسمح له بتعديل أدوار الأمن الأساسي أو مدراء مناطق آخرين
            instance_role_name = (getattr(instance.role, "name", "") or "").lower()

            # لا يمكنه تعديل super_admin أبداً
            if instance_role_name == "super_admin":
                raise serializers.ValidationError(
                    {"permission": "لا يمكنك تعديل حساب الأمن الأساسي"}
                )

            # لا يمكنه يرفع/يغيّر دور المستخدم إلى مدير منطقة أو سوبر أدمن
            if target_role_name in ("super_admin", "area_manager"):
                raise serializers.ValidationError(
                    {"role": "لا يمكنك ترقية المستخدم إلى مدير منطقة أو أمن أساسي"}
                )

            # يجب أن يكون المستخدم ضمن نفس منطقته
            if (
                instance.governorate != editor.governorate
                or instance.area != editor.area
                or instance.subarea != editor.subarea
            ):
                raise serializers.ValidationError(
                    {"location": "لا يمكنك تعديل مستخدمين خارج منطقتك"}
                )

            # بالنسبة للموقع: لو حاول يغيّر governorate/area/subarea لازم يظلوا ضمن نفسه
            new_governorate = attrs.get("governorate", instance.governorate)
            new_area = attrs.get("area", instance.area)
            new_subarea = attrs.get("subarea", instance.subarea)

            if (
                new_governorate != editor.governorate
                or new_area != editor.area
                or new_subarea != editor.subarea
            ):
                raise serializers.ValidationError(
                    {"location": "لا يمكنك نقل المستخدم إلى منطقة أخرى غير منطقتك"}
                )

        return attrs  
    
class AdminSetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        request = self.context["request"]
        actor = request.user                       # اللي عم يغير
        target_user: User = self.context["target_user"]  # اللي رح تتغير كلمته

        pw = attrs.get("new_password")
        cpw = attrs.get("confirm_password")

        if pw != cpw:
            raise serializers.ValidationError({"confirm_password": "كلمتا المرور غير متطابقتين"})

        # تحقق قوة كلمة السر حسب إعدادات Django validators
        validate_password(pw, user=target_user)

        # قواعد الأمان على حسب الدور
        if is_super_admin(actor):
            # (اختياري) منع سوبر أدمن يغير كلمة سوبر أدمن ثاني
            # إذا بدك تسمح احذف هالبلوك
            if get_role_name(target_user) == "super_admin" and actor.id != target_user.id:
                raise serializers.ValidationError({"permission": "لا يمكنك تغيير كلمة سر أمن أساسي آخر."})
            return attrs

        if is_area_manager(actor):
            # لا يسمح لمدير المنطقة بتغيير كلمة سر super_admin
            if get_role_name(target_user) == "super_admin":
                raise serializers.ValidationError({"permission": "لا يمكنك تغيير كلمة سر الأمن الأساسي."})

            # لازم يكون ضمن نفس المنطقة (حسب منطقك الحالي: governorate + area)
            if (
                target_user.governorate != actor.governorate
                or target_user.area != actor.area
            ):
                raise serializers.ValidationError({"location": "لا يمكنك تغيير كلمة سر مستخدم خارج منطقتك."})

            return attrs

        raise serializers.ValidationError({"permission": "ليس لديك صلاحية لتغيير كلمات المرور."})

    def save(self):
        target_user: User = self.context["target_user"]
        pw = self.validated_data["new_password"]
        target_user.set_password(pw)
        target_user.save(update_fields=["password"])
        return target_user
    

