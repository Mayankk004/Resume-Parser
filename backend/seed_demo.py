"""One-time demo seeder script to populate PostgreSQL + pgvector with realistic candidates."""

import os
import sys
from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from database import SessionLocal, create_tables  # noqa: E402
from routes.resume import prepare_resume_text, upsert_resume_with_embedding  # noqa: E402
from utils.embeddings import generate_document_embedding  # noqa: E402

DEMO_RESUMES = [
    {
        "name": "Aarav Sharma",
        "email": "aarav.sharma@demo-talent.io",
        "phone_number": "+91-98110-22334",
        "skills": {
            "Languages": ["Python", "SQL", "Go"],
            "Frameworks": ["FastAPI", "Django", "SQLAlchemy"],
            "Infrastructure": ["PostgreSQL", "pgvector", "Docker", "AWS", "Redis"],
        },
        "work_experience": [
            {
                "Company": "FinScale Systems",
                "Position": "Backend Engineer",
                "Duration": "2023 - Present",
                "Description": "Built high-throughput FastAPI microservices backed by PostgreSQL and Docker on AWS.",
            },
            {
                "Company": "CloudPulse Labs",
                "Position": "Software Engineer Intern",
                "Duration": "2022 - 2023",
                "Description": "Implemented Redis caching and asynchronous background job queues.",
            },
        ],
        "education": [{"Degree": "B.Tech in Computer Science", "Institution": "IIIT Delhi", "Year": "2023"}],
        "certifications": [{"Name": "AWS Certified Developer - Associate", "Issuer": "Amazon Web Services"}],
        "projects": [
            {"Name": "Semantic Doc Search", "Description": "RAG retrieval service using pgvector HNSW and FastAPI."}
        ],
        "gpa": "8.7",
        "model_type": "gemini",
        "file_name": "aarav_sharma_backend.pdf",
    },
    {
        "name": "Priya Nair",
        "email": "priya.nair@demo-talent.io",
        "phone_number": "+91-98204-55678",
        "skills": {
            "Frontend": ["React", "TypeScript", "Next.js", "Tailwind CSS", "JavaScript"],
            "Testing & State": ["Jest", "React Testing Library", "Redux Toolkit"],
            "Backend & Tools": ["Node.js", "GraphQL", "Vercel", "Git"],
        },
        "work_experience": [
            {
                "Company": "PixelCraft SaaS",
                "Position": "Frontend Engineer",
                "Duration": "2022 - Present",
                "Description": "Led React and TypeScript design system migration, improving Core Web Vitals by 38%.",
            }
        ],
        "education": [{"Degree": "B.E. in Information Technology", "Institution": "NIT Surathkal", "Year": "2022"}],
        "certifications": [{"Name": "Meta Front-End Developer", "Issuer": "Coursera"}],
        "projects": [
            {"Name": "Analytics Workbench", "Description": "Interactive SaaS dashboard in React, TypeScript, and Recharts."}
        ],
        "gpa": "8.9",
        "model_type": "gemini",
        "file_name": "priya_nair_frontend.pdf",
    },
    {
        "name": "Rohan Verma",
        "email": "rohan.verma@demo-talent.io",
        "phone_number": "+1-415-890-1244",
        "skills": {
            "AI & ML": ["PyTorch", "NLP", "LLMs", "RAG", "LangChain", "Transformers", "Scikit-learn"],
            "Languages": ["Python", "SQL", "C++"],
            "Data & MLOps": ["FastAPI", "Docker", "Hugging Face", "MLflow"],
        },
        "work_experience": [
            {
                "Company": "VectorMind AI",
                "Position": "Machine Learning Engineer",
                "Duration": "2023 - Present",
                "Description": "Fine-tuned embedding models and deployed hybrid RAG pipelines for enterprise search.",
            }
        ],
        "education": [{"Degree": "M.S. in Artificial Intelligence", "Institution": "University of California, San Diego", "Year": "2023"}],
        "certifications": [{"Name": "DeepLearning.AI Generative AI Specialization", "Issuer": "DeepLearning.AI"}],
        "projects": [
            {"Name": "Clinical QA RAG", "Description": "Dense + sparse hybrid medical document retrieval with PyTorch."}
        ],
        "gpa": "3.9",
        "model_type": "gemini",
        "file_name": "rohan_verma_ml.pdf",
    },
    {
        "name": "Saritha Kumar",
        "email": "saritha.kumar@demo-talent.io",
        "phone_number": "+91-85272-57547",
        "skills": {
            "Sales & Operations": ["Inside Sales Management", "B2B Sales", "Key Account Management", "Logistics Operations"],
            "CRM & Analytics": ["Salesforce", "HubSpot", "MS Excel", "CSAT & NPS Optimization"],
        },
        "work_experience": [
            {
                "Company": "DTDC Express Limited",
                "Position": "Senior Inside Sales & Account Manager",
                "Duration": "2021 - Present",
                "Description": "Managed B2B logistics accounts, enterprise onboarding, and client retention workflows.",
            }
        ],
        "education": [{"Degree": "MBA in Marketing & Operations", "Institution": "Symbiosis Pune", "Year": "2021"}],
        "certifications": [{"Name": "HubSpot Revenue Operations", "Issuer": "HubSpot Academy"}],
        "projects": [
            {"Name": "B2B Account Expansion", "Description": "Increased regional logistics wallet share by 28% across key accounts."}
        ],
        "gpa": "3.7",
        "model_type": "gemini",
        "file_name": "saritha_kumar_sales.pdf",
    },
    {
        "name": "Elena Rostova",
        "email": "elena.rostova@demo-talent.io",
        "phone_number": "+1-206-555-0148",
        "skills": {
            "Cloud & DevOps": ["Kubernetes", "Docker", "Terraform", "AWS", "GCP", "GitHub Actions"],
            "Monitoring & Scripting": ["Prometheus", "Grafana", "Linux", "Python", "Bash"],
        },
        "work_experience": [
            {
                "Company": "Nebula Cloud",
                "Position": "Site Reliability Engineer",
                "Duration": "2022 - Present",
                "Description": "Automated multi-region Kubernetes clusters with Terraform and cut CI/CD deploy times by 55%.",
            }
        ],
        "education": [{"Degree": "B.S. in Computer Engineering", "Institution": "University of Washington", "Year": "2022"}],
        "certifications": [
            {"Name": "Certified Kubernetes Administrator (CKA)", "Issuer": "CNCF"},
            {"Name": "AWS Certified Solutions Architect", "Issuer": "AWS"},
        ],
        "projects": [
            {"Name": "Zero-Downtime Canary Pipeline", "Description": "Automated GitHub Actions + ArgoCD deployment pipeline."}
        ],
        "gpa": "3.8",
        "model_type": "gemini",
        "file_name": "elena_rostova_devops.pdf",
    },
    {
        "name": "Kabir Mehta",
        "email": "kabir.mehta@demo-talent.io",
        "phone_number": "+91-99001-77889",
        "skills": {
            "Data Engineering": ["Apache Spark", "Airflow", "Kafka", "dbt", "Snowflake", "BigQuery"],
            "Languages & DB": ["Python", "SQL", "PostgreSQL", "Docker"],
        },
        "work_experience": [
            {
                "Company": "StreamMetric Data",
                "Position": "Data Engineer",
                "Duration": "2022 - Present",
                "Description": "Built real-time Kafka and PySpark ingestion pipelines processing 40M+ daily events.",
            }
        ],
        "education": [{"Degree": "B.Tech in Data Science", "Institution": "IIT Guwahati", "Year": "2022"}],
        "certifications": [{"Name": "Google Professional Data Engineer", "Issuer": "Google Cloud"}],
        "projects": [
            {"Name": "Lakehouse ETL Framework", "Description": "Orchestrated incremental Snowflake models using Airflow and dbt."}
        ],
        "gpa": "8.6",
        "model_type": "gemini",
        "file_name": "kabir_mehta_data.pdf",
    },
    {
        "name": "Maya Lin",
        "email": "maya.lin@demo-talent.io",
        "phone_number": "+1-650-555-0192",
        "skills": {
            "Full Stack": ["React", "Node.js", "TypeScript", "Python", "FastAPI", "PostgreSQL"],
            "Cloud & Tools": ["Docker", "Vercel", "Render", "REST APIs", "Git"],
        },
        "work_experience": [
            {
                "Company": "LaunchPad Studio",
                "Position": "Full Stack Software Engineer",
                "Duration": "2023 - Present",
                "Description": "Shipped end-to-end B2B SaaS products with React, FastAPI, and PostgreSQL.",
            }
        ],
        "education": [{"Degree": "B.S. in Computer Science", "Institution": "Georgia Tech", "Year": "2023"}],
        "certifications": [{"Name": "PostgreSQL Associate", "Issuer": "EDB"}],
        "projects": [
            {"Name": "Collaborative Issue Tracker", "Description": "Full-stack TypeScript + FastAPI app with role-based auth."}
        ],
        "gpa": "3.85",
        "model_type": "gemini",
        "file_name": "maya_lin_fullstack.pdf",
    },
]


def seed() -> None:
    if not os.getenv("GEMINI_API_KEY", "").strip():
        raise RuntimeError("GEMINI_API_KEY must be set in backend/.env to generate embeddings.")

    create_tables()
    db = SessionLocal()
    try:
        for item in DEMO_RESUMES:
            doc_text = prepare_resume_text(item)
            embedding = generate_document_embedding(doc_text)
            saved = upsert_resume_with_embedding(db, item, embedding)
            print(f"[SEEDED] ID {saved.id}: {saved.name} ({saved.email})")
        print(f"[DONE] Seeded {len(DEMO_RESUMES)} demo resumes.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
