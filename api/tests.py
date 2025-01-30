from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class RouteOptimizerTest(APITestCase):
    def setUp(self):
        self.url = reverse("find_optimal_route")

    def test_no_stops_needed(self):
        sample_data = {"start": "32.92599,-99.22488", "end": "32.92599,-100.22488"}

        response = self.client.post(self.url, sample_data)

        # check response code
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check stops returned
        self.assertEqual(response.data["stops"], [])

        # check total distance
        self.assertEqual(response.data["total_distance_meters"], 124468.7)

    def test_unable_to_find_stations_on_route(self):
        sample_data = {"start": "32.92599,-99.22488", "end": "32.92599,-110.22488"}

        response = self.client.post(self.url, sample_data)

        # check response code
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        # check error
        self.assertEqual(
            response.data["detail"], "Unable to find fueling stations in route"
        )

    def test_stops_needed(self):
        sample_data = {"start": "32.92599,-98.72488", "end": "32.92599,-105.92488"}

        response = self.client.post(self.url, sample_data)

        # check response code
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check stops returned
        self.assertEqual(
            response.data["stops"],
            [
                {
                    "distance": 35969,
                    "price": 3.00733333,
                    "Truckstop_Name": "WOODSHED OF BIG CABIN",
                    "Address": "I-44, EXIT 283 & US-69",
                    "lat": 32.75175,
                    "lng": -98.90258,
                }
            ],
        )

        # check total distance
        self.assertEqual(response.data["total_distance_meters"], 807311.3)

        # check total cost
        self.assertEqual(response.data["total_cost"], 150.85986459379134)
