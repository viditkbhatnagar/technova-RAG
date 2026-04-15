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
    bm25_index_path: str = "backend/bm25_index.pkl"
    graph_data_path: str = "backend/graph_data.json"

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
