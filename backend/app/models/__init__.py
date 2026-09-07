"""Entidades ORM mapeadas al esquema PostgreSQL real de Supabase (UUID PKs).

Los módulos aún sin implementar (entrevistas, etc.) usan las tablas
correspondientes del mismo esquema cuando se desarrollen.
"""

from app.models.candidato import (
    CandidateEducation,
    CandidateLanguage,
    CandidateProfile,
    CandidateSkill,
    Certification,
    WorkExperience,
)
from app.models.catalogo import FieldOfStudy, JobCategory, Language, Skill
from app.models.empresa import Company, CompanyMember, CompanyVerification, Sector
from app.models.notificacion import Notification
from app.models.seguridad import AuditLog, LoginAttempt
from app.models.usuario import AppUser, Role, UserRole
from app.models.vacante import (
    EmploymentType,
    JobEducationPreference,
    JobLanguageRequirement,
    JobPosting,
    JobSelectionStage,
    JobSkill,
    JobStatus,
    ScreeningOption,
    ScreeningQuestion,
    SeniorityLevel,
    SkillProficiencyLevel,
    WorkModality,
)
from app.models.postulacion import (
    Application,
    ApplicationAnswer,
    ApplicationNote,
    ApplicationStageHistory,
    ApplicationStatusHistory,
)

__all__ = [
    "AppUser",
    "Application",
    "ApplicationAnswer",
    "ApplicationNote",
    "ApplicationStageHistory",
    "ApplicationStatusHistory",
    "AuditLog",
    "CandidateEducation",
    "CandidateLanguage",
    "CandidateProfile",
    "CandidateSkill",
    "Certification",
    "Company",
    "CompanyMember",
    "CompanyVerification",
    "EmploymentType",
    "FieldOfStudy",
    "JobCategory",
    "JobEducationPreference",
    "JobLanguageRequirement",
    "JobPosting",
    "JobSelectionStage",
    "JobSkill",
    "JobStatus",
    "Language",
    "LoginAttempt",
    "Notification",
    "Role",
    "ScreeningOption",
    "ScreeningQuestion",
    "Sector",
    "SeniorityLevel",
    "Skill",
    "SkillProficiencyLevel",
    "UserRole",
    "WorkExperience",
    "WorkModality",
]
