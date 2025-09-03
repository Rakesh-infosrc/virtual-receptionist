import logging
import os
import random
import requests
import smtplib
import speech_recognition as sr
import pandas as pd
from PyPDF2 import PdfReader
from dotenv import load_dotenv
from collections import defaultdict
from typing import Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from livekit.agents import function_tool, RunContext
from langchain_community.tools import DuckDuckGoSearchRun

load_dotenv()

# ---------------- Config & Globals ----------------
EMPLOYEE_CSV = r"C:\Users\Rakesh\Desktop\Data_Eng\POC_Ideas\friday_jarvis\Virtual_Receptionist\dummy-data\employee_details.csv"
CANDIDATE_CSV = r"C:\Users\Rakesh\Desktop\Data_Eng\POC_Ideas\friday_jarvis\Virtual_Receptionist\dummy-data\candidate_interview.csv"
COMPANY_INFO_PDF = r"C:\Users\Rakesh\Desktop\Data_Eng\POC_Ideas\friday_jarvis\Virtual_Receptionist\dummy-data\company_info.pdf"
VISITOR_LOG = r"C:\Users\Rakesh\Desktop\Data_Eng\POC_Ideas\friday_jarvis\Virtual_Receptionist\dummy-data\visitor_log.csv"
MANAGER_VISIT_CSV = r"C:\Users\Rakesh\Desktop\Data_Eng\POC_Ideas\friday_jarvis\Virtual_Receptionist\dummy-data\manager_visit.csv"

otp_sessions = defaultdict(dict)  # Track OTPs temporarily

wake_word = "dhivya"
sleep_phrase = "don't talk anything"
is_awake = True


# ---------------- Company Info ----------------
@function_tool()
async def company_info(
    context: RunContext,  # type: ignore
    query: str = "general"
) -> str:
    """
    Fetch company information from company_info.pdf.
    
    Args:
        query: Optional keyword to search inside the PDF. 
               If 'general', return the first page summary.
    """
    try:
        if not os.path.exists(COMPANY_INFO_PDF):
            return "Company information file is missing."

        reader = PdfReader(COMPANY_INFO_PDF)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"

        if not text.strip():
            return "Company information could not be extracted."

        # If user asked general
        if query.lower() == "general":
            return text[:600] + "..."  # return first ~600 chars

        # Search for keyword inside text
        query_lower = query.lower()
        matches = [line for line in text.split("\n") if query_lower in line.lower()]

        if matches:
            return " | ".join(matches[:5])  # return top 5 matches
        else:
            return f"No specific details found for '{query}'."

    except Exception as e:
        return f"Error reading company information: {str(e)}"   


# ---------------- Employee Verification (OTP) ----------------
# @function_tool()
# async def get_employee_details(
#     context: RunContext, name: str, employee_id: str, otp: str = None
# ) -> str:
#     """
#     Secure Employee Verification Tool with improvements:
#     1. Normalize inputs (case/whitespace tolerant).
#     2. Check if EmployeeID exists → then validate Name + ID.
#     3. Fetch email only from CSV (no user input).
#     4. Send OTP with retry limit (max 3 attempts).
#     5. Use session memory to avoid asking name/ID again.
#     """
#     import re

#     try:
#         # Load employee database
#         df = pd.read_csv(EMPLOYEE_CSV)
#         df["Name_norm"] = df["Name"].astype(str).str.strip().str.lower()
#         df["EmployeeID_norm"] = df["EmployeeID"].astype(str).str.strip().str.upper()

#         # Normalize user input
#         name_norm = re.sub(r"\s+", " ", name).strip().lower()
#         empid_norm = re.sub(r"\s+", "", employee_id).strip().upper()

#         # Step 1: Check if Employee ID exists
#         id_match = df[df["EmployeeID_norm"] == empid_norm]
#         if id_match.empty:
#             return "❌ Employee ID not found. Please recheck it."

#         # Step 2: Check Name + ID together
#         match = id_match[id_match["Name_norm"] == name_norm]
#         if match.empty:
#             return "❌ Name and Employee ID don’t match. Please try again."

#         # Step 3: Extract record
#         record = match.iloc[0]
#         email = str(record["Email"]).strip()
#         emp_name = record["Name"]

#         # Initialize session memory
#         if email not in otp_sessions:
#             otp_sessions[email] = {"otp": None, "verified": False, "attempts": 0}

#         # Step 4: If OTP not provided → generate & send
#         if otp is None:
#             generated_otp = str(random.randint(100000, 999999))
#             otp_sessions[email]["otp"] = generated_otp
#             otp_sessions[email]["verified"] = False
#             otp_sessions[email]["attempts"] = 0
#             otp_sessions[email]["name"] = emp_name
#             otp_sessions[email]["employee_id"] = record["EmployeeID"]

#             # Send OTP via Gmail
#             gmail_user = os.getenv("GMAIL_USER")
#             gmail_password = os.getenv("GMAIL_APP_PASSWORD")
#             if not gmail_user or not gmail_password:
#                 return "❌ Email sending failed: Gmail credentials not configured."

#             msg = MIMEMultipart()
#             msg["From"] = gmail_user
#             msg["To"] = email
#             msg["Subject"] = "Your One-Time Password (OTP)"
#             msg.attach(MIMEText(f"Hello {emp_name}, your OTP is: {generated_otp}", "plain"))

#             try:
#                 server = smtplib.SMTP("smtp.gmail.com", 587)
#                 server.starttls()
#                 server.login(gmail_user, gmail_password)
#                 server.sendmail(gmail_user, [email], msg.as_string())
#                 server.quit()
#             except Exception as e:
#                 return f"❌ Error sending OTP: {str(e)}"

#             return f"✅ Hi {emp_name}, I sent an OTP to your email ({email}). 👉 Please tell me the OTP now."

#         # Step 5: OTP verification
#         saved_otp = otp_sessions[email].get("otp")
#         attempts = otp_sessions[email].get("attempts", 0)

#         if attempts >= 3:
#             # Too many failures → reset session
#             otp_sessions[email] = {"otp": None, "verified": False, "attempts": 0}
#             return "❌ Too many failed attempts. Restart verification from the beginning."

#         if saved_otp and otp.strip() == saved_otp:
#             otp_sessions[email]["verified"] = True
#             return f"✅ OTP verified. Welcome {emp_name}! You now have full access to all tools."
#         else:
#             otp_sessions[email]["attempts"] = attempts + 1
#             return f"❌ OTP incorrect. Attempts left: {3 - (attempts + 1)}."

#     except FileNotFoundError:
#         return "❌ Employee database file is missing."
#     except Exception as e:
#         return f"❌ Error verifying employee: {str(e)}"

@function_tool()
async def get_employee_details(
    context: RunContext, name: str, employee_id: str, otp: str = None
) -> str:
    """
    Secure Employee Verification Tool with improvements:
    1. Normalize inputs (case/whitespace tolerant).
    2. Check if EmployeeID exists → then validate Name + ID.
    3. Fetch email only from CSV (no user input).
    4. Send OTP with retry limit (max 3 attempts).
    5. Use session memory to avoid asking name/ID again.
    6. NEW: After OTP success, check manager_visit.csv → if today matches, greet specially.
    """
    import re
    import pandas as pd
    import random, os, smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from datetime import datetime

    try:
        # Load employee database
        df = pd.read_csv(EMPLOYEE_CSV)
        df["Name_norm"] = df["Name"].astype(str).str.strip().str.lower()
        df["EmployeeID_norm"] = df["EmployeeID"].astype(str).str.strip().str.upper()

        # Normalize user input
        name_norm = re.sub(r"\s+", " ", name).strip().lower()
        empid_norm = re.sub(r"\s+", "", employee_id).strip().upper()

        # Step 1: Check if Employee ID exists
        id_match = df[df["EmployeeID_norm"] == empid_norm]
        if id_match.empty:
            return "❌ Employee ID not found. Please recheck it."

        # Step 2: Check Name + ID together
        match = id_match[id_match["Name_norm"] == name_norm]
        if match.empty:
            return "❌ Name and Employee ID don’t match. Please try again."

        # Step 3: Extract record
        record = match.iloc[0]
        email = str(record["Email"]).strip()
        emp_name = record["Name"]

        # Initialize session memory
        if email not in otp_sessions:
            otp_sessions[email] = {"otp": None, "verified": False, "attempts": 0}

        # Step 4: If OTP not provided → generate & send
        if otp is None:
            generated_otp = str(random.randint(100000, 999999))
            otp_sessions[email]["otp"] = generated_otp
            otp_sessions[email]["verified"] = False
            otp_sessions[email]["attempts"] = 0
            otp_sessions[email]["name"] = emp_name
            otp_sessions[email]["employee_id"] = record["EmployeeID"]

            # Send OTP via Gmail
            gmail_user = os.getenv("GMAIL_USER")
            gmail_password = os.getenv("GMAIL_APP_PASSWORD")
            if not gmail_user or not gmail_password:
                return "❌ Email sending failed: Gmail credentials not configured."

            msg = MIMEMultipart()
            msg["From"] = gmail_user
            msg["To"] = email
            msg["Subject"] = "Your One-Time Password (OTP)"
            msg.attach(MIMEText(f"Hello {emp_name}, your OTP is: {generated_otp}", "plain"))

            try:
                server = smtplib.SMTP("smtp.gmail.com", 587)
                server.starttls()
                server.login(gmail_user, gmail_password)
                server.sendmail(gmail_user, [email], msg.as_string())
                server.quit()
            except Exception as e:
                return f"❌ Error sending OTP: {str(e)}"

            return f"✅ Hi {emp_name}, I sent an OTP to your email ({email}). 👉 Please tell me the OTP now."

        # Step 5: OTP verification
        saved_otp = otp_sessions[email].get("otp")
        attempts = otp_sessions[email].get("attempts", 0)

        if attempts >= 3:
            # Too many failures → reset session
            otp_sessions[email] = {"otp": None, "verified": False, "attempts": 0}
            return "❌ Too many failed attempts. Restart verification from the beginning."

        if saved_otp and otp.strip() == saved_otp:
            otp_sessions[email]["verified"] = True

            # ✅ NEW: Manager Visit Greeting
            try:
                df_mgr = pd.read_csv(MANAGER_VISIT_CSV, dtype=str).fillna("")
                df_mgr["Visit Date"] = pd.to_datetime(df_mgr["Visit Date"]).dt.strftime("%Y-%m-%d")
                today = datetime.now().strftime("%Y-%m-%d")

                mgr_match = df_mgr[
                    (df_mgr["EmployeeID"].astype(str).str.strip().str.upper() == empid_norm) &
                    (df_mgr["Visit Date"] == today)
                ]
                if not mgr_match.empty:
                    office = mgr_match.iloc[0]["Office"]
                    return (
                        f"✅ OTP verified. Welcome {emp_name}! 🎉\n"
                        "Hope you had a smooth and comfortable journey"
                        f"It was wonderful having you at our {office} office!"
                        "We truly hope your visit was both memorable and meaningful."
                        f"Thanks so much for taking the time to be with us—it really meant a lot to the whole {office} team."
                    )
            except FileNotFoundError:
                pass  # skip if manager_visit.csv is missing

            # Normal employee greeting
            return f"✅ OTP verified. Welcome {emp_name}! You now have full access to all tools."
        else:
            otp_sessions[email]["attempts"] = attempts + 1
            return f"❌ OTP incorrect. Attempts left: {3 - (attempts + 1)}."

    except FileNotFoundError:
        return "❌ Employee database file is missing."
    except Exception as e:
        return f"❌ Error verifying employee: {str(e)}"


# ---------------- Candidate Verification ----------------
@function_tool()
async def get_candidate_details(
    context: RunContext, candidate_name: str, interview_code: str
) -> str:
    """
    Candidate verification tool (code-first approach):
    - Look up candidate by Interview Code (unique key).
    - Then cross-check the provided name.
    - Retry limit (max 3 attempts).
    - Notify interviewer via email if valid.
    """
    import re

    try:
        # Load candidate CSV as text (avoid dtype issues)
        df_candidates = pd.read_csv(CANDIDATE_CSV, dtype=str).fillna("")

        # Normalize interview codes in CSV
        df_candidates["InterviewCode_norm"] = (
            df_candidates["Interview Code"]
            .astype(str)
            .str.encode("ascii", "ignore")
            .str.decode("ascii")
            .str.strip()
            .str.replace(r"[^0-9A-Za-z]", "", regex=True)
            .str.upper()
        )

        # Normalize candidate names in CSV
        df_candidates["Candidate_norm"] = (
            df_candidates["Candidate Name"]
            .astype(str)
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
            .str.lower()
        )

        # Normalize user inputs
        code_norm = (
            interview_code.encode("ascii", "ignore").decode("ascii").strip().upper()
        )
        cand_name_norm = (
            candidate_name.encode("ascii", "ignore").decode("ascii").strip().lower()
        )

        # Step 1: Lookup by code
        record_match = df_candidates[df_candidates["InterviewCode_norm"] == code_norm]
        if record_match.empty:
            return f"❌ Interview code '{interview_code}' not found in today’s list."

        record = record_match.iloc[0]
        expected_name = record["Candidate_norm"]

        # Step 2: Verify name matches the code
        if cand_name_norm != expected_name:
            return (
                f"❌ The name '{candidate_name}' does not match our records "
                f"for interview code {interview_code}. Please recheck."
            )

        # Step 3: Retry memory for candidates
        session_key = code_norm
        if session_key not in otp_sessions:
            otp_sessions[session_key] = {"verified": False, "attempts": 0}

        attempts = otp_sessions[session_key].get("attempts", 0)
        if attempts >= 3:
            otp_sessions.pop(session_key, None)
            return "❌ Too many failed attempts. Please restart candidate verification."

        # Step 4: Notify interviewer
        interviewer_name = str(record["Interviewer"]).strip()
        cand_role = record["Interview Role"]
        cand_time = record["Interview Time"]

        # Load employees to get interviewer email
        df_employees = pd.read_csv(EMPLOYEE_CSV, dtype=str).fillna("")
        df_employees["Name_norm"] = (
            df_employees["Name"].astype(str).str.strip().str.lower()
        )

        interviewer = df_employees[
            df_employees["Name_norm"] == interviewer_name.strip().lower()
        ]
        if interviewer.empty:
            return f"❌ Interviewer '{interviewer_name}' not found in employee records."

        interviewer_email = interviewer.iloc[0]["Email"]

        # Gmail credentials
        gmail_user = os.getenv("GMAIL_USER")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD")
        if not gmail_user or not gmail_password:
            return "❌ Email sending failed: Gmail credentials not configured."

        # Prepare email
        msg = MIMEMultipart()
        msg["From"] = gmail_user
        msg["To"] = interviewer_email
        msg["Subject"] = f"Candidate {record['Candidate Name']} has arrived for interview"

        body = (
            f"Hi {interviewer_name},\n\n"
            f"Candidate {record['Candidate Name']} has arrived for the {cand_role} interview.\n\n"
            f"Interview Time: {cand_time}\n"
            f"Interview Code: {record['Interview Code']}\n\n"
            "Please let me know if you're ready to meet them."
        )
        msg.attach(MIMEText(body, "plain"))

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, [interviewer_email], msg.as_string())
            server.quit()
        except Exception as e:
            return f"❌ Error sending email to interviewer: {str(e)}"

        otp_sessions[session_key]["verified"] = True
        return (
            f"✅ Hello {record['Candidate Name']}, your interview for {cand_role} is scheduled at {cand_time}. "
            f"Please wait for a few moments, {interviewer_name} will meet you shortly."
        )

    except FileNotFoundError:
        return "❌ Candidate or employee database file is missing."
    except Exception as e:
        return f"❌ Error verifying candidate: {str(e)}"
    
# ---------------- Visitor Info Capture  ----------------
@function_tool()
async def log_and_notify_visitor(
    context: RunContext, visitor_name: str, phone: str, purpose: str, meeting_employee: str
) -> str:
    """
    Log visitor details and notify the employee via email.
    """
    import pandas as pd
    from datetime import datetime

    try:
        # Append visitor log
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "Visitor Name": visitor_name,
            "Phone": phone,
            "Purpose": purpose,
            "Meeting Employee": meeting_employee,
            "Timestamp": timestamp,
        }

        try:
            df = pd.read_csv(VISITOR_LOG)
        except FileNotFoundError:
            df = pd.DataFrame(columns=["Visitor Name", "Phone", "Purpose", "Meeting Employee", "Timestamp"])

        df = pd.concat([df, pd.DataFrame([log_entry])], ignore_index=True)
        df.to_csv(VISITOR_LOG, index=False)

        # Lookup employee email
        df_employees = pd.read_csv(EMPLOYEE_CSV, dtype=str).fillna("")
        df_employees["Name_norm"] = df_employees["Name"].str.strip().str.lower()
        emp_match = df_employees[df_employees["Name_norm"] == meeting_employee.strip().lower()]
        if emp_match.empty:
            return f"❌ Employee '{meeting_employee}' not found in records."

        emp_email = emp_match.iloc[0]["Email"]

        gmail_user = os.getenv("GMAIL_USER")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD")
        if not gmail_user or not gmail_password:
            return "❌ Email sending failed: Gmail credentials not configured."

        # Prepare email
        msg = MIMEMultipart()
        msg["From"] = gmail_user
        msg["To"] = emp_email
        msg["Subject"] = f"Visitor {visitor_name} is waiting for you at reception"

        body = (
            f"Hi {meeting_employee},\n\n"
            f"A visitor has arrived to meet you.\n\n"
            f"Name: {visitor_name}\n"
            f"Phone: {phone}\n"
            f"Purpose: {purpose}\n"
            f"Arrived at: {timestamp}\n\n"
            "Please proceed to reception."
        )
        msg.attach(MIMEText(body, "plain"))

        import smtplib
        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, [emp_email], msg.as_string())
            server.quit()
        except Exception as e:
            return f"❌ Error sending visitor email: {str(e)}"

        return f"✅ Visitor {visitor_name} logged and {meeting_employee} has been notified by email."

    except Exception as e:
        return f"❌ Error in visitor flow: {str(e)}"


# ---------------- Other Tools ----------------
@function_tool()
async def listen_for_commands(context: RunContext) -> str:
    """Wake & Sleep Word Detection."""
    global is_awake
    r = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        print("Listening...")
        r.adjust_for_ambient_noise(source)
        audio = r.listen(source, phrase_time_limit=5)

    try:
        text = r.recognize_google(audio).lower()
        print(f"Heard: {text}")

        if not is_awake:
            if wake_word in text:
                is_awake = True
                return "Wake word detected: Divya is now active."
            else:
                return "Divya is sleeping. (Silent mode active)"

        if sleep_phrase in text:
            is_awake = False
            return "Sleep command detected: Divya will now stay silent until you say 'dhivya'."
        elif wake_word in text:
            return "Divya is already active."
        else:
            return f"Divya is active. Heard: {text}"

    except sr.UnknownValueError:
        return "No recognizable speech detected."
    except Exception as e:
        return f"Error in wake/sleep detection: {e}"


@function_tool()
async def get_weather(context: RunContext, city: str) -> str:
    """Get the current weather for a given city."""
    try:
        response = requests.get(f"https://wttr.in/{city}?format=3")
        return response.text.strip() if response.status_code == 200 else "❌ Could not retrieve weather."
    except Exception as e:
        return f"❌ Error retrieving weather: {e}"


@function_tool()
async def search_web(context: RunContext, query: str) -> str:
    """Search the web using DuckDuckGo."""
    try:
        return DuckDuckGoSearchRun().run(tool_input=query)
    except Exception as e:
        return f"❌ Error searching the web: {e}"


@function_tool()
async def send_email(
    context: RunContext, to_email: str, subject: str, message: str, cc_email: Optional[str] = None
) -> str:
    """Send an email through Gmail."""
    try:
        gmail_user = os.getenv("GMAIL_USER")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD")
        if not gmail_user or not gmail_password:
            return "❌ Email sending failed: Gmail credentials not configured."

        msg = MIMEMultipart()
        msg["From"] = gmail_user
        msg["To"] = to_email
        msg["Subject"] = subject
        if cc_email:
            msg["Cc"] = cc_email
        msg.attach(MIMEText(message, "plain"))

        recipients = [to_email] + ([cc_email] if cc_email else [])

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, recipients, msg.as_string())
        server.quit()

        return f"✅ Email sent successfully to {to_email}"

    except Exception as e:
        return f"❌ Error sending email: {str(e)}"



# ---------------- Example Usage ----------------
if __name__ == "__main__":
    # Dummy context
    class DummyContext: pass
    ctx = DummyContext()