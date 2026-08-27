"""Entidades ORM mapeadas al esquema PostgreSQL gestionado por schema.sql (UUID PKs).

Los módulos aún sin implementar (vacantes, postulaciones, entrevistas, etc.) usan
las tablas correspondientes del mismo esquema cuando se desarrollen.
"""

from app.models.candidato import (
    CandidateCertification,
    CandidateEducation,
    CandidateExperience,
    CandidateLanguage,
    CandidateProfile,
    CandidateSkill,
)
from app.models.catalogo import FieldOfStudy, JobCategory, Skill
from app.models.empresa import Company, CompanyMember, Sector
from app.models.seguridad import AuditLog, LoginAttempt
from app.models.usuario import AppUser, Role, UserRole

__all__ = [
    "AppUser",
    "AuditLog",
    "CandidateCertification",
    "CandidateEducation",
    "CandidateExperience",
    "CandidateLanguage",
    "CandidateProfile",
    "CandidateSkill",
    "Company",
    "CompanyMember",
    "FieldOfStudy",
    "JobCategory",
    "LoginAttempt",
    "Role",
    "Sector",
    "Skill",
    "UserRole",
]
