from datetime import datetime
from django.contrib.auth import get_user_model
from django.db.models import F, Count
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase, APIClient
from theatre.models import Play, TheatreHall, Performance, Genre, Actor
from theatre.serializers import (
    PlayListSerializer,
    PerformanceListSerializer,
    PerformanceSerializer,
    PerformanceDetailSerializer,
)


def sample_genre(**params):
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)
    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)
    return Actor.objects.create(**defaults)


def sample_theatre_hall(**params):
    defaults = {"name": "George", "rows": 10, "seats_in_row": 10}
    defaults.update(params)
    return TheatreHall.objects.create(**defaults)


def sample_play(**params):
    defaults = {
        "title": "Sample play",
        "description": "Sample description",
    }
    defaults.update(params)
    return Play.objects.create(**defaults)


def sample_performance(**params):
    theatre_hall = TheatreHall.objects.create(
        name="Blue", rows=20, seats_in_row=20
    )
    defaults = {
        "play": None,
        "theatre_hall": theatre_hall,
        "show_time": "2022-06-02 14:00:00",
    }
    defaults.update(params)
    return Performance.objects.create(**defaults)


def play_detail_url(play_id):
    return reverse("theatre:play-detail", args=[play_id])


PLAY_URL = reverse("theatre:play-list")
PERFORMANCE_URL = reverse("theatre:performance-list")


class UnauthenticatedTests(APITestCase):
    def setUp(self):
        self.client = APIClient()

    def test_unauthenticated_play(self):
        res = self.client.get(PLAY_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedTheatreApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass",
        )
        self.client.force_authenticate(self.user)

    def test_list_plays(self):
        sample_play()
        play1 = sample_play(title="Sample", description="test")
        genre1 = Genre.objects.create(name="Genre 1")
        play1.genres.add(genre1)
        res = self.client.get(PLAY_URL)
        plays = Play.objects.order_by("id")
        serializer = PlayListSerializer(plays, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_filter_plays_by_genres(self):
        genre1 = Genre.objects.create(name="Genre 1")
        genre2 = Genre.objects.create(name="Genre 2")
        play1 = sample_play(title="Movie 1", description="test")
        play2 = sample_play(title="Movie 2", description="test")
        play1.genres.add(genre1)
        play2.genres.add(genre2)
        play3 = sample_play(title="Play without genres and actors", description="test")
        res = self.client.get(PLAY_URL, {"genres": f"{genre1.id},{genre2.id}"})
        serializer1 = PlayListSerializer(play1)
        serializer2 = PlayListSerializer(play2)
        serializer3 = PlayListSerializer(play3)
        self.assertIn(serializer1.data, res.data["results"])
        self.assertIn(serializer2.data, res.data["results"])
        self.assertNotIn(serializer3.data, res.data["results"])

    def test_filter_plays_by_actors(self):
        actor1 = Actor.objects.create(first_name="Actor 1", last_name="Wilson")
        actor2 = Actor.objects.create(first_name="Actor 2", last_name="Wilson")
        play1 = sample_play(title="Movie 1", description="test")
        play2 = sample_play(title="Movie 2", description="test")
        play1.actors.add(actor1)
        play2.actors.add(actor2)
        play3 = sample_play(title="Play without genres and actors", description="test")
        res = self.client.get(PLAY_URL, {"actors": f"{actor1.id},{actor2.id}"})
        serializer1 = PlayListSerializer(play1)
        serializer2 = PlayListSerializer(play2)
        serializer3 = PlayListSerializer(play3)
        self.assertIn(serializer1.data, res.data["results"])
        self.assertIn(serializer2.data, res.data["results"])
        self.assertNotIn(serializer3.data, res.data["results"])


class PerformanceViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass",
        )
        self.client.force_authenticate(self.user)
        self.play = Play.objects.create(
            title="Hamlet", description="A tragedy by Shakespeare"
        )
        self.theatre_hall = TheatreHall.objects.create(
            name="Main Hall", rows=10, seats_in_row=10
        )
        self.performance = Performance.objects.create(
            play=self.play, theatre_hall=self.theatre_hall, show_time=datetime.now()
        )

    def test_list_performances(self):
        res = self.client.get(PERFORMANCE_URL)
        performances = Performance.objects.annotate(
            tickets_available=(
                    F("theatre_hall__rows") * F("theatre_hall__seats_in_row")
                    - Count("tickets_performance")
            )
        ).order_by("id")
        serializer = PerformanceListSerializer(performances, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_filter_performances_by_play(self):
        res = self.client.get(PERFORMANCE_URL, {"play": self.play.id})
        performances = Performance.objects.filter(play=self.play).order_by("id")
        serializer = PerformanceListSerializer(performances, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_performances_by_theatre_hall(self):
        res = self.client.get(PERFORMANCE_URL, {"hall": self.theatre_hall.id})
        performances = Performance.objects.filter(
            theatre_hall=self.theatre_hall
        ).annotate(
            tickets_available=(
                    F("theatre_hall__rows") * F("theatre_hall__seats_in_row")
                    - Count("tickets_performance")
            )
        )
        serializer = PerformanceListSerializer(performances, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_filter_performances_by_date(self):
        date = self.performance.show_time.date()
        res = self.client.get(PERFORMANCE_URL, {"date": date})
        performances = Performance.objects.filter(show_time__date=date).annotate(
            tickets_available=(
                    F("theatre_hall__rows") * F("theatre_hall__seats_in_row")
                    - Count("tickets_performance")
            )
        )
        serializer = PerformanceListSerializer(performances, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)
