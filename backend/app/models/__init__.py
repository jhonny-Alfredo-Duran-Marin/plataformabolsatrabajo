"""Entidades ORM mapeadas al esquema PostgreSQL real de Supabase (UUID PKs).

Los módulos aún sin implementar (vacantes, postulaciones, entrevistas, etc.) usan
las tablas correspondientes del mismo esquema cuando se desarrollen.
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
from app.models.seguridad import AuditLog, LoginAttempt
from app.models.usuario import AppUser, Role, UserRole
from app.models.vacante import JobPosting, ScreeningQuestion, ScreeningOption
from app.models.postulacion import Application, ApplicationAnswer

__all__ = [
    "AppUser",
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
    "Language",
    "LoginAttempt",
    "Role",
    "Sector",
    "Skill",
    "UserRole",
    "WorkExperience",
    "JobPosting",
    "ScreeningQuestion",
    "ScreeningOption",
    "Application",
    "ApplicationAnswer"
]
