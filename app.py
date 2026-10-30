"""
YottaFlex Enterprise Interactive Streamlit Dashboard.
Operational command center for AI employee onboarding, access governance,
asset custody tracking, offboarding workflows, and exception reconciliation.
"""

from pathlib import Path
import streamlit as st
import pandas as pd

from src.app_data import AppDataLayer
from src.services import (
    AccessGovernanceError,
    AssetUnavailableError,
    PrerequisiteNotSatisfiedError,
    WorkflowEngineError,
    WorkflowService,
)

# ----------------------------------------------------------------------------
# PAGE CONFIGURATION & COMPATIBILITY HELPERS
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="YottaFlex AI Workflow Automation",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def render_df(df: pd.DataFrame, **kwargs):
    """
    Renders dataframe using width='stretch' if supported by newer Streamlit versions,
    falling back seamlessly to use_container_width=True on older versions.
    """
    try:
        st.dataframe(df, width="stretch", **kwargs)
    except TypeError:
        st.dataframe(df, use_container_width=True, **kwargs)


# Resolve Database Connection
PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = PROJECT_ROOT / "yottaflex.db"

if not DB_PATH.exists():
    st.error(f"Database not found at `{DB_PATH}`. Please execute `python orchestrate.py` first.")
    st.stop()

data_layer = AppDataLayer(DB_PATH)
service = WorkflowService(DB_PATH)

# ----------------------------------------------------------------------------
# SIDEBAR NAVIGATION
# ----------------------------------------------------------------------------
st.sidebar.title("🏢 YottaFlex Enterprise")
st.sidebar.caption("Lifecycle Orchestration & Workflow Engine")

page = st.sidebar.radio(
    "Navigation Workspace:",
    [
        "📊 Executive Dashboard",
        "👥 Employee Directory",
        "🚀 Onboarding Workflows",
        "🔐 Access Governance",
        "💻 Asset Management",
        "🚪 Offboarding Workflows",
        "🛡️ Exceptions & Audit Ledger",
    ],
)

st.sidebar.divider()
st.sidebar.info(
    "**Operational Simulation Notice**\n\n"
    "This engine performs transactional state mutations directly against `yottaflex.db`. "
    "External corporate cloud integrations (Okta, Workday, FedEx) are simulated through verifiable database records."
)


# ============================================================================
# MODULE 1: EXECUTIVE DASHBOARD
# ============================================================================
if page == "📊 Executive Dashboard":
    st.title("📊 Executive Workflow & Operations Dashboard")
    st.caption("Real-time workforce metrics, lifecycle progression, and access compliance.")

    kpis = data_layer.get_executive_kpis()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Workforce", f"{kpis['total_employees']:,}", f"{kpis['active_employees']} Active")
    col2.metric("Active Onboarding", f"{kpis['active_onboarding_cases']}", "Cases In-Flight")
    col3.metric("Active Offboarding", f"{kpis['active_offboarding_cases']}", "Pending Departures")
    col4.metric("Task Completion", f"{kpis['task_completion_rate']:.1f}%", f"{kpis['pending_tasks']} Pending")

    st.divider()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Active Access Grants", f"{kpis['active_grants']:,}")
    m2.metric("Access Compliance", f"{kpis['access_compliance_rate']:.1f}%")
    m3.metric("Assigned Equipment", f"{kpis['assigned_assets']:,} / {kpis['total_assets']:,}")
    m4.metric("Active Exceptions", f"{kpis['total_exceptions']}", delta_color="inverse")

    st.subheader("⚠️ Critical Exception & Anomaly Alert Feed")
    anomalies = data_layer.get_detected_anomalies()
    if anomalies:
        df_anom = pd.DataFrame(anomalies)
        render_df(df_anom[["severity", "issue_type", "record_id", "description"]], hide_index=True)
    else:
        st.success("✅ Clean baseline state. No operational policy violations detected.")


# ============================================================================
# MODULE 2: EMPLOYEE DIRECTORY
# ============================================================================
elif page == "👥 Employee Directory":
    st.title("👥 Master Employee Directory")
    st.caption("Search, filter, and inspect worker profile details and supervisory hierarchy.")

    depts = [("ALL", "All Departments")] + data_layer.get_departments_list()
    statuses = ["ALL", "ACTIVE", "PRE_HIRE", "ROLE_CHANGE", "TERMINATED", "LEAVE"]

    f1, f2, f3 = st.columns([2, 1, 1])
    search_term = f1.text_input("🔍 Search by name, ID, or email:")
    dept_choice = f2.selectbox("Filter Department:", [d[0] for d in depts], format_func=lambda x: dict(depts).get(x, x))
    status_choice = f3.selectbox("Filter Status:", statuses)

    df_emps = data_layer.get_employees_df(dept_choice, status_choice, search_term)
    st.write(f"Showing **{len(df_emps)}** personnel records:")
    render_df(df_emps, hide_index=True)


# ============================================================================
# MODULE 3: ONBOARDING OPERATIONS
# ============================================================================
elif page == "🚀 Onboarding Workflows":
    st.title("🚀 Onboarding Operations & Task DAG Visualizer")
    st.caption("Manage pre-boarding, start readiness, and task dependency execution.")

    status_filter = st.selectbox("Filter Onboarding Status:", ["ALL", "IN_PROGRESS", "DELAYED", "PRE_BOARDING", "COMPLETED"])
    df_onb = data_layer.get_onboarding_cases_df(status_filter)
    render_df(df_onb, hide_index=True)

    st.divider()
    st.subheader("Interactive Case Task Execution")

    selected_case = st.text_input("Enter Onboarding Case ID (e.g. ONB-2026-000198):", value=df_onb["onboarding_case_id"].iloc[0] if not df_onb.empty else "")

    if selected_case:
        df_tasks = data_layer.get_case_tasks_df(selected_case)
        if not df_tasks.empty:
            st.write(f"Workflow Tasks for **{selected_case}**:")
            render_df(df_tasks, hide_index=True)

            st.markdown("#### ⚡ Complete Actionable Task")
            t_col1, t_col2 = st.columns(2)
            task_options = df_tasks[df_tasks["status"] != "COMPLETED"]["task_id"].tolist()

            if task_options:
                target_task = t_col1.selectbox("Select Task to Complete:", task_options)
                actor_role = t_col2.selectbox("Executing Actor Authority:", ["IT_OPERATIONS", "MANAGER", "HR_PARTNER", "SYSTEM_ADMIN", "CANDIDATE"])

                prereqs = data_layer.get_task_prerequisites(target_task)
                if prereqs:
                    st.write("**Prerequisite Verification:**")
                    for p in prereqs:
                        icon = "✅" if p["status"] == "COMPLETED" else "❌"
                        st.write(f"- {icon} `{p['task_id']}` ({p['task_name']}) — **{p['status']}**")

                allow_override = st.checkbox("Authorized Administrative Override (Skip Prerequisites)")
                override_justification = ""
                if allow_override:
                    override_justification = st.text_input("Enter Documented Override Reason:")

                if st.button("Execute Task Completion", type="primary"):
                    try:
                        res = service.complete_task(
                            task_id=target_task,
                            actor_id="EMP-000001",
                            actor_role=actor_role,
                            force_override=allow_override,
                            override_reason=override_justification,
                        )
                        st.success(f"Task `{res['task_id']}` marked COMPLETED successfully!")
                        st.rerun()
                    except PrerequisiteNotSatisfiedError as pne:
                        st.error(f"❌ Business Rule Rejection: {pne}")
                    except Exception as ex:
                        st.error(f"Operation failed: {ex}")
            else:
                st.info("All tasks for this case are already finalized.")
        else:
            st.warning(f"No task DAG records discovered for case `{selected_case}`.")


# ============================================================================
# MODULE 4: ACCESS GOVERNANCE
# ============================================================================
elif page == "🔐 Access Governance":
    st.title("🔐 Access Governance & Provisioning Engine")
    st.caption("Enforce segregation of duties: Request, Approval, Provisioning, and Revocation.")

    tab_view, tab_req, tab_app, tab_prov, tab_rev = st.tabs([
        "📋 View Grants",
        "➕ Request Access",
        "✅ Approve Grant",
        "🚀 Provision Access",
        "🛑 Revoke Grant",
    ])

    with tab_view:
        st_filter = st.selectbox("Filter Grant Status:", ["ALL", "REQUESTED", "APPROVED", "ACTIVE", "REVOKED"], key="grant_view_filter")
        df_grants = data_layer.get_access_grants_df(st_filter)
        render_df(df_grants, hide_index=True)

    with tab_req:
        st.markdown("#### Submit Access Request")
        emp_req_id = st.text_input("Target Employee ID (e.g. EMP-000160):", key="req_emp")
        roles_cat = data_layer.get_access_roles_catalog()
        role_map = {r["access_role_id"]: f"{r['role_name']} ({r['system_name']} - Risk: {r['risk_level']})" for r in roles_cat}
        sel_role = st.selectbox("Entitlement Role:", list(role_map.keys()), format_func=lambda x: role_map[x], key="req_role")
        req_notes = st.text_input("Business Justification:", value="Departmental tooling requirement.", key="req_notes")

        if st.button("Submit Request", type="primary"):
            try:
                grant = service.request_access(
                    employee_id=emp_req_id,
                    access_role_id=sel_role,
                    actor_id="EMP-000001",
                    actor_role="MANAGER",
                    notes=req_notes,
                )
                st.success(f"Access Grant `{grant['grant_id']}` registered with status `{grant['status']}`!")
            except AccessGovernanceError as age:
                st.error(f"❌ Access Governance Rejection: {age}")
            except Exception as ex:
                st.error(f"Operation failed: {ex}")

    with tab_app:
        st.markdown("#### Manager / HR Access Approval")
        app_grant_id = st.text_input("Enter Grant ID in REQUESTED status:", key="app_grant_id")
        app_role = st.selectbox("Approval Authority Role:", ["MANAGER", "HR_PARTNER", "SYSTEM_ADMIN"], key="app_role")
        app_notes = st.text_input("Approval Comments:", value="Approved following verification.", key="app_notes")

        if st.button("Sign and Approve Access"):
            try:
                g = service.approve_access(
                    grant_id=app_grant_id,
                    approver_id="EMP-000001",
                    approver_role=app_role,
                    notes=app_notes,
                )
                st.success(f"Grant `{g['grant_id']}` successfully approved!")
            except Exception as ex:
                st.error(f"Approval rejected: {ex}")

    with tab_prov:
        st.markdown("#### Execute Simulated Technical Provisioning")
        prov_grant_id = st.text_input("Enter Grant ID in APPROVED status:", key="prov_grant_id")
        if st.button("Activate Entitlement", type="primary"):
            try:
                g = service.provision_access(prov_grant_id, actor_id="EMP-000001", actor_role="SYSTEM_ADMIN")
                st.success(f"Grant `{g['grant_id']}` provisioned to ACTIVE status!")
            except AccessGovernanceError as age:
                st.error(f"❌ Provisioning Rejection: {age}")
            except Exception as ex:
                st.error(f"Operation failed: {ex}")

    with tab_rev:
        st.markdown("#### Immediate Security Revocation")
        rev_grant_id = st.text_input("Enter Active Grant ID to Revoke:", key="rev_grant_id")
        rev_reason = st.text_input("Revocation Reason:", value="Policy enforcement / departure.")
        if st.button("Revoke Access Immediately", type="primary"):
            try:
                g = service.revoke_access(rev_grant_id, actor_id="EMP-000001", actor_role="SYSTEM_ADMIN", reason=rev_reason)
                st.warning(f"Grant `{g['grant_id']}` has been REVOKED.")
            except Exception as ex:
                st.error(f"Revocation failed: {ex}")


# ============================================================================
# MODULE 5: ASSET MANAGEMENT
# ============================================================================
elif page == "💻 Asset Management":
    st.title("💻 Asset Inventory & Custody Lifecycle")
    st.caption("Manage hardware assignment, delivery acknowledgement, and recovery.")

    t_view, t_assign, t_ack, t_recover = st.tabs([
        "📦 Asset Inventory",
        "📥 Assign Asset",
        "✍️ Acknowledge Receipt",
        "🔄 Recover Asset",
    ])

    with t_view:
        f_stat = st.selectbox("Filter Status:", ["ALL", "IN_STOCK", "ASSIGNED", "RETURN_REQUESTED", "RECOVERED"], key="ast_stat")
        df_assets = data_layer.get_assets_df(status=f_stat)
        render_df(df_assets, hide_index=True)

    with t_assign:
        st.markdown("#### Assign Hardware to Employee")
        ast_id_in = st.text_input("Asset ID (e.g. AST-001001):", key="assign_ast_id")
        ast_emp_in = st.text_input("Assignee Employee ID (e.g. EMP-000160):", key="assign_emp_id")

        if st.button("Confirm Custody Allocation", type="primary"):
            try:
                a = service.assign_asset(ast_id_in, ast_emp_in, actor_id="EMP-000001", actor_role="IT_OPERATIONS")
                st.success(f"Asset `{a['asset_id']}` assigned to `{a['assigned_to']}`!")
            except AssetUnavailableError as aue:
                st.error(f"❌ Allocation Conflict: {aue}")
            except Exception as ex:
                st.error(f"Assignment failed: {ex}")

    with t_ack:
        st.markdown("#### Employee Custody Acknowledgement")
        ack_ast_id = st.text_input("Asset ID to Acknowledge:", key="ack_ast")
        ack_emp_id = st.text_input("Custodian Employee ID:", key="ack_emp")

        if st.button("Sign Custody Acknowledgement"):
            try:
                service.acknowledge_asset(ack_ast_id, ack_emp_id)
                st.success("Formal custodial acknowledgement confirmed and recorded in audit ledger.")
            except Exception as ex:
                st.error(f"Acknowledgement failed: {ex}")

    with t_recover:
        st.markdown("#### Recover Deployed Asset to Warehouse")
        rec_ast_id = st.text_input("Asset ID to Recover:", key="rec_ast")

        if st.button("Recover to Stock", type="primary"):
            try:
                rec = service.recover_asset(rec_ast_id, actor_id="EMP-000001", actor_role="IT_OPERATIONS")
                st.success(f"Asset `{rec['asset_id']}` successfully recovered. Custodian cleared.")
            except Exception as ex:
                st.error(f"Recovery failed: {ex}")


# ============================================================================
# MODULE 6: OFFBOARDING WORKFLOWS
# ============================================================================
elif page == "🚪 Offboarding Workflows":
    st.title("🚪 Offboarding Lifecycle & Departure Orchestration")
    st.caption("Initiate departures, instantiate exit task DAGs, and verify deprovisioning.")

    tab_off_view, tab_off_init = st.tabs(["📋 Active Offboarding Cases", "➕ Initiate Departure"])

    with tab_off_view:
        df_off = data_layer.get_offboarding_cases_df()
        render_df(df_off, hide_index=True)

    with tab_off_init:
        st.markdown("#### Initiate Separation Workflow")
        term_emp_id = st.text_input("Employee ID to Offboard (e.g. EMP-000500):", key="term_emp")
        t_type = st.selectbox("Termination Classification:", ["VOLUNTARY", "INVOLUNTARY", "CONTRACT_END", "URGENT_TERMINATION"])
        eff_date = st.date_input("Effective Separation Date:")
        term_reason = st.text_input("Documentation Notes:", value="Formal resignation received.")

        if st.button("Execute Departure Initiation", type="primary"):
            try:
                case = service.initiate_offboarding(
                    employee_id=term_emp_id,
                    termination_type=t_type,
                    effective_date=str(eff_date),
                    initiator_id="EMP-000001",
                    initiator_role="HR_PARTNER",
                    reason=term_reason,
                )
                st.success(
                    f"Offboarding case `{case['offboarding_case_id']}` created! "
                    "Departure task DAG instantiated and assigned hardware flagged for return."
                )
            except WorkflowEngineError as we:
                st.error(f"❌ Offboarding Rejection: {we}")
            except Exception as ex:
                st.error(f"Operation failed: {ex}")


# ============================================================================
# MODULE 7: EXCEPTIONS & AUDIT LEDGER
# ============================================================================
elif page == "🛡️ Exceptions & Audit Ledger":
    st.title("🛡️ Exceptions, Anomaly Detection & Audit Ledger")
    st.caption("Continuous compliance reconciliation and immutable chronological change ledger.")

    tab_anom, tab_audit = st.tabs(["🚨 Detected Non-Compliance Anomaly Feed", "📜 Immutable Audit Trail"])

    with tab_anom:
        st.markdown("#### Automated Detection of Injected Compliance Anomalies")
        detected = data_layer.get_detected_anomalies()
        st.write(f"Detected **{len(detected)}** policy violations via business rule detectors:")
        render_df(pd.DataFrame(detected), hide_index=True)

    with tab_audit:
        st.markdown("#### Immutable System Event Trail")
        a1, a2 = st.columns(2)
        ent_choice = a1.selectbox("Filter Entity:", ["ALL", "tasks", "access_grants", "assets", "employees", "offboarding_cases"])
        act_choice = a2.selectbox("Filter Action:", ["ALL", "INSERT", "UPDATE", "EXCEPTION", "OVERRIDE"])

        df_audit = data_layer.get_audit_trail_df(ent_choice, act_choice)
        render_df(df_audit, hide_index=True)