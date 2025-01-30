# Fuel Route Optimizer API

This is an Implementation of a route optimization API for trucks in the USA that aims to Optimize route taken by a truck to account for optimal fuel cost.

## How it works

![alt text](assests/graph.png)

1. The API calls for operroutesapi to find a route from origin to destination.
2. Calculate distance from route to fuel station to find nearby ones (candidate stops in yellow)
3. A greedy algorithim to select fueling stops for minimum cost (chosen stops in green).

## Implementation Details

1. OpenAPI docs upon running the api found at:
   `http://127.0.0.1:8000/api/docs`
   ![alt text](assests/docs.png)
1. Custom validation and serialization for Request and Response.
   `api/serializer.py`
1. Custom Exception handling.
   `api/exceptions.py`
1. Test cases for different outcomes.
   `api/tests.py`
1. Fromating and linting with ruff.
1. Dependancy managment with pipenv.

## How to Use

1. Create and activate python environment

2. Install pipenv `pip install pipenv`

3. Install dependencies `pipenv install`

4. Run the django app `python manage.py runserver`
