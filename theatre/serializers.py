from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import SlugRelatedField
from theatre.models import (
    Actor,
    Genre,
    Play,
    TheatreHall,
    Performance,
    Reservation,
    Ticket,
)


class ActorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Actor
        fields = (
            "id",
            "first_name",
            "last_name",
        )


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ("id", "name")


class PlaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Play
        fields = (
            "id",
            "title",
            "description",
            "actors",
            "genres",
        )


class PlayListSerializer(PlaySerializer):
    actors = SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="full_name",
    )
    genres = SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="name",
    )


class PlayDetailSerializer(PlaySerializer):
    actors = ActorSerializer(many=True,
                             read_only=True)
    genres = GenreSerializer(many=True)


class TheatreHallSerializer(serializers.ModelSerializer):
    class Meta:
        model = TheatreHall
        fields = (
            "id",
            "name",
            "rows",
            "seats_in_row",
        )

    def validate_rows(self, value):
        if value <= 1:
            raise serializers.ValidationError(
                "The number of "
                "rows must be greater than zero."
            )
        return value

    def validate_seats_in_row(self, value):
        if value <= 1:
            raise serializers.ValidationError(
                "The number of seats "
                "per row must be greater than zero."
            )
        return value


class PerformanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Performance
        fields = ("id", "play",
                  "theatre_hall", "show_time")


class TicketSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        data = super(TicketSerializer, self).validate(attrs=attrs)
        Ticket.validate_ticket(
            attrs["row"],
            attrs["seat"],
            attrs["performance"].theatre_hall,
            ValidationError,
        )
        return data

    class Meta:
        model = Ticket
        fields = ("id", "row", "seat",
                  "performance", "reservation")


class TicketPerformanceSerializer(TicketSerializer):
    class Meta:
        model = Ticket
        fields = ("row", "seat")


class PerformanceDetailSerializer(PerformanceSerializer):
    play = PlayDetailSerializer()
    theatre_hall = TheatreHallSerializer()
    taken_seats = TicketPerformanceSerializer(
        source="tickets_performance",
        many=True,
        read_only=True,
    )

    class Meta:
        model = Performance
        fields = (
            "id",
            "play",
            "theatre_hall",
            "show_time",
            "taken_seats",
        )


class PerformanceListSerializer(PerformanceSerializer):
    play = SlugRelatedField(read_only=True, slug_field="title")
    theatre_hall = SlugRelatedField(
        read_only=True,
        slug_field="name",
    )
    tickets_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = Performance
        fields = (
            "id",
            "play",
            "theatre_hall",
            "show_time",
            "tickets_available",
        )


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ("id", "created_at", "user")


class TicketDetailSerializer(TicketSerializer):
    performance = PerformanceListSerializer()
    reservation = ReservationSerializer()
