"""Entidades ORM mapeadas al esquema PostgreSQL real (UUID PKs)."""

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
from app.models.postulacion import (
    Application,
    ApplicationNote,
    ApplicationStageHistory,
    ApplicationStatusHistory,
)
from app.models.seguridad import AuditLog, LoginAttempt
from app.models.usuario import AppUser, Role, UserRole
from app.models.vacante import (
    JobEducationPreference,
    JobLanguageRequirement,
    JobPosting,
    JobSelectionStage,
    JobSkill,
)

__all__ = [
    "AppUser",
    "Application",
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
    "FieldOfStudy",
    "JobCategory",
    "JobEducationPreference",
    "JobLanguageRequirement",
    "JobPosting",
    "JobSelectionStage",
    "JobSkill",
    "Language",
    "LoginAttempt",
    "Notification",
    "Role",
    "Sector",
    "Skill",
    "UserRole",
    "WorkExperience",
]
