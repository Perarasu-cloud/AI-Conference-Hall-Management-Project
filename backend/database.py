import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
DB_NAME = os.path.join(DATABASE_DIR, "conference.db")


def get_connection():
    os.makedirs(DATABASE_DIR, exist_ok=True)

    connection = sqlite3.connect(
        DB_NAME,
        timeout=5
    )

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")

    return connection


def create_tables():
    os.makedirs(DATABASE_DIR, exist_ok=True)

    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS halls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            capacity INTEGER NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hall_id INTEGER NOT NULL,
            participants INTEGER NOT NULL,
            booking_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            FOREIGN KEY (hall_id) REFERENCES halls(id)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS hall_resources (
            hall_id INTEGER NOT NULL,
            resource_id INTEGER NOT NULL,
            PRIMARY KEY (hall_id, resource_id),
            FOREIGN KEY (hall_id) REFERENCES halls(id),
            FOREIGN KEY (resource_id) REFERENCES resources(id)
        )
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_bookings_hall_date
        ON bookings(hall_id, booking_date, start_time, end_time)
    """)

    connection.commit()
    connection.close()


def insert_sample_halls():
    connection = get_connection()

    count = connection.execute(
        "SELECT COUNT(*) FROM halls"
    ).fetchone()[0]

    if count == 0:
        connection.executemany(
            """
            INSERT INTO halls (name, capacity)
            VALUES (?, ?)
            """,
            [
                ("Innovation Hall", 50),
                ("Executive Conference Room", 30),
                ("Grand Meeting Hall", 100)
            ]
        )

        connection.commit()

    connection.close()


def insert_sample_resources():
    connection = get_connection()

    resources = [
        "Projector",
        "Video Conferencing",
        "Microphone",
        "Whiteboard"
    ]

    for resource in resources:
        connection.execute(
            """
            INSERT OR IGNORE INTO resources (name)
            VALUES (?)
            """,
            (resource,)
        )

    connection.commit()

    hall_resources = {
        1: [
            "Projector",
            "Video Conferencing",
            "Microphone"
        ],
        2: [
            "Projector",
            "Whiteboard"
        ],
        3: [
            "Projector",
            "Video Conferencing",
            "Microphone",
            "Whiteboard"
        ]
    }

    for hall_id, resource_names in hall_resources.items():

        for resource_name in resource_names:

            resource = connection.execute(
                """
                SELECT id
                FROM resources
                WHERE name = ?
                """,
                (resource_name,)
            ).fetchone()

            if resource:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO hall_resources
                    (hall_id, resource_id)
                    VALUES (?, ?)
                    """,
                    (
                        hall_id,
                        resource["id"]
                    )
                )

    connection.commit()
    connection.close()