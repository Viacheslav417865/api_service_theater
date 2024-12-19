from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.serializers import SlugRelatedField
from theatre.models import (
    Actor,
    Genre,
    Play,
    TheatreHall,
    Performance,
    Reservation,
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
        if value <= 0:
            raise serializers.ValidationError(
                "The number of "
                "rows must be greater than zero."
            )
        return value

    def validate_seats_in_row(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "The number of seats "
                "per row must be greater than zero."
            )
        return value


class PerformanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Performance
        fields = ("id", "play", "theatre_hall", "show_time")


class PerformanceDetailSerializer(PerformanceSerializer):
    play = PlayDetailSerializer()
    theatre_hall = TheatreHallSerializer()


class PerformanceListSerializer(PerformanceSerializer):
    play = SlugRelatedField(read_only=True, slug_field="title")
    theatre_hall = SlugRelatedField(
        read_only=True,
        slug_field="name",
    )


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ("id", "username", "password", "is_staff")
        read_only_fields = ("is_staff",)
        extra_kwargs = {
            "password":
                {"write_only": True,
                 "min_length": 5}
        }

    def create(self, validated_data):
        return get_user_model().objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ("created_at", "user")
