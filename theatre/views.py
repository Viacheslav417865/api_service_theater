from datetime import datetime
from django.shortcuts import render
from rest_framework import viewsets, filters
from rest_framework.exceptions import PermissionDenied

from theatre.models import (
    Actor,
    Genre,
    Play,
    TheatreHall,
    Performance,
    Reservation,
    Ticket,
)
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


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]


class PlayViewSet(viewsets.ModelViewSet):
    queryset = Play.objects.prefetch_related(
        "actors",
        "genres",
    )
    filter_backends = [filters.SearchFilter]
    search_fields = ["title"]

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


class TheatreHallViewSet(viewsets.ModelViewSet):
    queryset = TheatreHall.objects.all()
    serializer_class = TheatreHallSerializer


class PerformanceViewSet(viewsets.ModelViewSet):
    queryset = Performance.objects.select_related(
        "play",
        "theatre_hall",
    )

    def get_queryset(self):
        play_id = self.request.query_params.get(
            "play"
        )
        theatre_hall_id = self.request.query_params.get(
            "hall"
        )
        date = self.request.query_params.get(
            "date"
        )
        queryset = self.queryset
        if play_id:
            queryset = queryset.filter(
                play_id=int(play_id)
            )
        if theatre_hall_id:
            queryset = queryset.filter(
                theatre_hall_id=int(theatre_hall_id)
            )
        if date:
            date = datetime.strptime(
                date, "%Y-%m-%d").date()
            queryset = queryset.filter(
                show_time__date=date
            )
        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PerformanceDetailSerializer
        if self.action == "list":
            return PerformanceListSerializer
        return PerformanceSerializer


class ReservationViewSet(viewsets.ModelViewSet):
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
            "You do not have permission "
            "to access this resource."
        )


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
            return queryset.filter(reservation__user=self.request.user)
        raise PermissionDenied(
            "You do not have permission"
            " to access this resource."
        )
