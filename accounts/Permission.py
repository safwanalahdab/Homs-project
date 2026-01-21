from rest_framework.permissions import BasePermission
from .utils import is_super_admin, is_area_manager

class CanManageAccounts(BasePermission):
   
   message = "غير مصرح: هذه الواجهة لإدارة الحسابات (الأمن الأساسي ومدراء المناطق فقط)."

   def has_permission(self, request, view):
     user = request.user
     if not user or not user.is_authenticated:
            return False
     return is_super_admin(user) or is_area_manager(user)
