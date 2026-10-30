-- ============================================================================
-- YottaFlex AI Employee Onboarding and Offboarding Relational Schema
-- Engine: SQLite 3 (Requires Foreign Keys Enabled: PRAGMA foreign_keys = ON;)
-- Seed: 20261022 | Strict Typing & Constraint Validation Enforced
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- 1. DEPARTMENTS
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS departments (
    dept_id TEXT PRIMARY KEY CHECK (dept_id GLOB 'DEP-[0-9][0-9][0-9]'),
    dept_name TEXT NOT NULL UNIQUE CHECK (length(trim(dept_name)) > 1),
    cost_center TEXT NOT NULL UNIQUE CHECK (cost_center GLOB 'CC-[0-9][0-9][0-9][0-9]'),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now'))
);

-- ----------------------------------------------------------------------------
-- 2. ROLES
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS roles (
    role_id TEXT PRIMARY KEY CHECK (role_id GLOB 'ROL-[0-9][0-9][0-9]'),
    role_title TEXT NOT NULL CHECK (length(trim(role_title)) > 1),
    dept_id TEXT NOT NULL,
    standard_access_profile TEXT NOT NULL CHECK (standard_access_profile IN ('STANDARD_USER', 'ELEVATED_USER', 'DEPT_ADMIN', 'SYSTEM_ADMIN')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
    FOREIGN KEY (dept_id) REFERENCES departments(dept_id) ON DELETE RESTRICT,
    UNIQUE (role_title, dept_id)
);

-- ----------------------------------------------------------------------------
-- 3. EMPLOYEES
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS employees (
    employee_id TEXT PRIMARY KEY CHECK (employee_id GLOB 'EMP-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    first_name TEXT NOT NULL CHECK (length(trim(first_name)) > 0),
    last_name TEXT NOT NULL CHECK (length(trim(last_name)) > 0),
    email TEXT NOT NULL UNIQUE CHECK (email LIKE '%_@__%.__%'),
    role_id TEXT NOT NULL,
    dept_id TEXT NOT NULL,
    manager_id TEXT NULL,
    employment_type TEXT NOT NULL CHECK (employment_type IN ('FULL_TIME', 'CONTRACTOR', 'INTERN')),
    employment_status TEXT NOT NULL CHECK (employment_status IN ('PRE_HIRE', 'ACTIVE', 'ROLE_CHANGE', 'TERMINATED', 'LEAVE')),
    hire_date TEXT NOT NULL CHECK (hire_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    start_date TEXT NOT NULL CHECK (start_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    termination_date TEXT NULL CHECK (termination_date IS NULL OR termination_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
    FOREIGN KEY (role_id) REFERENCES roles(role_id) ON DELETE RESTRICT,
    FOREIGN KEY (dept_id) REFERENCES departments(dept_id) ON DELETE RESTRICT,
    FOREIGN KEY (manager_id) REFERENCES employees(employee_id) ON DELETE SET NULL,
    CHECK (termination_date IS NULL OR termination_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_employees_status ON employees(employment_status);
CREATE INDEX IF NOT EXISTS idx_employees_dept ON employees(dept_id);
CREATE INDEX IF NOT EXISTS idx_employees_manager ON employees(manager_id);

-- ----------------------------------------------------------------------------
-- 4. MANAGERS
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS managers (
    manager_id TEXT PRIMARY KEY CHECK (manager_id GLOB 'MGR-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    employee_id TEXT NOT NULL UNIQUE,
    dept_id TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    appointed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE RESTRICT,
    FOREIGN KEY (dept_id) REFERENCES departments(dept_id) ON DELETE RESTRICT
);

-- ----------------------------------------------------------------------------
-- 5. ONBOARDING CASES
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS onboarding_cases (
    onboarding_case_id TEXT PRIMARY KEY CHECK (onboarding_case_id GLOB 'ONB-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    employee_id TEXT NOT NULL UNIQUE,
    target_start_date TEXT NOT NULL CHECK (target_start_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    actual_start_date TEXT NULL CHECK (actual_start_date IS NULL OR actual_start_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    status TEXT NOT NULL CHECK (status IN ('DRAFT', 'PRE_BOARDING', 'IN_PROGRESS', 'COMPLETED', 'DELAYED', 'CANCELLED')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
    completed_at TEXT NULL CHECK (completed_at IS NULL OR completed_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]*'),
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_onboarding_status ON onboarding_cases(status);

-- ----------------------------------------------------------------------------
-- 6. TASKS
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY CHECK (task_id GLOB 'TASK-[A-Z][A-Z][A-Z]-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9]'),
    case_type TEXT NOT NULL CHECK (case_type IN ('ONBOARDING', 'OFFBOARDING')),
    case_id TEXT NOT NULL,
    task_name TEXT NOT NULL CHECK (length(trim(task_name)) > 1),
    task_category TEXT NOT NULL CHECK (task_category IN ('DOCUMENTATION', 'IT_PROVISIONING', 'TRAINING', 'HARDWARE', 'HR_APPROVAL', 'SECURITY')),
    assigned_actor TEXT NOT NULL CHECK (assigned_actor IN ('CANDIDATE', 'MANAGER', 'HR_PARTNER', 'IT_OPERATIONS', 'SYSTEM_ADMIN')),
    status TEXT NOT NULL CHECK (status IN ('BLOCKED', 'PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'WAIVED')),
    due_date TEXT NOT NULL CHECK (due_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    completed_at TEXT NULL CHECK (completed_at IS NULL OR completed_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]*'),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_tasks_case ON tasks(case_type, case_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_actor ON tasks(assigned_actor);

-- ----------------------------------------------------------------------------
-- 7. TASK DEPENDENCIES (Bridge Table for Workflow DAG)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS task_dependencies (
    dependency_id TEXT PRIMARY KEY CHECK (dependency_id GLOB 'DEP-TASK-[A-Z0-9-]*'),
    task_id TEXT NOT NULL,
    prerequisite_task_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
    FOREIGN KEY (prerequisite_task_id) REFERENCES tasks(task_id) ON DELETE RESTRICT,
    CHECK (task_id != prerequisite_task_id),
    UNIQUE (task_id, prerequisite_task_id)
);

CREATE INDEX IF NOT EXISTS idx_task_deps_parent ON task_dependencies(prerequisite_task_id);

-- ----------------------------------------------------------------------------
-- 8. ACCESS ROLES
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS access_roles (
    access_role_id TEXT PRIMARY KEY CHECK (access_role_id GLOB 'ACR-[0-9][0-9][0-9]'),
    role_name TEXT NOT NULL UNIQUE CHECK (length(trim(role_name)) > 1),
    system_name TEXT NOT NULL CHECK (length(trim(system_name)) > 1),
    risk_level TEXT NOT NULL CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    requires_manager_approval INTEGER NOT NULL CHECK (requires_manager_approval IN (0, 1)),
    requires_hr_approval INTEGER NOT NULL CHECK (requires_hr_approval IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now'))
);

-- ----------------------------------------------------------------------------
-- 9. ACCESS GRANTS (Bridge Table for Employee Entitlements)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS access_grants (
    grant_id TEXT PRIMARY KEY CHECK (grant_id GLOB 'GRANT-EMP-[0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9]'),
    employee_id TEXT NOT NULL,
    access_role_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('REQUESTED', 'APPROVED', 'ACTIVE', 'REVOKED', 'REJECTED')),
    granted_at TEXT NULL CHECK (granted_at IS NULL OR granted_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]*'),
    revoked_at TEXT NULL CHECK (revoked_at IS NULL OR revoked_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]*'),
    approver_id TEXT NULL,
    notes TEXT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE,
    FOREIGN KEY (access_role_id) REFERENCES access_roles(access_role_id) ON DELETE RESTRICT,
    FOREIGN KEY (approver_id) REFERENCES employees(employee_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_grants_emp ON access_grants(employee_id);
CREATE INDEX IF NOT EXISTS idx_grants_status ON access_grants(status);

-- ----------------------------------------------------------------------------
-- 10. ASSETS
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS assets (
    asset_id TEXT PRIMARY KEY CHECK (asset_id GLOB 'AST-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    asset_type TEXT NOT NULL CHECK (asset_type IN ('LAPTOP', 'MONITOR', 'SECURITY_KEY', 'PHONE', 'BADGE')),
    serial_number TEXT NOT NULL UNIQUE CHECK (length(trim(serial_number)) >= 6),
    model_name TEXT NOT NULL CHECK (length(trim(model_name)) > 1),
    assigned_to TEXT NULL,
    status TEXT NOT NULL CHECK (status IN ('IN_STOCK', 'PROVISIONED', 'ASSIGNED', 'RETURN_REQUESTED', 'RECOVERED', 'LOST', 'DECOMMISSIONED')),
    assigned_at TEXT NULL CHECK (assigned_at IS NULL OR assigned_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]*'),
    recovered_at TEXT NULL CHECK (recovered_at IS NULL OR recovered_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]*'),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
    FOREIGN KEY (assigned_to) REFERENCES employees(employee_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_assets_assigned ON assets(assigned_to);
CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(status);

-- ----------------------------------------------------------------------------
-- 11. OFFBOARDING CASES
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS offboarding_cases (
    offboarding_case_id TEXT PRIMARY KEY CHECK (offboarding_case_id GLOB 'OFF-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    employee_id TEXT NOT NULL UNIQUE,
    initiated_by TEXT NOT NULL,
    initiated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
    termination_type TEXT NOT NULL CHECK (termination_type IN ('VOLUNTARY', 'INVOLUNTARY', 'CONTRACT_END', 'URGENT_TERMINATION')),
    effective_date TEXT NOT NULL CHECK (effective_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    status TEXT NOT NULL CHECK (status IN ('INITIATED', 'IN_PROGRESS', 'PENDING_ASSET_RETURN', 'PENDING_ACCESS_REVOCATION', 'COMPLETED', 'FLAGGED')),
    completed_at TEXT NULL CHECK (completed_at IS NULL OR completed_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]*'),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE RESTRICT,
    FOREIGN KEY (initiated_by) REFERENCES employees(employee_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_offboarding_status ON offboarding_cases(status);

-- ----------------------------------------------------------------------------
-- 12. AUDIT EVENTS (Immutable Append-Only Ledger)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY CHECK (event_id GLOB 'AUD-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    entity_name TEXT NOT NULL CHECK (length(trim(entity_name)) > 0),
    record_id TEXT NOT NULL CHECK (length(trim(record_id)) > 0),
    action TEXT NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE', 'OVERRIDE', 'EXCEPTION')),
    actor_id TEXT NOT NULL CHECK (length(trim(actor_id)) > 0),
    actor_role TEXT NOT NULL CHECK (actor_role IN ('CANDIDATE', 'MANAGER', 'HR_PARTNER', 'IT_OPERATIONS', 'SYSTEM_ADMIN')),
    old_values_json TEXT NULL,
    new_values_json TEXT NULL,
    timestamp TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
    details TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_record ON audit_events(entity_name, record_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp);

-- ============================================================================
-- GROUND TRUTH ANOMALY CATALOG (Isolated Evaluation Metadata)
-- This table is explicitly decoupled from application features.
-- ============================================================================
CREATE TABLE IF NOT EXISTS labelled_anomalies (
    anomaly_id TEXT PRIMARY KEY CHECK (anomaly_id GLOB 'ANO-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    scenario_id TEXT NOT NULL CHECK (scenario_id IN (
        'SCENARIO_1_PRESTART_ACCESS',
        'SCENARIO_2_DUPLICATE_ASSET',
        'SCENARIO_3_TERMINATED_RETAINS_ACCESS',
        'SCENARIO_4_TASK_CYCLE',
        'SCENARIO_5_RECOVERED_REMAINS_ASSIGNED'
    )),
    entity_name TEXT NOT NULL,
    record_id TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    description TEXT NOT NULL,
    is_ground_truth INTEGER NOT NULL DEFAULT 1 CHECK (is_ground_truth = 1),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_anomalies_scenario ON labelled_anomalies(scenario_id);
CREATE INDEX IF NOT EXISTS idx_anomalies_record ON labelled_anomalies(entity_name, record_id);