const API_BASE_URL = "https://ai-conference-hall-backend.onrender.com";

const form = document.getElementById("hallForm");
const results = document.getElementById("results");
const aiMessage = document.getElementById("aiMessage");
const aiSearchButton = document.getElementById("aiSearchButton");

let selectedBookingDetails = {};

function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = String(value);
    return div.innerHTML;
}

function showErrorMessage(message) {
    results.innerHTML = `
        <div class="result-card">
            <h3>Request could not be completed</h3>
            <p>${escapeHtml(message)}</p>
        </div>
    `;
}

function displayAvailableHalls(halls) {

    halls.forEach(function (hall, index) {

        const card = document.createElement("div");

        card.className = "result-card";

        const recommendation =
            index === 0
                ? `<p><strong>Recommended match ⭐</strong></p>`
                : "";

        const reason = hall.why_recommended
            ? `
                <p>
                    <strong>Why it matches:</strong>
                    ${escapeHtml(hall.why_recommended)}
                </p>
            `
            : "";

        const resources =
            hall.matched_resources &&
            hall.matched_resources.length > 0
                ? `
                    <p>
                        <strong>Resources:</strong>
                        ${hall.matched_resources
                            .map(escapeHtml)
                            .join(", ")}
                    </p>
                `
                : "";

        card.innerHTML = `
            <h3>${escapeHtml(hall.name)}</h3>

            ${recommendation}

            <p>
                <strong>Capacity:</strong>
                ${escapeHtml(hall.capacity)}
                people
            </p>

            ${resources}

            ${reason}

            <button
                onclick="selectHall(
                    ${hall.id},
                    '${escapeHtml(hall.name)}'
                )"
            >
                Select Hall
            </button>
        `;

        results.appendChild(card);
    });
}

function displayAlternatives(alternatives) {

    if (!alternatives || alternatives.length === 0) {
        return;
    }

    const container =
        document.createElement("div");

    container.className = "result-card";

    let html = `
        <h3>Alternative time slots</h3>
        <p>
            No hall was available for your exact
            time. These nearby options are available:
        </p>
    `;

    alternatives.forEach(function (alternative) {

        html += `
            <div>
                <p>
                    <strong>
                        ${escapeHtml(alternative.date)}
                    </strong>
                    <br>
                    ${escapeHtml(alternative.start_time)}
                    -
                    ${escapeHtml(alternative.end_time)}
                </p>
            </div>
        `;
    });

    container.innerHTML = html;

    results.appendChild(container);
}

form.addEventListener(
    "submit",
    async function (event) {

        event.preventDefault();

        const participants =
            document.getElementById(
                "participants"
            ).value;

        const bookingDate =
            document.getElementById(
                "date"
            ).value;

        const startTime =
            document.getElementById(
                "startTime"
            ).value;

        const endTime =
            document.getElementById(
                "endTime"
            ).value;

        const checkboxes =
            document.querySelectorAll(
                '.resource input[type="checkbox"]:checked'
            );

        const resources = [];

        checkboxes.forEach(
            function (checkbox) {

                const resourceName =
                    checkbox
                        .nextElementSibling
                        .textContent
                        .trim();

                resources.push(resourceName);
            }
        );

        if (
            !participants ||
            !bookingDate ||
            !startTime ||
            !endTime
        ) {
            showErrorMessage(
                "Please fill all required fields."
            );
            return;
        }

        if (Number(participants) <= 0) {
            showErrorMessage(
                "Number of participants must be greater than zero."
            );
            return;
        }

        if (endTime <= startTime) {
            showErrorMessage(
                "End time must be after start time."
            );
            return;
        }

        selectedBookingDetails = {
            participants: participants,
            bookingDate: bookingDate,
            startTime: startTime,
            endTime: endTime
        };

        results.innerHTML = `
            <div class="result-card">
                <h3>Searching for available halls...</h3>
            </div>
        `;

        const requiredResources =
            resources.join(",");

        const url =
            `${API_BASE_URL}/available-halls` +
            `?participants=${encodeURIComponent(participants)}` +
            `&booking_date=${encodeURIComponent(bookingDate)}` +
            `&start_time=${encodeURIComponent(startTime)}` +
            `&end_time=${encodeURIComponent(endTime)}` +
            `&required_resources=${encodeURIComponent(requiredResources)}`;

        try {

            const response =
                await fetch(url);

            const data =
                await response.json();

            if (!response.ok) {

                showErrorMessage(
                    data.detail ||
                    "Unable to process the request."
                );

                return;
            }

            if (
                !data.available_halls ||
                data.available_halls.length === 0
            ) {

                results.innerHTML = `
                    <div class="result-card">
                        <h3>No suitable halls available</h3>
                        <p>
                            No hall matches your
                            capacity, time, and
                            resource requirements.
                        </p>
                    </div>
                `;

                displayAlternatives(
                    data.alternatives
                );

                return;
            }

            results.innerHTML = "";

            displayAvailableHalls(
                data.available_halls
            );

        } catch (error) {

            console.error(error);

            showErrorMessage(
                "Please make sure FastAPI is running and try again."
            );
        }
    }
);


aiSearchButton.addEventListener(
    "click",
    async function () {

        const message =
            aiMessage.value.trim();

        if (!message) {

            results.innerHTML = `
                <div class="result-card">
                    <h3>Describe your meeting</h3>
                    <p>
                        Example: I need a hall tomorrow
                        from 2 PM to 4 PM for 40 people
                        with a projector.
                    </p>
                </div>
            `;

            return;
        }

        results.innerHTML = `
            <div class="result-card">
                <h3>Processing your request...</h3>
                <p>Please wait.</p>
            </div>
        `;

        aiSearchButton.disabled = true;
        aiSearchButton.textContent =
            "Processing...";

        try {

            const response =
                await fetch(
                    `${API_BASE_URL}/ai-booking`,
                    {
                        method: "POST",
                        headers: {
                            "Content-Type":
                                "application/json"
                        },
                        body: JSON.stringify({
                            message: message
                        })
                    }
                );

            const data =
                await response.json();

            if (data.status === "irrelevant") {

                results.innerHTML = `
                    <div class="result-card">
                        <h3>Conference Hall Assistant</h3>

                        <p>
                            This assistant is designed
                            to help with conference
                            hall bookings.
                        </p>

                        <p>
                            Please describe your meeting
                            requirement, such as
                            participants, date, time,
                            and required resources.
                        </p>
                    </div>
                `;

                return;
            }

            if (
                data.status ===
                "unsupported_resource"
            ) {

                results.innerHTML = `
                    <div class="result-card">
                        <h3>Resource not currently supported</h3>

                        <p>
                            The system cannot currently
                            search for:
                            <strong>
                                ${data.unsupported_resources
                                    .map(escapeHtml)
                                    .join(", ")}
                            </strong>
                        </p>

                        <p>
                            Supported resources:
                            Projector,
                            Video Conferencing,
                            Microphone,
                            Whiteboard.
                        </p>
                    </div>
                `;

                return;
            }

            if (
                data.status ===
                "incomplete"
            ) {

                const fieldNames = {
                    participants:
                        "Number of participants",
                    date:
                        "Date",
                    start_time:
                        "Start time",
                    end_time:
                        "End time"
                };

                const missingFields =
                    data.missing_fields
                        .map(
                            function (field) {
                                return fieldNames[field];
                            }
                        )
                        .join(", ");

                const requirements =
                    data.requirements;

                results.innerHTML = `
                    <div class="result-card">
                        <h3>Almost there 👍</h3>

                        <p>
                            I understood your
                            booking request.
                        </p>

                        <p>
                            <strong>
                                Participants:
                            </strong>
                            ${
                                requirements.participants !== null
                                    ? escapeHtml(
                                        requirements.participants
                                    )
                                    : "Not provided"
                            }
                        </p>

                        <p>
                            <strong>
                                Still needed:
                            </strong>
                            ${escapeHtml(missingFields)}
                        </p>

                        <p>
                            Please provide the
                            missing information
                            and try again.
                        </p>
                    </div>
                `;

                return;
            }

            if (
                data.status ===
                "invalid"
            ) {

                results.innerHTML = `
                    <div class="result-card">
                        <h3>Invalid booking details</h3>

                        <p>
                            ${escapeHtml(
                                data.message
                            )}
                        </p>
                    </div>
                `;

                return;
            }

            if (
                data.status ===
                "error"
            ) {

                results.innerHTML = `
                    <div class="result-card">
                        <h3>Request temporarily unavailable</h3>

                        <p>
                            Please try again
                            in a moment.
                        </p>
                    </div>
                `;

                return;
            }

            if (
                data.status !==
                "complete"
            ) {

                results.innerHTML = `
                    <div class="result-card">
                        <h3>Unable to complete request</h3>

                        <p>
                            Please try describing
                            your meeting requirements
                            again.
                        </p>
                    </div>
                `;

                return;
            }

            const requirements =
                data.requirements;

            selectedBookingDetails = {
                participants:
                    requirements.participants,
                bookingDate:
                    requirements.date,
                startTime:
                    requirements.start_time,
                endTime:
                    requirements.end_time
            };

            const resourceText =
                requirements.resources.length > 0
                    ? requirements.resources
                        .map(escapeHtml)
                        .join(", ")
                    : "No specific resources";

            results.innerHTML = `
                <div class="result-card">
                    <h3>
                        Booking requirement
                        understood ✅
                    </h3>

                    <p>
                        <strong>
                            Participants:
                        </strong>
                        ${escapeHtml(
                            requirements.participants
                        )}
                    </p>

                    <p>
                        <strong>Date:</strong>
                        ${escapeHtml(
                            requirements.date
                        )}
                    </p>

                    <p>
                        <strong>Time:</strong>
                        ${escapeHtml(
                            requirements.start_time
                        )}
                        -
                        ${escapeHtml(
                            requirements.end_time
                        )}
                    </p>

                    <p>
                        <strong>Resources:</strong>
                        ${resourceText}
                    </p>
                </div>
            `;

            if (
                !data.available_halls ||
                data.available_halls.length === 0
            ) {

                results.innerHTML += `
                    <div class="result-card">
                        <h3>
                            No suitable halls available
                        </h3>

                        <p>
                            No hall matches your
                            requirements for the
                            selected date and time.
                        </p>
                    </div>
                `;

                displayAlternatives(
                    data.alternatives
                );

                return;
            }

            displayAvailableHalls(
                data.available_halls
            );

        } catch (error) {

            console.error(error);

            results.innerHTML = `
                <div class="result-card">
                    <h3>
                        Request temporarily unavailable
                    </h3>

                    <p>
                        Please make sure FastAPI
                        is running and try again.
                    </p>
                </div>
            `;

        } finally {

            aiSearchButton.disabled = false;

            aiSearchButton.textContent =
                "Find Hall with AI";
        }
    }
);


async function selectHall(
    hallId,
    hallName
) {

    results.innerHTML = `
        <div class="result-card">
            <h3>
                Booking
                ${escapeHtml(hallName)}...
            </h3>

            <p>Please wait...</p>
        </div>
    `;

    const bookingData = {
        hall_id: hallId,
        participants:
            Number(
                selectedBookingDetails.participants
            ),
        booking_date:
            selectedBookingDetails.bookingDate,
        start_time:
            selectedBookingDetails.startTime,
        end_time:
            selectedBookingDetails.endTime
    };

    try {

        const response =
            await fetch(
                `${API_BASE_URL}/bookings`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body:
                        JSON.stringify(
                            bookingData
                        )
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            if (response.status === 409) {

                results.innerHTML = `
                    <div class="result-card">
                        <h3>
                            Hall was just booked
                        </h3>

                        <p>
                            Someone else booked
                            this hall before your
                            request was completed.
                        </p>

                        <p>
                            Please search again
                            for another available hall.
                        </p>
                    </div>
                `;

                return;
            }

            showErrorMessage(
                data.detail ||
                "Unable to complete the booking."
            );

            return;
        }

        results.innerHTML = `
            <div class="result-card">
                <h3>
                    Booking Successful ✅
                </h3>

                <p>
                    <strong>Hall:</strong>
                    ${escapeHtml(hallName)}
                </p>

                <p>
                    <strong>Booking ID:</strong>
                    ${escapeHtml(
                        data.booking_id
                    )}
                </p>

                <p>
                    <strong>Date:</strong>
                    ${escapeHtml(
                        selectedBookingDetails.bookingDate
                    )}
                </p>

                <p>
                    <strong>Time:</strong>
                    ${escapeHtml(
                        selectedBookingDetails.startTime
                    )}
                    -
                    ${escapeHtml(
                        selectedBookingDetails.endTime
                    )}
                </p>

                <p>
                    <strong>Participants:</strong>
                    ${escapeHtml(
                        selectedBookingDetails.participants
                    )}
                </p>
            </div>
        `;

    } catch (error) {

        console.error(error);

        results.innerHTML = `
            <div class="result-card">
                <h3>
                    Booking temporarily unavailable
                </h3>

                <p>
                    Please make sure FastAPI
                    is running and try again.
                </p>
            </div>
        `;
    }
}
