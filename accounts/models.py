from django.db import models
from django.contrib.auth.models import AbstractUser 
from django.utils import timezone 

# المدينة مثل حمص
class Governorate( models.Model ) : 
    name = models.CharField( max_length = 100 ) 

    def __str__(self):
        return self.name 
    
# المنطقة مثل الرستن
class Area( models.Model ) : 
    name = models.CharField( max_length = 100 ) 
    governorate = models.ForeignKey( Governorate , on_delete = models.PROTECT , related_name = "areas" )
    
    def __str__(self):
        return self.name 

#ناحية متل تلبيسة 
class SubArea ( models.Model ) : 
    name = models.CharField( max_length = 100 ) 
    area = models.ForeignKey( Area , on_delete = models.PROTECT , related_name = "subareas" ) 

    def __str__(self):
        return self.name 
    
#قرية مثل الغنطو
class Village ( models.Model ) : 
    class VillageType( models.TextChoices ) : 
        VILLAGE_UNDER_MUNICIPALITY = "village_under_municipality", "Village under municipality"
        MUNICIPALITY = "municipality", "Municipality"
        VILLAGE_UNDER_CITY = "village_under_city", "Village under city"
        CITY = "city", "City"

    name = models.CharField( max_length = 100 ) 
    subarea = models.ForeignKey( SubArea , on_delete = models.PROTECT , related_name = "villages" ) 
    type = models.CharField( max_length = 100 , choices = VillageType.choices ) 
    parent_name = models.CharField( max_length = 100 , null = True , blank = True ) 

    def __str__(self):
        return self.name 
    

class Role ( models.Model ) : 
    name = models.CharField( max_length = 100 , unique = True ) 

    def __str__(self):
        return self.name 

class Permission( models.Model ) : 
    action = models.CharField( max_length = 100 ) 
    entity = models.CharField( max_length = 100 ) 
    
    """
    class Meta : 
        constraints = [
            models.UniqueConstraint( fields = ['action','entity'] , name = "uniq_action_entity" ) 
        ]
    """

    def __str__(self):
        return f"{self.action}:{self.entity}" 

class PermissionRole ( models.Model ) : 
    role = models.ForeignKey( Role , on_delete = models.PROTECT , related_name = "permission_links" ) 
    permission = models.ForeignKey( Permission , on_delete = models.PROTECT , related_name = "role_links" )

    """class Meta:
      constraints = [
            models.UniqueConstraint(fields=["role", "permission"], name="uniq_role_permission")
        ]
    """

class User ( AbstractUser ) : 
    class Gender( models.TextChoices ) : 
        MALE = "male", "Male"
        FEMALE = "female", "Female"

    class Status ( models.TextChoices ) :
        ACTIVE = "active", "Active"
        DEACTIVE = "deactive", "Deactive"

    gender = models.CharField( max_length = 100 , choices = Gender.choices , null = True , blank = True ) 
    birth_date = models.DateField( blank = True , null = True )
    phone = models.CharField( max_length = 15 , blank = True , null = True ) 
    email = models.EmailField( unique = True ) 
    role = models.ForeignKey( Role , on_delete = models.PROTECT , related_name = "users" , null = True , blank = True ) 

    governorate = models.ForeignKey( Governorate , on_delete = models.PROTECT , related_name = "users" , null = True , blank = True)
    area = models.ForeignKey( Area , on_delete = models.PROTECT , related_name = "users" , null = True , blank = True)
    subarea = models.ForeignKey( SubArea , on_delete = models.PROTECT , related_name = "users" , null = True , blank = True)
    
    status = models.CharField( max_length = 100 , choices = Status.choices , default = Status.ACTIVE ) 

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True) 

# الطائفة
class Sect(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

#العرق
class Ethnicity(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

#قبيلة عشيرة
class Tribe(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name
    
class Person(models.Model):
    name = models.CharField(max_length=255)

    sect = models.ForeignKey(Sect, on_delete=models.PROTECT, related_name="persons", blank=True, null=True)
    ethnicity = models.ForeignKey(Ethnicity, on_delete=models.PROTECT, related_name="persons", blank=True, null=True)
    tribe = models.ForeignKey(Tribe, on_delete=models.PROTECT, related_name="persons", blank=True, null=True)

    village = models.ForeignKey(Village, on_delete=models.PROTECT, related_name="persons")
    phone = models.CharField(max_length=50, blank=True, null=True)
    address = models.CharField(max_length=500, blank=True, null=True)

    educational_qualifications = models.CharField(max_length=500, blank=True, null=True)
    work = models.CharField(max_length=255, blank=True, null=True)
    social_interests = models.TextField(blank=True, null=True)
    community_influence = models.TextField(blank=True, null=True)
    system_affiliation = models.TextField(blank=True, null=True)
    new_leadership = models.TextField(blank=True, null=True)

    area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name="persons", blank=True, null=True)

    locked = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_persons")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name
    
class VillageSect(models.Model):
    village = models.ForeignKey(Village, on_delete=models.CASCADE, related_name="village_sects")
    sect = models.ForeignKey(Sect, on_delete=models.PROTECT, related_name="village_sects")

    family_count = models.IntegerField(blank=True, null=True)
    individual_count = models.IntegerField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_village_sects")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["village", "sect"], name="uniq_village_sect")
        ]

#الاشخاص المهمين في القرية حسب الطائفة
class VillageSectKeyFigure(models.Model):
    village_sect = models.ForeignKey(VillageSect, on_delete=models.CASCADE, related_name="key_figures")
    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="sect_key_figure_links")

    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_village_sect_key_figures")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["village_sect", "person"], name="uniq_village_sect_person")
        ]


class VillageEthnicity(models.Model):
    village = models.ForeignKey(Village, on_delete=models.CASCADE, related_name="village_ethnicities")
    ethnicity = models.ForeignKey(Ethnicity, on_delete=models.PROTECT, related_name="village_ethnicities")
    year = models.PositiveSmallIntegerField()

    family_count = models.IntegerField(blank=True, null=True)
    individual_count = models.IntegerField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["village", "ethnicity", "year"], name="uniq_village_ethnicity_year")
        ]
#الاشخاص المهمين حسب العرق
class EthnicityKeyFigure(models.Model):
    village_ethnicity = models.ForeignKey(VillageEthnicity, on_delete=models.CASCADE, related_name="key_figures")
    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="ethnicity_key_figure_links")

    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_ethnicity_key_figures")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["village_ethnicity", "person"], name="uniq_village_ethnicity_person")
        ]


class VillageTribe(models.Model):
    village = models.ForeignKey(Village, on_delete=models.CASCADE, related_name="village_tribes")
    tribe = models.ForeignKey(Tribe, on_delete=models.PROTECT, related_name="village_tribes")
    year = models.PositiveSmallIntegerField()

    individual_count = models.IntegerField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["village", "tribe", "year"], name="uniq_village_tribe_year")
        ]

# الاشخاص المهمين حسب القبيلة
class VillageTribeKeyFigure(models.Model):
    village_tribe = models.ForeignKey(VillageTribe, on_delete=models.CASCADE, related_name="key_figures")
    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="tribe_key_figure_links")

    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_village_tribe_key_figures")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["village_tribe", "person"], name="uniq_village_tribe_person")
        ]


class ModificationRequest(models.Model):
    class EntityType(models.TextChoices):
        SUBAREA = "subarea", "SubArea"
        VILLAGES = "villages", "Villages"
        SECTS = "sects", "Sects"
        PERSONS = "persons", "Persons"
        ETHNICITIES = "ethnicities", "Ethnicities"
        TRIBES = "tribes", "Tribes"
        LIVESTOCK = "livestock", "Livestock"
        GOVERNMENT_DEPARTMENTS = "government_departments", "Government Departments"
        NATURAL_ASSETS = "natural_assets", "Natural Assets"
        INDUSTRIAL_ZONES = "industrial_zones", "Industrial Zones"
        TOURISM_FACILITIES = "tourism_facilities", "Tourism Facilities"
        ARCHAEOLOGICAL_SITES = "archaeological_sites", "Archaeological Sites"
        COMMERCIAL_ACTIVITIES = "commercial_activities", "Commercial Activities"
        DEMOGRAPHIC_DATA = "demographic_data", "Demographic Data"
        AGRICULTURAL_STATUS = "agricultural_status", "Agricultural Status"
        AGRICULTURAL_CROPS = "agricultural_crops", "Agricultural Crops"
        INDUSTRIAL_FACILITIES = "industrial_facilities", "Industrial Facilities"

    class Action(models.TextChoices):
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    name = models.CharField(max_length=255)
    entity_type = models.CharField(max_length=64, choices=EntityType.choices)
    entity_id = models.IntegerField()
    action = models.CharField(max_length=10, choices=Action.choices)

    requested_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="mod_requests")
    old_data = models.JSONField()
    new_data = models.JSONField()

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    reviewed_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="reviewed_mod_requests", blank=True, null=True
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)

class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        HARDDELETE = "harddelete", "Hard Delete"

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="audit_logs")
    entity_type = models.CharField(max_length=100)
    entity_id = models.IntegerField()

    action = models.CharField(max_length=20, choices=Action.choices)
    old_data = models.JSONField(blank=True, null=True)
    new_data = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)


class UserHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="history")
    entity_type = models.CharField(max_length=100)
    entity_id = models.IntegerField()

    active = models.BooleanField(default=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)

#بيانات الثروة الحيوانية لقرية ضمن سنة.
class Livestock(models.Model):
    village = models.ForeignKey(Village, on_delete=models.CASCADE, related_name="livestock_records")
    year = models.PositiveSmallIntegerField()

    cows_count = models.IntegerField(blank=True, null=True)
    sheep_count = models.IntegerField(blank=True, null=True)
    poultry_count = models.IntegerField(blank=True, null=True)
    camels_count = models.IntegerField(blank=True, null=True)
    fish_count = models.IntegerField(blank=True, null=True)

    feeds = models.JSONField(blank=True, null=True)
    grazing_areas = models.IntegerField(blank=True, null=True)
    grazing_areas_size = models.IntegerField(blank=True, null=True)

    meat_production = models.IntegerField(blank=True, null=True)
    milk_products = models.JSONField(blank=True, null=True)
    egg_production = models.IntegerField(blank=True, null=True)

    breeders_count = models.IntegerField(blank=True, null=True)
    veterinarians_count = models.IntegerField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_livestock")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["village", "year"], name="uniq_livestock_village_year")
        ]

#أي دائرة حكومية موجودة بأي قرية، بأي سنة، وتحت أي وزارة، مع تفاصيل التواصل والإدارة.
class GovernmentDepartment(models.Model):
    class MinistryName(models.TextChoices):
        ECONIMIC = "econimic", "Econimic"      
        TECHNOLOGY = "technology", "Technology"

    year = models.PositiveSmallIntegerField()
    ministry_name = models.CharField(max_length=32, choices=MinistryName.choices)
    department_name = models.CharField(max_length=255)

    village = models.ForeignKey(Village, on_delete=models.CASCADE, related_name="government_departments")
    address = models.CharField(max_length=500, blank=True, null=True)
    director_name = models.CharField(max_length=255, blank=True, null=True)
    contact_number = models.CharField(max_length=50, blank=True, null=True)
    staff_count = models.IntegerField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["village", "year", "department_name"], name="uniq_dept_village_year_name")
        ]

"""

جدول NaturalAsset يهدف إلى تخزين وتوثيق بيانات الأصول/المعالم الطبيعية الموجودة ضمن قرية/مدينة محددة خلال
سنة معينة، مثل: مياه/غابات/محميات/معادن/جبال/ساحل… إلخ، مع تحديد التصنيف، مستوى الأهمية، نوع الملكية،
المالك/المستثمر (إن وجد)، وبعض المؤشرات مثل عدد الزوار والإيراد السنوي.

"""

class NaturalAsset(models.Model):
    class AssetType(models.TextChoices):
        WATER = "water", "Water"
        FOREST = "forest", "Forest"
        RESERVE = "reserve", "Reserve"
        MINERAL = "mineral", "Mineral"
        MOUNTAIN = "mountain", "Mountain"
        COAST = "coast", "Coast"
        DESERT = "desert", "Desert"
        NATURE_RESERVE = "nature_reserve", "Nature reserve"
        PETROLEUM_RESOURCE = "Petroleum_Resource", "Petroleum Resource"

    class Classification(models.TextChoices):
        PROTECTED_AREA = "PROTECTED_AREA", "Protected area"
        TOURIST_SITE = "TOURIST_SITE", "Tourist site"
        INVESTMENT_ZONE = "INVESTMENT_ZONE", "Investment zone"
        PUBLIC_PARK = "PUBLIC_PARK", "Public park"
        FORESTRY_AREA = "FORESTRY_AREA", "Forestry area"
        NATURAL_RESOURCE = "NATURAL_RESOURCE", "Natural resource"

    class ImportantLevel(models.TextChoices):
        LOCAL = "local", "Local"
        NATIONAL = "national", "National"
        INTERNATIONAL = "international", "International"

    class Ownership(models.TextChoices):
        STATE = "state", "State"
        PRIVATE = "private", "Private"
        MIXED = "mixed", "Mixed"

    village = models.ForeignKey(Village, on_delete=models.CASCADE, related_name="natural_assets")
    year = models.PositiveSmallIntegerField()

    type = models.CharField(max_length=64, choices=AssetType.choices)
    name = models.CharField(max_length=255)

    classification = models.CharField(max_length=64, choices=Classification.choices)
    important_level = models.CharField(max_length=32, choices=ImportantLevel.choices)
    ownership = models.CharField(max_length=16, choices=Ownership.choices)

    person_id_owner_name = models.ForeignKey(
        Person, on_delete=models.PROTECT, related_name="owned_natural_assets", blank=True, null=True
    )
    supervising_authority = models.CharField(max_length=255, blank=True, null=True)
    person_id_investor_name = models.ForeignKey(
        Person, on_delete=models.PROTECT, related_name="invested_natural_assets", blank=True, null=True
    )

    average_visitors = models.IntegerField(blank=True, null=True)
    annual_revenue = models.IntegerField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)


#مناطق صناعية
class IndustrialFacility(models.Model):
    class FacilityType(models.TextChoices):
        WORKSHOP = "workshop", "Workshop"
        SMALL_FACTORY = "small_factory", "Small factory"
        MEDIUM_FACTORY = "medium_factory", "Medium factory"
        LARGE_FACTORY = "large_factory", "Large factory"
        PROCESSING_PLANT = "processing_plant", "Processing plant"
        OTHER = "other", "Other"

    class Classification(models.TextChoices):
        LOCAL = "Local", "Local"
        NATIONAL = "National", "National"
        INTERNATIONAL = "International", "International"

    class LicenseType(models.TextChoices):
        INDUSTRIAL = "industrial", "Industrial"
        ENVIRONMENTAL = "environmental", "Environmental"
        COMMERCIAL = "commercial", "Commercial"
        SAFETY = "safety", "Safety"
        OTHER = "other", "Other"

    village = models.ForeignKey(Village, on_delete=models.CASCADE, related_name="industrial_facilities")
    year = models.PositiveSmallIntegerField()

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=32, choices=FacilityType.choices)

    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="industrial_facilities", blank=True, null=True)
    classification = models.CharField(max_length=32, choices=Classification.choices, blank=True, null=True)

    number_of_workers = models.IntegerField(blank=True, null=True)
    has_license = models.BooleanField(default=False)
    license_type = models.CharField(max_length=32, choices=LicenseType.choices, blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_industrial_facilities")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["village", "year", "name"], name="uniq_ind_facility_village_year_name")
        ]

class IndustrialZone(models.Model):
    village = models.ForeignKey(Village, on_delete=models.CASCADE, related_name="industrial_zones")
    year = models.PositiveSmallIntegerField()

    number_of_facilities = models.IntegerField(blank=True, null=True)
    number_of_shops = models.IntegerField(blank=True, null=True)
    number_of_workers = models.IntegerField(blank=True, null=True)
    annual_revenue = models.IntegerField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_industrial_zones")
    created_at = models.IntegerField()  # TODO: غالباً timestamp
    updated_at = models.IntegerField()  # TODO: غالباً timestamp

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["village", "year"], name="uniq_industrial_zone_village_year")
        ]


#منشات أثرية
class ArchaeologicalSite(models.Model):
    village = models.ForeignKey(Village, on_delete=models.CASCADE, related_name="archaeological_sites")
    year = models.PositiveSmallIntegerField()

    name = models.CharField(max_length=255)
    site_date = models.CharField(max_length=255, blank=True, null=True)
    archaeological_feature = models.CharField(max_length=500, blank=True, null=True)

    is_registered = models.BooleanField(default=False)
    registered_organization = models.CharField(max_length=255, blank=True, null=True)
    registration_date = models.DateField(blank=True, null=True)

    average_visitors = models.IntegerField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_archaeological_sites")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

class TourismFacility(models.Model):
    class FacilityType(models.TextChoices):
        HOTEL = "HOTEL", "Hotel"
        RESORT = "RESORT", "Resort"
        TOURIST_RESTAURANT = "TOURIST_RESTAURANT", "Tourist restaurant"
        PARK = "PARK", "Park"
        ARCHAEOLOGICAL_SITE = "ARCHAEOLOGICAL_SITE", "Archaeological site"
        BEACH = "BEACH", "Beach"
        MUSEUM = "MUSEUM", "Museum"

    class Classification(models.TextChoices):
        LOCAL = "LOCAL", "Local"
        NATIONAL = "NATIONAL", "National"
        INTERNATIONAL = "INTERNATIONAL", "International"

    village = models.ForeignKey(Village, on_delete=models.CASCADE, related_name="tourism_facilities")
    year = models.PositiveSmallIntegerField()

    type = models.CharField(max_length=64, choices=FacilityType.choices)
    is_invested = models.BooleanField(default=False)
    is_private_property = models.BooleanField(default=False)

    person_id_investor_name = models.ForeignKey(
        Person, on_delete=models.PROTECT, related_name="investor_tourism_facilities", blank=True, null=True
    )
    person_id_owner_name = models.ForeignKey(
        Person, on_delete=models.PROTECT, related_name="owner_tourism_facilities", blank=True, null=True
    )

    supervising_authority = models.CharField(max_length=255, blank=True, null=True)
    classification = models.CharField(max_length=32, choices=Classification.choices, blank=True, null=True)

    average_visitors = models.IntegerField(blank=True, null=True)
    annual_revenue = models.IntegerField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_tourism_facilities")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)


#نشاطات تجارية
class CommercialActivity(models.Model):
    class ActivityType(models.TextChoices):
        GROCERY = "grocery", "Grocery"
        SUPERMARKET = "supermarket", "Supermarket"
        RESTAURANT = "restaurant", "Restaurant"
        CAFE = "cafe", "Cafe"
        BAKERY = "bakery", "Bakery"
        PHARMACY = "pharmacy", "Pharmacy"
        CLOTHING_STORE = "clothing_store", "Clothing store"
        ELECTRONICS = "electronics", "Electronics"
        WORKSHOP = "workshop", "Workshop"
        FUEL_STATION = "fuel_station", "Fuel station"
        OTHER = "other", "Other"

    class LicenseType(models.TextChoices):
        MUNICIPAL = "municipal", "Municipal"
        COMMERCIAL = "commercial", "Commercial"
        INDUSTRIAL = "industrial", "Industrial"
        TOURISM = "tourism", "Tourism"
        HEALTH = "health", "Health"
        TEMPORARY = "temporary", "Temporary"

    village = models.ForeignKey(Village, on_delete=models.CASCADE, related_name="commercial_activities")
    year = models.PositiveSmallIntegerField()

    name = models.CharField(max_length=255)
    activity_type = models.CharField(max_length=32, choices=ActivityType.choices)
    address = models.CharField(max_length=500, blank=True, null=True)

    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="commercial_activities", blank=True, null=True)

    is_licensed = models.BooleanField(default=False)
    license_type = models.CharField(max_length=32, choices=LicenseType.choices, blank=True, null=True)
    license_date = models.DateField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_commercial_activities")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)


#ديموغرايفية
class DemographicData(models.Model):
    village = models.ForeignKey(Village, on_delete=models.CASCADE, related_name="demographic_data")
    year = models.PositiveSmallIntegerField()

    administrative_boundaries = models.CharField(max_length=500, blank=True, null=True)
    area = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    population = models.IntegerField(blank=True, null=True)
    number_of_families = models.IntegerField(blank=True, null=True)

    male_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    female_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    number_of_martyrs = models.IntegerField(blank=True, null=True)
    number_of_injured = models.IntegerField(blank=True, null=True)
    number_of_detainees = models.IntegerField(blank=True, null=True)

    displaced_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    returned_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    unemployment_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    poverty_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    wealth_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    government_workers_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    private_sector_workers_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    elderly_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    farmers_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    industrial_workers_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    traders_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    craftsmen_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    expatriates_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_demographic_data")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["village", "year"], name="uniq_demographic_village_year")
        ]

class AgriculturalStatus(models.Model):
    class Season(models.TextChoices):
        WINTER = "winter", "Winter"
        SPRING = "spring", "Spring"
        SUMMER = "summer", "Summer"
        AUTUMN = "autumn", "Autumn"

    village = models.ForeignKey(Village, on_delete=models.CASCADE, related_name="agricultural_statuses")
    year = models.PositiveSmallIntegerField()

    total_agricultural_area = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    irrigated_land_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    rainfed_land_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    critical_land_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    state_owned_land_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    water_resources = models.JSONField(blank=True, null=True)
    season = models.CharField(
        max_length=10, choices=Season.choices, blank=True, null=True
    )  # NULL = annual report

    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_agricultural_statuses")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["village", "year", "season"], name="uniq_agri_status_village_year_season")
        ]

class Crop(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_crops")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
class AgriculturalCrop(models.Model):
    agricultural_status = models.ForeignKey(
        AgriculturalStatus, on_delete=models.CASCADE, related_name="agricultural_crops"
    )
    crop = models.ForeignKey(Crop, on_delete=models.PROTECT, related_name="agricultural_crops")

    area = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_strategic = models.BooleanField(default=False)

    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_agricultural_crops")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["agricultural_status", "crop"], name="uniq_ag_status_crop")
        ]