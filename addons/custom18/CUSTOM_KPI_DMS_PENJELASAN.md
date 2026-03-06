# Custom KPI OKR + DMS Feature Explanation (Odoo 18)

## 1) Solution Overview
This document explains two custom modules:
- `c18_performance` (KPI OKR)
- `c18_dms` (Document Management System)

Business goals:
- Run OKR-based performance planning from executive level down to staff.
- Manage documents in a structured way with approval, lifecycle, and auditability.
- Connect KPI check-ins with document evidence for accountability.

---

## 2) Personas and Access Roles
### KPI OKR (`c18_performance`)
- `C18 Performance User`: focused on KPI/check-in input and updates.
- `C18 Performance Manager`: validates check-ins, monitors department data, manages operational master data.
- `C18 Performance Executive`: focused on strategic monitoring via executive dashboards.

KPI access control:
- Users are restricted by their employee department.
- Managers have broader write/create/delete access than users.
- Executives are primarily read-oriented for oversight.

### DMS (`c18_dms`)
- `C18 DMS User`: uploads and manages working documents, submits for review.
- `C18 DMS Supervisor`: performs supervisor-level approval.
- `C18 DMS Manager`: performs final manager approval and compliance monitoring.
- `C18 DMS Executive`: management-level dashboard and oversight.

DMS access control:
- Documents/directories are restricted by `effective_department` or explicit user sharing.
- Version history and share logs follow document-level access control.
- External access is only available through validated public token links.

---

## 3) Main End-to-End Scenarios (Customer Demo)
### Scenario A: Q2 KPI Planning
1. HR/Manager creates a new cycle, for example **Q2 2026** (Apr-Jun 2026), then moves state from `Draft -> Open`.
2. Manager prepares `BSC Perspectives` (Financial, Customer, Internal Process, Learning & Growth).
3. Management creates company-level objectives and cascades them to department and individual objectives (parent-child hierarchy).
4. Each objective gets multiple KPIs (Key Results), including:
   - type (numeric/percentage/milestone),
   - target model (overall/periodic),
   - weight,
   - owner,
   - data source (manual/automatic).

### Scenario B: Monthly Execution and Review
1. Staff submits progress via `Quick Check-in` or `Mass Monthly Check-in`.
2. Check-ins are automatically created in `Pending` state and can include evidence attachments.
3. Manager reviews and either `Approves` or `Rejects` (with manager comments).
4. KPI automatically computes:
   - `achievement_rate`,
   - `kpi_progress`,
   - `rag` status (red/amber/green),
   - state (new/in_progress/successful/failed).
5. Objective progress is updated automatically based on KPI + aligned child objective calculations (weighted/equal).

### Scenario C: KPI Finalization
1. Near cycle end, manager ensures there are no pending check-ins.
2. Manager runs `Lock Score` on the objective:
   - system blocks locking if pending check-ins still exist,
   - final score is saved from the latest progress.
3. Objective can be moved to `Mark Done`, then cycle can be closed (`Locked -> Closed`) by authorized role.

### Scenario D: Policy and Evidence Documents (DMS)
1. User uploads SOP/policy/evidence documents into department directories.
2. Metadata defaults are inherited from directory (department + default tags).
3. Document is submitted for review:
   - supervisor review stage,
   - manager review stage (final approval).
4. After approval:
   - lifecycle dates are set automatically (next review & retention due),
   - document can be shared internally/externally as permitted.
5. If file content is replaced, previous version is preserved in `Version History`.

### Scenario E: External Sharing to Vendors/Auditors
1. User enables `allow_external_share`.
2. System generates token-based `share_url`.
3. Link is valid only when the document is:
   - in `approved` state,
   - not expired,
   - still within active share period.
4. Every public access is logged in `Share Audit Log` (page view/download, IP, user agent).
5. When share period expires, cron automatically revokes external sharing.

---

## 4) KPI OKR Module Features (`c18_performance`)
### 4.1 Master Data
- **Cycle**: annual/quarterly/custom, start-end date, review date, state workflow.
- **BSC Perspective**: strategic objective classification.

### 4.2 Objective Management
- Objective scope: company/department/individual.
- Hierarchy levels: management/manager/supervisor/staff.
- Parent-child objective alignment for OKR cascading.
- Progress methods:
  - `weighted`: uses KPI/alignment weights,
  - `equal`: simple average.
- Locking mechanism:
  - locked objectives/cycles block core field edits,
  - objective cannot be locked if related check-ins are still pending.

### 4.3 KPI / Key Result Management
- KR types:
  - `numeric`
  - `percentage`
  - `milestone`
- Target modes:
  - `overall`: single target value,
  - `periodic`: monthly target lines.
- Automatic KPI status:
  - RAG (red/amber/green),
  - KPI state (new/in_progress/successful/failed),
  - progress and achievement rate.
- Auto check-in data sources:
  - total employees,
  - department employees,
  - confirmed sales amount/count (if Sales module exists),
  - done project tasks (if Project/Task module is relevant).

### 4.4 Check-in and Approval
- Quick check-in wizard per KPI.
- Mass monthly check-in wizard for bulk submission.
- Evidence attachment per check-in.
- Approval states: pending/approved/rejected.
- Approval audit fields are auto-tracked (`approved_by`, `approved_date`).
- Validation rule: `period_date` must be the first day of the month.

### 4.5 Monitoring, Alerts, and Dashboards
- Overdue check-in detector.
- Weekly reminder cron for KPIs missing recent check-ins.
- Daily auto check-in cron for KPIs using automatic data sources.
- Role-based boards:
  - Staff Board,
  - Manager Board,
  - Operations Board,
  - Executive Board.
- Reporting views:
  - Company Health,
  - Department Leaderboard,
  - Cycle Scorecard,
  - Owner Scorecard.

---

## 5) DMS Module Features (`c18_dms`)
### 5.1 Document Structure and Metadata
- Hierarchical directories (parent-child) with full path (`complete_name`).
- Directory defaults:
  - default department,
  - default shared users,
  - default tags.
- Document metadata:
  - directory, department, project, document type, tags,
  - internal shared users/partners,
  - expiry date and lifecycle status.

### 5.2 Document Approval Workflow
- States:
  - draft -> supervisor_review -> manager_review -> approved/rejected.
- Reviewer auto-derivation from employee reporting lines.
- Review SLA based on `review_sla_days`.
- Process actions:
  - submit for review,
  - approve supervisor,
  - approve manager,
  - reject,
  - reset to draft.
- Chatter, mail activities, and email templates are used for process notifications.

### 5.3 Versioning and History
- When main attachment is replaced:
  - previous file is automatically moved to `Version History`.
- History actions:
  - preview,
  - download.

### 5.4 Internal and External Sharing
- Internal sharing:
  - through shared users/partners,
  - follower synchronization is automatic.
- External sharing:
  - tokenized public URL,
  - share status: inactive/active/expiring/expired,
  - quick expiry setup (7/30 days),
  - token regeneration,
  - manual revoke.
- Public access guard:
  - only approved documents,
  - must not be expired,
  - share window must still be active.

### 5.5 Audit Trail and Compliance
- All public page/download access is logged in `c18.dms.share.log`.
- Share audit export wizard supports CSV/XLSX.
- Compliance report provides:
  - total documents,
  - approved documents,
  - review overdue,
  - expiring/expired,
  - retention overdue.

### 5.6 Lifecycle and Retention
- Controlled by `Document Type`:
  - default review SLA,
  - review interval days,
  - retention days,
  - auto archive on retention.
- On approval, system sets:
  - `last_review_date`,
  - `next_review_date`,
  - `retention_due_date`.
- Daily cron jobs:
  - SLA overdue reminders,
  - lifecycle review reminders,
  - auto archive on retention due (if policy enabled),
  - auto revoke expired external share.

### 5.7 Fast Operations
- Multi-upload wizard for creating many documents in one action.
- “Apply Directory Defaults” for faster, consistent metadata input.

---

## 6) Dashboards to Present to Customer
### KPI OKR Dashboards
- Staff Board: daily execution focus (my objectives, my KPIs, my check-ins, overdue).
- Manager Board: pending approvals, rejected items, and department visibility.
- Executive Board: company health, cycle scorecard, hierarchy, owner scorecard.

### DMS Dashboards
- Staff Board: my docs, all docs, expiring docs, version history.
- Supervisor Board: pending supervisor reviews + overdue reviews.
- Manager Board: pending manager reviews + compliance monitoring.
- Management Board: spread report, share audit, compliance, revision trend.

---

## 7) Customer Business Value
- **Strong governance**: KPI and document processes include approval trails and auditable logs.
- **Cross-level transparency**: objectives cascade from executives to staff.
- **Compliance control**: SLA review, retention, and lifecycle are automated.
- **Operational efficiency**: quick/mass check-in, multi-upload, role-based dashboards.
- **Safer external collaboration**: tokenized sharing, expiry control, full access logging.

---

## 8) Key Talking Points for Presentation
- Demonstrate flow from `planning -> execution -> review -> lock -> evaluation`.
- Show connection between KPI check-ins and evidence documents.
- Compare role-specific dashboards (Staff vs Manager vs Executive).
- Show public share link behavior and download audit logs.
- Show retention auto-archive example to explain compliance impact.

---

## 9) Important Rules and Constraints to Explain
- Objective cannot be locked while related check-ins are pending.
- Check-in period must be the first day of each month.
- Core objective/KPI/check-in fields are restricted when objective/cycle is locked.
- Public share works only for approved and still-valid documents.
- Some KPI auto data sources depend on additional modules (for example Sales/Project).
