from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.db.models import F, Count
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase, APIClient
from theatre.models import (
    Play,
    TheatreHall,
    Performance,
    Genre,
    Actor,
    Reservation,
    Ticket,
)
from theatre.serializers import (
    PlayListSerializer,
    PerformanceListSerializer,
)


def sample_genre(**params):
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)
    return Genre.objects.get_or_create(**defaults)[0]


def sample_actor(**params):
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)
    return Actor.objects.get_or_create(**defaults)[0]


def sample_theatre_hall(**params):
    defaults = {"name": "George", "rows": 10, "seats_in_row": 10}
    defaults.update(params)
    return TheatreHall.objects.get_or_create(**defaults)[0]


def sample_play(**params):
    defaults = {
        "title": "Sample play",
        "description": "Sample description",
    }
    defaults.update(params)
    return Play.objects.get_or_create(**defaults)[0]


def sample_performance(**params):
    theatre_hall = sample_theatre_hall()
    play = sample_play()
    defaults = {
        "play": play,
        "theatre_hall": theatre_hall,
        "show_time": "2022-06-02 14:00:00",
    }
    defaults.update(params)
    return Performance.objects.get_or_create(**defaults)[0]

    def sample_reservation(**params):
        user = get_user_model().objects.create(username="test", password="PASSWORD")
        defaults = {
            "user": user,
        }
        defaults.update(params)
        return Reservation.objects.get_or_create(**defaults)[0]

    def sample_ticket(**params):
        performance = sample_performance()
        reservation = sample_reservation()
        defaults = {
            "row": 1,
            "seat": 1,
            "performance": performance,
            "reservation": reservation,
        }
        defaults.update(params)
        return Ticket.objects.get_or_create(**defaults)[0]


def play_detail_url(play_id):
    return reverse(
        "theatre:play-detail",
        args=[play_id]
    )


PLAY_URL = reverse("theatre:play-list")
PERFORMANCE_URL = reverse("theatre:performance-list")
TICKET_URL = reverse("theatre:ticket-list")


class UnauthenticatedTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@test.com",
            "testpass",
        )
        self.reservation = Reservation.objects.create(user=self.user)

    def test_unauthenticated_play(self):
        res = self.client.get(PLAY_URL)
        self.assertEqual(res.status_code,
                         status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_reservations(self):
        res = self.client.get(reverse("theatre:reservation-list"))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_tickets(self):
        res = self.client.get(reverse("theatre:ticket-list"))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AuthenticatedUserPlaysTests(APITestCase):
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


class AuthenticatedUserPerformancesTests(APITestCase):
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
        performances = Performance.objects.filter(play=self.play).annotate(
            tickets_available=(
                    F("theatre_hall__rows") * F("theatre_hall__seats_in_row")
                    - Count("tickets_performance")
            )
        )
        serializer = PerformanceListSerializer(performances, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

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

    def test_user_create_put_patch_delete_performance(self):
        performance = sample_performance()
        url = reverse("theatre:performance-detail", args=[performance.id])
        show_time = datetime.now().replace(microsecond=0)
        payload = {
            "play": self.play.id,
            "theatre_hall": self.theatre_hall.id,
            "show_time": show_time,
        }
        res = self.client.post(PERFORMANCE_URL, payload)
        self.assertEqual(
            res.status_code, status.HTTP_403_FORBIDDEN, msg="CREATE failed!"
        )
        res = self.client.put(url, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN, msg="PUT failed!")
        payload = {
            "play": self.play.id,
            "theatre_hall": self.theatre_hall.id,
        }
        res = self.client.delete(url)
        self.assertEqual(
            res.status_code, status.HTTP_403_FORBIDDEN, msg="DELETE failed!"
        )


class AuthenticatedAdminPerformancesTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@test.com",
            "testpass",
        )
        self.client.force_authenticate(self.user)
        self.play = sample_play(title="Hamlet",
                                description="A tragedy by Shakespeare")
        self.theatre_hall = sample_theatre_hall(
            name="Main Hall", rows=10, seats_in_row=10
        )
        self.performance = sample_performance(
            play=self.play, theatre_hall=self.theatre_hall, show_time=datetime.now()
        )

    def test_admin_create_put_patch_delete_performance(self):
        hall = sample_theatre_hall(name="Main rest11",
                                   rows=11, seats_in_row=10)
        show_time = datetime.now().replace(microsecond=0)
        payload = {
            "play": self.play.id,
            "theatre_hall": self.theatre_hall.id,
            "show_time": show_time,
        }
        show_time_plus_5 = show_time + timedelta(hours=5)
        updating_payload = {
            "play": self.play.id,
            "theatre_hall": self.theatre_hall.id,
            "show_time": show_time_plus_5,
        }
        res = self.client.post(PERFORMANCE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, msg="CREATE failed!")
        url = reverse("theatre:performance-detail",
                      args=[self.performance.id])
        res = self.client.put(url, updating_payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK,
                         msg="PUT failed!")
        payload = {
            "play": self.play.id,
            "theatre_hall": hall.id,
        }
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK,
                         msg="PATCH failed!")
        res = self.client.delete(url)
        self.assertEqual(
            res.status_code, status.HTTP_204_NO_CONTENT,
            msg="DELETE failed!"
        )


class ReservationViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("user@test.com", "testpass")
        self.staff_user = get_user_model().objects.create_user(
            "staff@test.com", "testpass"
        )
        self.staff_user.is_staff = True
        self.staff_user.save()
        self.reservation = Reservation.objects.create(user=self.user)
        self.reservation_admin = Reservation.objects.create(user=self.staff_user)
        self.url = reverse("theatre:reservation-detail", args=[self.reservation.id])

    def test_get_queryset_as_staff_user(self):
        """Test that a staff user can retrieve all reservations"""
        self.client.force_authenticate(self.staff_user)
        res = self.client.get(reverse("theatre:reservation-list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), Reservation.objects.count())

    def test_get_queryset_as_authenticated_user(self):
        """Test that an authenticated user can retrieve their own reservations"""
        self.client.force_authenticate(self.user)
        res = self.client.get(reverse("theatre:reservation-list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(res.data["results"]), Reservation.objects.filter(user=self.user).count()
        )


class AuthenticatedUserTicketTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("user@test.com", "testpass")
        self.client.force_authenticate(self.user)
        self.another_user = get_user_model().objects.create_user(
            "another_user@test.com", "testpass"
        )
        self.reservation = Reservation.objects.create(user=self.user)
        self.another_reservation = Reservation.objects.create(user=self.another_user)
        self.theatre_hall = sample_theatre_hall()
        self.play = sample_play(title="Hamlet", description="A tragedy")
        self.performance = sample_performance(
            play=self.play, theatre_hall=self.theatre_hall, show_time=datetime.now()
        )
        self.ticket = Ticket.objects.create(
            row=2, seat=3, performance=self.performance, reservation=self.reservation
        )
        self.another_ticket = Ticket.objects.create(
            row=3,
            seat=4,
            performance=self.performance,
            reservation=self.another_reservation,
        )

    def test_retrieve_ticket_as_authenticated_user(self):
        url = reverse("theatre:ticket-detail", args=[self.ticket.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.ticket.id)

    def test_list_tickets_as_authenticated_user(self):
        res = self.client.get(TICKET_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)

    def test_create_ticket_as_authenticated_user(self):
        payload = {
            "row": 4,
            "seat": 2,
            "performance": self.performance.id,
            "reservation": self.reservation.id,
        }
        res = self.client.post(TICKET_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        payload = {
            "row": 4,
            "seat": 4,
            "performance": self.performance.id,
            "reservation": self.another_reservation.id,
        }
        res = self.client.post(TICKET_URL, payload)
        self.assertEqual(
            res.status_code,
            status.HTTP_403_FORBIDDEN,
            msg="Not allowed create tickets with another user on reservation",
        )


class AuthenticatedUserTicketTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("user@test.com", "testpass")
        self.client.force_authenticate(self.user)
        self.another_user = get_user_model().objects.create_user(
            "another_user@test.com", "testpass"
        )
        self.reservation = Reservation.objects.create(user=self.user)
        self.another_reservation = Reservation.objects.create(user=self.another_user)
        self.theatre_hall = sample_theatre_hall()
        self.play = sample_play(title="Hamlet", description="A tragedy")
        self.performance = sample_performance(
            play=self.play, theatre_hall=self.theatre_hall, show_time=datetime.now()
        )
        self.ticket = Ticket.objects.create(
            row=2,
            seat=3,
            performance=self.performance,
            reservation=self.reservation,
        )
        self.another_ticket = Ticket.objects.create(
            row=3,
            seat=4,
            performance=self.performance,
            reservation=self.another_reservation,
        )

    def test_retrieve_ticket_as_authenticated_user(self):
        url = reverse("theatre:ticket-detail", args=[self.ticket.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.ticket.id)

    def test_list_tickets_as_authenticated_user(self):
        res = self.client.get(TICKET_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)

    def test_create_ticket_as_authenticated_user(self):
        payload = {
            "row": 4,
            "seat": 2,
            "performance": self.performance.id,
            "reservation": self.reservation.id,
        }
        res = self.client.post(TICKET_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        payload = {
            "row": 4,
            "seat": 4,
            "performance": self.performance.id,
            "reservation": self.another_reservation.id,
        }
        res = self.client.post(TICKET_URL, payload)
        self.assertEqual(
            res.status_code,
            status.HTTP_403_FORBIDDEN,
            msg="Not allowed create tickets with another user on reservation",
        )

    def test_delete_ticket_as_authenticated_user(self):
        url = reverse("theatre:ticket-detail", args=[self.ticket.id])
        res = self.client.delete(url)
        self.assertEqual(
            res.status_code, status.HTTP_204_NO_CONTENT, msg="Deleted as owner"
        )
        self.assertFalse(Ticket.objects.filter(id=self.ticket.id).exists())
        url = reverse("theatre:ticket-detail", args=[self.another_ticket.id])
        res = self.client.delete(url)
        self.assertEqual(
            res.status_code, status.HTTP_404_NOT_FOUND, msg="Deleted as not owner"
        )
        self.assertTrue(Ticket.objects.filter(id=self.another_ticket.id).exists())


class AuthenticatedAdminTicketTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "user@test.com", "testpass"
        )
        self.client.force_authenticate(self.user)
        self.another_user = get_user_model().objects.create_user(
            "another_user@test.com", "testpass"
        )
        self.reservation = Reservation.objects.create(user=self.user)
        self.another_reservation = Reservation.objects.create(user=self.another_user)
        self.theatre_hall = sample_theatre_hall()
        self.play = sample_play(title="Hamlet", description="A tragedy")
        self.performance = sample_performance(
            play=self.play, theatre_hall=self.theatre_hall, show_time=datetime.now()
        )
        self.ticket = Ticket.objects.create(
            row=2, seat=3, performance=self.performance, reservation=self.reservation
        )
        self.another_ticket = Ticket.objects.create(
            row=3,
            seat=4,
            performance=self.performance,
            reservation=self.another_reservation,
        )

    def test_retrieve_ticket_as_authenticated_admin(self):
        url = reverse("theatre:ticket-detail", args=[self.ticket.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.ticket.id)

    def test_list_tickets_as_authenticated_admin(self):
        res = self.client.get(TICKET_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)

    def test_create_ticket_as_authenticated_admin(self):
        payload = {
            "row": 4,
            "seat": 2,
            "performance": self.performance.id,
            "reservation": self.reservation.id,
        }
        res = self.client.post(TICKET_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        payload = {
            "row": 4,
            "seat": 4,
            "performance": self.performance.id,
            "reservation": self.another_reservation.id,
        }
        res = self.client.post(TICKET_URL, payload)
        self.assertEqual(
            res.status_code,
            status.HTTP_201_CREATED,
            msg="Allowed create tickets with another user on reservation",
        )

    def test_delete_ticket_as_staff_user(self):
        url = reverse("theatre:ticket-detail", args=[self.ticket.id])
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Ticket.objects.filter(id=self.ticket.id).exists())
        url = reverse("theatre:ticket-detail", args=[self.another_ticket.id])
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Ticket.objects.filter(id=self.another_ticket.id).exists())
