# DISEÑO DE BASE DE DATOS
## Plataforma de Reclutamiento y Bolsa de Trabajo

**Versión 3** — corrige una inconsistencia real detectada en la V2: el CHECK de `Conversation`
permitía violar su propia Regla 23 ("nunca ambos" orígenes a la vez). También se formaliza
como CHECK ejecutable la restricción de dominio de `ApplicationStatusHistory`, que en la V2
quedaba solo como nota de texto. Ver "Cambios de esta versión" al final del documento.

Motor: PostgreSQL 16+ con extensión **pgvector** habilitada (requerida por `JobEmbedding` /
`CandidateEmbedding`, Módulo 12). La imagen de PostgreSQL debe ser `pgvector/pgvector:pg16`
(o equivalente con la extensión instalada) — la imagen oficial `postgres:16-alpine` **no** la trae.
Arquitectura: Monolito modular FastAPI (ver `Arquitectura_Monolito_Modular.md`)
Backend: FastAPI + SQLAlchemy
Convención BD: inglés + snake_case
Identificadores: UUID
Fechas con hora: TIMESTAMPTZ

## MÓDULO 1: USUARIOS, ROLES Y SEGURIDAD

### User

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador único |
| email | VARCHAR(255) | | NOT NULL | Correo utilizado para autenticación |
| password_hash | VARCHAR(255) | | NOT NULL | Hash de contraseña |
| account_status | VARCHAR(30) | | NOT NULL, DEFAULT 'pending_verification', CHECK | Estado de la cuenta |
| email_verified_at | TIMESTAMPTZ | | NULL | Fecha de verificación del correo |
| last_login_at | TIMESTAMPTZ | | NULL | Último inicio de sesión |
| deleted_at | TIMESTAMPTZ | | NULL | Soft delete/anonimización de cuenta |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Fecha de creación |
| updated_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Última actualización |

Valores account_status:
- pending_verification
- active
- suspended
- blocked

Restricción recomendada PostgreSQL:
UNIQUE(LOWER(email)) WHERE deleted_at IS NULL


### Role

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| name | VARCHAR(50) | | NOT NULL, UNIQUE | Nombre del rol |
| description | TEXT | | NULL | Descripción |

Valores iniciales sugeridos:
- candidate
- moderator
- platform_admin

Nota:
Los permisos dentro de una empresa se controlan mediante CompanyMember.member_role,
no mediante roles globales.


### UserRole

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| user_id | UUID | PK, FK | NOT NULL, REFERENCES User(id) ON DELETE CASCADE | Usuario |
| role_id | UUID | PK, FK | NOT NULL, REFERENCES Role(id) ON DELETE CASCADE | Rol |
| assigned_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Fecha de asignación |

Constraint:
UNIQUE(user_id, role_id)


### UserToken

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| user_id | UUID | FK | NOT NULL, REFERENCES User(id) ON DELETE CASCADE | Usuario |
| token_type | VARCHAR(30) | | NOT NULL, CHECK | Tipo de token |
| token_hash | VARCHAR(255) | | NOT NULL, UNIQUE | Hash del token |
| expires_at | TIMESTAMPTZ | | NOT NULL | Expiración |
| used_at | TIMESTAMPTZ | | NULL | Fecha de utilización |
| revoked_at | TIMESTAMPTZ | | NULL | Fecha de revocación |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Fecha de creación |

Valores token_type:
- email_verification
- password_reset
- refresh_token

Nunca almacenar el token real.


### AuditLog

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| user_id | UUID | FK | NULL, REFERENCES User(id) ON DELETE SET NULL | Usuario responsable |
| action | VARCHAR(80) | | NOT NULL | Acción realizada |
| entity_type | VARCHAR(80) | | NOT NULL | Tipo de entidad afectada |
| entity_id | UUID | | NULL | ID de entidad afectada |
| result | VARCHAR(20) | | NOT NULL, CHECK | Resultado |
| ip_address | VARCHAR(45) | | NULL | IP |
| details_json | JSONB | | NULL | Detalle adicional |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Fecha de evento |

Valores result:
- success
- failure


### PasswordHistory

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| user_id | UUID | FK | NOT NULL, REFERENCES User(id) ON DELETE CASCADE | Usuario |
| password_hash | VARCHAR(255) | | NOT NULL | Hash de contraseña anterior |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Fecha de reemplazo |

Política:
Conservar los últimos 10 hashes por usuario para impedir reuso de
contraseñas recientes (refuerza RNF-05..RNF-08).
Purga: job programado elimina registros excedentes.


### LoginAttempt

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| email | VARCHAR(255) | | NOT NULL | Correo intentado (puede no existir) |
| user_id | UUID | FK | NULL, REFERENCES User(id) ON DELETE SET NULL | Usuario si existe |
| ip_address | VARCHAR(45) | | NULL | IP origen |
| user_agent | VARCHAR(300) | | NULL | Navegador/cliente |
| success | BOOLEAN | | NOT NULL | Resultado del intento |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Fecha |

Propósito:
Alimenta rate-limiting y bloqueo temporal por fuerza bruta.
Retención: purgar registros con más de 90 días (job programado).


## MÓDULO 2: CANDIDATOS

### CandidateProfile

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador del candidato |
| user_id | UUID | FK | NOT NULL, UNIQUE, REFERENCES User(id) ON DELETE RESTRICT | Cuenta asociada |
| first_name | VARCHAR(100) | | NOT NULL | Nombres |
| last_name | VARCHAR(100) | | NOT NULL | Apellidos |
| phone | VARCHAR(30) | | NULL | Teléfono |
| country_code | CHAR(2) | | NULL | País ISO-3166 |
| city | VARCHAR(100) | | NULL | Ciudad |
| professional_headline | VARCHAR(200) | | NULL | Título profesional mostrado |
| professional_summary | TEXT | | NULL | Resumen profesional |
| profile_photo_key | VARCHAR(500) | | NULL | Ruta/storage key de foto |
| portfolio_url | VARCHAR(500) | | NULL | Portafolio/LinkedIn/GitHub |
| document_type | VARCHAR(20) | | NULL, CHECK | Tipo de documento de identidad |
| document_number | VARCHAR(50) | | NULL | Número de documento (CI/pasaporte) |
| document_country_code | CHAR(2) | | NULL | País emisor del documento |
| verification_status | VARCHAR(30) | | NOT NULL, DEFAULT 'pending', CHECK | Verificación institucional del egresado (global) |
| verified_at | TIMESTAMPTZ | | NULL | Fecha de verificación institucional |
| profile_visibility | VARCHAR(30) | | NOT NULL, DEFAULT 'platform', CHECK | Visibilidad |
| contact_visibility | BOOLEAN | | NOT NULL, DEFAULT false | Mostrar información de contacto |
| job_search_status | VARCHAR(30) | | NULL, CHECK | Estado de búsqueda |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Fecha de creación |
| updated_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Actualización |

Valores profile_visibility:
- public
- platform
- private

Valores job_search_status:
- actively_looking
- open_to_offers
- not_looking

Valores document_type:
- ci
- passport
- foreign_id
- other

Valores verification_status:
- pending
- in_review
- verified
- rejected

Restricción recomendada PostgreSQL:
UNIQUE(document_country_code, document_type, document_number) WHERE document_number IS NOT NULL

Nota:
No contiene universidad ni carrera. La formación se almacena en CandidateEducation.
La verificación institucional opera en dos niveles: por registro académico
(EducationVerification, Módulo 3) y estado global del candidato (verification_status).


### CandidatePreference

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| candidate_id | UUID | PK, FK | NOT NULL, REFERENCES CandidateProfile(id) ON DELETE CASCADE | Candidato |
| desired_salary_min | NUMERIC(12,2) | | NULL | Salario mínimo esperado |
| desired_salary_max | NUMERIC(12,2) | | NULL | Salario máximo esperado |
| currency | CHAR(3) | | NULL | Moneda ISO |
| accepts_onsite | BOOLEAN | | NOT NULL, DEFAULT true | Acepta presencial |
| accepts_remote | BOOLEAN | | NOT NULL, DEFAULT true | Acepta remoto |
| accepts_hybrid | BOOLEAN | | NOT NULL, DEFAULT true | Acepta híbrido |
| preferred_country_code | CHAR(2) | | NULL | País preferido |
| preferred_city | VARCHAR(100) | | NULL | Ciudad preferida |
| relocation_allowed | BOOLEAN | | NOT NULL, DEFAULT false | Puede reubicarse |
| available_from | DATE | | NULL | Disponibilidad |
| updated_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Actualización |

CHECK:
desired_salary_min <= desired_salary_max


## MÓDULO 3: EDUCACIÓN

### EducationalInstitution

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| name | VARCHAR(250) | | NOT NULL | Nombre |
| institution_type | VARCHAR(40) | | NULL, CHECK | Tipo |
| country_code | CHAR(2) | | NULL | País |
| city | VARCHAR(100) | | NULL | Ciudad |
| website | VARCHAR(500) | | NULL | Sitio web |
| verification_status | VARCHAR(30) | | NOT NULL, DEFAULT 'unverified', CHECK | Verificación |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Creación |
| updated_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Actualización |

Valores institution_type:
- university
- technical_institute
- academy
- training_center
- other

Valores verification_status:
- unverified
- pending
- verified
- rejected


### FieldOfStudy

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| name | VARCHAR(200) | | NOT NULL | Carrera/área académica |
| category | VARCHAR(100) | | NULL | Área general |
| is_active | BOOLEAN | | NOT NULL, DEFAULT true | Estado |


### CandidateEducation

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| candidate_id | UUID | FK | NOT NULL, REFERENCES CandidateProfile(id) ON DELETE CASCADE | Candidato |
| institution_id | UUID | FK | NULL, REFERENCES EducationalInstitution(id) ON DELETE SET NULL | Institución normalizada |
| field_of_study_id | UUID | FK | NULL, REFERENCES FieldOfStudy(id) ON DELETE SET NULL | Carrera/área |
| institution_name | VARCHAR(250) | | NULL | Institución no registrada en catálogo |
| program_name | VARCHAR(250) | | NOT NULL | Nombre del programa/título |
| education_level | VARCHAR(40) | | NOT NULL, CHECK | Nivel |
| academic_status | VARCHAR(30) | | NOT NULL, CHECK | Estado académico |
| start_date | DATE | | NULL | Inicio |
| end_date | DATE | | NULL | Finalización |
| graduation_date | DATE | | NULL | Fecha de graduación |
| description | TEXT | | NULL | Descripción |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Creación |
| updated_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Actualización |

Valores education_level:
- secondary
- technical
- undergraduate
- postgraduate
- diploma
- course
- certification
- other

Valores academic_status:
- in_progress
- completed
- graduated
- withdrawn

CHECK:
end_date >= start_date


### EducationVerification

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| candidate_education_id | UUID | FK | NOT NULL, REFERENCES CandidateEducation(id) ON DELETE CASCADE | Formación |
| status | VARCHAR(30) | | NOT NULL, DEFAULT 'pending', CHECK | Estado |
| verification_method | VARCHAR(40) | | NULL, CHECK | Método |
| evidence_document_id | UUID | FK | NULL, REFERENCES CandidateDocument(id) ON DELETE SET NULL | Evidencia. Nota: tabla definida en el Módulo 4; crear CandidateDocument antes (ver Orden de Creación) |
| reviewed_by | UUID | FK | NULL, REFERENCES User(id) ON DELETE SET NULL | Revisor |
| reviewed_at | TIMESTAMPTZ | | NULL | Fecha revisión |
| rejection_reason | TEXT | | NULL | Motivo |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Creación |

Valores status:
- pending
- verified
- rejected

Valores verification_method:
- institution
- document
- administrator
- integration


## MÓDULO 4: PERFIL PROFESIONAL

### Skill

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| name | VARCHAR(120) | | NOT NULL, UNIQUE | Nombre |
| category | VARCHAR(80) | | NULL | Técnica, blanda, herramienta, etc. |
| is_active | BOOLEAN | | NOT NULL, DEFAULT true | Estado |


### CandidateSkill

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| candidate_id | UUID | PK, FK | NOT NULL, REFERENCES CandidateProfile(id) ON DELETE CASCADE | Candidato |
| skill_id | UUID | PK, FK | NOT NULL, REFERENCES Skill(id) ON DELETE RESTRICT | Habilidad |
| proficiency_level | VARCHAR(20) | | NULL, CHECK | Nivel |
| years_experience | NUMERIC(4,1) | | NULL, CHECK >= 0 | Años de experiencia |

Valores proficiency_level:
- basic
- intermediate
- advanced
- expert

Constraint:
UNIQUE(candidate_id, skill_id)


### Language

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| name | VARCHAR(80) | | NOT NULL, UNIQUE | Idioma |
| iso_code | VARCHAR(10) | | NULL, UNIQUE | Código ISO |


### CandidateLanguage

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| candidate_id | UUID | PK, FK | NOT NULL, REFERENCES CandidateProfile(id) ON DELETE CASCADE | Candidato |
| language_id | UUID | PK, FK | NOT NULL, REFERENCES Language(id) ON DELETE RESTRICT | Idioma |
| proficiency_level | VARCHAR(30) | | NOT NULL, CHECK | Dominio |

Valores proficiency_level:
- basic
- intermediate
- advanced
- fluent
- native


### Certification

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| candidate_id | UUID | FK | NOT NULL, REFERENCES CandidateProfile(id) ON DELETE CASCADE | Candidato |
| name | VARCHAR(250) | | NOT NULL | Certificación |
| issuer | VARCHAR(250) | | NULL | Emisor |
| credential_id | VARCHAR(150) | | NULL | Código credencial |
| credential_url | VARCHAR(500) | | NULL | URL |
| issued_at | DATE | | NULL | Emisión |
| expires_at | DATE | | NULL | Vencimiento |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Creación |

CHECK:
expires_at >= issued_at


### WorkExperience

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| candidate_id | UUID | FK | NOT NULL, REFERENCES CandidateProfile(id) ON DELETE CASCADE | Candidato |
| company_id | UUID | FK | NULL, REFERENCES Company(id) ON DELETE SET NULL | Empresa registrada. Nota: tabla definida en el Módulo 5 (ver Orden de Creación) |
| employer_name | VARCHAR(250) | | NOT NULL | Nombre histórico de empresa |
| job_title | VARCHAR(200) | | NOT NULL | Cargo |
| description | TEXT | | NULL | Funciones/logros |
| start_date | DATE | | NOT NULL | Inicio |
| end_date | DATE | | NULL | Fin; NULL = empleo actual |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Creación |
| updated_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Actualización |

CHECK:
end_date >= start_date


### EmploymentStatusHistory

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| candidate_id | UUID | FK | NOT NULL, REFERENCES CandidateProfile(id) ON DELETE CASCADE | Candidato |
| employment_status | VARCHAR(30) | | NOT NULL, CHECK | Situación laboral |
| effective_from | DATE | | NOT NULL | Vigencia desde |
| effective_to | DATE | | NULL | Vigencia hasta |
| source_type | VARCHAR(30) | | NOT NULL, CHECK | Fuente |
| related_work_experience_id | UUID | FK | NULL, REFERENCES WorkExperience(id) ON DELETE SET NULL | Experiencia asociada |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Registro |

Estados:
- unemployed
- employed
- self_employed
- freelancer
- student
- inactive

Fuentes:
- profile
- survey
- placement
- administrator


### CandidateDocument

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| candidate_id | UUID | FK | NOT NULL, REFERENCES CandidateProfile(id) ON DELETE CASCADE | Candidato |
| document_type | VARCHAR(40) | | NOT NULL, CHECK | Tipo |
| storage_key | VARCHAR(500) | | NOT NULL | Ubicación en almacenamiento |
| original_filename | VARCHAR(255) | | NOT NULL | Nombre original |
| mime_type | VARCHAR(100) | | NULL | MIME |
| file_size | BIGINT | | NULL, CHECK >= 0 | Tamaño |
| checksum | VARCHAR(128) | | NULL | Hash del archivo |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Creación |
| deleted_at | TIMESTAMPTZ | | NULL | Baja lógica |

Tipos:
- uploaded_cv
- generated_cv
- certificate
- education_proof
- portfolio
- other


## MÓDULO 5: EMPRESAS

### Sector

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| name | VARCHAR(120) | | NOT NULL, UNIQUE | Sector |
| is_active | BOOLEAN | | NOT NULL, DEFAULT true | Estado |


### Company

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| legal_name | VARCHAR(250) | | NOT NULL | Razón social |
| trade_name | VARCHAR(250) | | NULL | Nombre comercial |
| tax_id | VARCHAR(50) | | NULL | NIT/RUC/etc. |
| country_code | CHAR(2) | | NULL | País |
| sector_id | UUID | FK | NULL, REFERENCES Sector(id) ON DELETE SET NULL | Sector |
| description | TEXT | | NULL | Descripción |
| company_size | VARCHAR(30) | | NULL, CHECK | Tamaño |
| website | VARCHAR(500) | | NULL | Web |
| logo_key | VARCHAR(500) | | NULL | Logo |
| phone | VARCHAR(30) | | NULL | Teléfono |
| contact_email | VARCHAR(255) | | NULL | Correo |
| city | VARCHAR(100) | | NULL | Ciudad |
| address | VARCHAR(300) | | NULL | Dirección |
| verification_status | VARCHAR(30) | | NOT NULL, DEFAULT 'pending', CHECK | Verificación |
| status | VARCHAR(30) | | NOT NULL, DEFAULT 'active', CHECK | Estado |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Creación |
| updated_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Actualización |

UNIQUE recomendado:
(country_code, tax_id) cuando tax_id IS NOT NULL.

verification_status:
- pending
- verified
- rejected

status:
- active
- suspended
- blocked

Valores company_size:
- micro
- small
- medium
- large
- enterprise


### CompanyMember

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| company_id | UUID | FK | NOT NULL, REFERENCES Company(id) ON DELETE RESTRICT | Empresa |
| user_id | UUID | FK | NOT NULL, REFERENCES User(id) ON DELETE RESTRICT | Usuario |
| member_role | VARCHAR(30) | | NOT NULL, CHECK | Rol interno |
| job_title | VARCHAR(150) | | NULL | Cargo |
| status | VARCHAR(20) | | NOT NULL, DEFAULT 'active' | Estado |
| joined_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Incorporación |

Constraint:
UNIQUE(company_id, user_id)

member_role:
- owner
- admin
- recruiter
- viewer


### CompanyVerification

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| company_id | UUID | FK | NOT NULL, REFERENCES Company(id) ON DELETE RESTRICT | Empresa |
| status | VARCHAR(30) | | NOT NULL, CHECK | Estado |
| document_key | VARCHAR(500) | | NULL | Documento |
| reviewed_by | UUID | FK | NULL, REFERENCES User(id) ON DELETE SET NULL | Revisor |
| reviewed_at | TIMESTAMPTZ | | NULL | Fecha |
| rejection_reason | TEXT | | NULL | Motivo |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Creación |

Valores status:
- pending
- verified
- rejected


## MÓDULO 6: VACANTES

### JobCategory

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| name | VARCHAR(120) | | NOT NULL, UNIQUE | Categoría |
| is_active | BOOLEAN | | NOT NULL, DEFAULT true | Estado |


### JobPosting

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| company_id | UUID | FK | NOT NULL, REFERENCES Company(id) ON DELETE RESTRICT | Empresa |
| created_by_member_id | UUID | FK | NULL, REFERENCES CompanyMember(id) ON DELETE SET NULL | Autor |
| category_id | UUID | FK | NULL, REFERENCES JobCategory(id) ON DELETE SET NULL | Categoría |
| title | VARCHAR(200) | | NOT NULL | Título |
| description | TEXT | | NOT NULL | Descripción |
| responsibilities | TEXT | | NULL | Responsabilidades |
| requirements | TEXT | | NULL | Requisitos adicionales |
| seniority_level | VARCHAR(30) | | NULL, CHECK | Seniority |
| employment_type | VARCHAR(30) | | NULL, CHECK | Contrato |
| work_modality | VARCHAR(20) | | NULL, CHECK | Modalidad |
| minimum_education_level | VARCHAR(40) | | NULL, CHECK | Nivel educativo mínimo (mismo dominio que CandidateEducation.education_level) |
| required_experience_years | NUMERIC(4,1) | | NULL, CHECK >= 0 | Experiencia mínima |
| country_code | CHAR(2) | | NULL | País |
| city | VARCHAR(100) | | NULL | Ciudad |
| location_text | VARCHAR(300) | | NULL | Ubicación |
| latitude | NUMERIC(9,6) | | NULL, CHECK BETWEEN -90 AND 90 | Latitud |
| longitude | NUMERIC(9,6) | | NULL, CHECK BETWEEN -180 AND 180 | Longitud |
| salary_min | NUMERIC(12,2) | | NULL | Salario mínimo |
| salary_max | NUMERIC(12,2) | | NULL | Salario máximo |
| currency | CHAR(3) | | NULL | Moneda |
| salary_visible | BOOLEAN | | NOT NULL, DEFAULT true | Mostrar salario |
| positions_count | INTEGER | | NOT NULL, DEFAULT 1, CHECK > 0 | Número de posiciones |
| status | VARCHAR(30) | | NOT NULL, DEFAULT 'draft', CHECK | Estado |
| published_at | TIMESTAMPTZ | | NULL | Publicación |
| closes_at | TIMESTAMPTZ | | NULL | Cierre |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Creación |
| updated_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Actualización |

seniority_level:
- internship
- junior
- mid
- senior
- lead
- manager

employment_type:
- permanent
- temporary
- project
- internship
- freelance

work_modality:
- onsite
- remote
- hybrid

status:
- draft
- pending_review
- published
- paused
- closed
- rejected

CHECK:
salary_min <= salary_max
(latitude IS NULL) = (longitude IS NULL)
(status <> 'published') OR (published_at IS NOT NULL)
(closes_at IS NULL) OR (published_at IS NULL) OR (closes_at > published_at)

Nota:
Coordenadas opcionales y siempre en pareja; su ausencia indica vacante
remota o sin ubicación física (soporta búsqueda geolocalizada RF-M02).


### JobSkill

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| job_id | UUID | PK, FK | NOT NULL, REFERENCES JobPosting(id) ON DELETE CASCADE | Vacante |
| skill_id | UUID | PK, FK | NOT NULL, REFERENCES Skill(id) ON DELETE RESTRICT | Habilidad |
| required_level | VARCHAR(20) | | NULL, CHECK | Nivel esperado (mismo dominio que proficiency_level) |
| is_required | BOOLEAN | | NOT NULL, DEFAULT false | Excluyente |
| weight | NUMERIC(5,2) | | NULL, CHECK BETWEEN 0 AND 100 | Peso matching |

Constraint:
UNIQUE(job_id, skill_id)

Valores required_level:
- basic
- intermediate
- advanced
- expert


### JobEducationPreference

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| job_id | UUID | FK | NOT NULL, REFERENCES JobPosting(id) ON DELETE CASCADE | Vacante |
| field_of_study_id | UUID | FK | NOT NULL, REFERENCES FieldOfStudy(id) ON DELETE RESTRICT | Carrera/área |
| is_required | BOOLEAN | | NOT NULL, DEFAULT false | Si es obligatoria |

Constraint:
UNIQUE(job_id, field_of_study_id)


### ScreeningQuestion

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| job_id | UUID | FK | NOT NULL, REFERENCES JobPosting(id) ON DELETE CASCADE | Vacante |
| question_text | TEXT | | NOT NULL | Pregunta |
| question_type | VARCHAR(30) | | NOT NULL, CHECK | Tipo |
| is_required | BOOLEAN | | NOT NULL, DEFAULT true | Obligatoria |
| is_knockout | BOOLEAN | | NOT NULL, DEFAULT false | Puede descartar |
| position | INTEGER | | NOT NULL | Orden |

question_type:
- yes_no
- single_choice
- text
- number

Constraint:
UNIQUE(job_id, position)


### ScreeningOption

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| question_id | UUID | FK | NOT NULL, REFERENCES ScreeningQuestion(id) ON DELETE CASCADE | Pregunta |
| option_text | VARCHAR(300) | | NOT NULL | Opción |
| is_accepted | BOOLEAN | | NULL | Respuesta aceptable |
| position | INTEGER | | NOT NULL | Orden |

Constraint:
UNIQUE(question_id, position)


### JobSelectionStage

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| job_id | UUID | FK | NOT NULL, REFERENCES JobPosting(id) ON DELETE RESTRICT | Vacante |
| name | VARCHAR(120) | | NOT NULL | Etapa |
| position | INTEGER | | NOT NULL | Orden |
| is_terminal | BOOLEAN | | NOT NULL, DEFAULT false | Etapa final |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Creación |

Constraint:
UNIQUE(job_id, position)


### SavedSearch

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| candidate_id | UUID | FK | NOT NULL, REFERENCES CandidateProfile(id) ON DELETE CASCADE | Propietario |
| name | VARCHAR(120) | | NOT NULL | Nombre de la búsqueda guardada |
| filters_json | JSONB | | NOT NULL | Criterios: texto, categoría, modalidad, salario, ubicación, radio |
| alert_enabled | BOOLEAN | | NOT NULL, DEFAULT false | Alertas activas |
| alert_frequency | VARCHAR(20) | | NULL, CHECK | Frecuencia de alerta |
| last_alerted_at | TIMESTAMPTZ | | NULL | Última alerta enviada |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Creación |
| updated_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Actualización |

CHECK:
alert_enabled = false OR alert_frequency IS NOT NULL

Valores alert_frequency:
- immediate
- daily
- weekly


## MÓDULO 7: POSTULACIÓN Y SELECCIÓN

### Application

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| candidate_id | UUID | FK | NOT NULL, REFERENCES CandidateProfile(id) ON DELETE RESTRICT | Candidato |
| job_id | UUID | FK | NOT NULL, REFERENCES JobPosting(id) ON DELETE RESTRICT | Vacante |
| submitted_cv_document_id | UUID | FK | NULL, REFERENCES CandidateDocument(id) ON DELETE RESTRICT | CV utilizado |
| current_stage_id | UUID | FK | NULL, REFERENCES JobSelectionStage(id) ON DELETE SET NULL | Etapa actual |
| cover_letter | TEXT | | NULL | Carta |
| current_status | VARCHAR(30) | | NOT NULL, DEFAULT 'applied', CHECK | Estado |
| applied_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Postulación |
| withdrawn_at | TIMESTAMPTZ | | NULL | Retiro |
| updated_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Actualización |

Constraint:
UNIQUE(candidate_id, job_id)

current_status:
- applied
- screening
- in_review
- shortlisted
- interview
- assessment
- offer
- hired
- rejected
- withdrawn

Nota:
current_stage_id debe pertenecer a la misma vacante (job_id). Validar en backend/transacción
(ver "Integridad No Expresable con FK").


### ApplicationAnswer

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| application_id | UUID | FK | NOT NULL, REFERENCES Application(id) ON DELETE CASCADE | Postulación |
| question_id | UUID | FK | NOT NULL, REFERENCES ScreeningQuestion(id) ON DELETE RESTRICT | Pregunta |
| selected_option_id | UUID | FK | NULL, REFERENCES ScreeningOption(id) ON DELETE SET NULL | Opción |
| answer_text | TEXT | | NULL | Texto |
| answer_number | NUMERIC(15,4) | | NULL | Número |
| passed | BOOLEAN | | NULL | Resultado filtro |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Registro |

Constraint:
UNIQUE(application_id, question_id)


### ApplicationStatusHistory

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| application_id | UUID | FK | NOT NULL, REFERENCES Application(id) ON DELETE CASCADE | Postulación |
| from_status | VARCHAR(30) | | NULL, CHECK | Estado anterior |
| to_status | VARCHAR(30) | | NOT NULL, CHECK | Nuevo estado |
| changed_by | UUID | FK | NULL, REFERENCES User(id) ON DELETE SET NULL | Responsable |
| reason | TEXT | | NULL | Motivo |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Cambio |

Valores from_status / to_status (mismo dominio que Application.current_status):
- applied
- screening
- in_review
- shortlisted
- interview
- assessment
- offer
- hired
- rejected
- withdrawn


### ApplicationStageHistory

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| application_id | UUID | FK | NOT NULL, REFERENCES Application(id) ON DELETE CASCADE | Postulación |
| stage_id | UUID | FK | NOT NULL, REFERENCES JobSelectionStage(id) ON DELETE RESTRICT | Etapa |
| entered_at | TIMESTAMPTZ | | NOT NULL | Entrada |
| left_at | TIMESTAMPTZ | | NULL | Salida |
| changed_by | UUID | FK | NULL, REFERENCES User(id) ON DELETE SET NULL | Responsable |
| result | VARCHAR(30) | | NULL, CHECK | Resultado |
| notes | TEXT | | NULL | Observaciones |

result:
- passed
- failed
- withdrawn
- pending


### ApplicationNote

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| application_id | UUID | FK | NOT NULL, REFERENCES Application(id) ON DELETE CASCADE | Postulación |
| company_member_id | UUID | FK | NOT NULL, REFERENCES CompanyMember(id) ON DELETE RESTRICT | Autor |
| content | TEXT | | NOT NULL | Nota privada |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Creación |
| updated_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Actualización |


### Placement

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| application_id | UUID | FK | NOT NULL, UNIQUE, REFERENCES Application(id) ON DELETE RESTRICT | Postulación origen |
| position_title | VARCHAR(200) | | NOT NULL | Cargo |
| hire_date | DATE | | NOT NULL | Fecha contratación |
| start_date | DATE | | NULL | Inicio |
| end_date | DATE | | NULL | Fin |
| salary | NUMERIC(12,2) | | NULL | Salario |
| currency | CHAR(3) | | NULL | Moneda |
| status | VARCHAR(20) | | NOT NULL, DEFAULT 'active', CHECK | Estado |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Registro |

status:
- active
- completed
- cancelled

CHECK:
end_date >= start_date

Nota:
Placement representa una contratación obtenida mediante la plataforma.
WorkExperience representa la trayectoria laboral general.


## MÓDULO 8: COMUNICACIÓN

### Conversation

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| application_id | UUID | FK | NULL, UNIQUE, REFERENCES Application(id) ON DELETE RESTRICT | Postulación asociada (contexto aplicación) |
| candidate_id | UUID | FK | NULL, REFERENCES CandidateProfile(id) ON DELETE RESTRICT | Candidato (contexto contacto directo) |
| company_id | UUID | FK | NULL, REFERENCES Company(id) ON DELETE RESTRICT | Empresa (contexto contacto directo) |
| last_message_at | TIMESTAMPTZ | | NULL | Último mensaje |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Creación |

Restricciones:
- CHECK (exactamente un origen, nunca ambos — ver "Cambios de esta versión"):
  `(application_id IS NOT NULL) <> (candidate_id IS NOT NULL AND company_id IS NOT NULL)`
- CHECK adicional de coherencia de par: `(candidate_id IS NULL) = (company_id IS NULL)`
- UNIQUE parcial: `UNIQUE(candidate_id, company_id) WHERE application_id IS NULL` (evita chats directos duplicados por par candidato-empresa)

Contextos soportados:
- Aplicación: chat derivado de una postulación concreta.
- Contacto directo: empresa contacta proactivamente al candidato desde el pool de postulantes (HU-16).


### ConversationMember

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| conversation_id | UUID | PK, FK | NOT NULL, REFERENCES Conversation(id) ON DELETE CASCADE | Conversación |
| user_id | UUID | PK, FK | NOT NULL, REFERENCES User(id) ON DELETE RESTRICT | Participante |
| last_read_at | TIMESTAMPTZ | | NULL | Última lectura |
| joined_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Incorporación |


### Message

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| conversation_id | UUID | FK | NOT NULL, REFERENCES Conversation(id) ON DELETE CASCADE | Conversación |
| sender_id | UUID | FK | NOT NULL, REFERENCES User(id) ON DELETE RESTRICT | Emisor |
| content | TEXT | | NOT NULL | Mensaje |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Envío |
| edited_at | TIMESTAMPTZ | | NULL | Edición |
| deleted_at | TIMESTAMPTZ | | NULL | Baja lógica |


### MessageAttachment

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| message_id | UUID | FK | NOT NULL, REFERENCES Message(id) ON DELETE CASCADE | Mensaje |
| storage_key | VARCHAR(500) | | NOT NULL | Archivo |
| original_filename | VARCHAR(255) | | NOT NULL | Nombre |
| mime_type | VARCHAR(100) | | NULL | MIME |
| file_size | BIGINT | | NULL, CHECK >= 0 | Tamaño |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Creación |


## MÓDULO 9: ENTREVISTAS

### Interview

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| application_id | UUID | FK | NOT NULL, REFERENCES Application(id) ON DELETE RESTRICT | Postulación |
| scheduled_start | TIMESTAMPTZ | | NOT NULL | Inicio |
| scheduled_end | TIMESTAMPTZ | | NULL | Fin |
| modality | VARCHAR(20) | | NOT NULL, CHECK | Modalidad |
| location | VARCHAR(300) | | NULL | Ubicación |
| meeting_url | VARCHAR(500) | | NULL | Videollamada |
| status | VARCHAR(30) | | NOT NULL, DEFAULT 'scheduled', CHECK | Estado |
| created_by | UUID | FK | NULL, REFERENCES User(id) ON DELETE SET NULL | Creador |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Creación |
| updated_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Actualización |

modality:
- onsite
- virtual

status:
- scheduled
- confirmed
- completed
- cancelled
- no_show

CHECK:
scheduled_end > scheduled_start


### InterviewParticipant

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| interview_id | UUID | PK, FK | NOT NULL, REFERENCES Interview(id) ON DELETE CASCADE | Entrevista |
| user_id | UUID | PK, FK | NOT NULL, REFERENCES User(id) ON DELETE RESTRICT | Participante |
| participant_role | VARCHAR(30) | | NOT NULL, CHECK | Rol |
| confirmation_status | VARCHAR(30) | | NOT NULL, DEFAULT 'pending', CHECK | Confirmación |

confirmation_status:
- pending
- accepted
- declined

Valores participant_role:
- interviewer
- candidate
- coordinator
- observer


### InterviewFeedback

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| interview_id | UUID | FK | NOT NULL, REFERENCES Interview(id) ON DELETE CASCADE | Entrevista |
| evaluator_id | UUID | FK | NOT NULL, REFERENCES User(id) ON DELETE RESTRICT | Evaluador |
| rating | INTEGER | | NULL, CHECK BETWEEN 1 AND 5 | Calificación |
| recommendation | VARCHAR(30) | | NULL, CHECK | Recomendación |
| comments | TEXT | | NULL | Comentarios |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Creación |

Constraint:
UNIQUE(interview_id, evaluator_id)

recommendation:
- hire
- next_round
- reject
- undecided


## MÓDULO 10: NOTIFICACIONES

### Notification

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| user_id | UUID | FK | NOT NULL, REFERENCES User(id) ON DELETE CASCADE | Destinatario |
| notification_type | VARCHAR(50) | | NOT NULL | Tipo |
| title | VARCHAR(200) | | NOT NULL | Título |
| body | TEXT | | NOT NULL | Contenido |
| link | VARCHAR(500) | | NULL | Ruta relacionada |
| read_at | TIMESTAMPTZ | | NULL | Fecha de lectura |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Creación |


### NotificationPreference

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| user_id | UUID | PK, FK | NOT NULL, REFERENCES User(id) ON DELETE CASCADE | Usuario |
| email_enabled | BOOLEAN | | NOT NULL, DEFAULT true | Correo |
| push_enabled | BOOLEAN | | NOT NULL, DEFAULT true | Push |
| in_app_enabled | BOOLEAN | | NOT NULL, DEFAULT true | Internas |
| updated_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Actualización |


### DeviceToken

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| user_id | UUID | FK | NOT NULL, REFERENCES User(id) ON DELETE CASCADE | Usuario |
| token | VARCHAR(500) | | NOT NULL, UNIQUE | Token push |
| platform | VARCHAR(20) | | NOT NULL, CHECK | Plataforma |
| is_active | BOOLEAN | | NOT NULL, DEFAULT true | Estado |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Registro |

platform:
- android
- ios
- web


## MÓDULO 11: MODERACIÓN Y ANTIFRAUDE

### ModerationReport

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| reporter_id | UUID | FK | NOT NULL, REFERENCES User(id) ON DELETE RESTRICT | Usuario denunciante |
| job_id | UUID | FK | NULL, REFERENCES JobPosting(id) ON DELETE RESTRICT | Vacante |
| company_id | UUID | FK | NULL, REFERENCES Company(id) ON DELETE RESTRICT | Empresa |
| category | VARCHAR(30) | | NOT NULL, CHECK | Motivo |
| description | TEXT | | NOT NULL | Descripción |
| status | VARCHAR(30) | | NOT NULL, DEFAULT 'pending', CHECK | Estado |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Creación |
| resolved_at | TIMESTAMPTZ | | NULL | Resolución |

CHECK:
(job_id IS NULL) <> (company_id IS NULL) -- exactamente uno no nulo

category:
- fraud
- inappropriate
- spam
- fake_information
- discrimination
- other

status:
- pending
- investigating
- resolved
- dismissed


### ModerationCase

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| report_id | UUID | FK | NULL, REFERENCES ModerationReport(id) ON DELETE SET NULL | Denuncia origen |
| job_id | UUID | FK | NULL, REFERENCES JobPosting(id) ON DELETE RESTRICT | Vacante |
| company_id | UUID | FK | NULL, REFERENCES Company(id) ON DELETE RESTRICT | Empresa |
| case_type | VARCHAR(30) | | NOT NULL, CHECK | Tipo |
| status | VARCHAR(30) | | NOT NULL, DEFAULT 'open', CHECK | Estado |
| assigned_to | UUID | FK | NULL, REFERENCES User(id) ON DELETE SET NULL | Moderador |
| opened_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Apertura |
| closed_at | TIMESTAMPTZ | | NULL | Cierre |

case_type:
- prepublication_review
- user_report
- manual_review


### ModerationAction

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| case_id | UUID | FK | NOT NULL, REFERENCES ModerationCase(id) ON DELETE CASCADE | Caso |
| moderator_id | UUID | FK | NULL, REFERENCES User(id) ON DELETE SET NULL | Moderador |
| action | VARCHAR(40) | | NOT NULL, CHECK | Acción |
| notes | TEXT | | NULL | Observaciones |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Fecha |

Valores action:
- reject_job_posting
- suspend_company
- suspend_user
- warn_user
- dismiss_report
- restore_content


## MÓDULO 12: INTELIGENCIA ARTIFICIAL

### AIModel

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| model_name | VARCHAR(150) | | NOT NULL | Modelo |
| version | VARCHAR(50) | | NOT NULL | Versión |
| model_type | VARCHAR(40) | | NOT NULL, CHECK | Tipo |
| configuration_json | JSONB | | NULL | Configuración |
| is_active | BOOLEAN | | NOT NULL, DEFAULT false | Modelo activo |
| trained_at | TIMESTAMPTZ | | NULL | Entrenamiento |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Registro |

Constraint:
UNIQUE(model_name, version)

model_type:
- matching
- generative
- chatbot
- embedding
- employability_prediction


### MatchScore

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| candidate_id | UUID | FK | NOT NULL, REFERENCES CandidateProfile(id) ON DELETE CASCADE | Candidato |
| job_id | UUID | FK | NOT NULL, REFERENCES JobPosting(id) ON DELETE CASCADE | Vacante |
| model_id | UUID | FK | NOT NULL, REFERENCES AIModel(id) ON DELETE RESTRICT | Modelo |
| candidate_fit_score | NUMERIC(5,4) | | NOT NULL, CHECK BETWEEN 0 AND 1 | Afinidad para candidato |
| employer_fit_score | NUMERIC(5,4) | | NOT NULL, CHECK BETWEEN 0 AND 1 | Afinidad para empresa |
| overall_score | NUMERIC(5,4) | | NOT NULL, CHECK BETWEEN 0 AND 1 | Score total |
| explanation_json | JSONB | | NULL | Explicación |
| computed_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Cálculo |

Constraint:
UNIQUE(candidate_id, job_id, model_id)


### JobEmbedding

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| job_id | UUID | PK, FK | NOT NULL, REFERENCES JobPosting(id) ON DELETE CASCADE | Vacante vectorizada |
| model_id | UUID | PK, FK | NOT NULL, REFERENCES AIModel(id) ON DELETE RESTRICT | Modelo generador del vector |
| content_hash | VARCHAR(64) | | NOT NULL | Hash del texto fuente; detecta vectores obsoletos |
| embedding | VECTOR(768) | | NOT NULL | Vector de embeddings de la vacante |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Creación |
| updated_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Última regeneración |

PK compuesta: (job_id, model_id)


### CandidateEmbedding

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| candidate_id | UUID | PK, FK | NOT NULL, REFERENCES CandidateProfile(id) ON DELETE CASCADE | Candidato vectorizado |
| model_id | UUID | PK, FK | NOT NULL, REFERENCES AIModel(id) ON DELETE RESTRICT | Modelo generador del vector |
| content_hash | VARCHAR(64) | | NOT NULL | Hash del texto fuente; detecta vectores obsoletos |
| embedding | VECTOR(768) | | NOT NULL | Vector de embeddings del perfil |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Creación |
| updated_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Última regeneración |

PK compuesta: (candidate_id, model_id)

Notas pgvector:
- Requiere: `CREATE EXTENSION IF NOT EXISTS vector;` (la imagen de Postgres debe incluirla, ver cabecera).
- La dimensión (768) depende del modelo activo; cambiarla implica registrar un nuevo AIModel
  y, en la práctica, crear una tabla de embeddings nueva o migrar los vectores existentes
  (pgvector no permite un `ALTER COLUMN` que cambie la dimensión sin recalcular los vectores).
- Índice HNSW sobre embedding para similitud coseno.


### AIGeneratedContent

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| user_id | UUID | FK | NULL, REFERENCES User(id) ON DELETE SET NULL | Solicitante |
| model_id | UUID | FK | NULL, REFERENCES AIModel(id) ON DELETE SET NULL | Modelo |
| candidate_id | UUID | FK | NULL, REFERENCES CandidateProfile(id) ON DELETE SET NULL | Candidato relacionado |
| job_id | UUID | FK | NULL, REFERENCES JobPosting(id) ON DELETE SET NULL | Vacante relacionada |
| content_type | VARCHAR(40) | | NOT NULL, CHECK | Tipo |
| generated_text | TEXT | | NOT NULL | Contenido |
| accepted_at | TIMESTAMPTZ | | NULL | Aceptación |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Creación |

content_type:
- professional_summary
- job_description
- interview_advice


### ChatbotSession

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Sesión |
| user_id | UUID | FK | NULL, REFERENCES User(id) ON DELETE SET NULL | Usuario |
| started_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Inicio |
| ended_at | TIMESTAMPTZ | | NULL | Fin |


### ChatbotMessage

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Mensaje |
| session_id | UUID | FK | NOT NULL, REFERENCES ChatbotSession(id) ON DELETE CASCADE | Sesión |
| message_role | VARCHAR(20) | | NOT NULL, CHECK | Rol |
| content | TEXT | | NOT NULL | Contenido |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Fecha |

message_role:
- user
- assistant
- system


### SemanticSearchLog

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| user_id | UUID | FK | NULL, REFERENCES User(id) ON DELETE SET NULL | Usuario |
| query_text | TEXT | | NOT NULL | Consulta |
| results_count | INTEGER | | NULL, CHECK >= 0 | Resultados |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Fecha |


### EmployabilityPrediction

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| model_id | UUID | FK | NULL, REFERENCES AIModel(id) ON DELETE SET NULL | Modelo |
| institution_id | UUID | FK | NULL, REFERENCES EducationalInstitution(id) ON DELETE SET NULL | Institución |
| field_of_study_id | UUID | FK | NULL, REFERENCES FieldOfStudy(id) ON DELETE SET NULL | Área |
| metric_name | VARCHAR(80) | | NOT NULL | Métrica |
| predicted_value | NUMERIC(12,4) | | NOT NULL | Predicción |
| unit | VARCHAR(30) | | NOT NULL | Unidad |
| forecast_start | DATE | | NULL | Inicio período |
| forecast_end | DATE | | NULL | Fin período |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Generación |


## MÓDULO 13: ENCUESTAS Y REPORTES

### Survey

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| title | VARCHAR(250) | | NOT NULL | Título |
| description | TEXT | | NULL | Descripción |
| target_scope | VARCHAR(30) | | NOT NULL, DEFAULT 'all_candidates', CHECK | Segmento |
| institution_id | UUID | FK | NULL, REFERENCES EducationalInstitution(id) ON DELETE SET NULL | Institución |
| field_of_study_id | UUID | FK | NULL, REFERENCES FieldOfStudy(id) ON DELETE SET NULL | Área |
| created_by | UUID | FK | NULL, REFERENCES User(id) ON DELETE SET NULL | Creador |
| is_active | BOOLEAN | | NOT NULL, DEFAULT true | Estado |
| starts_at | TIMESTAMPTZ | | NULL | Inicio |
| expires_at | TIMESTAMPTZ | | NULL | Expiración |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Creación |

target_scope:
- all_candidates
- institution
- field_of_study

CHECK:
(target_scope <> 'all_candidates') OR (institution_id IS NULL AND field_of_study_id IS NULL)
(target_scope <> 'institution') OR (institution_id IS NOT NULL)
(target_scope <> 'field_of_study') OR (field_of_study_id IS NOT NULL)


### SurveyQuestion

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| survey_id | UUID | FK | NOT NULL, REFERENCES Survey(id) ON DELETE CASCADE | Encuesta |
| question_text | TEXT | | NOT NULL | Pregunta |
| question_type | VARCHAR(30) | | NOT NULL, CHECK | Tipo |
| is_required | BOOLEAN | | NOT NULL, DEFAULT true | Obligatoria |
| position | INTEGER | | NOT NULL | Orden |

question_type:
- single_choice
- text
- number
- scale

Constraint:
UNIQUE(survey_id, position)


### SurveyQuestionOption

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| question_id | UUID | FK | NOT NULL, REFERENCES SurveyQuestion(id) ON DELETE CASCADE | Pregunta |
| option_text | VARCHAR(300) | | NOT NULL | Opción |
| position | INTEGER | | NOT NULL | Orden |

Constraint:
UNIQUE(question_id, position)


### SurveyResponse

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| survey_id | UUID | FK | NOT NULL, REFERENCES Survey(id) ON DELETE RESTRICT | Encuesta |
| candidate_id | UUID | FK | NOT NULL, REFERENCES CandidateProfile(id) ON DELETE RESTRICT | Candidato |
| submitted_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Envío |

Constraint:
UNIQUE(survey_id, candidate_id)


### SurveyAnswer

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| response_id | UUID | FK | NOT NULL, REFERENCES SurveyResponse(id) ON DELETE CASCADE | Respuesta |
| question_id | UUID | FK | NOT NULL, REFERENCES SurveyQuestion(id) ON DELETE RESTRICT | Pregunta |
| selected_option_id | UUID | FK | NULL, REFERENCES SurveyQuestionOption(id) ON DELETE SET NULL | Opción |
| answer_text | TEXT | | NULL | Texto |
| answer_number | NUMERIC(15,4) | | NULL | Número |
| created_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Registro |

Constraint:
UNIQUE(response_id, question_id)


### GeneratedReport

| Nombre | Tipo | PK/FK | Restricciones | Descripción |
|---|---|---|---|---|
| id | UUID | PK | NOT NULL, DEFAULT gen_random_uuid() | Identificador |
| requested_by | UUID | FK | NULL, REFERENCES User(id) ON DELETE SET NULL | Usuario |
| report_type | VARCHAR(80) | | NOT NULL | Tipo |
| parameters_json | JSONB | | NULL | Filtros |
| storage_key | VARCHAR(500) | | NOT NULL | Archivo |
| file_format | VARCHAR(20) | | NOT NULL, CHECK | Formato |
| generated_at | TIMESTAMPTZ | | NOT NULL, DEFAULT NOW() | Generación |

file_format:
- pdf
- xlsx
- csv


## Vistas Analíticas Recomendadas

No deberían crearse como tablas transaccionales normales.

1. mv_skill_demand
   Origen: JobPosting, JobSkill, Skill

2. mv_skill_gap
   Origen: CandidateSkill, JobSkill, CandidateEducation

3. mv_placement_rate
   Origen: Application, Placement, CandidateEducation

4. mv_time_to_first_job
   Origen: CandidateEducation, Placement, WorkExperience

5. mv_company_hiring_stats
   Origen: Company, JobPosting, Application, Placement

6. mv_employment_by_field
   Origen: CandidateEducation, EmploymentStatusHistory, Placement


## Relaciones Principales

```
User (1) --------- (0..1) CandidateProfile
User (M) -- UserRole -- (N) Role
User (1) --------- (M) UserToken
User (1) --------- (M) AuditLog
User (1) --------- (M) PasswordHistory
User (1) --------- (M) LoginAttempt

CandidateProfile (1) --------- (1) CandidatePreference
CandidateProfile (1) --------- (M) CandidateEducation
CandidateProfile (M) -- CandidateSkill -- (N) Skill
CandidateProfile (M) -- CandidateLanguage -- (N) Language
CandidateProfile (1) --------- (M) Certification
CandidateProfile (1) --------- (M) WorkExperience
CandidateProfile (1) --------- (M) EmploymentStatusHistory
CandidateProfile (1) --------- (M) CandidateDocument
CandidateProfile (1) --------- (M) SavedSearch
CandidateProfile (1) --------- (M) CandidateEmbedding
WorkExperience (M) --------- (0..1) Company
EmploymentStatusHistory (M) --------- (0..1) WorkExperience

CandidateEducation (M) --------- (1) EducationalInstitution
CandidateEducation (M) --------- (1) FieldOfStudy
CandidateEducation (1) --------- (M) EducationVerification

Company (1) --------- (M) CompanyMember
User (1) --------- (M) CompanyMember
Company (1) --------- (M) CompanyVerification
Company (1) --------- (M) JobPosting
JobPosting (M) --------- (0..1) CompanyMember (created_by_member_id, autor)

JobPosting (M) -- JobSkill -- (N) Skill
JobPosting (1) --------- (M) JobEducationPreference
FieldOfStudy (1) --------- (M) JobEducationPreference

JobPosting (1) --------- (M) ScreeningQuestion
ScreeningQuestion (1) --------- (M) ScreeningOption

JobPosting (1) --------- (M) JobSelectionStage

CandidateProfile (M) -- Application -- (N) JobPosting

Application (1) --------- (M) ApplicationAnswer
Application (1) --------- (M) ApplicationStatusHistory
Application (1) --------- (M) ApplicationStageHistory
Application (1) --------- (M) ApplicationNote
Application (1) --------- (0..1) Placement
Application (M) --------- (0..1) CandidateDocument (CV utilizado en la postulación)

Application (1) --------- (0..1) Conversation (contexto aplicación)
Company (1) --------- (M) Conversation (contexto contacto directo)
CandidateProfile (1) --------- (M) Conversation (contexto contacto directo)
Conversation (M) -- ConversationMember -- (N) User
Conversation (1) --------- (M) Message
Message (1) --------- (M) MessageAttachment

Application (1) --------- (M) Interview
Interview (M) -- InterviewParticipant -- (N) User
Interview (1) --------- (M) InterviewFeedback

User (1) --------- (M) Notification
User (1) --------- (1) NotificationPreference
User (1) --------- (M) DeviceToken

CandidateProfile (1) --------- (M) MatchScore
JobPosting (1) --------- (M) MatchScore
AIModel (1) --------- (M) MatchScore
AIModel (1) --------- (M) JobEmbedding
JobPosting (1) --------- (M) JobEmbedding

User (1) --------- (M) ModerationReport
ModerationReport (M) --------- (0..1) JobPosting
ModerationReport (M) --------- (0..1) Company
ModerationCase (M) --------- (0..1) ModerationReport
ModerationCase (M) --------- (0..1) JobPosting
ModerationCase (M) --------- (0..1) Company
ModerationCase (M) --------- (0..1) User (assigned_to)
ModerationCase (1) --------- (M) ModerationAction

User (1) --------- (M) AIGeneratedContent
AIModel (1) --------- (M) AIGeneratedContent
ChatbotSession (M) --------- (0..1) User
ChatbotSession (1) --------- (M) ChatbotMessage
User (1) --------- (M) SemanticSearchLog
AIModel (1) --------- (M) EmployabilityPrediction
User (1) --------- (M) GeneratedReport

Survey (1) --------- (M) SurveyQuestion
SurveyQuestion (1) --------- (M) SurveyQuestionOption
Survey (1) --------- (M) SurveyResponse
SurveyResponse (1) --------- (M) SurveyAnswer
Survey (M) --------- (0..1) EducationalInstitution (target_scope)
Survey (M) --------- (0..1) FieldOfStudy (target_scope)
Survey (M) --------- (0..1) User (created_by)
```


## Índices Recomendados

Los siguientes índices forman parte del DDL inicial, además de PK y UNIQUE ya definidos.

### Módulo 1 - Seguridad
- User: índice único parcial (LOWER(email)) WHERE deleted_at IS NULL.
- UserToken: (user_id); (expires_at) WHERE used_at IS NULL AND revoked_at IS NULL.
- PasswordHistory: (user_id, created_at DESC).
- LoginAttempt: (email, created_at DESC); (ip_address, created_at DESC).
- AuditLog: (entity_type, entity_id); (user_id, created_at DESC); (created_at DESC).

### Módulos 2/3/4 - Candidatos y perfil
- CandidateProfile: unique parcial (document_country_code, document_type, document_number) WHERE document_number IS NOT NULL; (verification_status).
- CandidateEducation: (candidate_id); (institution_id); (field_of_study_id); (graduation_date).
- WorkExperience: (candidate_id, start_date DESC).
- Certification / CandidateDocument / CandidateSkill / CandidateLanguage: (candidate_id).
- EmploymentStatusHistory: (candidate_id, effective_from); unique parcial (candidate_id) WHERE effective_to IS NULL (un solo estado laboral vigente).

### Módulo 5 - Empresas
- Company: unique parcial (country_code, tax_id) WHERE tax_id IS NOT NULL; (sector_id); (verification_status).
- CompanyMember: (user_id).

### Módulo 6 - Vacantes
- JobPosting: (company_id, status); (status, published_at DESC); (category_id); (country_code, city); (latitude, longitude).
- JobSkill: (skill_id).
- SavedSearch: (candidate_id); (alert_frequency) WHERE alert_enabled = true.

### Módulo 7 - Postulación
- Application: (job_id); (current_status). El UNIQUE(candidate_id, job_id) cubre filtros por candidato.
- ApplicationAnswer / ApplicationStatusHistory / ApplicationStageHistory / ApplicationNote: (application_id).
- ApplicationStageHistory: unique parcial (application_id) WHERE left_at IS NULL (impide estar en dos etapas activas a la vez).
- Placement: (hire_date DESC).

### Módulos 8/9 - Comunicación y entrevistas
- Message: (conversation_id, created_at DESC).
- MessageAttachment: (message_id).
- ConversationMember: (user_id).
- Interview: (application_id); (scheduled_start).
- InterviewParticipant: (user_id); InterviewFeedback: (evaluator_id).

### Módulo 10 - Notificaciones
- Notification: (user_id, created_at DESC); (user_id) WHERE read_at IS NULL.
- DeviceToken: (user_id).

### Módulo 11 - Moderación
- ModerationReport: (status, created_at DESC); (reporter_id).
- ModerationCase: (status); (assigned_to).

### Módulo 12 - IA
- JobEmbedding / CandidateEmbedding: índice HNSW sobre embedding (cosine_ops); los PK compuestos cubren acceso por entidad y modelo.
- MatchScore: (job_id, overall_score DESC); (candidate_id, overall_score DESC).
- ChatbotMessage: (session_id, created_at).

### Módulo 13 - Encuestas y reportes
- SurveyResponse: el UNIQUE(survey_id, candidate_id) ya cubre los accesos típicos; añadir (survey_id) si se listan respuestas por encuesta.
- SurveyAnswer: (response_id); (question_id).
- GeneratedReport: (generated_at DESC).


## Integridad No Expresable con FK (Trigger o Servicio)

Estas reglas cruzan entidades y no pueden garantizarse con claves foráneas simples:

1. Application.current_stage_id: la etapa debe pertenecer a la misma vacante (JobSelectionStage.job_id = Application.job_id). Trigger BEFORE INSERT OR UPDATE.
2. Message.sender_id debe ser miembro de la conversación (ConversationMember).
3. SurveyAnswer.question_id debe pertenecer a la encuesta de su SurveyResponse.
4. ApplicationAnswer.question_id debe pertenecer a una ScreeningQuestion de la vacante postulada; selected_option_id debe pertenecer a esa pregunta.
5. Toda Interview debe incluir como participante al candidato titular de la postulación.
6. Las transiciones de Application.current_status siguen una máquina de estados permitida (validación en servicio; histórico en ApplicationStatusHistory).
7. Una vacante en estado closed o rejected no acepta nuevas Application.


## Orden de Creación Sugerido (DDL)

Resuelve las dependencias entre módulos (incluida la referencia adelantada EducationVerification → CandidateDocument):

1. Extensión: `CREATE EXTENSION IF NOT EXISTS vector;`
2. Catálogos sin dependencias: Role, Skill, Language, Sector, EducationalInstitution, FieldOfStudy, JobCategory, AIModel
3. User → UserRole, UserToken, PasswordHistory, LoginAttempt, AuditLog, NotificationPreference, DeviceToken
4. CandidateProfile → CandidatePreference, CandidateDocument, CandidateEducation, CandidateSkill, CandidateLanguage, Certification, SavedSearch, CandidateEmbedding
5. Company → CompanyMember, CompanyVerification (requerida por WorkExperience del paso 6)
6. WorkExperience → EmploymentStatusHistory
7. JobPosting → JobSkill, JobEducationPreference, ScreeningQuestion → ScreeningOption, JobSelectionStage, JobEmbedding
8. Application → ApplicationAnswer, ApplicationStatusHistory, ApplicationStageHistory, ApplicationNote, Placement
9. Conversation → ConversationMember, Message → MessageAttachment
10. Interview → InterviewParticipant, InterviewFeedback
11. Notification
12. EducationVerification (requiere CandidateDocument del paso 4); MatchScore
13. Survey → SurveyQuestion → SurveyQuestionOption, SurveyResponse → SurveyAnswer (Survey requiere User del paso 3)
14. ModerationReport → ModerationCase → ModerationAction
15. AIGeneratedContent, ChatbotSession → ChatbotMessage, SemanticSearchLog, EmployabilityPrediction
16. GeneratedReport
17. Vistas materializadas analíticas

Nota práctica: si el equipo genera el esquema con SQLAlchemy + Alembic en vez de SQL a mano,
`Base.metadata.create_all()` y el autogenerate de Alembic ordenan las dependencias de FK
automáticamente y este orden manual deja de ser necesario mantenerlo a mano.


## Reglas Clave del Diseño

1. La plataforma no depende de una universidad específica.
2. UAGRM es una EducationalInstitution más dentro del sistema.
3. CandidateProfile no tiene university_id ni career_id.
4. Toda formación académica se guarda en CandidateEducation.
5. Una empresa puede tener múltiples usuarios mediante CompanyMember.
6. Un candidato no puede postular dos veces a la misma vacante.
7. Una vacante puede requerir múltiples habilidades.
8. Una vacante puede aceptar múltiples áreas académicas.
9. Application.current_status conserva el estado actual y ApplicationStatusHistory el histórico.
10. Application.current_stage_id conserva la etapa actual y ApplicationStageHistory el histórico.
11. Una postulación puede tener múltiples entrevistas.
12. Una entrevista puede tener múltiples evaluadores.
13. Una conversación tiene un único origen: una postulación o un contacto directo candidato-empresa (ver regla 23).
14. Placement representa contratación lograda mediante la plataforma.
15. WorkExperience representa trayectoria laboral general del candidato.
16. Los archivos no se almacenan físicamente en PostgreSQL.
17. PostgreSQL guarda solamente storage_key, metadatos y referencias.
18. Los scores de IA deben quedar asociados a la versión del modelo utilizado.
19. Los reportes analíticos derivados deben implementarse preferentemente mediante VIEW o MATERIALIZED VIEW.
20. No eliminar físicamente vacantes, empresas o usuarios con historial relevante.
21. El documento de identidad del candidato es único por país emisor y tipo de documento.
22. La verificación institucional del egresado opera en dos niveles: por estudio (EducationVerification) y estado global (CandidateProfile.verification_status).
23. Toda conversación tiene un único origen: una postulación o un contacto directo candidato-empresa; nunca ambos a la vez. El CHECK de `Conversation` usa `<>` (exclusión mutua real), igual que en `ModerationReport`.
24. Los embeddings quedan asociados a la versión del modelo que los generó; content_hash indica cuándo deben regenerarse.
25. Las coordenadas geográficas son opcionales, van en pareja y su ausencia implica vacante remota o sin ubicación física.
26. SavedSearch agrupa criterios de búsqueda reutilizables y configura alertas por frecuencia (inmediata/diaria/semanal).
27. PasswordHistory impide el reuso de contraseñas recientes; LoginAttempt alimenta el rate-limiting y bloqueos temporales.
28. Los índices de la sección correspondiente forman parte del DDL inicial; ajustes posteriores solo con medición previa (EXPLAIN).
29. Todo dominio de valores fijos (VARCHAR + CHECK) debe estar enumerado explícitamente junto a la tabla que lo define; una referencia "mismo dominio que X" sin lista propia no es ejecutable como CHECK real (ver corrección en ApplicationStatusHistory).


## Cambios de esta versión (V3, respecto de V2)

1. **Conversation — bug de exclusión mutua corregido.** El CHECK de V2 (`application_id IS NOT NULL OR (candidate_id IS NOT NULL AND company_id IS NOT NULL)`) permitía que una fila tuviera los tres campos llenos a la vez, violando la propia Regla 23 ("nunca ambos"). Se reemplazó por `(application_id IS NOT NULL) <> (candidate_id IS NOT NULL AND company_id IS NOT NULL)`, siguiendo el mismo patrón `<>` que ya se usaba correctamente en `ModerationReport`. Se agregó además un CHECK de coherencia de par `(candidate_id IS NULL) = (company_id IS NULL)`.
2. **ApplicationStatusHistory — dominio formalizado.** En V2, `from_status`/`to_status` solo tenían una nota de texto ("mismo dominio que Application.current_status") sin lista de valores propia, por lo que no era un CHECK ejecutable. Se agregó `CHECK` en ambas columnas y se enumeraron los 10 valores válidos.
3. **Cabecera — imagen de Postgres.** Se aclaró que `pgvector` requiere una imagen de PostgreSQL que la incluya (`pgvector/pgvector:pg16`), ya que la imagen oficial `postgres:16-alpine` no trae la extensión instalada.
4. **Regla 29 agregada**, documentando el criterio general que motivó la corrección #2 (todo dominio debe enumerarse junto a su tabla, no solo mencionarse por referencia).

Sin cambios de alcance: siguen siendo 67 tablas, mismas 13 módulos, mismo orden de creación (salvo la nota práctica sobre Alembic agregada al final de esa sección).

---

**Fin del diseño lógico.**
