from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# إعداد التوثيق التلقائي باستخدام drf-yasg 
schema_view = get_schema_view(
    openapi.Info(
        title="My API",  # عنوان الـ API
        default_version='v1',  # النسخة الافتراضية للـ API
        description="This is the API documentation for our project",  # وصف الـ API
        terms_of_service="https://www.google.com/policies/terms/",  # رابط شروط الخدمة
        contact=openapi.Contact(email="contact@myapi.local"),  # معلومات الاتصال
        license=openapi.License(name="BSD License"),  # الترخيص
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),  # تحديد صلاحيات الوصول (يسمح للجميع)
)

urlpatterns = [
    path('admin/', admin.site.urls),  # مسار لوحة التحكم الإدارية
    path('api/auth/', include('accounts.urls')),  # مسار الـ authentication
    path('locations/', include('locations.urls')),  # مسار الـ locations
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),  # توثيق Swagger
    path('openapi/', schema_view.without_ui(cache_timeout=0), name='schema-json'),  # مسار الـ OpenAPI JSON
]
