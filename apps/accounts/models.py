import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from apps.corporate.models import CorporateOffice
# Create your models here.


class Office(models.Model):
    name = models.CharField(max_length=255, verbose_name=_("name"))
    geo_loc = models.CharField(max_length=255, verbose_name=_("geo location"))
    geo_lat = models.DecimalField(max_digits=10, decimal_places=6, verbose_name=_("latitude"))
    geo_lng = models.DecimalField(max_digits=10, decimal_places=6, verbose_name=_("longitude"))
    phone = models.CharField(max_length=15, verbose_name=_("phone"))
    email = models.EmailField(verbose_name=_("email"))
    address = models.CharField(max_length=255, verbose_name=_("physical address"))
    description = models.TextField(verbose_name=_("description"))
    pickup_first_free_kms = models.PositiveIntegerField(default=0)

    enable_pickup = models.BooleanField(default=True)
    pickup_discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default="0.00",
        help_text="Discount (%) on intracity pickup fee for intercounty deliveries."
    )
    max_pickup_km = models.DecimalField(
        max_digits=5, decimal_places=2, default="5.00",
        help_text="Distance covered under base pickup fee."
    )

    is_intracity_centre = models.BooleanField(
        default=False,
        help_text="Mark the office as the central point for intracity deliveries in the region."
    )
    intracity_radius_km = models.DecimalField(
        max_digits=6, decimal_places=2, default=35.00, help_text="Max intracity delivery coverage in km."
    )

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    def create_user(self, email, full_name, phone, role, password, **extra_fileds):

        if not email:
            raise ValueError("Email is required")

        if not full_name:
            raise ValueError("Full name is required")
        
        if not phone:
            raise ValueError("Phone is required")
        

        user = self.model(
            full_name=full_name,
            email=self.normalize_email(email).lower(),
            phone=phone,
            role=role,
            **extra_fileds
        )
        user.set_password(password)
        user.save(using=self._db)
        return user
    

    def create_superuser(self, email, full_name, phone, role, password, **extra_fileds):
        if not email:
            raise ValueError("Email is required")

        if not full_name:
            raise ValueError("Full name is required")
        
        if not phone:
            raise ValueError("Phone is required")
        

        extra_fileds.setdefault('is_staff', True)
        extra_fileds.setdefault('is_superuser', True)
        extra_fileds.setdefault('is_admin', True)

        if extra_fileds.get("is_staff") is not True:
            raise ValueError('Superuser must have is_staff=True.')
        
        if extra_fileds.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        

        user = self.create_user(
            full_name=full_name,
            email=email,
            phone=phone,
            role=role,
            password=password,
            **extra_fileds
        )
        user.save(using=self._db)
        return user



class User(AbstractBaseUser, PermissionsMixin):

    ROLE_CHOICES = [
        ( "admin", "Admin", ),
        ( "client", "Client", ),
        ( 'manager', 'Manager', ),
        ( 'driver', 'Driver', ),
        ( 'partner_shop', 'Partner Pickup Shop', ),
        ( 'partner_rider', 'Partner Rider', ),
    ]


    ACCOUNT_TYPE_CHOICES = [
        ('personal', 'Personal'),
        ('business', 'Business'),
    ]


    GENDER_CHOICES = [
        ( 'female', 'Female', ),
        ( 'male', 'Male', ),
        ( 'not_say', 'Not say', ),
    ]


    id = models.UUIDField(primary_key=True, editable=False, unique=True, default=uuid.uuid4, verbose_name=_("unique ID"))
    full_name = models.CharField(max_length=255, verbose_name=_("user name"))
    phone = models.CharField(max_length=15, unique=True, verbose_name=_("phone"))
    email = models.EmailField(unique=True, verbose_name=_("email"))
    gender = models.CharField(max_length=60, choices=GENDER_CHOICES, null=True, blank=True)

    role = models.CharField(max_length=100, choices=ROLE_CHOICES, verbose_name=_("role"))
    office = models.ForeignKey(Office, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("office allocated (manager)"))
    corporate_office = models.ForeignKey(CorporateOffice, on_delete=models.SET_NULL, null=True, blank=True, related_name="corporate_office")
    profile_image = models.ImageField(upload_to="users/", null=True, blank=True, verbose_name=_("user image"))
    account_type = models.CharField(max_length=50, choices=ACCOUNT_TYPE_CHOICES, default="personal")

    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)

    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = [
        'full_name', 'phone', 'role'
    ]


    def __str__(self):
        return self.email



class PartnerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='partner_profile')
    office = models.OneToOneField(Office, on_delete=models.SET_NULL, null=True)
    business_name = models.CharField(max_length=255)
    license_number = models.CharField(max_length=100, blank=True)
    id_document = models.FileField(upload_to="partner_ids/")
    is_verified = models.BooleanField(default=False)
    location_latLang = models.CharField(max_length=70, null=True, verbose_name=_("partner shop latitude,longitude"))
    location = models.CharField(max_length=70, null=True, verbose_name=_("shop address"))

    def __str__(self):
        return f"{self.user.email}"


class DriverLocation(models.Model):
    driver = models.OneToOneField(User, on_delete=models.CASCADE, related_name="location", limit_choices_to={ 'role__in': [ 'driver', 'partner_rider']})
    latitude = models.DecimalField(max_digits=10, decimal_places=6)
    longitude = models.DecimalField(max_digits=10, decimal_places=6)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.driver.full_name} location"




