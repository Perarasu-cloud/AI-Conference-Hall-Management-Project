import json
import re
from datetime import datetime, timedelta
from typing import List, Optional, Literal

from pydantic import BaseModel, Field
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client()

ALLOWED_RESOURCES = [
    "Projector",
    "Video Conferencing",
    "Microphone",
    "Whiteboard"
]


class MeetingRequirements(BaseModel):
    intent: Literal["booking", "irrelevant"]

    participants: Optional[int] = Field(
        default=None,
        description="Number of participants. Return null if not provided."
    )

    date: Optional[str] = Field(
        default=None,
        description="Meeting date. Return null if not provided."
    )

    start_time: Optional[str] = Field(
        default=None,
        description="Meeting start time. Return null if not provided."
    )

    end_time: Optional[str] = Field(
        default=None,
        description="Meeting end time. Return null if not provided."
    )

    resources: List[str] = Field(
        default_factory=list,
        description="Supported resources requested by the user."
    )

    unsupported_resources: List[str] = Field(
        default_factory=list,
        description="Resources requested by the user that are not supported."
    )


def convert_date(date_text):

    if not date_text:
        return None

    text = date_text.strip().lower()

    text = re.sub(
        r"(\d{1,2})(st|nd|rd|th)",
        r"\1",
        text
    )

    today = datetime.now().date()

    if text == "today":
        return today.strftime("%Y-%m-%d")

    if text == "tomorrow":
        return (
            today + timedelta(days=1)
        ).strftime("%Y-%m-%d")

    if text == "day after tomorrow":
        return (
            today + timedelta(days=2)
        ).strftime("%Y-%m-%d")

    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6
    }

    weekday_match = re.fullmatch(
        r"(today|this|next|coming)?\s*(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
        text
    )

    if weekday_match:

        modifier = weekday_match.group(1)
        weekday_name = weekday_match.group(2)

        target_day = weekdays[weekday_name]
        difference = (
            target_day - today.weekday()
        ) % 7

        if modifier in ["next", "coming"] and difference == 0:
            difference = 7

        if modifier == "next" and difference == 0:
            difference = 7

        if modifier == "this" and difference == 0:
            difference = 0

        return (
            today + timedelta(days=difference)
        ).strftime("%Y-%m-%d")

    date_formats = [
        "%Y-%m-%d",
        "%B %d %Y",
        "%b %d %Y",
        "%B %d",
        "%b %d",
        "%d %B %Y",
        "%d %b %Y",
        "%d %B",
        "%d %b"
    ]

    for date_format in date_formats:

        try:
            parsed = datetime.strptime(
                text,
                date_format
            ).date()

            if "%Y" not in date_format:
                parsed = parsed.replace(
                    year=today.year
                )

            return parsed.strftime("%Y-%m-%d")

        except ValueError:
            continue

    raise ValueError(
        f"Unable to understand date: {date_text}"
    )


def convert_time(time_text):

    if not time_text:
        return None

    text = time_text.strip().upper()

    if re.fullmatch(r"\d{1,2}:\d{2}", text):

        time_value = datetime.strptime(
            text,
            "%H:%M"
        )

        return time_value.strftime("%H:%M")

    match = re.fullmatch(
        r"(\d{1,2})(?::(\d{2}))?\s*(AM|PM)",
        text
    )

    if match:

        hour = int(match.group(1))

        minute = int(
            match.group(2)
            if match.group(2)
            else 0
        )

        period = match.group(3)

        if hour > 12 or minute > 59:
            raise ValueError(
                f"Unable to understand time: {time_text}"
            )

        if period == "PM" and hour != 12:
            hour += 12

        if period == "AM" and hour == 12:
            hour = 0

        return f"{hour:02d}:{minute:02d}"

    raise ValueError(
        f"Unable to understand time: {time_text}"
    )


def extract_meeting_requirements(user_message):

    today = datetime.now().date().strftime(
        "%Y-%m-%d"
    )

    prompt = f"""
You are an AI assistant for a Conference Hall Management System.

Today's date is {today}.

Analyze the user's message and classify its intent.

Set intent to "booking" when the message is related to:
- booking a conference hall
- reserving a meeting room
- finding an available hall
- scheduling a meeting
- meeting-room requirements
- requesting a hall even when information is missing

Set intent to "irrelevant" when the message is unrelated to:
- conference halls
- meeting rooms
- meetings
- reservations
- booking requirements

Examples of booking requests:

"I need a hall for 10 people"

"Book a conference room tomorrow"

"I need a meeting room with a projector"

"Find a hall for 50 people from 2 PM to 4 PM"

Examples of irrelevant requests:

"I love cricket"

"Tell me a joke"

"What is the capital of India?"

"How is the weather today?"

For booking requests:

- Extract the number of participants if provided.
- Extract the date if provided.
- Extract start time if provided.
- Extract end time if provided.
- Do not invent missing information.
- Return null for missing values.
- Extract supported resources separately.
- If the user requests an unsupported resource, put it in unsupported_resources.
- Do not treat general words such as "room" or "hall" as resources.

Supported resources:

Projector
Video Conferencing
Microphone
Whiteboard

For dates:

- Prefer YYYY-MM-DD.
- Convert relative dates using today's date.
- "tomorrow" means the day after today.
- "next Friday" should be converted to its actual date.
- Do not invent a year unless it can be reasonably determined.

For irrelevant requests:

- Set intent to "irrelevant".
- participants = null
- date = null
- start_time = null
- end_time = null
- resources = []
- unsupported_resources = []

User message:

{user_message}
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": MeetingRequirements
        }
    )

    result = json.loads(response.text)

    result["date"] = convert_date(
        result.get("date")
    )

    result["start_time"] = convert_time(
        result.get("start_time")
    )

    result["end_time"] = convert_time(
        result.get("end_time")
    )

    supported_resources = []

    for resource in result.get(
        "resources",
        []
    ):

        for allowed_resource in ALLOWED_RESOURCES:

            if resource.lower() == allowed_resource.lower():

                supported_resources.append(
                    allowed_resource
                )

    result["resources"] = list(
        dict.fromkeys(
            supported_resources
        )
    )

    result["unsupported_resources"] = list(
        dict.fromkeys(
            result.get(
                "unsupported_resources",
                []
            )
        )
    )

    return result