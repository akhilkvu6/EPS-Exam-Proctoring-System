# EPS Phoenix — Institutional Administrative Handbook

## 1. Overview & Institutional Governance

**EPS Phoenix** provides an end-to-end institutional examination lifecycle. This handbook outlines operational procedures for Institutional Administrators, Academic Faculty (Teachers), and Examination Officers.

---

## 2. Institutional Roles & Privileges

| Role | Permissions & Operational Scope |
|---|---|
| **Administrator (`ADMIN`)** | Master institutional governance. Manages institutional branding, onboards and approves faculty members, adjudicates escalated admission applications, audits system logs, reviews system health, and manages user account states (active/suspended). |
| **Faculty / Teacher (`TEACHER`)** | Scoped academic access. Reviews student admission dossiers in assigned departments, authors question banks within assigned subjects, configures and schedules examinations, monitors live invigilator consoles, issues proctoring warnings and time extensions, and grades subjective evaluation rubrics. |
| **Candidate / Student (`STUDENT`)** | Enrolled candidate. Submits admission dossiers, views enrolled subjects, enters exam lobbies, takes proctored exams in distraction-free rooms, views cryptographic receipts, and downloads published PDF scorecards. |

---

## 3. Admissions Workflow & Sequential Roll Allocation

```text
Student Registration
  ↓
Dossier Review Queue (Teacher Workspace)
  ↓
[Approve / Request Info / Reject / Escalate to Admin]
  ↓ (Approved)
Atomic Sequential Roll Allocation (select_for_update)
  ↓
Academic Cohort Enrollment
```

1. **Reviewing Dossiers**: Navigate to `Teacher Workspace` &rarr; `Admission Reviews`. Select a pending applicant to review their registered credentials and academic history.
2. **Standard Approval**: Selecting **Approve** triggers the atomic roll allocator. The system acquires a row lock on the departmental `RollSequenceCounter`, increments the monotonic sequence, stamps the official roll number (e.g. `CSE-2026-0001`), and creates an immutable audit record in `RollAllocationRecord`.
3. **Escalation**: If a candidate dossier contains non-standard credentials or requires dean-level clearance, click **Escalate to Admin**. The dossier is placed in the `Administration Workspace` &rarr; `Escalated Admissions` queue.

---

## 4. Academic Hierarchy & Scoping

EPS Phoenix enforces strict hierarchical scoping to prevent cross-department unauthorized access:
1. **Department**: Set up the parent faculty (e.g., Computer Science & Engineering).
2. **Course / Degree**: Define academic programs (e.g., B.Tech Computer Science).
3. **Academic Batch**: Register graduating cohorts (e.g., Batch 2026-2030).
4. **Semester**: Create active semester terms within the batch.
5. **Subject**: Create curriculum modules (e.g., CS101 Data Structures).
6. **Teacher Assignment**: Assign faculty members to instruct/invigilate specific Subjects for a specific Academic Batch.
7. **Student Enrollment**: Enrol candidates into the Academic Batch. When examinations are published, candidates enrolled in the batch are automatically provisioned onto the examination roster.

---

## 5. Question Bank Management & Snapshot Immutability

1. **Question Types Supported**:
   - Single Choice Objective (`MCQ_SINGLE`)
   - Multiple Choice Objective (`MCQ_MULTI`)
   - True / False (`TRUE_FALSE`)
   - Fill in the Blanks (`FILL_BLANKS`)
   - Numerical Value with Tolerance Band (`NUMERICAL`)
   - Short Answer (`SHORT_ANSWER`)
   - Descriptive / Essay with Rubric Criteria (`DESCRIPTIVE`)
   - Image-Based Prompt (`IMAGE_BASED`)
2. **Versioned Question Snapshots**:
   When questions are configured into an examination section, an immutable `QuestionSnapshot` is permanently generated. Future edits to the Question Bank increment the version counter (`v1` &rarr; `v2`) without modifying or invalidating ongoing or past examinations.

---

## 6. Examination Delivery & Invigilator Operations

### 6.1 Publishing & Scheduling
- In `Teacher Workspace` &rarr; `Examinations`, create an examination with title, code, start window, end window, duration minutes, and late entry grace period.
- Add sections and associate questions.
- Click **Publish Examination**. The system recalculates total marks, verifies all questions, and auto-provisions `CandidateAssignment` records for all students in the batch.

### 6.2 Distraction-Free Exam Room
- Candidates enter the exam lobby via `/exam/lobby/<exam_code>/`.
- The system checks eligibility and initiates an `ExamAttempt` with a server-authoritative `expires_at` timestamp.
- **Dual-Layer Autosave**:
  - *Layer 1*: 600ms debounced network sync to `/exam/api/<attempt_id>/sync/`.
  - *Layer 2*: Offline IndexedDB/localStorage journal that queues unsynced answers during network dropouts and automatically flushes upon reconnection.

### 6.3 Real-Time Invigilation & Disciplinary Interventions
- Access the live console at `/incidents/live/<exam_id>/`.
- **Live Candidate Dossiers**: Displays candidate progress, answer count, and dynamic Trust Score.
- **Intervention Actions**:
  - *Issue Warning*: Sends an instant warning alert that displays on the student's exam room screen.
  - *Grant Time Extension*: Adds extra minutes to the candidate's server-authoritative timer.
  - *Disciplinary Termination*: Force-submits the candidate's exam attempt for cause and records an incident review.

---

## 7. Evaluation, Results & Cryptographic PDF Scorecards

1. **Auto-Grading Objective Items**:
   Navigate to `/evaluation/cohort/<exam_id>/` and click **Run Auto-Grader**. Single MCQ, Multi MCQ, True/False, Fill in the Blanks, and Numerical items are scored deterministically according to version-locked snapshot criteria, applying negative marking where configured.
2. **Subjective Rubric Evaluation**:
   Open the subjective queue to review descriptive responses against the teacher's grading rubric, awarding marks and constructive feedback.
3. **Cohort Result Publication**:
   Click **Publish Cohort Results**. The platform computes final percentages, assigns institutional grade letters (`O`, `A+`, `A`, `B+`, `B`, `C`, `F`), and derives a cryptographic SHA-256 verification hash:
   $$\text{hash} = \text{SHA-256}(\text{Roll} : \text{ExamCode} : \text{Score} : \text{Date} : \text{AttemptId})$$
4. **PDF Scorecard Access**:
   Students can view and download their official ReportLab PDF transcript via `/results/scorecard/<result_id>/pdf/`.
5. **Public Verification Portal**:
   Employers and registrars can authenticate transcripts at `/results/verify/<result_id>/` without requiring authentication.

---

## 8. Emergency Recovery & Disaster Procedures

- **Candidate Power Outage / Computer Crash**:
  The candidate's answers are safely held in the server database (via Layer 1 autosave) and local storage (via Layer 2). The candidate can log in on any supported device, re-open the examination room, and resume work with all saved answers restored.
- **Network Interruptions During Exam**:
  The candidate interface continues to function seamlessly offline. Candidate answers are journaled locally. When connection restores, the browser silently flushes the journal.
- **Server Timer Absolute Expiry**:
  If the candidate's device loses power or disconnects permanently, the server-authoritative countdown ensures that once `expires_at` is reached, the attempt is marked `AUTO_SUBMITTED` with whatever answers were last saved.
