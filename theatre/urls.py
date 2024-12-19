from rest_framework import routers
from django.urls import path, include
from theatre.views import (
    GenreViewSet,
    ActorViewSet,
    PlayViewSet,
)

router = routers.DefaultRouter()
router.register("genres", GenreViewSet)
router.register("actors", ActorViewSet)
router.register("plays", PlayViewSet)

urlpatterns = [
    path("", include(router.urls)),
]

app_name = "theatre"
