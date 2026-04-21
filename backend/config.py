"""Central configuration for the TechNova RAG backend."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", PROJECT_ROOT / "backend" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    embedding_model: str = "BAAI/bge-base-en-v1.5"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    collection_name: str = "technova_docs"
    chunk_size: int = 500
    chunk_overlap: int = 100
    top_k_retrieval: int = 10
    top_k_final: int = 5
    rrf_k: int = 60
    llm_model: str = "gpt-4o-mini"
    docs_path: str = "docs/"
    structured_docs_path: str = "docs/structured_docs/"
    bm25_index_path: str = "backend/bm25_index.pkl"
    graph_data_path: str = "backend/graph_data.json"
    sqlite_db_path: str = "backend/structured.db"
    sql_schema_registry_path: str = "backend/sql_schema_registry.json"
    database_url: str = ""
    sql_row_limit: int = 100
    sql_statement_timeout_ms: int = 5000

    @property
    def docs_dir(self) -> Path:
        path = Path(self.docs_path)
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def bm25_index_file(self) -> Path:
        path = Path(self.bm25_index_path)
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def graph_data_file(self) -> Path:
        path = Path(self.graph_data_path)
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def structured_docs_dir(self) -> Path:
        path = Path(self.structured_docs_path)
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def sqlite_db_file(self) -> Path:
        path = Path(self.sqlite_db_path)
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def sql_schema_registry_file(self) -> Path:
        path = Path(self.sql_schema_registry_path)
        return path if path.is_absolute() else PROJECT_ROOT / path


settings = Settings()


ORG_ID = "technova"
EMBEDDING_DIM = 768

SECURITY_LEVELS: dict[str, int] = {
    "PUBLIC": 0,
    "INTERNAL": 1,
    "CONFIDENTIAL": 2,
    "RESTRICTED": 3,
}

ROLE_CLEARANCE: dict[str, int] = {
    "employee": 1,
    "manager": 2,
    "admin": 3,
}

DOCUMENT_METADATA: dict[str, dict] = {
    "TechNova_HR_Policy_Handbook.pdf": {
        "doc_name": "TechNova HR Policy Handbook",
        "doc_slug": "hr_handbook",
        "domain": "HR",
        "security_level": 1,
        "security_label": "INTERNAL",
    },
    "TechNova_Training_Compliance.pdf": {
        "doc_name": "TechNova Training & Compliance",
        "doc_slug": "training_compliance",
        "domain": "HR",
        "security_level": 0,
        "security_label": "PUBLIC",
    },
    "TechNova_IT_Asset_Policy.pdf": {
        "doc_name": "TechNova IT Asset Policy",
        "doc_slug": "it_asset_policy",
        "domain": "IT",
        "security_level": 1,
        "security_label": "INTERNAL",
    },
    "TechNova_Platform_Architecture.pdf": {
        "doc_name": "TechNova Platform Architecture",
        "doc_slug": "platform_architecture",
        "domain": "Engineering",
        "security_level": 1,
        "security_label": "INTERNAL",
    },
    "TechNova_OnCall_Runbook.pdf": {
        "doc_name": "TechNova OnCall Runbook",
        "doc_slug": "oncall_runbook",
        "domain": "Engineering",
        "security_level": 1,
        "security_label": "INTERNAL",
    },
    "TechNova_Q4_Financial_Report.pdf": {
        "doc_name": "TechNova Q4 Financial Report",
        "doc_slug": "q4_financial_report",
        "domain": "Finance",
        "security_level": 2,
        "security_label": "CONFIDENTIAL",
    },
    "TechNova_Product_Roadmap_2026.pdf": {
        "doc_name": "TechNova Product Roadmap 2026",
        "doc_slug": "product_roadmap_2026",
        "domain": "Product",
        "security_level": 2,
        "security_label": "CONFIDENTIAL",
    },
    "TechNova_Vendor_Contracts.pdf": {
        "doc_name": "TechNova Vendor Contracts",
        "doc_slug": "vendor_contracts",
        "domain": "Procurement",
        "security_level": 2,
        "security_label": "CONFIDENTIAL",
    },
    "TechNova_Salary_Structure.pdf": {
        "doc_name": "TechNova Salary Structure",
        "doc_slug": "salary_structure",
        "domain": "HR",
        "security_level": 3,
        "security_label": "RESTRICTED",
    },
    "TechNova_Board_Minutes_Q4.pdf": {
        "doc_name": "TechNova Board Minutes Q4",
        "doc_slug": "board_minutes_q4",
        "domain": "Executive",
        "security_level": 3,
        "security_label": "RESTRICTED",
    },
    "TechNova_Security_Incident_Report.pdf": {
        "doc_name": "TechNova Security Incident Report",
        "doc_slug": "security_incident_report",
        "domain": "Security",
        "security_level": 3,
        "security_label": "RESTRICTED",
    },
}


TABLE_METADATA: dict[str, dict] = {
    "departments": {
        "source_file": "01_Departments.xlsx",
        "sheet": "Departments",
        "description": "Master list of TechNova organizational departments with budgets and cost-center codes.",
        "primary_key": "department_id",
        "domain": "Corporate",
        "security_level": 0,
        "security_label": "PUBLIC",
    },
    "employees": {
        "source_file": "02_Employees.xlsx",
        "sheet": "Employees",
        "description": "Master employee roster with level (L1-L8), department, manager, location, status.",
        "primary_key": "employee_id",
        "domain": "HR",
        "security_level": 1,
        "security_label": "INTERNAL",
    },
    "salary_records": {
        "source_file": "03_Salary_Records.xlsx",
        "sheet": "Salary_Records",
        "description": "Compensation per employee for FY2025-26: base, variable, CTC, ESOPs, rating.",
        "primary_key": "salary_record_id",
        "domain": "HR",
        "security_level": 3,
        "security_label": "RESTRICTED",
    },
    "customers": {
        "source_file": "04_Customers.xlsx",
        "sheet": "Customers",
        "description": "Enterprise customer accounts: tier, region, ARR, contract renewal, account manager.",
        "primary_key": "customer_id",
        "domain": "Sales",
        "security_level": 2,
        "security_label": "CONFIDENTIAL",
    },
    "products_services": {
        "source_file": "05_Products_Services.xlsx",
        "sheet": "Products_Services",
        "description": "Nova Platform microservices + AI products. Criticality tier, owning dept, tech stack.",
        "primary_key": "service_id",
        "domain": "Engineering",
        "security_level": 1,
        "security_label": "INTERNAL",
    },
    "incidents": {
        "source_file": "06_Incidents.xlsx",
        "sheet": "Incidents",
        "description": "Security & ops incidents. SEV classification, affected service, reporter, remediation cost.",
        "primary_key": "incident_id",
        "domain": "Security",
        "security_level": 3,
        "security_label": "RESTRICTED",
    },
    "vendors": {
        "source_file": "07_Vendors.xlsx",
        "sheet": "Vendors",
        "description": "Third-party vendors with SIG-Lite risk score, category, annual spend, owning dept.",
        "primary_key": "vendor_id",
        "domain": "Procurement",
        "security_level": 2,
        "security_label": "CONFIDENTIAL",
    },
    "financial_transactions": {
        "source_file": "08_Financial_Transactions.xlsx",
        "sheet": "Financial_Transactions",
        "description": "Quarterly P&L/CapEx lines by department, region, vendor, customer (INR crores).",
        "primary_key": "transaction_id",
        "domain": "Finance",
        "security_level": 2,
        "security_label": "CONFIDENTIAL",
    },
    "training_compliance": {
        "source_file": "09_Training_Compliance.xlsx",
        "sheet": "Training_Compliance",
        "description": "Mandatory training + external certification records per employee (4 modules x employees).",
        "primary_key": "training_record_id",
        "domain": "HR",
        "security_level": 0,
        "security_label": "PUBLIC",
    },
    "assets_licenses": {
        "source_file": "10_Assets_Licenses.xlsx",
        "sheet": "Assets_Licenses",
        "description": "Hardware (laptops, GPU workstations) and software licenses allocated per employee.",
        "primary_key": "asset_id",
        "domain": "IT",
        "security_level": 1,
        "security_label": "INTERNAL",
    },
}


FOREIGN_KEYS: list[dict] = [
    {"table": "employees", "column": "department_id", "references": "departments.department_id"},
    {"table": "employees", "column": "manager_employee_id", "references": "employees.employee_id"},
    {"table": "salary_records", "column": "employee_id", "references": "employees.employee_id"},
    {"table": "customers", "column": "account_manager_employee_id", "references": "employees.employee_id"},
    {"table": "products_services", "column": "owner_department_id", "references": "departments.department_id"},
    {"table": "incidents", "column": "affected_service_id", "references": "products_services.service_id"},
    {"table": "incidents", "column": "reporter_employee_id", "references": "employees.employee_id"},
    {"table": "vendors", "column": "owner_department_id", "references": "departments.department_id"},
    {"table": "financial_transactions", "column": "department_id", "references": "departments.department_id"},
    {"table": "financial_transactions", "column": "vendor_id", "references": "vendors.vendor_id"},
    {"table": "financial_transactions", "column": "customer_id", "references": "customers.customer_id"},
    {"table": "training_compliance", "column": "employee_id", "references": "employees.employee_id"},
    {"table": "assets_licenses", "column": "employee_id", "references": "employees.employee_id"},
    {"table": "assets_licenses", "column": "vendor_id", "references": "vendors.vendor_id"},
]


NARRATIVE_ROW_TABLES: dict[str, dict] = {
    "incidents": {
        "doc_slug": "structured_incidents",
        "doc_name": "Incidents (Structured Rows)",
        "id_column": "incident_id",
        "ref_column": "incident_ref",
        "template_columns": [
            "incident_ref", "incident_type", "severity", "status",
            "reported_date", "resolved_date", "affected_service_id",
            "reporter_employee_id", "impact_region",
            "customers_affected_count", "data_exfiltrated_gb",
            "remediation_cost_inr_lakhs", "description",
        ],
    },
}


EXAMPLE_SQL_QUERIES: list[dict] = [
    {
        "question": "Which Tier-1 customers in APAC are managed by account managers who have NOT completed DPDP training?",
        "sql": (
            "SELECT DISTINCT c.customer_name, c.tier, c.region, "
            "e.first_name || ' ' || e.last_name AS account_manager "
            "FROM customers c "
            "JOIN employees e ON e.employee_id = c.account_manager_employee_id "
            "WHERE c.tier = 'Tier 1' AND c.region = 'APAC' "
            "AND NOT EXISTS ("
            "  SELECT 1 FROM training_compliance tc "
            "  WHERE tc.employee_id = e.employee_id "
            "  AND tc.module_name = 'DPDP Act 2023' "
            "  AND tc.status = 'Completed'"
            ") "
            "LIMIT 100"
        ),
    },
    {
        "question": "Show critical services whose owning department has a flagged vendor. List the service, department, and flagged vendor names.",
        "sql": (
            "SELECT ps.service_name, ps.criticality_tier, d.department_name, "
            "GROUP_CONCAT(DISTINCT v.vendor_name) AS flagged_vendors "
            "FROM products_services ps "
            "JOIN departments d ON d.department_id = ps.owner_department_id "
            "JOIN vendors v ON v.owner_department_id = ps.owner_department_id "
            "WHERE ps.criticality_tier = 'Critical' "
            "AND v.risk_status IN ('Conditional','Suspended') "
            "GROUP BY ps.service_id, ps.service_name, ps.criticality_tier, d.department_name "
            "ORDER BY ps.service_name "
            "LIMIT 100"
        ),
    },
    {
        "question": "Which departments have at least 3 employees overdue on mandatory training?",
        "sql": (
            "SELECT d.department_name, "
            "COUNT(DISTINCT tc.employee_id) AS overdue_employees "
            "FROM training_compliance tc "
            "JOIN employees e ON e.employee_id = tc.employee_id "
            "JOIN departments d ON d.department_id = e.department_id "
            "WHERE tc.status = 'Overdue' "
            "GROUP BY d.department_name "
            "HAVING overdue_employees >= 3 "
            "ORDER BY overdue_employees DESC "
            "LIMIT 100"
        ),
    },
    {
        "question": "Total vendor spend per department in FY2025-26 by vendor category.",
        "sql": (
            "SELECT d.department_name, v.category, "
            "SUM(ft.amount) AS total_spend_inr_crores "
            "FROM financial_transactions ft "
            "JOIN departments d ON d.department_id = ft.department_id "
            "JOIN vendors v ON v.vendor_id = ft.vendor_id "
            "WHERE ft.period_quarter LIKE '%FY2025-26' "
            "GROUP BY d.department_name, v.category "
            "ORDER BY total_spend_inr_crores DESC "
            "LIMIT 100"
        ),
    },
]


