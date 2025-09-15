import os
import random
import requests
import smtplib
import speech_recognition as sr
import face_recognition
import cv2
from dotenv import load_dotenv
from datetime import datetime
from collections import defaultdict
from typing import Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from livekit.agents import function_tool, RunContext
from langchain_community.tools import DuckDuckGoSearchRun

# Appwrite SDK
from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.services.storage import Storage
from appwrite.query import Query

# ---------------- Config & Globals ----------------
load_dotenv()

APPWRITE_ENDPOINT = os.getenv("APPWRITE_ENDPOINT", "https://cloud.appwrite.io/v1")
APPWRITE_PROJECT = os.getenv("APPWRITE_PROJECT_ID")
APPWRITE_API_KEY = os.getenv("APPWRITE_API_KEY")
APPWRITE_DB_ID = os.getenv("APPWRITE_DB_ID", "ReceptionistDB")
FACES_BUCKET = "faces"

# Client
client = Client()
client.set_endpoint(APPWRITE_ENDPOINT) \
      .set_project(APPWRITE_PROJECT) \
      .set_key(APPWRITE_API_KEY)

databases = Databases(client)
storage = Storage(client)

otp_sessions = defaultdict(dict)
wake_word = "Clara"
sleep_phrase = "don't talk anything"
is_awake = True


# ================================================================
# COMPANY INFO
# ================================================================
@function_tool()
async def company_info(context: RunContext, query: str = "general") -> str:
    """Return company info stored in Appwrite (e.g., company_info table)."""
    try:
        result = databases.list_documents(APPWRITE_DB_ID, "company_info")
        if result["total"] == 0:
            return "❌ No company information available."

        text = " ".join([doc["text"] for doc in result["documents"] if "text" in doc])

        if query.lower() == "general":
            return text[:600] + "..."
        matches = [line for line in text.split(".") if query.lower() in line.lower()]
        return " | ".join(matches[:5]) if matches else f"No details found for '{query}'."
    except Exception as e:
        return f"❌ Error fetching company info: {e}"


# ================================================================
# EMPLOYEE VERIFICATION (OTP + MANAGER GREETING)
# ================================================================
@function_tool()
async def get_employee_details(context: RunContext, name: str, employee_id: str, otp: str = None) -> str:
    import re
    gmail_user = os.getenv("GMAIL_USER")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    try:
        # Step 1: Lookup Employee in Appwrite
        result = databases.list_documents(
            APPWRITE_DB_ID, "employees",
            [Query.equal("employeeId", employee_id), Query.equal("name", name)]
        )
        if result["total"] == 0:
            return "❌ Employee not found or mismatch."

        emp = result["documents"][0]
        emp_name = emp["name"]
        email = emp["email"]

        # Init session
        if email not in otp_sessions:
            otp_sessions[email] = {"otp": None, "verified": False, "attempts": 0}

        # Step 2: Send OTP
        if otp is None:
            generated_otp = str(random.randint(100000, 999999))
            otp_sessions[email].update({"otp": generated_otp, "verified": False, "attempts": 0})

            msg = MIMEMultipart()
            msg["From"] = gmail_user
            msg["To"] = email
            msg["Subject"] = "Your OTP"
            msg.attach(MIMEText(f"Hello {emp_name}, your OTP is: {generated_otp}", "plain"))

            try:
                server = smtplib.SMTP("smtp.gmail.com", 587)
                server.starttls()
                server.login(gmail_user, gmail_password)
                server.sendmail(gmail_user, [email], msg.as_string())
                server.quit()
            except Exception as e:
                return f"❌ Error sending OTP: {e}"

            return f"✅ Hi {emp_name}, OTP sent to {email}. Please provide it."

        # Step 3: Verify OTP
        saved_otp = otp_sessions[email]["otp"]
        attempts = otp_sessions[email]["attempts"]

        if attempts >= 3:
            otp_sessions[email] = {"otp": None, "verified": False, "attempts": 0}
            return "❌ Too many failed attempts. Restart verification."

        if otp.strip() == saved_otp:
            otp_sessions[email]["verified"] = True

            # Check Manager Visit Greeting
            mgr = databases.list_documents(
                APPWRITE_DB_ID, "manager_visits",
                [Query.equal("employeeId", employee_id),
                 Query.equal("visitDate", datetime.now().strftime("%Y-%m-%d"))]
            )
            if mgr["total"] > 0:
                office = mgr["documents"][0]["office"]
                return (f"✅ OTP verified. Welcome {emp_name}! 🎉\n"
                        f"It’s great to have you at our {office} office. "
                        "Hope your visit is meaningful and memorable!")

            return f"✅ OTP verified. Welcome {emp_name}!"
        else:
            otp_sessions[email]["attempts"] = attempts + 1
            return f"❌ Wrong OTP. Attempts left: {3 - (attempts+1)}"
    except Exception as e:
        return f"❌ Error: {e}"


# ================================================================
# CANDIDATE VERIFICATION
# ================================================================
@function_tool()
async def get_candidate_details(context: RunContext, candidate_name: str, interview_code: str) -> str:
    gmail_user = os.getenv("GMAIL_USER")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    try:
        # Lookup Candidate
        result = databases.list_documents(
            APPWRITE_DB_ID, "candidates",
            [Query.equal("candidateName", candidate_name), Query.equal("interviewCode", interview_code)]
        )
        if result["total"] == 0:
            return "❌ Candidate not found."

        cand = result["documents"][0]
        interviewer_email = cand["interviewerEmail"]
        cand_role, cand_time = cand["interviewRole"], cand["scheduledTime"]

        # Notify interviewer
        msg = MIMEMultipart()
        msg["From"] = gmail_user
        msg["To"] = interviewer_email
        msg["Subject"] = f"Candidate {candidate_name} has arrived"
        msg.attach(MIMEText(
            f"Hi,\n\nCandidate {candidate_name} has arrived for {cand_role} at {cand_time}.\n\nPlease meet them.", "plain"
        ))

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, [interviewer_email], msg.as_string())
            server.quit()
        except Exception as e:
            return f"❌ Email error: {e}"

        return f"✅ Candidate {candidate_name} verified. Interviewer has been notified."
    except Exception as e:
        return f"❌ Error verifying candidate: {e}"


# ================================================================
# VISITOR LOG + NOTIFY
# ================================================================
@function_tool()
async def log_and_notify_visitor(context: RunContext, visitor_name: str, phone: str, purpose: str, meeting_employee: str) -> str:
    gmail_user = os.getenv("GMAIL_USER")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    try:
        # Log visitor
        databases.create_document(APPWRITE_DB_ID, "visitors", "unique()", {
            "visitorName": visitor_name,
            "phone": phone,
            "purpose": purpose,
            "hostEmployeeName": meeting_employee,
            "timestamp": datetime.now().isoformat()
        })

        # Lookup employee email
        emp = databases.list_documents(APPWRITE_DB_ID, "employees", [Query.equal("name", meeting_employee)])
        if emp["total"] == 0:
            return f"❌ Employee {meeting_employee} not found."

        emp_email = emp["documents"][0]["email"]

        # Send email
        msg = MIMEMultipart()
        msg["From"] = gmail_user
        msg["To"] = emp_email
        msg["Subject"] = f"Visitor {visitor_name} at reception"
        msg.attach(MIMEText(
            f"Hi {meeting_employee},\n\nVisitor {visitor_name} is waiting.\nPurpose: {purpose}\nPhone: {phone}", "plain"
        ))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, [emp_email], msg.as_string())
        server.quit()

        return f"✅ Visitor {visitor_name} logged and {meeting_employee} notified."
    except Exception as e:
        return f"❌ Visitor flow error: {e}"


# ================================================================
# FACE RECOGNITION
# ================================================================
@function_tool()
async def verify_face(context: RunContext, employee_id: str, live_image_path: str) -> str:
    """Compare employee stored face with live capture."""
    try:
        # Fetch employee record
        emp = databases.list_documents(APPWRITE_DB_ID, "employees", [Query.equal("employeeId", employee_id)])
        if emp["total"] == 0:
            return "❌ Employee not found."

        photo_url = emp["documents"][0].get("photoUrl")
        if not photo_url:
            return "❌ No stored photo for employee."

        # Download stored photo (simplified: assume local path for demo)
        stored_img = face_recognition.load_image_file("employee.jpg")
        stored_enc = face_recognition.face_encodings(stored_img)[0]

        live_img = face_recognition.load_image_file(live_image_path)
        live_enc = face_recognition.face_encodings(live_img)[0]

        results = face_recognition.compare_faces([stored_enc], live_enc)
        return "✅ Face matched!" if results[0] else "❌ Face mismatch."
    except Exception as e:
        return f"❌ Face verification error: {e}"


# ================================================================
# OTHER TOOLS
# ================================================================
@function_tool()
async def listen_for_commands(context: RunContext) -> str:
    """Wake/Sleep detection."""
    global is_awake
    r = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        audio = r.listen(source, phrase_time_limit=5)

    try:
        text = r.recognize_google(audio).lower()
        if not is_awake:
            if wake_word in text:
                is_awake = True
                return "Wake word detected: Dhivya is active."
            return "Dhivya is sleeping."
        if sleep_phrase in text:
            is_awake = False
            return "Dhivya now sleeping."
        elif wake_word in text:
            return "Dhivya already active."
        else:
            return f"Dhivya heard: {text}"
    except:
        return "❌ Speech not recognized."


@function_tool()
async def get_weather(context: RunContext, city: str) -> str:
    try:
        r = requests.get(f"https://wttr.in/{city}?format=3")
        return r.text.strip() if r.status_code == 200 else "❌ Weather fetch failed."
    except Exception as e:
        return f"❌ Error: {e}"


@function_tool()
async def search_web(context: RunContext, query: str) -> str:
    try:
        return DuckDuckGoSearchRun().run(tool_input=query)
    except Exception as e:
        return f"❌ Web search error: {e}"


@function_tool()
async def send_email(context: RunContext, to_email: str, subject: str, message: str, cc_email: Optional[str] = None) -> str:
    try:
        gmail_user = os.getenv("GMAIL_USER")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD")
        msg = MIMEMultipart()
        msg["From"] = gmail_user
        msg["To"] = to_email
        msg["Subject"] = subject
        if cc_email: msg["Cc"] = cc_email
        msg.attach(MIMEText(message, "plain"))
        recipients = [to_email] + ([cc_email] if cc_email else [])
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, recipients, msg.as_string())
        server.quit()
        return "✅ Email sent."
    except Exception as e:
        return f"❌ Email error: {e}"
