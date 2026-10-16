# EPS Installation & Comprehensive User Guide

**Project:** EPS — Exam Proctoring System  
**Guide Version:** 2.0  
**Target Audience:** Students, Faculty, Administrators, and System Evaluators  
**Date:** October 15, 2026  

---

## 1. System Requirements & Prerequisites

### 1.1 Minimum Hardware Requirements
- **Processor:** 1.5 GHz dual-core or faster (Intel / AMD / Apple Silicon).
- **RAM:** Minimum 4 GB (8 GB recommended for concurrent multi-student invigilation).
- **Disk Space:** 500 MB free storage for application files and SQLite database.
- **Peripherals (for Students):** Integrated or USB webcam and microphone for live proctoring.

### 1.2 Software Prerequisites
- **Operating System:** Windows 10/11, macOS 12+, or Ubuntu/Debian Linux 22.04 LTS.
- **Python:** Python 3.12, 3.13, or 3.14.
- **Web Browser:** Modern Chromium-based browser (Google Chrome 115+, Microsoft Edge 115+, Brave) or Mozilla Firefox 115+ with camera permissions enabled.

---

## 2. Step-by-Step Installation Instructions

### 2.1 Clone or Navigate to Project
```powershell
cd C:\Users\akhil\OneDrive\Desktop\EPS-Exam-Proctoring-System
```

### 2.2 Create & Activate Python Virtual Environment
```powershell
# Create virtual environment
python -m venv venv

# Activate on Windows PowerShell:
.\venv\Scripts\Activate.ps1

# (Or activate on Linux/macOS: source venv/bin/activate)
```

### 2.3 Install Python Dependencies
```powershell
pip install -r requirements.txt
# Alternatively, core dependencies:
pip install Django==6.1.1 pandas openpyxl pillow
```

### 2.4 Apply Database Migrations
```powershell
python manage.py migrate
```

### 2.5 Create an Administrator Superuser (Optional)
If setting up a fresh database:
```powershell
python manage.py createsuperuser
```
Follow prompts to enter username (e.g. `admin`), email (leave blank or enter placeholder), and password.

### 2.6 Run Development Server
```powershell
python manage.py runserver 127.0.0.1:8000
```
Open your browser and navigate to: `http://127.0.0.1:8000/`

---

## 3. Seed Accounts & Credentials

The pre-populated database `db.sqlite3` contains active, verified institutional accounts for demonstration:

| Role | Username | Password | Purpose |
|---|---|---|---|
| **Administrator** | `admin` | `admin123` | Institutional control center, teacher approvals, user audit |
| **Faculty / Teacher** | `teacher_test_01` | `teacher123` | Exam authoring, student approval, live invigilation |
| **Faculty (Alternative)**| `prof_anita` | `teacher123` | Departmental verification & exam administration |
| **Student** | `student_test_01` | `student123` | Taking exams, reviewing scorecards and proctoring telemetry |
| **Student (Alternative)**| `student_priya` | `student123` | Multi-student attempt simulation and verification |

---

## 4. Student User Guide

### 4.1 Registration & Account Approval
1. Navigate to `http://127.0.0.1:8000/accounts/student/register/`.
2. Fill in username, full name, enrollment number (e.g. `BCA-2026-089`), department, semester, and password.
3. Submit the form. Your account enters the **Pending Approval** state.
4. **Zero-Email Policy Notice:** No email confirmation will be sent. A faculty member will approve your registration in-app. Once approved, you can log in immediately.

### 4.2 Logging In & Student Command Center
1. Navigate to `/accounts/login/` and log in with your credentials.
2. The Student Dashboard presents:
   - Your active integrity score and attempt counts.
   - Available upcoming examinations.
   - Historical exam performance scorecards.

### 4.3 Taking an Examination & The Proctoring HUD
1. Click **"Enter Exam"** on an active test from your catalog.
2. Read the institutional exam rules and click **"I Agree & Start Exam"**.
3. Allow browser camera permissions when prompted.
4. **The Live Exam Room:**
   - **Proctoring HUD (Left Panel):** Displays your live video feed, real-time countdown timer, and tab-switch warning badge.
   - **Exam Workspace (Right Panel):** Displays the current question, multiple-choice options, and text fields for descriptive responses.
   - **Autosave:** Your answers save automatically in real time whenever an option is selected.
   - **Question Palette (Bottom):** Jump directly to any question by clicking its number pill.
5. **Exam Rules & Strict Conduct:**
   - Do **NOT** switch browser tabs or minimize the window. Every tab switch is logged and flagged on the teacher's monitor.
   - Do **NOT** attempt to copy, paste, or right-click. Clipboard actions are blocked.
   - Maintain face visibility within the webcam frame.

### 4.4 Submitting & Reviewing Results
1. Click **"Submit Examination"** when complete.
2. Confirm the submission prompt.
3. Once published by faculty, view your detailed score breakdown, percentage, grade, and proctoring integrity report under **"My Results"**.

---

## 5. Teacher / Faculty User Guide

### 5.1 Registration & Admin Clearance
1. Register at `/accounts/teacher/register/` with your Employee ID and academic department.
2. An institutional administrator will approve your profile in the Admin Control Center.

### 5.2 Student Approvals Queue
1. Log in to the Teacher Portal. If students have registered, an alert badge appears on your dashboard.
2. Click **"Student Approvals"** (`/accounts/teacher/student-approvals/`).
3. Review the student's name and enrollment number. Click **"Approve"** to grant instant exam access.

### 5.3 Creating & Managing Examinations
1. Click **"Create Exam"** (`/exams/create/`).
2. Specify title, academic course/subject, duration (in minutes), pass percentage, and toggle **"Enable Proctoring"**.
3. Add questions directly or select existing questions from your centralized **Question Bank**.

### 5.4 Live Invigilation Monitor
1. While an examination is in progress, navigate to **"Live Invigilation"** (`/exams/<id>/invigilate/`).
2. The radar dashboard displays all connected students in real time:
   - **Green Badge:** Normal, attentive student.
   - **Yellow Badge:** Minor violations (1-2 tab switches).
   - **Red Badge:** Serious infractions (multiple faces detected, repeated fullscreen exits).
3. Click any student card to inspect their timestamped proctoring violation log.

### 5.5 Grading Descriptive Answers
1. Navigate to **"Submissions"** after an exam concludes.
2. Click **"Evaluate"** on student attempts with descriptive answers.
3. Review student answers, assign marks, enter instructor feedback, and click **"Save Evaluation & Publish"**.

---

## 6. Administrator User Guide

### 6.1 Administrator Control Center
1. Log in with admin credentials at `/accounts/login/`.
2. The Admin Dashboard (`/accounts/admin/dashboard/`) provides institutional visibility:
   - Total registered students, faculty, exams, and system health status.
   - Real-time audit logs of administrative actions.

### 6.2 Faculty Approvals
1. Click **"Teacher Approvals"** (`/accounts/admin/teacher-approvals/`).
2. Review pending faculty registrations and click **"Approve Faculty"**.

### 6.3 Batch Excel Student Import
1. Navigate to **"Import Students"** (`/accounts/admin/import-students/`).
2. Upload an `.xlsx` spreadsheet containing: `username`, `first_name`, `last_name`, `enrollment_number`, `department`, `semester`.
3. The system parses the spreadsheet, creates pre-approved student accounts in bulk, and reports the import summary.

---

## 7. Troubleshooting & FAQ

- **Q: Camera feed shows a black screen in the exam room.**  
  *A:* Click the lock/tune icon in the browser address bar, set **Camera** to "Allow", and refresh the page.
- **Q: My exam timer reached zero while answering.**  
  *A:* The system automatically packages all autosaved answers and safely marks your attempt as `AUTO_SUBMITTED`. No responses are lost.
- **Q: How do students reset their password without email?**  
  *A:* In accordance with the zero-email policy, password resets are processed in-app by contacting the institutional faculty administrator, who can update user credentials through the user management console.
