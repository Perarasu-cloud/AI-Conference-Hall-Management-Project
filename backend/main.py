from datetime import datetime, date, time, timedelta
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import (
    create_tables,
    get_connection,
    insert_sample_halls,
    insert_sample_resources
)

from ai_service import extract_meeting_requirements


app = FastAPI(
    title="AI Conference Hall Management System",
    version="1.0.0"
)


frontend_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_URL",
        "http://127.0.0.1:5500,http://localhost:5500"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


create_tables()
insert_sample_halls()
insert_sample_resources()


class Booking(BaseModel):
    hall_id: int
    participants: int = Field(gt=0)
    booking_date: str
    start_time: str
    end_time: str


class AIRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=1000
    )


def validate_booking_details(
    participants,
    booking_date,
    start_time,
    end_time
):

    if participants <= 0:
        return (
            "Number of participants "
            "must be greater than zero."
        )

    try:
        requested_date = datetime.strptime(
            booking_date,
            "%Y-%m-%d"
        ).date()
    except ValueError:
        return "Please provide a valid booking date."

    today = date.today()

    if requested_date < today:
        return (
            "The booking date has already passed. "
            "Please choose today or a future date."
        )

    try:
        start = datetime.strptime(
            start_time,
            "%H:%M"
        ).time()

        end = datetime.strptime(
            end_time,
            "%H:%M"
        ).time()

    except ValueError:
        return "Please provide a valid time."

    if start == end:
        return (
            "Start time and end time "
            "cannot be the same."
        )

    if end <= start:
        return "End time must be after start time."

    return None


def get_requested_resources(
    connection,
    resource_names
):

    valid_resources = []

    for resource_name in resource_names:

        resource = connection.execute(
            """
            SELECT id, name
            FROM resources
            WHERE name = ?
            """,
            (resource_name,)
        ).fetchone()

        if resource:
            valid_resources.append(
                dict(resource)
            )

    return valid_resources


def find_available_halls(
    connection,
    participants,
    booking_date,
    start_time,
    end_time,
    required_resources
):

    halls = connection.execute(
        """
        SELECT *
        FROM halls
        WHERE capacity >= ?
        """,
        (participants,)
    ).fetchall()

    available_halls = []

    for hall in halls:

        conflict = connection.execute(
            """
            SELECT id
            FROM bookings
            WHERE hall_id = ?
            AND booking_date = ?
            AND start_time < ?
            AND end_time > ?
            LIMIT 1
            """,
            (
                hall["id"],
                booking_date,
                end_time,
                start_time
            )
        ).fetchone()

        if conflict:
            continue

        hall_resources = connection.execute(
            """
            SELECT resources.name
            FROM resources
            INNER JOIN hall_resources
                ON resources.id = hall_resources.resource_id
            WHERE hall_resources.hall_id = ?
            """,
            (hall["id"],)
        ).fetchall()

        hall_resource_names = [
            row["name"]
            for row in hall_resources
        ]

        missing_resources = [
            resource
            for resource in required_resources
            if resource not in hall_resource_names
        ]

        if missing_resources:
            continue

        if required_resources:

            reason = (
                f"Capacity supports {participants} "
                f"participants and all requested "
                f"resources are available."
            )

        else:

            reason = (
                f"Capacity supports {participants} "
                f"participants and the hall is "
                f"available during the requested time."
            )

        available_halls.append({
            "id": hall["id"],
            "name": hall["name"],
            "capacity": hall["capacity"],
            "matched_resources": required_resources,
            "why_recommended": reason
        })

    available_halls.sort(
        key=lambda hall: (
            hall["capacity"] - participants,
            hall["capacity"]
        )
    )

    return available_halls


def find_alternative_slots(
    connection,
    participants,
    booking_date,
    start_time,
    end_time,
    required_resources
):

    requested_start = datetime.strptime(
        f"{booking_date} {start_time}",
        "%Y-%m-%d %H:%M"
    )

    requested_end = datetime.strptime(
        f"{booking_date} {end_time}",
        "%Y-%m-%d %H:%M"
    )

    duration = requested_end - requested_start

    alternatives = []

    for offset in range(
        -8,
        9
    ):

        candidate_start = (
            requested_start
            + timedelta(minutes=30 * offset)
        )

        if candidate_start == requested_start:
            continue

        candidate_end = (
            candidate_start + duration
        )

        if candidate_start.date() != requested_start.date():
            continue

        if candidate_start.hour < 8:
            continue

        if candidate_end.hour > 22 or (
            candidate_end.hour == 22
            and candidate_end.minute > 0
        ):
            continue

        candidate_date = (
            candidate_start.date()
            .strftime("%Y-%m-%d")
        )

        candidate_start_time = (
            candidate_start.strftime("%H:%M")
        )

        candidate_end_time = (
            candidate_end.strftime("%H:%M")
        )

        halls = find_available_halls(
            connection,
            participants,
            candidate_date,
            candidate_start_time,
            candidate_end_time,
            required_resources
        )

        if halls:

            alternatives.append({
                "date": candidate_date,
                "start_time": candidate_start_time,
                "end_time": candidate_end_time,
                "available_halls": halls[:2]
            })

        if len(alternatives) >= 3:
            break

    return alternatives


@app.get("/")
def home():

    return {
        "message":
        "Conference Hall Management API is running!"
    }


@app.get("/halls")
def get_halls():

    connection = get_connection()

    halls = connection.execute(
        "SELECT * FROM halls"
    ).fetchall()

    connection.close()

    return {
        "halls": [
            dict(hall)
            for hall in halls
        ]
    }


@app.get("/bookings")
def get_bookings():

    connection = get_connection()

    bookings = connection.execute(
        "SELECT * FROM bookings"
    ).fetchall()

    connection.close()

    return {
        "bookings": [
            dict(booking)
            for booking in bookings
        ]
    }


@app.post("/bookings")
def create_booking(
    booking: Booking
):

    validation_error = validate_booking_details(
        booking.participants,
        booking.booking_date,
        booking.start_time,
        booking.end_time
    )

    if validation_error:
        raise HTTPException(
            status_code=400,
            detail=validation_error
        )

    connection = get_connection()

    try:

        connection.execute(
            "BEGIN IMMEDIATE"
        )

        hall = connection.execute(
            """
            SELECT *
            FROM halls
            WHERE id = ?
            """,
            (booking.hall_id,)
        ).fetchone()

        if hall is None:

            connection.rollback()

            raise HTTPException(
                status_code=404,
                detail="Hall not found."
            )

        if booking.participants > hall["capacity"]:

            connection.rollback()

            raise HTTPException(
                status_code=400,
                detail=(
                    "Number of participants "
                    "exceeds hall capacity."
                )
            )

        conflict = connection.execute(
            """
            SELECT id
            FROM bookings
            WHERE hall_id = ?
            AND booking_date = ?
            AND start_time < ?
            AND end_time > ?
            LIMIT 1
            """,
            (
                booking.hall_id,
                booking.booking_date,
                booking.end_time,
                booking.start_time
            )
        ).fetchone()

        if conflict:

            connection.rollback()

            raise HTTPException(
                status_code=409,
                detail=(
                    "This hall was booked by "
                    "another request during "
                    "the selected time."
                )
            )

        cursor = connection.execute(
            """
            INSERT INTO bookings
            (
                hall_id,
                participants,
                booking_date,
                start_time,
                end_time
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                booking.hall_id,
                booking.participants,
                booking.booking_date,
                booking.start_time,
                booking.end_time
            )
        )

        connection.commit()

        return {
            "message":
            "Booking created successfully.",
            "booking_id":
            cursor.lastrowid
        }

    except HTTPException:
        raise

    except Exception:

        connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to complete the booking "
                "at this time."
            )
        )

    finally:
        connection.close()


@app.get("/available-halls")
def get_available_halls(
    participants: int,
    booking_date: str,
    start_time: str,
    end_time: str,
    required_resources: str = ""
):

    validation_error = validate_booking_details(
        participants,
        booking_date,
        start_time,
        end_time
    )

    if validation_error:
        raise HTTPException(
            status_code=400,
            detail=validation_error
        )

    connection = get_connection()

    try:

        requested_resources = [
            resource.strip()
            for resource in required_resources.split(",")
            if resource.strip()
        ]

        available_halls = find_available_halls(
            connection,
            participants,
            booking_date,
            start_time,
            end_time,
            requested_resources
        )

        alternatives = []

        if not available_halls:

            alternatives = find_alternative_slots(
                connection,
                participants,
                booking_date,
                start_time,
                end_time,
                requested_resources
            )

        return {
            "available_halls": available_halls,
            "alternatives": alternatives
        }

    finally:
        connection.close()


@app.post("/ai-booking")
def ai_booking(
    request: AIRequest
):

    try:

        requirements = extract_meeting_requirements(
            request.message
        )

        if requirements["intent"] == "irrelevant":

            return {
                "status": "irrelevant",
                "message": (
                    "This assistant is designed "
                    "to help with conference "
                    "hall bookings."
                ),
                "requirements": requirements
            }

        unsupported_resources = requirements.get(
            "unsupported_resources",
            []
        )

        if unsupported_resources:

            return {
                "status": "unsupported_resource",
                "message": (
                    "Some requested resources "
                    "are not currently supported."
                ),
                "unsupported_resources":
                    unsupported_resources,
                "supported_resources": [
                    "Projector",
                    "Video Conferencing",
                    "Microphone",
                    "Whiteboard"
                ],
                "requirements": requirements
            }

        missing_fields = []

        if requirements["participants"] is None:
            missing_fields.append(
                "participants"
            )

        if requirements["date"] is None:
            missing_fields.append(
                "date"
            )

        if requirements["start_time"] is None:
            missing_fields.append(
                "start_time"
            )

        if requirements["end_time"] is None:
            missing_fields.append(
                "end_time"
            )

        if missing_fields:

            return {
                "status": "incomplete",
                "message":
                    "Some booking information is missing.",
                "missing_fields":
                    missing_fields,
                "requirements":
                    requirements
            }

        validation_error = validate_booking_details(
            requirements["participants"],
            requirements["date"],
            requirements["start_time"],
            requirements["end_time"]
        )

        if validation_error:

            return {
                "status": "invalid",
                "message": validation_error,
                "requirements": requirements
            }

        connection = get_connection()

        try:

            available_halls = find_available_halls(
                connection,
                requirements["participants"],
                requirements["date"],
                requirements["start_time"],
                requirements["end_time"],
                requirements["resources"]
            )

            alternatives = []

            if not available_halls:

                alternatives = find_alternative_slots(
                    connection,
                    requirements["participants"],
                    requirements["date"],
                    requirements["start_time"],
                    requirements["end_time"],
                    requirements["resources"]
                )

            return {
                "status": "complete",
                "message":
                    "Booking request processed successfully.",
                "requirements":
                    requirements,
                "available_halls":
                    available_halls,
                "alternatives":
                    alternatives
            }

        finally:

            connection.close()

    except ValueError as error:

        return {
            "status": "invalid",
            "message": str(error)
        }

    except Exception:

        return {
            "status": "error",
            "message":
                "Unable to process the request at this time."
        }