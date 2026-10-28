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
from app.models.chatbot import ChatbotMessage, ChatbotSession
from app.models.empresa import Company, CompanyMember, CompanyVerification, Sector
from app.models.grupo import UserGroup, UserGroupMember, UserGroupPermission
from app.models.institucion import (
    CompanyInstitution,
    Institution,
    PlanPayment,
    SaasPlan,
    UniversitySignupRequest,
)
from app.models.moderacion import ModerationReport
from app.models.notificacion import Notification, NotificationPreference
from app.models.respaldo import SystemBackup
from app.models.tarea import ScheduledTaskRun
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
from app.models.colocacion import Placement
from app.models.comunicacion import (
    Conversation,
    ConversationMember,
    Message,
    MessageAttachment,
)
from app.models.encuesta import Survey, SurveyAnswer, SurveyQuestion, SurveyQuestionOption, SurveyResponse
from app.models.entrevista import Interview
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
    "Interview",
    "ApplicationAnswer",
    "ApplicationNote",
    "ApplicationStageHistory",
    "ApplicationStatusHistory",
    "AuditLog",
    "Conversation",
    "ConversationMember",
    "Message",
    "MessageAttachment",
    "CandidateEducation",
    "CandidateLanguage",
    "CandidateProfile",
    "CandidateSkill",
    "Certification",
    "ChatbotMessage",
    "ChatbotSession",
    "Company",
    "CompanyInstitution",
    "CompanyMember",
    "CompanyVerification",
    "EmploymentType",
    "FieldOfStudy",
    "Institution",
    "JobCategory",
    "JobEducationPreference",
    "JobLanguageRequirement",
    "JobPosting",
    "JobSelectionStage",
    "JobSkill",
    "JobStatus",
    "Language",
    "LoginAttempt",
    "ModerationReport",
    "Notification",
    "NotificationPreference",
    "PlanPayment",
    "Placement",
    "Role",
    "SaasPlan",
    "ScheduledTaskRun",
    "ScreeningOption",
    "ScreeningQuestion",
    "Sector",
    "SeniorityLevel",
    "Skill",
    "SkillProficiencyLevel",
    "Survey",
    "SurveyAnswer",
    "SurveyQuestion",
    "SurveyQuestionOption",
    "SurveyResponse",
    "SystemBackup",
    "UniversitySignupRequest",
    "UserGroup",
    "UserGroupMember",
    "UserGroupPermission",
    "UserRole",
    "WorkExperience",
    "WorkModality",
]
