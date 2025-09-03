# Virtual Receptionist 🤖  

Divya is an **AI-powered virtual receptionist** for an Info Services company. She acts as the first point of contact for anyone visiting — employees, interview candidates, or walk-in visitors. Divya verifies identities, notifies the right people, and keeps a record of visits.  

---

## ✨ Features  

✅ **Employee Verification**  
- Enter Name + Employee ID.  
- Receive OTP via email.  
- Secure login with retry limit.  

✅ **Candidate Verification**  
- Provide Interview Code + Name.  
- Divya notifies the assigned interviewer by email.  

✅ **Visitor Registration**  
- Enter Name, Phone Number, Purpose, and Employee to meet.  
- Visitor logged in `visitor_log.csv`.  
- Host employee notified by email.  

✅ **Manager Visit Greeting**  
- Managers listed in `manager_visit.csv` get a **VIP greeting** if visiting today’s office.  

✅ **Company Info Access**  
- Divya can answer company-related FAQs (from `company_info.pdf`).  

---

## 🚀 Getting Started  

### 1. Clone the Repository  
```bash
git clone https://github.com/YOUR_USERNAME/virtual-receptionist.git
cd virtual-receptionist
```

### 2. Create Virtual Environment  
```bash
python -m venv venv
# On macOS/Linux
source venv/bin/activate
# On Windows
venv\Scripts\activate
```

### 3. Install Dependencies  
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables  
Create a `.env` file in the root directory with:  

```env
# Gmail credentials (for sending OTPs & notifications)
GMAIL_USER=yourcompanyemail@gmail.com
GMAIL_APP_PASSWORD=xxxxxxx   # App-specific password

# Twilio (optional, for SMS support)
TWILIO_SID=xxxxxxx
TWILIO_AUTH=xxxxxxx
TWILIO_FROM=+1234567890
```

> ⚠️ Do **NOT** commit `.env` to GitHub (already ignored in `.gitignore`).  

### 5. Prepare Data Files  
Inside the `dummy-data/` folder, create these CSV files:  

#### 📂 `employee_details.csv`  
```csv
Name,EmployeeID,Email,Phone
Rakesh,E009,rakesh@company.com,+919876543210
Rahul Kumar,E010,rahul@company.com,+919876543211
```

#### 📂 `candidate_interview.csv`  
```csv
Candidate Name,Interview Role,HR Coordinator,Interviewer,Interview Time,Interview Code
Manish Patel,Business Analyst,Pooja Menon,Rahul Kumar,2025-09-04 14:30,INT009
```

#### 📂 `visitor_log.csv`  
*(auto-generated, no need to pre-fill)*  
```csv
Visitor Name,Phone,Purpose,Meeting Employee,Timestamp
```

#### 📂 `manager_visit.csv`  
```csv
Manager Name,EmployeeID,Office,Visit Date
Rakesh,E009,Chennai,2025-09-05
```

---

## ▶️ Running the Project  

Start the receptionist agent:  
```bash
python agent.py
```

Divya will now handle interactions according to `prompts.py` and your defined tools in `tools.py`.  

---

## 📂 Project Structure  

```
virtual-receptionist/
├── agent.py                # Main agent logic
├── tools.py                # Employee, Candidate, Visitor tools
├── prompts.py              # Agent instructions
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
├── dummy-data/             # Local data files (ignored in Git)
│   ├── employee_details.csv
│   ├── candidate_interview.csv
│   ├── visitor_log.csv
│   └── manager_visit.csv
└── .gitignore
```

---

## ⚡ Example Flows  

### Employee Flow  
```
User: "I am Rakesh, employee ID E009."
Divya: "Thanks Rakesh. Checking your record… I’ve sent an OTP to your email. Please tell me the OTP now."
User: "123456"
Divya: "✅ OTP verified. Welcome Rakesh!"
```

### Candidate Flow  
```
User: "I am Manish Patel, here for interview code INT009."
Divya: "Thanks Manish. Checking your record… ✅ Please wait, Rahul Kumar will meet you shortly."
```

### Visitor Flow  
```
User: "I’m Anil Kumar, here to meet Rakesh."
Divya: "Thanks Anil. Please provide your contact number."
User: "+91 9876543210"
Divya: "What is the purpose of your visit?"
User: "Partnership discussion."
Divya: "✅ I’ve logged your visit and informed Rakesh. Please wait at the reception."
```

### Manager Visit (VIP Greeting)  
```
User: "I am Rakesh, employee ID E009."
Divya: "Thanks Rakesh. Checking your record… I’ve sent an OTP to your email. Please tell me the OTP now."
User: "654321"
Divya: "✅ OTP verified. Welcome Rakesh! 🎉 I see you’re visiting our Chennai office today. Wishing you a productive and pleasant visit 🚀"
```

---

## 🛠 Troubleshooting  

- **❌ Email not sending** → Check Gmail App Password & `.env` setup.  
- **❌ Employee/Candidate not found** → Ensure CSV files are correctly formatted.  
- **❌ OTP incorrect** → OTPs are session-based; ask Divya to resend.  
- **FileNotFoundError** → Make sure CSV files exist in `dummy-data/`.  

---

## 🤝 Contributing  

1. Fork this repo  
2. Create a feature branch (`feature-new`)  
3. Commit changes  
4. Push to branch  
5. Open a Pull Request  

---

## 📜 License  
This project is licensed under the MIT License.  
