# Car Parking Backend API

A comprehensive FastAPI-based backend for managing car parking operations, including vehicle entry/exit, payments, reservations, memberships, and EV charging.

## Table of Contents

- [Getting Started](#getting-started)
- [Features Overview](#features-overview)
- [Authentication](#authentication)
- [API Endpoints](#api-endpoints)
  - [Authentication](#authentication-endpoints)
  - [Vehicles](#vehicles)
  - [Parking Structure](#parking-structure)
  - [Sessions](#sessions)
  - [Payments & Rates](#payments--rates)
  - [Discounts](#discounts)
  - [Reservations](#reservations)
  - [Memberships](#memberships)
  - [EV Charging](#ev-charging)
  - [Reports](#reports)
- [User Journeys](#user-journeys)
- [Running Tests](#running-tests)

---

## Getting Started

### Prerequisites

- Python 3.11+
- pip or uv package manager

### Installation

```bash
# Clone the repository
cd toy-carpark

# Install dependencies
pip install -e ".[dev]"

# Or with uv
uv pip install -e ".[dev]"
```

### Environment Configuration

Create a `.env` file (see `.env.example`):

```env
DATABASE_URL=sqlite+aiosqlite:///./carpark.db
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Database Setup

```bash
# Run migrations
alembic upgrade head
```

### Running the Server

```bash
# Development mode with auto-reload
uvicorn src.main:app --reload

# Production mode
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Features Overview

| Feature | Description |
|---------|-------------|
| **Vehicle Entry/Exit** | Track vehicles with timestamps, ticket generation, LPR support |
| **Parking Space Management** | Real-time tracking by zone, level, and space type |
| **Payment Processing** | Multiple payment methods, rate calculations, receipts |
| **Reservation System** | Advance booking with confirmation numbers |
| **Memberships** | Monthly/annual passes with usage tracking |
| **Vehicle Types** | Different rates/spaces for various vehicle sizes |
| **Dynamic Pricing** | Hourly/daily rates with grace periods |
| **Zones & Levels** | Multi-level parking structure support |
| **Discounts** | Percentage and fixed-amount promo codes |
| **EV Charging** | Charging stations, sessions, and billing |
| **Reports** | Occupancy, revenue, and dashboard analytics |
| **User Accounts** | Customer profiles with role-based access |

---

## Authentication

The API uses JWT (JSON Web Token) authentication.

### Register a User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword",
    "full_name": "John Doe",
    "phone": "+1234567890"
  }'
```

Response includes an `access_token` for subsequent requests.

### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=securepassword"
```

### Using the Token

Include the token in the `Authorization` header:

```bash
curl -H "Authorization: Bearer <your-token>" \
  http://localhost:8000/api/v1/auth/me
```

### User Roles

- **CUSTOMER**: Regular users who can register vehicles, make reservations, and pay
- **OPERATOR**: Staff who process vehicle entry/exit
- **ADMIN**: Full access including reports and system management

---

## API Endpoints

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register a new user |
| POST | `/api/v1/auth/login` | Login and get access token |
| GET | `/api/v1/auth/me` | Get current user profile |

---

### Vehicles

Manage vehicles and vehicle types.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/vehicle-types` | List all vehicle types |
| POST | `/api/v1/vehicle-types` | Create a vehicle type |
| GET | `/api/v1/vehicles` | List user's vehicles |
| POST | `/api/v1/vehicles` | Register a new vehicle |
| GET | `/api/v1/vehicles/plate/{plate}` | Find vehicle by license plate |
| PUT | `/api/v1/vehicles/{id}` | Update vehicle details |
| DELETE | `/api/v1/vehicles/{id}` | Remove a vehicle |

#### Register a Vehicle

```bash
curl -X POST http://localhost:8000/api/v1/vehicles \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "license_plate": "ABC123",
    "vehicle_type_id": 1,
    "make": "Toyota",
    "model": "Camry",
    "color": "Silver",
    "is_ev": false
  }'
```

---

### Parking Structure

Manage levels, zones, and parking spaces.

#### Levels

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/levels` | List all levels |
| POST | `/api/v1/levels` | Create a level |
| PUT | `/api/v1/levels/{id}` | Update a level |

#### Zones

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/zones` | List zones (optionally filter by level) |
| POST | `/api/v1/zones` | Create a zone |
| PUT | `/api/v1/zones/{id}` | Update a zone |
| GET | `/api/v1/zones/{id}/availability` | Get zone occupancy stats |

#### Spaces

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/spaces` | List spaces with pagination and filters |
| POST | `/api/v1/spaces` | Create a parking space |
| PUT | `/api/v1/spaces/{id}` | Update space details |
| GET | `/api/v1/spaces/available` | Find available spaces |

#### Space Types

- `STANDARD` - Regular parking spaces
- `COMPACT` - Smaller spaces for compact cars
- `HANDICAPPED` - Accessible parking
- `EV` - Electric vehicle charging spots
- `MOTORCYCLE` - Motorcycle parking

#### Get Zone Availability

```bash
curl http://localhost:8000/api/v1/zones/1/availability \
  -H "Authorization: Bearer <token>"
```

Response:
```json
{
  "zone_id": 1,
  "total": 50,
  "available": 35,
  "occupied": 12,
  "reserved": 2,
  "maintenance": 1,
  "occupancy_rate": 30.0
}
```

---

### Sessions

Core parking operations: vehicle entry, exit, and fee calculation.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/sessions/entry` | Process vehicle entry |
| POST | `/api/v1/sessions/exit` | Process vehicle exit |
| GET | `/api/v1/sessions/active` | List active parking sessions |
| GET | `/api/v1/sessions/{id}` | Get session details |
| GET | `/api/v1/sessions/ticket/{ticket}` | Find session by ticket number |
| GET | `/api/v1/sessions/{id}/calculate-fee` | Calculate parking fee |
| POST | `/api/v1/sessions/{id}/assign-space` | Assign a space to session |

#### Vehicle Entry

```bash
curl -X POST http://localhost:8000/api/v1/sessions/entry \
  -H "Authorization: Bearer <operator-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "license_plate": "ABC123",
    "entry_gate": "Main Entrance"
  }'
```

Response:
```json
{
  "session": {
    "id": 1,
    "vehicle_id": 1,
    "space_id": 5,
    "entry_time": "2024-01-15T10:30:00Z",
    "status": "active"
  },
  "ticket_number": "TKT-A1B2C3D4E5F6",
  "space_assigned": {
    "id": 5,
    "space_number": "A-105",
    "zone": { "name": "Zone A", "level": { "name": "Level 1" } }
  }
}
```

#### Calculate Fee

```bash
curl http://localhost:8000/api/v1/sessions/1/calculate-fee \
  -H "Authorization: Bearer <token>"
```

Response:
```json
{
  "session_id": 1,
  "duration_minutes": 127,
  "base_fee": 15.0,
  "discounts": 0,
  "tax": 0,
  "total": 15.0,
  "breakdown": [
    { "description": "Parking (3 hour(s) @ $5/hr)", "amount": 15.0 }
  ]
}
```

#### Vehicle Exit

```bash
curl -X POST http://localhost:8000/api/v1/sessions/exit \
  -H "Authorization: Bearer <operator-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_number": "TKT-A1B2C3D4E5F6",
    "exit_gate": "Exit A"
  }'
```

---

### Payments & Rates

Process payments and manage pricing.

#### Rates

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/rates` | List all rates |
| POST | `/api/v1/rates` | Create a rate |
| PUT | `/api/v1/rates/{id}` | Update a rate |
| DELETE | `/api/v1/rates/{id}` | Deactivate a rate |

#### Rate Types

- `HOURLY` - Charged per hour (rounded up)
- `DAILY` - Maximum daily charge
- `FLAT` - Fixed fee regardless of duration

#### Create a Rate

```bash
curl -X POST http://localhost:8000/api/v1/rates \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Standard Hourly",
    "rate_type": "hourly",
    "amount": 5.0,
    "grace_period_minutes": 15,
    "effective_from": "2024-01-01T00:00:00Z"
  }'
```

#### Payments

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/payments` | Process a payment |
| GET | `/api/v1/payments` | List payments |
| GET | `/api/v1/payments/{id}` | Get payment details |
| POST | `/api/v1/payments/validate-exit` | Check if vehicle can exit |

#### Process Payment

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 1,
    "payment_method": "card",
    "amount": 15.0,
    "discount_code": "WELCOME10"
  }'
```

#### Payment Methods

- `CASH`
- `CARD`
- `MOBILE`

#### Validate Exit

```bash
curl -X POST http://localhost:8000/api/v1/payments/validate-exit \
  -H "Content-Type: application/json" \
  -d '{ "ticket_number": "TKT-A1B2C3D4E5F6" }'
```

Response:
```json
{
  "is_paid": true,
  "can_exit": true,
  "time_remaining_minutes": 15
}
```

---

### Discounts

Manage promotional codes and partner validations.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/discounts` | List all discounts |
| POST | `/api/v1/discounts` | Create a discount |
| PUT | `/api/v1/discounts/{id}` | Update a discount |
| DELETE | `/api/v1/discounts/{id}` | Deactivate a discount |
| POST | `/api/v1/discounts/validate` | Validate a discount code |

#### Discount Types

- `PERCENTAGE` - Percentage off (e.g., 10% off)
- `FIXED_AMOUNT` - Fixed dollar amount off
- `FREE_HOURS` - Free parking hours

#### Create a Discount

```bash
curl -X POST http://localhost:8000/api/v1/discounts \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "SUMMER20",
    "name": "Summer Sale 20% Off",
    "discount_type": "percentage",
    "value": 20.0,
    "valid_from": "2024-06-01T00:00:00Z",
    "valid_to": "2024-08-31T23:59:59Z",
    "max_uses": 1000
  }'
```

#### Validate a Discount

```bash
curl -X POST http://localhost:8000/api/v1/discounts/validate \
  -H "Content-Type: application/json" \
  -d '{
    "code": "SUMMER20",
    "session_id": 1
  }'
```

---

### Reservations

Book parking spaces in advance.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/reservations` | Create a reservation |
| GET | `/api/v1/reservations` | List reservations |
| GET | `/api/v1/reservations/{id}` | Get reservation details |
| GET | `/api/v1/reservations/confirmation/{code}` | Find by confirmation number |
| PUT | `/api/v1/reservations/{id}` | Update a reservation |
| DELETE | `/api/v1/reservations/{id}` | Cancel a reservation |
| POST | `/api/v1/reservations/{id}/check-in` | Check in to reservation |
| GET | `/api/v1/reservations/availability` | Check space availability |

#### Create a Reservation

```bash
curl -X POST http://localhost:8000/api/v1/reservations \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id": 1,
    "zone_id": 1,
    "start_time": "2024-01-20T09:00:00Z",
    "end_time": "2024-01-20T17:00:00Z",
    "special_requests": "Near elevator please"
  }'
```

Response:
```json
{
  "reservation": {
    "id": 1,
    "status": "confirmed",
    "start_time": "2024-01-20T09:00:00Z",
    "end_time": "2024-01-20T17:00:00Z"
  },
  "confirmation_number": "RSV-A1B2C3D4"
}
```

#### Check Availability

```bash
curl "http://localhost:8000/api/v1/reservations/availability?start_time=2024-01-20T09:00:00Z&end_time=2024-01-20T17:00:00Z&zone_id=1" \
  -H "Authorization: Bearer <token>"
```

#### Check In

```bash
curl -X POST http://localhost:8000/api/v1/reservations/1/check-in \
  -H "Authorization: Bearer <operator-token>"
```

---

### Memberships

Subscription plans for regular parkers.

#### Plans

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/membership-plans` | List available plans |
| POST | `/api/v1/membership-plans` | Create a plan |
| PUT | `/api/v1/membership-plans/{id}` | Update a plan |

#### Subscriptions

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/memberships` | Subscribe to a plan |
| GET | `/api/v1/memberships` | List memberships |
| GET | `/api/v1/memberships/{id}` | Get membership details |
| GET | `/api/v1/memberships/{id}/usage` | Get usage statistics |
| POST | `/api/v1/memberships/{id}/cancel` | Cancel membership |
| POST | `/api/v1/memberships/{id}/renew` | Renew membership |

#### Create a Membership Plan

```bash
curl -X POST http://localhost:8000/api/v1/membership-plans \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Premium Monthly",
    "description": "Unlimited parking with reserved spot",
    "duration_months": 1,
    "price": 150.0,
    "vehicle_limit": 2,
    "included_hours": null,
    "discount_percentage": 20.0,
    "is_active": true
  }'
```

#### Subscribe

```bash
curl -X POST http://localhost:8000/api/v1/memberships \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": 1,
    "vehicle_ids": [1, 2],
    "auto_renew": true
  }'
```

#### Check Usage

```bash
curl http://localhost:8000/api/v1/memberships/1/usage \
  -H "Authorization: Bearer <token>"
```

Response:
```json
{
  "membership_id": 1,
  "hours_used": 45.5,
  "hours_remaining": null,
  "sessions_count": 12,
  "savings_to_date": 85.0,
  "days_remaining": 18
}
```

---

### EV Charging

Manage electric vehicle charging stations and sessions.

#### Stations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/ev-stations` | List charging stations |
| POST | `/api/v1/ev-stations` | Create a station |
| PUT | `/api/v1/ev-stations/{id}` | Update a station |

#### Charging Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/ev-charging/start` | Start charging session |
| POST | `/api/v1/ev-charging/{id}/stop` | Stop charging session |
| GET | `/api/v1/ev-charging/sessions` | List charging sessions |

#### Charger Types

- `LEVEL1` - Standard 120V outlet (slow)
- `LEVEL2` - 240V charging (medium)
- `DC_FAST` - DC fast charging (rapid)

#### Create a Charging Station

```bash
curl -X POST http://localhost:8000/api/v1/ev-stations \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "space_id": 10,
    "charger_type": "level2",
    "power_kw": 7.2,
    "connector_type": "J1772",
    "price_per_kwh": 0.25
  }'
```

#### Start Charging

```bash
curl -X POST http://localhost:8000/api/v1/ev-charging/start \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "station_id": 1,
    "vehicle_id": 1,
    "parking_session_id": 5,
    "max_power_requested": 7.2
  }'
```

#### Stop Charging

```bash
curl -X POST http://localhost:8000/api/v1/ev-charging/1/stop \
  -H "Authorization: Bearer <token>"
```

Response:
```json
{
  "session": {
    "id": 1,
    "status": "completed",
    "energy_kwh": 12.5,
    "cost": 3.13
  },
  "energy_used": 12.5,
  "cost": 3.13,
  "duration_minutes": 104
}
```

---

### Reports

Analytics and dashboard for administrators.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/reports/dashboard` | Get dashboard summary |

#### Dashboard (Admin Only)

```bash
curl http://localhost:8000/api/v1/reports/dashboard \
  -H "Authorization: Bearer <admin-token>"
```

Response:
```json
{
  "total_spaces": 200,
  "occupied_spaces": 85,
  "available_spaces": 110,
  "reserved_spaces": 5,
  "occupancy_rate": 42.5,
  "active_sessions": 85,
  "today_entries": 156,
  "today_exits": 142,
  "today_revenue": 1250.50,
  "active_ev_charging": 8,
  "pending_reservations": 12
}
```

---

## User Journeys

### Journey 1: Regular Customer Parking

1. **Register** an account
2. **Register** your vehicle
3. **Arrive** at parking - operator processes entry
4. **Park** in assigned space
5. **Check fee** before leaving
6. **Pay** at kiosk or via app
7. **Exit** - operator validates and opens gate

### Journey 2: Reservation Flow

1. **Check availability** for desired date/time
2. **Create reservation** with confirmation number
3. **Arrive** at scheduled time
4. **Check in** using confirmation number
5. **Park** in reserved/assigned space
6. **Pay** and **exit** as normal

### Journey 3: EV Charging

1. **Enter** parking and get assigned EV space
2. **Start charging** session
3. **Monitor** charging progress (optional)
4. **Stop charging** when done
5. **Pay** for parking + charging
6. **Exit**

### Journey 4: Membership

1. **View** available membership plans
2. **Subscribe** to preferred plan
3. **Register** vehicles to membership
4. **Use** parking with automatic discounts
5. **Track** usage and savings
6. **Renew** or cancel as needed

---

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_sessions.py

# Run specific test
pytest tests/test_e2e_journeys.py::TestCustomerParkingJourney::test_complete_parking_flow

# Run with coverage
pytest --cov=src
```

---

## Project Structure

```
toy-carpark/
├── src/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Settings configuration
│   ├── database.py          # Database connection
│   ├── api/v1/              # API route handlers
│   ├── core/                # Security, exceptions, dependencies
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   └── utils/               # Constants and utilities
├── tests/                   # Test suite
├── alembic/                 # Database migrations
├── pyproject.toml           # Project dependencies
└── README.md                # This file
```

---

## License

MIT License
