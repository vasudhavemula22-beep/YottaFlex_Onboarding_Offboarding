
# YottaFlex Data Dictionary & Specification Manual

## Canonical Seed: 20261022
## Target Storage Engine: SQLite 3

---

### 1. `departments`
Stores organizational divisions managing cost centers and headcount.

| Field Name | SQL Type | Python Type | Nullable | Uniqueness | Allowed Values / Pattern | Units | Description & Validation Rule | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `dept_id` | `TEXT` | `str` | NO | PRIMARY KEY | `GLOB 'DEP-[0-9][0-9][0-9]'` | Code | Deterministic 3-digit department identifier | `DEP-001` |
| `dept_name` | `TEXT` | `str` | NO | UNIQUE | Length > 1 | Text | Canonical name of business division | `Engineering` |
| `cost_center` | `TEXT` | `str` | NO | UNIQUE | `GLOB 'CC-[0-9][0-9][0-9][0-9]'` | Code | General ledger accounting code | `CC-1001` |
| `created_at` | `TEXT` | `str` | NO | NONE | ISO-8601 UTC `YYYY-MM-DD HH:MM:SS` | UTC Time | Record creation timestamp | `2026-01-01 08:00:00` |

---

### 2. `roles`
Stores specific positions within departments with baseline access definitions.

| Field Name | SQL Type | Python Type | Nullable | Uniqueness | Allowed Values / Pattern | Units | Description & Validation Rule | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `role_id` | `TEXT` | `str` | NO | PRIMARY KEY | `GLOB 'ROL-[0-9][0-9][0-9]'` | Code | Deterministic role identifier | `ROL-001` |
| `role_title` | `TEXT` | `str` | NO | COMPOSITE (dept_id) | Length > 1 | Text | Functional job title | `Senior DevOps Engineer` |
| `dept_id` | `TEXT` | `str` | NO | FOREIGN KEY | References `departments(dept_id)` | FK | Owning department ID | `DEP-001` |
| `standard_access_profile` | `TEXT` | `str` | NO | NONE | `STANDARD_USER`, `ELEVATED_USER`, `DEPT_ADMIN`, `SYSTEM_ADMIN` | Enum | Baseline security profile | `ELEVATED_USER` |
| `created_at` | `TEXT` | `str` | NO | NONE | ISO-8601 UTC `YYYY-MM-DD HH:MM:SS` | UTC Time | Record creation timestamp | `2026-01-01 08:00:00` |

---

### 3. `employees`
Core master entity representing workers throughout their employment lifecycle.

| Field Name | SQL Type | Python Type | Nullable | Uniqueness | Allowed Values / Pattern | Units | Description & Validation Rule | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `employee_id` | `TEXT` | `str` | NO | PRIMARY KEY | `GLOB 'EMP-[0-9][0-9][0-9][0-9][0-9][0-9]'` | Code | Deterministic 6-digit employee ID | `EMP-000001` |
| `first_name` | `TEXT` | `str` | NO | NONE | Length > 0 | Text | Employee first legal name | `Alex` |
| `last_name` | `TEXT` | `str` | NO | NONE | Length > 0 | Text | Employee last legal name | `Vance` |
| `email` | `TEXT` | `str` | NO | UNIQUE | RFC-compliant standard format | Email | Corporate email address | `alex.vance@yottaflex.internal` |
| `role_id` | `TEXT` | `str` | NO | FOREIGN KEY | References `roles(role_id)` | FK | Current active role | `ROL-001` |
| `dept_id` | `TEXT` | `str` | NO | FOREIGN KEY | References `departments(dept_id)` | FK | Current active department | `DEP-001` |
| `manager_id` | `TEXT` | `str` | YES | FOREIGN KEY | References `employees(employee_id)` | FK | Supervisory manager (null for top executive) | `EMP-000010` |
| `employment_type` | `TEXT` | `str` | NO | NONE | `FULL_TIME`, `CONTRACTOR`, `INTERN` | Enum | Worker contract type | `FULL_TIME` |
| `employment_status`| `TEXT` | `str` | NO | NONE | `PRE_HIRE`, `ACTIVE`, `ROLE_CHANGE`, `TERMINATED`, `LEAVE` | Enum | Real-time employment status | `ACTIVE` |
| `hire_date` | `TEXT` | `str` | NO | NONE | `YYYY-MM-DD` | Date | Date offer was formalized | `2026-01-15` |
| `start_date` | `TEXT` | `str` | NO | NONE | `YYYY-MM-DD` | Date | Official first day of work | `2026-02-01` |
| `termination_date`| `TEXT` | `str` | YES | NONE | `YYYY-MM-DD` | Date | Final day of employment (NULL if active) | `2026-10-15` |
| `created_at` | `TEXT` | `str` | NO | NONE | ISO-8601 UTC `YYYY-MM-DD HH:MM:SS` | UTC Time | Record creation timestamp | `2026-01-15 09:30:00` |
| `updated_at` | `TEXT` | `str` | NO | NONE | ISO-8601 UTC `YYYY-MM-DD HH:MM:SS` | UTC Time | Record modification timestamp | `2026-02-01 08:00:00` |

---

### 4. `managers`
Explicit organizational roster identifying appointed managers and their oversight span.

| Field Name | SQL Type | Python Type | Nullable | Uniqueness | Allowed Values / Pattern | Units | Description & Validation Rule | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `manager_id` | `TEXT` | `str` | NO | PRIMARY KEY | `GLOB 'MGR-[0-9][0-9][0-9][0-9][0-9][0-9]'` | Code | Deterministic manager appointment ID | `MGR-000001` |
| `employee_id` | `TEXT` | `str` | NO | UNIQUE | References `employees(employee_id)` | FK | Employee serving as manager | `EMP-000010` |
| `dept_id` | `TEXT` | `str` | NO | FOREIGN KEY | References `departments(dept_id)` | FK | Department under manager's oversight | `DEP-001` |
| `is_active` | `INTEGER`| `int` | NO | NONE | `0` or `1` | Boolean | Whether managerial authority is active | `1` |
| `appointed_at` | `TEXT` | `str` | NO | NONE | ISO-8601 UTC `YYYY-MM-DD HH:MM:SS` | UTC Time | Appointment effective timestamp | `2026-01-01 00:00:00` |

---

### 5. `onboarding_cases`
Lifecycle container tracking onboarding from offer acceptance to verified completion.

| Field Name | SQL Type | Python Type | Nullable | Uniqueness | Allowed Values / Pattern | Units | Description & Validation Rule | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `onboarding_case_id` | `TEXT` | `str` | NO | PRIMARY KEY | `GLOB 'ONB-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]'` | Code | Deterministic onboarding case ID | `ONB-2026-000001` |
| `employee_id` | `TEXT` | `str` | NO | UNIQUE | References `employees(employee_id)` | FK | Employee being onboarded | `EMP-000001` |
| `target_start_date` | `TEXT` | `str` | NO | NONE | `YYYY-MM-DD` | Date | Planned employment start date | `2026-02-01` |
| `actual_start_date` | `TEXT` | `str` | YES | NONE | `YYYY-MM-DD` | Date | Actual start date | `2026-02-01` |
| `status` | `TEXT` | `str` | NO | NONE | `DRAFT`, `PRE_BOARDING`, `IN_PROGRESS`, `COMPLETED`, `DELAYED`, `CANCELLED` | Enum | Case lifecycle status | `IN_PROGRESS` |
| `created_at` | `TEXT` | `str` | NO | NONE | ISO-8601 UTC `YYYY-MM-DD HH:MM:SS` | UTC Time | Case initialization timestamp | `2026-01-15 09:00:00` |
| `completed_at` | `TEXT` | `str` | YES | NONE | ISO-8601 UTC timestamp or NULL | UTC Time | Timestamp when all tasks finalized | `2026-02-02 17:00:00` |

---

### 6. `tasks`
Discrete actionable work items required during onboarding or offboarding.

| Field Name | SQL Type | Python Type | Nullable | Uniqueness | Allowed Values / Pattern | Units | Description & Validation Rule | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `task_id` | `TEXT` | `str` | NO | PRIMARY KEY | `GLOB 'TASK-[A-Z0-9-]*'` | Code | Deterministic task identifier | `TASK-ONB-2026-000001-001` |
| `case_type` | `TEXT` | `str` | NO | NONE | `ONBOARDING`, `OFFBOARDING` | Enum | Workflow context | `ONBOARDING` |
| `case_id` | `TEXT` | `str` | NO | NONE | Matches `onboarding_case_id` or `offboarding_case_id` | ID | Owning case identifier | `ONB-2026-000001` |
| `task_name` | `TEXT` | `str` | NO | NONE | Length > 1 | Text | Human-readable title of activity | `Provision Corporate Laptop` |
| `task_category` | `TEXT` | `str` | NO | NONE | `DOCUMENTATION`, `IT_PROVISIONING`, `TRAINING`, `HARDWARE`, `HR_APPROVAL`, `SECURITY` | Enum | Workstream classification | `HARDWARE` |
| `assigned_actor`| `TEXT` | `str` | NO | NONE | `CANDIDATE`, `MANAGER`, `HR_PARTNER`, `IT_OPERATIONS`, `SYSTEM_ADMIN` | Enum | Role responsible for execution | `IT_OPERATIONS` |
| `status` | `TEXT` | `str` | NO | NONE | `BLOCKED`, `PENDING`, `IN_PROGRESS`, `COMPLETED`, `FAILED`, `WAIVED` | Enum | Operational task state | `COMPLETED` |
| `due_date` | `TEXT` | `str` | NO | NONE | `YYYY-MM-DD` | Date | Target completion date | `2026-01-28` |
| `completed_at` | `TEXT` | `str` | YES | NONE | ISO-8601 UTC timestamp or NULL | UTC Time | Resolution timestamp | `2026-01-27 16:30:00` |
| `created_at` | `TEXT` | `str` | NO | NONE | ISO-8601 UTC `YYYY-MM-DD HH:MM:SS` | UTC Time | Task creation timestamp | `2026-01-15 09:00:00` |

---

### 7. `task_dependencies`
Bridge table establishing directed edges for task workflow sequences (DAG).

| Field Name | SQL Type | Python Type | Nullable | Uniqueness | Allowed Values / Pattern | Units | Description & Validation Rule | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `dependency_id` | `TEXT` | `str` | NO | PRIMARY KEY | `GLOB 'DEP-TASK-[A-Z0-9-]*'` | Code | Deterministic edge identifier | `DEP-TASK-ONB-2026-000001-002-001` |
| `task_id` | `TEXT` | `str` | NO | COMPOSITE | References `tasks(task_id)` | FK | Target dependent task | `TASK-ONB-2026-000001-002` |
| `prerequisite_task_id` | `TEXT` | `str` | NO | COMPOSITE | References `tasks(task_id)` | FK | Required prerequisite task | `TASK-ONB-2026-000001-001` |
| `created_at` | `TEXT` | `str` | NO | NONE | ISO-8601 UTC `YYYY-MM-DD HH:MM:SS` | UTC Time | Creation timestamp | `2026-01-15 09:00:00` |

---

### 8. `access_roles`
Catalog of system privileges, access permissions, and risk tiers.

| Field Name | SQL Type | Python Type | Nullable | Uniqueness | Allowed Values / Pattern | Units | Description & Validation Rule | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `access_role_id`| `TEXT` | `str` | NO | PRIMARY KEY | `GLOB 'ACR-[0-9][0-9][0-9]'` | Code | Deterministic access role ID | `ACR-001` |
| `role_name` | `TEXT` | `str` | NO | UNIQUE | Length > 1 | Text | Name of system entitlement | `Production AWS Admin` |
| `system_name` | `TEXT` | `str` | NO | NONE | Length > 1 | Text | Host system or SaaS application | `Amazon Web Services` |
| `risk_level` | `TEXT` | `str` | NO | NONE | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` | Enum | Inherent security risk tier | `CRITICAL` |
| `requires_manager_approval` | `INTEGER` | `int` | NO | NONE | `0` or `1` | Boolean | Manager sign-off flag | `1` |
| `requires_hr_approval` | `INTEGER` | `int` | NO | NONE | `0` or `1` | Boolean | HR partner sign-off flag | `0` |
| `created_at` | `TEXT` | `str` | NO | NONE | ISO-8601 UTC `YYYY-MM-DD HH:MM:SS` | UTC Time | Creation timestamp | `2026-01-01 00:00:00` |

---

### 9. `access_grants`
Bridge entity representing point-in-time access entitlements issued to employees.

| Field Name | SQL Type | Python Type | Nullable | Uniqueness | Allowed Values / Pattern | Units | Description & Validation Rule | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `grant_id` | `TEXT` | `str` | NO | PRIMARY KEY | `GLOB 'GRANT-EMP-[0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9]'` | Code | Deterministic grant ID | `GRANT-EMP-000001-001` |
| `employee_id` | `TEXT` | `str` | NO | FOREIGN KEY | References `employees(employee_id)` | FK | Receiving employee | `EMP-000001` |
| `access_role_id`| `TEXT` | `str` | NO | FOREIGN KEY | References `access_roles(access_role_id)`| FK | Entitlement granted | `ACR-001` |
| `status` | `TEXT` | `str` | NO | NONE | `REQUESTED`, `APPROVED`, `ACTIVE`, `REVOKED`, `REJECTED` | Enum | Current access status | `ACTIVE` |
| `granted_at` | `TEXT` | `str` | YES | NONE | ISO-8601 UTC timestamp or NULL | UTC Time | Timestamp access was granted | `2026-02-01 08:30:00` |
| `revoked_at` | `TEXT` | `str` | YES | NONE | ISO-8601 UTC timestamp or NULL | UTC Time | Timestamp access was revoked | `2026-10-15 17:00:00` |
| `approver_id` | `TEXT` | `str` | YES | FOREIGN KEY | References `employees(employee_id)` | FK | Employee who approved grant | `EMP-000010` |
| `notes` | `TEXT` | `str` | YES | NONE | Open text | Text | Audit and business justification | `Standard onboarding grant` |
| `created_at` | `TEXT` | `str` | NO | NONE | ISO-8601 UTC `YYYY-MM-DD HH:MM:SS` | UTC Time | Record creation timestamp | `2026-01-20 10:00:00` |

---

### 10. `assets`
Physical hardware, security devices, and equipment inventory.

| Field Name | SQL Type | Python Type | Nullable | Uniqueness | Allowed Values / Pattern | Units | Description & Validation Rule | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `asset_id` | `TEXT` | `str` | NO | PRIMARY KEY | `GLOB 'AST-[0-9][0-9][0-9][0-9][0-9][0-9]'` | Code | Deterministic asset ID | `AST-000001` |
| `asset_type` | `TEXT` | `str` | NO | NONE | `LAPTOP`, `MONITOR`, `SECURITY_KEY`, `PHONE`, `BADGE` | Enum | Hardware classification | `LAPTOP` |
| `serial_number` | `TEXT` | `str` | NO | UNIQUE | Length >= 6 | Code | Manufacturer serial identifier | `LT-SN-994821` |
| `model_name` | `TEXT` | `str` | NO | NONE | Length > 1 | Text | Hardware make and model | `ThinkPad P16s Gen 2` |
| `assigned_to` | `TEXT` | `str` | YES | FOREIGN KEY | References `employees(employee_id)` | FK | Current custodian (NULL if in stock) | `EMP-000001` |
| `status` | `TEXT` | `str` | NO | NONE | `IN_STOCK`, `PROVISIONED`, `ASSIGNED`, `RETURN_REQUESTED`, `RECOVERED`, `LOST`, `DECOMMISSIONED` | Enum | Hardware lifecycle state | `ASSIGNED` |
| `assigned_at` | `TEXT` | `str` | YES | NONE | ISO-8601 UTC timestamp or NULL | UTC Time | Timestamp asset assigned | `2026-01-28 14:00:00` |
| `recovered_at` | `TEXT` | `str` | YES | NONE | ISO-8601 UTC timestamp or NULL | UTC Time | Timestamp asset recovered | `2026-10-15 16:00:00` |
| `created_at` | `TEXT` | `str` | NO | NONE | ISO-8601 UTC `YYYY-MM-DD HH:MM:SS` | UTC Time | Record creation timestamp | `2026-01-01 00:00:00` |

---

### 11. `offboarding_cases`
Lifecycle container governing employee departure, asset recovery, and revocation.

| Field Name | SQL Type | Python Type | Nullable | Uniqueness | Allowed Values / Pattern | Units | Description & Validation Rule | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `offboarding_case_id` | `TEXT` | `str` | NO | PRIMARY KEY | `GLOB 'OFF-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]'` | Code | Deterministic offboarding ID | `OFF-2026-000001` |
| `employee_id` | `TEXT` | `str` | NO | UNIQUE | References `employees(employee_id)` | FK | Employee separating from firm | `EMP-000001` |
| `initiated_by` | `TEXT` | `str` | NO | FOREIGN KEY | References `employees(employee_id)` | FK | HR or Manager initiator | `EMP-000010` |
| `initiated_at` | `TEXT` | `str` | NO | NONE | ISO-8601 UTC `YYYY-MM-DD HH:MM:SS` | UTC Time | Case creation timestamp | `2026-10-01 10:00:00` |
| `termination_type` | `TEXT` | `str` | NO | NONE | `VOLUNTARY`, `INVOLUNTARY`, `CONTRACT_END`, `URGENT_TERMINATION` | Enum | Nature of departure | `VOLUNTARY` |
| `effective_date` | `TEXT` | `str` | NO | NONE | `YYYY-MM-DD` | Date | Official last working date | `2026-10-15` |
| `status` | `TEXT` | `str` | NO | NONE | `INITIATED`, `IN_PROGRESS`, `PENDING_ASSET_RETURN`, `PENDING_ACCESS_REVOCATION`, `COMPLETED`, `FLAGGED` | Enum | Case lifecycle status | `IN_PROGRESS` |
| `completed_at` | `TEXT` | `str` | YES | NONE | ISO-8601 UTC timestamp or NULL | UTC Time | Final completion timestamp | `2026-10-15 18:00:00` |
| `created_at` | `TEXT` | `str` | NO | NONE | ISO-8601 UTC `YYYY-MM-DD HH:MM:SS` | UTC Time | Database insertion timestamp | `2026-10-01 10:00:00` |

---

### 12. `audit_events`
Immutable ledger capturing state changes, exceptions, and security overrides.

| Field Name | SQL Type | Python Type | Nullable | Uniqueness | Allowed Values / Pattern | Units | Description & Validation Rule | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `event_id` | `TEXT` | `str` | NO | PRIMARY KEY | `GLOB 'AUD-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'` | Code | Deterministic 10-digit audit ID | `AUD-0000000001` |
| `entity_name` | `TEXT` | `str` | NO | NONE | Target table name | Name | Entity modified | `access_grants` |
| `record_id` | `TEXT` | `str` | NO | NONE | Target primary key value | ID | Specific record identifier | `GRANT-EMP-000001-001` |
| `action` | `TEXT` | `str` | NO | NONE | `INSERT`, `UPDATE`, `DELETE`, `OVERRIDE`, `EXCEPTION` | Enum | Nature of database change | `UPDATE` |
| `actor_id` | `TEXT` | `str` | NO | NONE | Actor employee ID or `SYSTEM` | ID | Identity that triggered action | `EMP-000010` |
| `actor_role` | `TEXT` | `str` | NO | NONE | `CANDIDATE`, `MANAGER`, `HR_PARTNER`, `IT_OPERATIONS`, `SYSTEM_ADMIN` | Enum | Authority role of the actor | `IT_OPERATIONS` |
| `old_values_json`| `TEXT` | `str` | YES | NONE | Valid JSON object or NULL | JSON | Prior state snapshot | `{"status": "ACTIVE"}` |
| `new_values_json`| `TEXT` | `str` | YES | NONE | Valid JSON object or NULL | JSON | Updated state snapshot | `{"status": "REVOKED"}` |
| `timestamp` | `TEXT` | `str` | NO | NONE | ISO-8601 UTC `YYYY-MM-DD HH:MM:SS` | UTC Time | Time of mutation | `2026-10-15 17:00:00` |
| `details` | `TEXT` | `str` | YES | NONE | Free text explanation | Text | Contextual notes or exception trace | `Revocation on departure` |

---

### 13. `labelled_anomalies` (Ground Truth Evaluation Store)
Isolated repository of deliberately injected anomalies used exclusively to benchmark anomaly detection performance.

| Field Name | SQL Type | Python Type | Nullable | Uniqueness | Allowed Values / Pattern | Units | Description & Validation Rule | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `anomaly_id` | `TEXT` | `str` | NO | PRIMARY KEY | `GLOB 'ANO-[0-9][0-9][0-9][0-9][0-9][0-9]'` | Code | Deterministic anomaly identifier | `ANO-000001` |
| `scenario_id` | `TEXT` | `str` | NO | NONE | `SCENARIO_1_PRESTART_ACCESS`, `SCENARIO_2_DUPLICATE_ASSET`, `SCENARIO_3_TERMINATED_RETAINS_ACCESS`, `SCENARIO_4_TASK_CYCLE`, `SCENARIO_5_RECOVERED_REMAINS_ASSIGNED` | Enum | Mandatory benchmark scenario | `SCENARIO_1_PRESTART_ACCESS` |
| `entity_name` | `TEXT` | `str` | NO | NONE | Target table name | Name | Entity housing anomaly | `access_grants` |
| `record_id` | `TEXT` | `str` | NO | NONE | Target record identifier | ID | Record exhibiting anomalous behavior | `GRANT-EMP-000042-001` |
| `issue_type` | `TEXT` | `str` | NO | NONE | Classification string | Category | Canonical issue identifier | `PRE_HIRE_ACTIVE_ACCESS` |
| `description` | `TEXT` | `str` | NO | NONE | Technical explanation | Text | Ground truth rationale | `Active grant prior to hire` |
| `is_ground_truth` | `INTEGER` | `int` | NO | NONE | `1` | Constant | Benchmark marker | `1` |
| `created_at` | `TEXT` | `str` | NO | NONE | ISO-8601 UTC `YYYY-MM-DD HH:MM:SS` | UTC Time | Insertion timestamp | `2026-01-01 00:00:00` |