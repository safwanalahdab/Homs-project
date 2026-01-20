from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .serializers import * 
from .helper import *

User = get_user_model() 

def user_payload(user) :
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": getattr(user.role, "name", None),
        "scope": {
            "governorate_id": user.governorate_id,
            "area_id": user.area_id,
            "subarea_id": user.subarea_id,
        }
    }

class LoginView( APIView ) :
   permission_classes = [ permissions.AllowAny ]

   def post( self , request ) : 
       serializer = LoginSerizlizer( data = request.data ) 
       serializer.is_valid( raise_exception = True )
       user = serializer.validated_data["user"]

       refresh = RefreshToken.for_user(user) 
       access = str(refresh.access_token)

       response = Response(
           {
               "Message" : "تم تسجيل الدخول بنجاح" ,
               "access" : access , 
               "user" : user_payload(user) 
           } , status = status.HTTP_200_OK
       )
       
       set_refresh_cookie( response , str(refresh) ) 
       return response
   

class RefreshView( APIView ) : 
    permission_classes = [permissions.AllowAny] 

    def post( self , request ) :
        refresh_token = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if not refresh_token : 
            return Response({
                "error" : "no refresh token" 
            } , status = status.HTTP_401_UNAUTHORIZED)

        try : 
            old_refresh = RefreshToken(refresh_token) 
            user_id = old_refresh.get("user_id") 
        except TokenError : 
            return Response(
                {"error" : "invalid refresh token"} ,
                status = status.HTTP_401_UNAUTHORIZED
            )    
        
        user = User.objects.filter( id = user_id ).first()
        if not user : 
           return Response({"error": "User not found"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            old_refresh.blacklist()
        except Exception:
            pass

        new_refresh = RefreshToken.for_user(user)
        new_access = str(new_refresh.access_token)

        response = Response(
            {"access": new_access},
            status=status.HTTP_200_OK
        )
        set_refresh_cookie(response, str(new_refresh))
        return response

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.COOKIES.get(REFRESH_COOKIE_NAME)

        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except Exception:
                pass

        response = Response({"message": "تم تسجيل الخروج بنجاح"}, status=status.HTTP_200_OK)
        clear_refresh_cookie(response)
        return response
    
class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(user_payload(request.user), status=status.HTTP_200_OK)


class ChangePasswordView(APIView) :
    permission_classes = [permissions.IsAuthenticated] 

    def post( self , request ) : 
        serializer = ChangePasswordSerializer( data = request.data , context = {"request" : request})
        serializer.is_valid(raise_exception=True) 

        
        user = request.user
        new_password = serializer.validated_data["new_password"]
        user.set_password(new_password)
        user.save()

        refresh_token = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except Exception:
                pass

        response = Response({"message": "تم تغيير كلمة المرور بنجاح"}, status=status.HTTP_200_OK)
        clear_refresh_cookie(response)  # يخليه يسجّل دخول من جديد
        return response
