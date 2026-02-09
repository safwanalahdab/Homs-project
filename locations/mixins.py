# core/mixins.py

from accounts.utils import is_super_admin, is_area_manager, is_data_entry


class LocationScopedQuerysetMixin :

    """
    مكسين للجداول اللي فيها FK على Village.
    يفلتر البيانات بحسب موقع المستخدم:
    - super_admin: يشوف كل السجلات
    - area_manager / data_entry: يشوف فقط السجلات ضمن محافظته + منطقته
    """

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

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
    