from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from rest_framework import permissions, generics, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes

from core.throttling import LoginRateThrottle
from core.pagination import StandardResultsSetPagination
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from accounts.serializers import (
    RegisterSerializer,
    StudentProfileSerializer,
    UserSerializer,
    ParentProfileSerializer,
    TeacherProfileSerializer,
    AccountantProfileSerializer,
    AcademicCoordinatorProfileSerializer,
)

from .models import (
    CustomUser,
    ParentProfile,
    StudentProfile,
    TeacherProfile,
    AccountantProfile,
    AcademicCoordinatorProfile,
)


# ============================================================
# PROFILE MODEL MAPPING
# ============================================================

PROFILE_MODELS = {
    CustomUser.Role.PARENT: ParentProfile,
    CustomUser.Role.TEACHER: TeacherProfile,
    CustomUser.Role.ACCOUNTANT: AccountantProfile,
    CustomUser.Role.ACADEMIC_COORDINATOR: AcademicCoordinatorProfile,
    CustomUser.Role.STUDENT: StudentProfile,
}

# Reverse lookup for deleting old profiles when a user's role changes.
PROFILE_MODELS_BY_ROLE = PROFILE_MODELS


# ============================================================
# LOGIN
# ============================================================

@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def Login(request):

    username = request.data.get("username")
    password = request.data.get("password")

    if not username or not password:
        return Response(
            {
                "error": "Username and password are required."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(
        username=username,
        password=password,
    )

    if user is None:
        return Response(
            {
                "error": "Invalid username or password."
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # NOTE: authenticate() already returns None for inactive users
    # (ModelBackend.user_can_authenticate), so this branch is defensive.
    # It deliberately returns the SAME message and status as a wrong
    # password: distinguishing the two let an attacker confirm which
    # usernames exist by observing 403 vs 401.
    if not user.is_active:
        return Response(
            {
                "success": False,
                "message": "Invalid username or password.",
                "error": "Invalid username or password.",
                "errors": {},
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    refresh = RefreshToken.for_user(user)

    return Response(
        {
            "message": "Login successful",
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": UserSerializer(user).data,
        },
        status=status.HTTP_200_OK,
    )


# ============================================================
# LOGIN TEST
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def test(request):

    return Response(
        {
            "id": request.user.id,
            "username": request.user.username,
            "email": request.user.email,
            "role": request.user.role,
        },
        status=status.HTTP_200_OK,
    )


# ============================================================
# LOGOUT
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def Logout(request):

    refresh_token = request.data.get("refresh")

    if not refresh_token:
        return Response(
            {
                "error": "Refresh token is required."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        token = RefreshToken(refresh_token)
        token.blacklist()

        return Response(
            {
                "message": "Logout successful."
            },
            status=status.HTTP_200_OK,
        )

    except TokenError:
        return Response(
            {
                "error": "Invalid or expired refresh token."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


# ============================================================
# REGISTRATION
# ============================================================

@api_view(["POST"])
@transaction.atomic
@permission_classes([IsAuthenticated])
def Register(request):

    # --------------------------------------------------------
    # Only Super Admin can create accounts
    # --------------------------------------------------------

    if request.user.role != CustomUser.Role.SUPER_ADMIN:
        return Response(
            {
                "error": (
                    "Only the Super Admin can create "
                    "user accounts."
                )
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    username = request.data.get("username")
    email = request.data.get("email")
    password = request.data.get("password")
    role = request.data.get("role")
    phone_number = request.data.get("phone_number")

    # --------------------------------------------------------
    # Required fields
    # --------------------------------------------------------

    if not username or not email or not password or not role:
        return Response(
            {
                "error": (
                    "Username, email, password and role "
                    "are required."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # --------------------------------------------------------
    # Check username
    # --------------------------------------------------------

    if CustomUser.objects.filter(
        username=username
    ).exists():
        return Response(
            {
                "error": "Username already exists."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # --------------------------------------------------------
    # Check email
    # --------------------------------------------------------

    if CustomUser.objects.filter(
        email=email
    ).exists():
        return Response(
            {
                "error": "Email already exists."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        serializer = RegisterSerializer(
            data=request.data
        )

        if serializer.is_valid():

            user = serializer.save()

            # ------------------------------------------------
            # TEACHER
            # ------------------------------------------------

            if user.role == CustomUser.Role.TEACHER:

                TeacherProfile.objects.create(
                    user=user,
                    employee_number=request.data.get(
                        "employee_number"
                    ),
                    national_id=request.data.get(
                        "national_id"
                    ),
                    gender=request.data.get(
                        "gender"
                    ),
                    date_of_birth=request.data.get(
                        "date_of_birth"
                    ),
                    qualification=request.data.get(
                        "qualification"
                    ),
                    employment_date=request.data.get(
                        "employment_date"
                    ),
                )

            # ------------------------------------------------
            # PARENT
            # ------------------------------------------------

            elif user.role == CustomUser.Role.PARENT:

                ParentProfile.objects.create(
                    user=user,
                    occupation=request.data.get(
                        "occupation",
                        "",
                    ),
                    address=request.data.get(
                        "address",
                        "",
                    ),
                )

            # ------------------------------------------------
            # ACCOUNTANT
            # ------------------------------------------------

            elif user.role == CustomUser.Role.ACCOUNTANT:

                AccountantProfile.objects.create(
                    user=user,
                    employee_number=request.data.get(
                        "employee_number"
                    ),
                )

            # ------------------------------------------------
            # ACADEMIC COORDINATOR
            # ------------------------------------------------

            elif (
                user.role
                == CustomUser.Role.ACADEMIC_COORDINATOR
            ):

                AcademicCoordinatorProfile.objects.create(
                    user=user,
                    employee_number=request.data.get(
                        "employee_number"
                    ),
                )

            # ------------------------------------------------
            # STUDENT
            # ------------------------------------------------

            elif user.role == CustomUser.Role.STUDENT:

                StudentProfile.objects.create(
                    user=user,
                    admission_number=request.data.get(
                        "admission_number"
                    ),
                    national_id=request.data.get(
                        "national_id"
                    ) or None,
                    gender=request.data.get(
                        "gender"
                    ),
                    date_of_birth=request.data.get(
                        "date_of_birth"
                    ),
                )

            return Response(
                {
                    "message": (
                        "User account created successfully."
                    ),
                    "user": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    except IntegrityError as e:

        return Response(
            {
                "error": str(e)
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


# ============================================================
# LIST ALL USERS
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def UserList(request):

    if request.user.role != CustomUser.Role.SUPER_ADMIN:
        return Response(
            {
                "error": (
                    "Only the Super Admin can view "
                    "all users."
                )
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    users = CustomUser.objects.order_by("id")

    # ========================================================
    # QUERY PARAMETER FILTERS
    #
    # ?role=TEACHER
    # ?is_active=true
    # ?search=name/email/username
    # ========================================================

    role = request.query_params.get("role")
    is_active = request.query_params.get("is_active")
    search = request.query_params.get("search")

    if role:
        users = users.filter(
            role=role.upper()
        )

    if is_active is not None:
        users = users.filter(
            is_active=is_active.lower()
            in ["true", "1", "yes"]
        )

    if search:
        users = users.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
            | Q(username__icontains=search)
            | Q(phone_number__icontains=search)
        )

    # PAGINATION
    # ----------
    # This returned EVERY user in the system, fully serialized, in one
    # response - DEFAULT_PAGINATION_CLASS does not apply to @api_view
    # function views.
    #
    # Backward compatible: the paginated envelope is only used when the
    # caller asks for it (?page= or ?page_size=). Existing frontend
    # code that expects a bare array keeps working; new code can opt in.
    paginator = StandardResultsSetPagination()

    if "page" in request.query_params or "page_size" in request.query_params:
        page = paginator.paginate_queryset(users, request)
        serializer = UserSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    serializer = UserSerializer(
        users,
        many=True,
    )

    return Response(
        serializer.data,
        status=status.HTTP_200_OK,
    )


# ============================================================
# USER DETAILS
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def UserDetail(request, id):

    if request.user.role != CustomUser.Role.SUPER_ADMIN:
        return Response(
            {
                "error": (
                    "Only the Super Admin can view "
                    "user details."
                )
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    user = get_object_or_404(
        CustomUser,
        id=id,
    )

    serializer = UserSerializer(user)

    return Response(
        serializer.data,
        status=status.HTTP_200_OK,
    )


# ============================================================
# UPDATE USER
# ============================================================

@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def UpdateUser(request, id):

    # --------------------------------------------------------
    # Only Super Admin can update users
    # --------------------------------------------------------

    if request.user.role != CustomUser.Role.SUPER_ADMIN:
        return Response(
            {
                "error": (
                    "Only the Super Admin can update "
                    "user accounts."
                )
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        user = CustomUser.objects.get(id=id)

    except CustomUser.DoesNotExist:

        return Response(
            {
                "error": "User not found."
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    username = request.data.get(
        "username",
        user.username,
    )

    first_name = request.data.get(
        "first_name",
        user.first_name,
    )

    last_name = request.data.get(
        "last_name",
        user.last_name,
    )

    email = request.data.get(
        "email",
        user.email,
    )

    phone_number = request.data.get(
        "phone_number",
        user.phone_number,
    )

    role = request.data.get(
        "role",
        user.role,
    )

    is_active = request.data.get(
        "is_active",
        user.is_active,
    )

    # --------------------------------------------------------
    # Check username uniqueness
    # --------------------------------------------------------

    if (
        CustomUser.objects
        .exclude(id=user.id)
        .filter(username=username)
        .exists()
    ):
        return Response(
            {
                "error": "Username already exists."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # --------------------------------------------------------
    # Check email uniqueness
    # --------------------------------------------------------

    if (
        CustomUser.objects
        .exclude(id=user.id)
        .filter(email=email)
        .exists()
    ):
        return Response(
            {
                "error": "Email already exists."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    old_role = user.role

    user.username = username
    user.first_name = first_name
    user.last_name = last_name
    user.email = email
    user.phone_number = phone_number
    user.role = role
    user.is_active = is_active

    user.save()

    # ========================================================
    # ROLE CHANGE
    # ========================================================

    profile_warning = None

    if old_role != role:

        # ----------------------------------------------------
        # Remove old profile
        # ----------------------------------------------------

        old_profile_model = PROFILE_MODELS_BY_ROLE.get(
            old_role
        )

        if old_profile_model:
            old_profile_model.objects.filter(
                user=user
            ).delete()

        # ----------------------------------------------------
        # Create new profile
        # ----------------------------------------------------

        new_profile_model = PROFILE_MODELS_BY_ROLE.get(
            role
        )

        if new_profile_model:

            # Use a nested transaction so that an IntegrityError
            # here does not break the outer atomic transaction.
            try:
                with transaction.atomic():
                    new_profile_model.objects.get_or_create(
                        user=user
                    )

            except IntegrityError:

                profile_warning = (
                    f"User role changed to {role}, but the "
                    f"matching profile could not be "
                    f"auto-created because required fields "
                    f"are missing. Please complete the "
                    f"{new_profile_model.__name__} details "
                    f"for this user."
                )

    # ========================================================
    # RESPONSE
    # ========================================================

    response_data = {
        "message": "User updated successfully.",
        "user": {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone_number": user.phone_number,
            "role": user.role,
            "is_active": user.is_active,
        },
    }

    if profile_warning:
        response_data["profile_warning"] = profile_warning

    return Response(
        response_data,
        status=status.HTTP_200_OK,
    )


# ============================================================
# DELETE / DEACTIVATE USER
# ============================================================

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def DeleteUser(request, id):

    if request.user.role != CustomUser.Role.SUPER_ADMIN:
        return Response(
            {
                "error": (
                    "Only the Super Admin can deactivate "
                    "user accounts."
                )
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    user = get_object_or_404(
        CustomUser,
        id=id,
    )

    # --------------------------------------------------------
    # Prevent deleting yourself
    # --------------------------------------------------------

    if user.id == request.user.id:
        return Response(
            {
                "error": (
                    "You cannot deactivate your own account."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.is_active = False
    user.save()

    return Response(
        {
            "message": (
                "User account has been deactivated "
                "successfully."
            )
        },
        status=status.HTTP_200_OK,
    )


# ============================================================
# RESTORE DEACTIVATED USER
# ============================================================

@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def RestoreUser(request, id):

    if request.user.role != CustomUser.Role.SUPER_ADMIN:
        return Response(
            {
                "error": (
                    "Only the Super Admin can restore "
                    "user accounts."
                )
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    user = get_object_or_404(
        CustomUser,
        id=id,
    )

    user.is_active = True
    user.save()

    return Response(
        {
            "message": (
                "User account restored successfully."
            )
        },
        status=status.HTTP_200_OK,
    )


# ============================================================
# CHANGE PASSWORD
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ChangePassword(request):

    user = request.user

    old_password = request.data.get(
        "old_password"
    )

    new_password = request.data.get(
        "new_password"
    )

    confirm_password = request.data.get(
        "confirm_password"
    )

    # --------------------------------------------------------
    # Required fields
    # --------------------------------------------------------

    if (
        not old_password
        or not new_password
        or not confirm_password
    ):
        return Response(
            {
                "error": (
                    "Old password, new password and "
                    "confirm password are required."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # --------------------------------------------------------
    # Check old password
    # --------------------------------------------------------

    if not user.check_password(old_password):

        return Response(
            {
                "error": "Old password is incorrect."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # --------------------------------------------------------
    # Check confirmation
    # --------------------------------------------------------

    if new_password != confirm_password:

        return Response(
            {
                "error": "New passwords do not match."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # --------------------------------------------------------
    # Prevent password reuse
    # --------------------------------------------------------

    if user.check_password(new_password):

        return Response(
            {
                "error": (
                    "New password must be different "
                    "from the old password."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # --------------------------------------------------------
    # Validate password
    # --------------------------------------------------------

    try:

        validate_password(
            new_password,
            user,
        )

    except ValidationError as e:

        return Response(
            {
                "error": e.messages
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # --------------------------------------------------------
    # Save password
    # --------------------------------------------------------

    user.set_password(new_password)
    user.save()

    return Response(
        {
            "message": (
                "Password changed successfully."
            )
        },
        status=status.HTTP_200_OK,
    )


# ============================================================
# RESET USER PASSWORD
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ResetPassword(request, id):

    # --------------------------------------------------------
    # Only Super Admin can reset passwords
    # --------------------------------------------------------

    if request.user.role != CustomUser.Role.SUPER_ADMIN:
        return Response(
            {
                "error": (
                    "Only the Super Admin can reset "
                    "user passwords."
                )
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    user = get_object_or_404(
        CustomUser,
        id=id,
    )

    new_password = request.data.get(
        "new_password"
    )

    confirm_password = request.data.get(
        "confirm_password"
    )

    # --------------------------------------------------------
    # Required fields
    # --------------------------------------------------------

    if not new_password or not confirm_password:

        return Response(
            {
                "error": (
                    "New password and confirm password "
                    "are required."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # --------------------------------------------------------
    # Check confirmation
    # --------------------------------------------------------

    if new_password != confirm_password:

        return Response(
            {
                "error": "Passwords do not match."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # --------------------------------------------------------
    # Prevent reuse
    # --------------------------------------------------------

    if user.check_password(new_password):

        return Response(
            {
                "error": (
                    "The new password cannot be the same "
                    "as the current password."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # --------------------------------------------------------
    # Validate password
    # --------------------------------------------------------

    try:

        validate_password(
            new_password,
            user,
        )

    except ValidationError as e:

        return Response(
            {
                "error": e.messages
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # --------------------------------------------------------
    # Save password
    # --------------------------------------------------------

    user.set_password(new_password)
    user.save()

    return Response(
        {
            "message": (
                f"Password for '{user.username}' "
                "has been reset successfully."
            )
        },
        status=status.HTTP_200_OK,
    )


# ============================================================
# ACADEMIC COORDINATOR PROFILE
# ============================================================

class AcademicCoordinatorProfileView(
    generics.RetrieveUpdateAPIView
):

    serializer_class = AcademicCoordinatorProfileSerializer

    permission_classes = [
        permissions.IsAuthenticated
    ]

    def get_object(self):

        instance = (
            AcademicCoordinatorProfile.objects
            .filter(user=self.request.user)
            .first()
        )

        if instance is None:
            raise NotFound(
                "Academic coordinator profile not found."
            )

        return instance


# ============================================================
# TEACHER PROFILE
# ============================================================

class TeacherProfileView(
    generics.RetrieveUpdateAPIView
):

    serializer_class = TeacherProfileSerializer

    permission_classes = [
        permissions.IsAuthenticated
    ]

    def get_object(self):

        instance = (
            TeacherProfile.objects
            .filter(user=self.request.user)
            .first()
        )

        if instance is None:
            raise NotFound(
                "Teacher profile not found."
            )

        return instance


# ============================================================
# ACCOUNTANT PROFILE
# ============================================================

class AccountantProfileView(
    generics.RetrieveUpdateAPIView
):

    serializer_class = AccountantProfileSerializer

    permission_classes = [
        permissions.IsAuthenticated
    ]

    def get_object(self):

        instance = (
            AccountantProfile.objects
            .filter(user=self.request.user)
            .first()
        )

        if instance is None:
            raise NotFound(
                "Accountant profile not found."
            )

        return instance


# ============================================================
# PARENT PROFILE
# ============================================================

class ParentProfileView(
    generics.RetrieveUpdateAPIView
):

    serializer_class = ParentProfileSerializer

    permission_classes = [
        permissions.IsAuthenticated
    ]

    def get_object(self):

        instance = (
            ParentProfile.objects
            .filter(user=self.request.user)
            .first()
        )

        if instance is None:
            raise NotFound(
                "Parent profile not found."
            )

        return instance


# ============================================================
# STUDENT PROFILE
# ============================================================
class StudentProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = StudentProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        pk = self.kwargs.get("pk")

        if pk:
            # ✅ LOOKUP BY USER ID — matches what your frontend sends!
            try:
                return StudentProfile.objects.get(user__pk=pk)
            except StudentProfile.DoesNotExist:
                raise NotFound("Student profile not found for this user.")
        else:
            # Return logged-in user's own profile
            try:
                return StudentProfile.objects.get(user=self.request.user)
            except StudentProfile.DoesNotExist:
                raise NotFound("Student profile not found.")

# ============================================================
# LIST ALL PARENTS
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ParentList(request):

    # --------------------------------------------------------
    # Only staff roles that legitimately need the complete
    # parent/child roster may access this endpoint.
    # --------------------------------------------------------

    allowed_roles = [
        CustomUser.Role.SUPER_ADMIN,
        CustomUser.Role.ACADEMIC_COORDINATOR,
        CustomUser.Role.ACCOUNTANT,
    ]

    if request.user.role not in allowed_roles:

        return Response(
            {
                "error": (
                    "You do not have permission "
                    "to view the parent list."
                )
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    parents = (
        ParentProfile.objects
        .select_related("user")
        .prefetch_related("children")
        .order_by(
            "user__first_name",
            "user__last_name",
        )
    )

    # ========================================================
    # QUERY PARAMETER SEARCH
    #
    # ?search=name/phone/email
    # ========================================================

    search = request.query_params.get(
        "search"
    )

    if search:

        parents = parents.filter(
            Q(
                user__first_name__icontains=search
            )
            | Q(
                user__last_name__icontains=search
            )
            | Q(
                user__phone_number__icontains=search
            )
            | Q(
                user__email__icontains=search
            )
        )

    serializer = ParentProfileSerializer(
        parents,
        many=True,
    )

    return Response(
        serializer.data,
        status=status.HTTP_200_OK,
    )


# ============================================================
# LIST ALL TEACHER PROFILES
# ============================================================
#
# TeacherProfileView:
#     Returns ONLY the logged-in teacher's profile.
#
# TeacherProfilesListView:
#     Returns ALL registered teacher profiles.
#
# Used by:
#     - Super Admin
#     - Academic Coordinator
#
# ============================================================

class TeacherProfilesListView(
    generics.ListAPIView
):

    serializer_class = TeacherProfileSerializer

    permission_classes = [
        permissions.IsAuthenticated
    ]

    def get_queryset(self):

        # ----------------------------------------------------
        # Only Super Admin and Academic Coordinator can
        # access the complete teacher list.
        # ----------------------------------------------------

        allowed_roles = [
            CustomUser.Role.SUPER_ADMIN,
            CustomUser.Role.ACADEMIC_COORDINATOR,
        ]

        if self.request.user.role not in allowed_roles:

            return TeacherProfile.objects.none()

        # ----------------------------------------------------
        # Return all teacher profiles.
        # ----------------------------------------------------

        return (
            TeacherProfile.objects
            .select_related("user")
            .order_by(
                "user__first_name",
                "user__last_name",
                "id",
            )
        )

    # ========================================================
    # QUERY PARAMETER FILTERS
    #
    # ?search=name/employee_number
    # ?gender=Male/Female
    # ========================================================

    def filter_queryset(self, queryset):

        queryset = super().filter_queryset(
            queryset
        )

        search = self.request.query_params.get(
            "search"
        )

        gender = self.request.query_params.get(
            "gender"
        )

        if search:

            queryset = queryset.filter(
                Q(
                    user__first_name__icontains=search
                )
                | Q(
                    user__last_name__icontains=search
                )
                | Q(
                    employee_number__icontains=search
                )
                | Q(
                    user__username__icontains=search
                )
            )

        if gender:

            queryset = queryset.filter(
                gender=gender
            )

        return queryset