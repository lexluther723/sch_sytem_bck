from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ParentChildrenViewSet


router = DefaultRouter()

router.register(
    r"children",
    ParentChildrenViewSet,
    basename="parent-children"
)


urlpatterns = [
    path("", include(router.urls)),
]