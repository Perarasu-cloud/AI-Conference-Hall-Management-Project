from ai_service import extract_meeting_requirements


message = """
I need a conference hall tomorrow from 2 PM to 4 PM
for 40 people with a projector and video conferencing.
"""


result = extract_meeting_requirements(message)

print(result)