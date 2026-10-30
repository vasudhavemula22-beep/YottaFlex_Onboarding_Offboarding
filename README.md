# 🏢 YottaFlex — AI Employee Onboarding & Offboarding Workflow Automation

![Python Version](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Database](https://img.shields.io/badge/Database-SQLite%203-003B57?logo=sqlite&logoColor=white)
![UI Framework](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Deterministic Seed](https://img.shields.io/badge/Seed-20261022-success)
![Integrity](https://img.shields.io/badge/Foreign%20Keys-Enforced%20(ON)-blue)

An enterprise lifecycle automation engine governing worker pre-boarding, onboarding, equipment provisioning, access governance, offboarding, and compliance audit tracking. Built using a normalized SQLite relational schema, an atomic business rules service layer, an anomaly injection framework, and an interactive Streamlit operations dashboard.

---

## 📌 Executive Summary

Modern enterprise HR and IT operations often suffer from deprovisioning gaps (e.g., terminated employees retaining system access) and workflow bottlenecks. **YottaFlex** solves this with:
- **Directed Acyclic Graph (DAG) Task Engine**: Prevents dependent tasks from completing until prerequisites are satisfied (with traceable administrative overrides).
- **Segregation of Duties**: Enforces multi-stage access approval (`REQUESTED` ➔ `APPROVED` ➔ `ACTIVE` ➔ `REVOKED`).
- **Asset Custody & Recovery**: Eliminates duplicate equipment assignments and ensures recovered assets have cleared custodians.
- **Continuous Compliance & Anomaly Benchmarking**: Evaluates compliance detectors against deliberately injected negative scenarios using isolated ground truth.
- **100% Deterministic & Synthetic**: Reproducible from seed `20261022` with zero third-party confidential data.

---

## 🏛️ System Architecture & 12 Relational Entities

The system defines 12 core relational entities plus an isolated anomaly evaluation store:
