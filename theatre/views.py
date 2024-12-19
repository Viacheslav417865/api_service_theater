from datetime import datetime
from django.db.models import F, Count
from rest_framework import viewsets, filters, mixins
from rest_framework.viewsets import GenericViewSet
from rest_framework.exceptions import PermissionDenied
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter

from theatre.models import (
    Actor,
    Genre,
    Play,
    TheatreHall,
    Performance,
    Reservation,
    Ticket,
)
from theatre.permissions import IsAdminOrIfAuthenticatedReadOnly
from theatre.serializers import (
    ActorSerializer,
    GenreSerializer,
    PlayListSerializer,
    PlayDetailSerializer,
    TheatreHallSerializer,
    PerformanceListSerializer,
    PerformanceDetailSerializer,
    PerformanceSerializer,
    PlaySerializer,
    ReservationSerializer,
    TicketSerializer,
    TicketDetailSerializer,
)


class ActorViewSet(viewsets.ModelViewSet):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["first_name", "last_name"]
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class PlayViewSet(viewsets.ModelViewSet):
    queryset = Play.objects.prefetch_related(
        "actors",
        "genres",
    )
    filter_backends = [filters.SearchFilter]
    search_fields = ["title"]
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @staticmethod
    def _params_to_ints(qs):
        return [int(str_id) for str_id in qs.split(",")]

    def get_queryset(self):
        genres = self.request.query_params.get("genres")
        actors = self.request.query_params.get("actors")
        queryset = self.queryset
        if genres:
            genres_ids = self._params_to_ints(genres)
            queryset = queryset.filter(
                genres__id__in=genres_ids
            )
        if actors:
            actors_ids = self._params_to_ints(actors)
            queryset = queryset.filter(
                actors__id__in=actors_ids
            )
        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PlayDetailSerializer
        if self.action == "list":
            return PlayListSerializer
        return PlaySerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "genres",
                type=OpenApiTypes.NUMBER,
                description="Filter by genres (ex. ?genres=2,1)",
                many=True,
            ),
            OpenApiParameter(
                "actors",
                type=OpenApiTypes.NUMBER,
                description="Filter by actors id (ex. ?actors=2,3)",
                many=True,
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request,
                            *args, **kwargs)


class TheatreHallViewSet(viewsets.ModelViewSet):
    queryset = TheatreHall.objects.all()
    serializer_class = TheatreHallSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class PerformanceViewSet(viewsets.ModelViewSet):
    queryset = Performance.objects.select_related(
        "play", "theatre_hall").annotate(
        tickets_available=(
                F("theatre_hall__rows") *
                F("theatre_hall__seats_in_row")
                - Count("tickets_performance")
        )
    )
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):
        play_id = self.request.query_params.get("play")
        theatre_hall_id = self.request.query_params.get(
            "hall"
        )
        date = self.request.query_params.get("date")

        queryset = self.queryset

        if play_id:
            queryset = queryset.filter(play_id=int(play_id))

        if theatre_hall_id:
            queryset = queryset.filter(
                theatre_hall_id=int(theatre_hall_id)
            )

        if date:
            date = datetime.strptime(
                date, "%Y-%m-%d").date()
            queryset = queryset.filter(show_time__date=date)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PerformanceDetailSerializer
        if self.action == "list":
            return PerformanceListSerializer
        return PerformanceSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "play_id",
                type=OpenApiTypes.INT,
                description="Filter by play id (ex. ?play=2)",
            ),
            OpenApiParameter(
                "theatre_hall_id",
                type=OpenApiTypes.INT,
                description=
                "Filter by theatre hall id (ex. ?hall=2)",
            ),
            OpenApiParameter(
                "date",
                type=OpenApiTypes.DATE,
                description=(
                        "Filter by datetime of performance " "("
                        "ex. ?date=2022-10-23)"
                ),
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class ReservationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    serializer_class = ReservationSerializer

    def get_queryset(self):
        queryset = Reservation.objects.prefetch_related(
            "user", "tickets_reservation"
        ).all()
        if self.request.user.is_staff:
            return queryset
        if self.request.user.is_authenticated:
            return queryset.filter(user=self.request.user)
        raise PermissionDenied(
            "You do not have "
            "permission to access this resource."
        )

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise PermissionDenied(
                "You must be "
                "authenticated to create a reservation."
            )
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        if (
                not self.request.user.is_authenticated
                or self.request.user != instance.user
                and not self.request.user.is_staff
        ):
            raise PermissionDenied(
                "You do not have "
                "permission to delete this reservation."
            )
        instance.delete()


class TicketViewSet(viewsets.ModelViewSet):

    def get_serializer_class(self):
        if self.action == "retrieve":
            return TicketDetailSerializer
        return TicketSerializer

    def get_queryset(self):
        queryset = Ticket.objects.select_related(
            "performance__play",
            "performance__theatre_hall",
            "reservation__user",
        ).all()
        if self.request.user.is_staff:
            return queryset
        if self.request.user.is_authenticated:
            return queryset.filter(
                reservation__user=self.request.user
            )
        raise PermissionDenied(
            "You do not have permission "
            "to access this resource."
        )

    def perform_create(self, serializer):
        reservation = serializer.validated_data["reservation"]
        if (
                not self.request.user.is_authenticated
                or self.request.user != reservation.user
                and not self.request.user.is_staff
        ):
            raise PermissionDenied(
                "You do not have permission"
                " to create a ticket for this reservation."
            )
        serializer.save()
