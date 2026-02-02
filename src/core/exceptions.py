from fastapi import HTTPException, status


class CarParkException(HTTPException):
    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "An error occurred",
    ):
        super().__init__(status_code=status_code, detail=detail)


class AuthenticationError(CarParkException):
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class AuthorizationError(CarParkException):
    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class NotFoundError(CarParkException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ConflictError(CarParkException):
    def __init__(self, detail: str = "Resource conflict"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class ValidationError(CarParkException):
    def __init__(self, detail: str = "Validation error"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


class PaymentError(CarParkException):
    def __init__(self, detail: str = "Payment processing failed"):
        super().__init__(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=detail)


class SpaceUnavailableError(CarParkException):
    def __init__(self, detail: str = "Parking space is not available"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class ReservationConflictError(CarParkException):
    def __init__(self, detail: str = "Reservation conflict"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class MembershipExpiredError(CarParkException):
    def __init__(self, detail: str = "Membership has expired"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
