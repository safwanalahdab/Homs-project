# locations/permissions.py

from rest_framework.permissions import BasePermission
from accounts.utils import is_super_admin, is_area_manager, is_data_entry


class IsSuperAdmin(BasePermission):
    message = "هذه العمليات متاحة للأدمن الأساسي فقط."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and is_super_admin(user))


class IsLocationStaff(BasePermission):
    """
    مستخدم له علاقة بالتقسيم الإداري:
    - الأدمن الأساسي
    - مدير منطقة
    - مدخل بيانات
    """

    message = "لا تملك صلاحية لإدارة هذه البيانات."

    def has_permission(self, request, view) :
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return is_super_admin(user) or is_area_manager(user) or is_data_entry(user)

