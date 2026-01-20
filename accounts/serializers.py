from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q
from rest_framework import serializers

User = get_user_model()

class LoginSerizlizer( serializers.Serializer ) : 
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