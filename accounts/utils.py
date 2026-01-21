

def get_role_name(user) -> str:
    role = getattr(user, "role", None)
    if not role:
        return ""
    return (getattr(role, "name", "") or "").lower()


def is_super_admin(user) -> bool:
    return get_role_name(user) == "super_admin"


def is_area_manager(user) -> bool:
    return get_role_name(user) == "area_manager"


def is_data_entry(user) -> bool:
    return get_role_name(user) == "data_entry"
