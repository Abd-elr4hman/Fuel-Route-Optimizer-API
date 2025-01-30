from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import RouteException, StationException
from .serializer import (
    ErrorSerializer,
    RouteOptimizerResponseSerializer,
    RouteOptimizerSerializer,
)
from .utils import calculate_optimal_stops, find_stations_on_route, get_route


class RouteOptimizerView(APIView):
    @extend_schema(
        request=RouteOptimizerSerializer,
    )
    @extend_schema(
        responses={
            200: RouteOptimizerResponseSerializer,
            400: OpenApiResponse(description="Bad Request", response=ErrorSerializer),
            404: OpenApiResponse(description="Not Found", response=ErrorSerializer),
            500: OpenApiResponse(
                description="Internal Server Error", response=ErrorSerializer
            ),
        },
    )
    @extend_schema(
        examples=[
            OpenApiExample(
                "Valid Request-no stops needed",
                value={"start": "32.92599,-99.22488", "end": "32.92599,-100.22488"},
                request_only=True,
            ),
            OpenApiExample(
                "Unable to find fueling stations in route",
                value={"start": "32.92599,-99.22488", "end": "32.92599,-110.22488"},
                request_only=True,
            ),
            OpenApiExample(
                "Valid Request-stops needed",
                value={"start": "32.92599,-98.72488", "end": "32.92599,-105.92488"},
                request_only=True,
            ),
        ]
    )
    def post(self, request):
        # Input Validation
        serializer = RouteOptimizerSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Invalid input", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = serializer.validated_data
        start_coord = data["start"]
        end_address = data["end"]

        # route finding with openstreatroute
        try:
            line, route = get_route((start_coord, end_address))
        except Exception:
            raise RouteException()

        try:
            # find candidate stations on route
            stations = find_stations_on_route(line)

            # calculate optimal stops
            stops, total_cost = calculate_optimal_stops(
                stations, route["routes"][0]["summary"]["distance"]
            )
        except Exception:
            raise StationException()

        # calculate optimal stops
        stops, total_cost = calculate_optimal_stops(
            stations, route["routes"][0]["summary"]["distance"]
        )

        if stops is None:
            # no stations in range error
            raise StationException()

        # Build Response
        response_data = {
            "route": {
                "summary": route["routes"][0]["summary"],
                "segments": route["routes"][0]["segments"],
                "geometry": route["routes"][0]["geometry"],
            },
            "stops": stops,
            "total_cost": total_cost,
            "total_distance_meters": route["routes"][0]["summary"]["distance"],
        }

        # Validate Response Format
        response_serializer = RouteOptimizerResponseSerializer(data=response_data)
        if not response_serializer.is_valid():
            return Response(
                {
                    "error": "Invalid response format",
                    "details": response_serializer.errors,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(response_serializer.validated_data)
