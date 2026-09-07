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
<<<<<<< HEAD
from app.models.oferta import JobEducationPreference, JobPosting, JobSkill
=======
from app.models.notificacion import Notification
>>>>>>> 8a7aaf477858b3da8e1335d385ccfa4cc3d228ad
from app.models.seguridad import AuditLog, LoginAttempt
from app.models.seleccion import (
    Application,
    ApplicationNote,
    ApplicationStageHistory,
    JobSelectionStage,
    Notification,
)
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
<<<<<<< HEAD
    "ApplicationNote",
    "ApplicationStageHistory",
=======
    "ApplicationAnswer",
    "ApplicationNote",
    "ApplicationStageHistory",
    "ApplicationStatusHistory",
>>>>>>> 8a7aaf477858b3da8e1335d385ccfa4cc3d228ad
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
<<<<<<< HEAD
    "JobPosting",
    "JobSelectionStage",
    "JobSkill",
=======
    "JobLanguageRequirement",
    "JobPosting",
    "JobSelectionStage",
    "JobSkill",
    "JobStatus",
>>>>>>> 8a7aaf477858b3da8e1335d385ccfa4cc3d228ad
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
