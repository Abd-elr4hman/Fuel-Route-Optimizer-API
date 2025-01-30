from rest_framework import status
from rest_framework.exceptions import APIException


class RouteException(APIException):
    # Default status code
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    # Default error message
    default_detail = "Unable to calculate trip route at the moment."

    # Default error code (optional)
    # default_code = 'custom_error'

    def __init__(self, detail=None, code=None, status_code=None):
        """
        Override the constructor to allow custom status codes and details.
        """
        if detail is not None:
            self.detail = detail
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        super().__init__(detail, code)


class StationException(APIException):
    # Default status code
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    # Default error message
    default_detail = "Unable to find fueling stations in route"

    # Default error code (optional)
    # default_code = 'custom_error'

    def __init__(self, detail=None, code=None, status_code=None):
        """
        Override the constructor to allow custom status codes and details.
        """
        if detail is not None:
            self.detail = detail
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        super().__init__(detail, code)
