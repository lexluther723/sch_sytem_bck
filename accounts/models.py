from django.contrib.auth.models import AbstractUser
from django.db import models



class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
        ACADEMIC_COORDINATOR = "ACADEMIC_COORDINATOR", "Academic Coordinator"
        ACCOUNTANT = "ACCOUNTANT", "Accountant"
        TEACHER = "TEACHER", "Teacher"
        PARENT = "PARENT", "Parent"
        STUDENT = "STUDENT", "Student"


    # SECURITY: this previously defaulted to Role.SUPER_ADMIN, so any
    # code path that created a user without explicitly passing a role
    # (a data migration, a fixture, a management command, a forgotten
    # kwarg) silently minted a full system administrator.
    #
    # STUDENT is the least-privileged role in the system, so it is the
    # correct default. Registration always sets the role explicitly,
    # so no existing flow changes behaviour.
    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.STUDENT,
        db_index=True,
    )


    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )


    profile_picture = models.ImageField(
        upload_to="profile_pictures/",
        blank=True,
        null=True,
    )


    is_active = models.BooleanField(default=True)


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        ordering = ["first_name", "last_name", "username"]


    def __str__(self):
        full_name = self.get_full_name()
        return full_name if full_name else self.username



# ==========================================
# Parent Profile
# ==========================================
class ParentProfile(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="parent_profile",
    )


    occupation = models.CharField(
        max_length=100,
        blank=True,
    )


    address = models.TextField(
        blank=True,
    )


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        ordering = ["user__first_name", "user__last_name"]


    def __str__(self):
        return self.user.get_full_name() or self.user.username



# ==========================================
# Teacher Profile
# ==========================================
class TeacherProfile(models.Model):


    class Gender(models.TextChoices):
        MALE = "Male", "Male"
        FEMALE = "Female", "Female"


    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="teacher_profile",
    )


    employee_number = models.CharField(
        max_length=30,
        unique=True,
    )


    national_id = models.CharField(
        max_length=20,
        unique=True,
    )


    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
    )


    date_of_birth = models.DateField()


    qualification = models.CharField(
        max_length=100,
    )


    employment_date = models.DateField()


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        ordering = ["employee_number"]


    def __str__(self):
        return self.user.get_full_name() or self.user.username



# ==========================================
# Accountant Profile
# ==========================================
class AccountantProfile(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="accountant_profile",
    )


    employee_number = models.CharField(
        max_length=30,
        unique=True,
    )


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        ordering = ["employee_number"]


    def __str__(self):
        return self.user.get_full_name() or self.user.username



# ==========================================
# Academic Coordinator Profile
# ==========================================
class AcademicCoordinatorProfile(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="academic_coordinator_profile",
    )


    employee_number = models.CharField(
        max_length=30,
        unique=True,
    )


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        ordering = ["employee_number"]


    def __str__(self):
        return self.user.get_full_name() or self.user.username 


# ==========================================
# Student Profile — ✅ PHONE ADDED
# ==========================================
class StudentProfile(models.Model):
    class Gender(models.TextChoices):
        MALE = "Male", "Male"
        FEMALE = "Female", "Female"


    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )


    admission_number = models.CharField(
        max_length=30,
        unique=True,
    )


    national_id = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        unique=True,
    )


    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
    )


    date_of_birth = models.DateField()

    # ✅ ADDED: Direct parent phone field on StudentProfile
    parent_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Parent/Guardian phone number",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        ordering = ["admission_number"]


    def __str__(self):
        return self.user.get_full_name() or self.user.username