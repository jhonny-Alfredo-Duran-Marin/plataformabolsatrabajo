"""Cambios de esquema aditivos e idempotentes que el backend asegura al arrancar.

Solo agregan lo que falta (nunca borran datos) y antes de cada ALTER se consulta el
catálogo, así un arranque normal no toma candados sobre tablas con tráfico. Sirve para que
un despliegue no dependa de que alguien haya corrido antes la migración a mano.
"""

import logging

from sqlalchemy import Connection, text

logger = logging.getLogger(__name__)

# Índices de las consultas frecuentes (campanita, pipeline de la empresa, mis postulaciones,
# bitácora, tareas diarias, listado de vacantes). Postgres no indexa las claves foráneas solo.
# (nombre, tabla, sentencia); solo se crean si la tabla existe y el índice no.
_INDICES = (
    ("ix_notification_user_created", "notification",
     "CREATE INDEX IF NOT EXISTS ix_notification_user_created ON notification (user_id, created_at DESC)"),
    ("ix_notification_type_link", "notification",
     "CREATE INDEX IF NOT EXISTS ix_notification_type_link ON notification (notification_type, link)"),
    ("ix_application_job", "application",
     "CREATE INDEX IF NOT EXISTS ix_application_job ON application (job_id)"),
    ("ix_application_candidate", "application",
     "CREATE INDEX IF NOT EXISTS ix_application_candidate ON application (candidate_id)"),
    ("ix_company_member_user", "company_member",
     "CREATE INDEX IF NOT EXISTS ix_company_member_user ON company_member (user_id)"),
    ("ix_company_member_company", "company_member",
     "CREATE INDEX IF NOT EXISTS ix_company_member_company ON company_member (company_id)"),
    ("ix_interview_start", "interview",
     "CREATE INDEX IF NOT EXISTS ix_interview_start ON interview (scheduled_start)"),
    ("ix_audit_log_created", "audit_log",
     "CREATE INDEX IF NOT EXISTS ix_audit_log_created ON audit_log (created_at DESC)"),
    ("ix_audit_log_user_created", "audit_log",
     "CREATE INDEX IF NOT EXISTS ix_audit_log_user_created ON audit_log (user_id, created_at DESC)"),
    ("ix_moderation_report_job", "moderation_report",
     "CREATE INDEX IF NOT EXISTS ix_moderation_report_job ON moderation_report (job_id)"),
    ("ix_job_posting_published_feed", "job_posting",
     "CREATE INDEX IF NOT EXISTS ix_job_posting_published_feed ON job_posting (published_at DESC NULLS LAST) "
     "WHERE status = 'published'"),
)

_TAREAS = """CREATE TABLE IF NOT EXISTS scheduled_task_run (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    task varchar(50) NOT NULL,
    trigger varchar(20) NOT NULL DEFAULT 'automatico',
    status varchar(20) NOT NULL DEFAULT 'running',
    summary varchar(500),
    triggered_by_email varchar(255),
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    CONSTRAINT ck_task_run_trigger CHECK (trigger IN ('automatico', 'manual')),
    CONSTRAINT ck_task_run_status CHECK (status IN ('running', 'success', 'failure'))
)"""


_GRUPOS = (
    """CREATE TABLE IF NOT EXISTS user_group (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES educational_institution(id) ON DELETE CASCADE,
    name varchar(80) NOT NULL,
    description text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_user_group_name UNIQUE (institution_id, name)
)""",
    """CREATE TABLE IF NOT EXISTS user_group_member (
    group_id uuid NOT NULL REFERENCES user_group(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    added_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (group_id, user_id)
)""",
    """CREATE TABLE IF NOT EXISTS user_group_permission (
    group_id uuid NOT NULL REFERENCES user_group(id) ON DELETE CASCADE,
    permission_code varchar(80) NOT NULL,
    PRIMARY KEY (group_id, permission_code)
)""",
    "CREATE INDEX IF NOT EXISTS ix_user_group_member_user ON user_group_member (user_id)",
    "ALTER TABLE user_group ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE user_group_member ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE user_group_permission ENABLE ROW LEVEL SECURITY",
)


def asegurar_esquema_requisitos(conn: Connection) -> list[str]:
    """Bitácora cifrada, copias automáticas, tareas programadas y grupos de usuarios.

    Devuelve lo que cambió.
    """
    cambios: list[str] = []

    # En una base nueva las tablas todavía no existen: las crea después create_all con todo.
    existe_bitacora = conn.execute(text("SELECT to_regclass('public.audit_log')")).scalar() is not None
    tiene_payload = conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'audit_log' AND column_name = 'payload_cifrado'"
        )
    ).first()
    if existe_bitacora and tiene_payload is None:
        conn.execute(text("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS payload_cifrado text"))
        cambios.append("audit_log.payload_cifrado")

    regla = conn.execute(
        text("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'ck_system_backup_kind'")
    ).scalar()
    if regla is not None and "automatica" not in regla:
        conn.execute(text("ALTER TABLE system_backup DROP CONSTRAINT ck_system_backup_kind"))
        conn.execute(
            text(
                "ALTER TABLE system_backup ADD CONSTRAINT ck_system_backup_kind "
                "CHECK (kind IN ('manual', 'previa_restauracion', 'subido', 'automatica'))"
            )
        )
        cambios.append("system_backup.kind admite 'automatica'")

    if conn.execute(text("SELECT to_regclass('public.scheduled_task_run')")).scalar() is None:
        conn.execute(text(_TAREAS))
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_task_run_task_started ON scheduled_task_run (task, started_at DESC)")
        )
        conn.execute(text("ALTER TABLE scheduled_task_run ENABLE ROW LEVEL SECURITY"))
        cambios.append("scheduled_task_run")

    # Grupos de usuarios (requisito 2). Necesitan las tablas a las que referencian.
    existe_base = conn.execute(text("SELECT to_regclass('public.app_user')")).scalar() is not None
    falta_grupos = conn.execute(text("SELECT to_regclass('public.user_group_permission')")).scalar() is None
    if existe_base and falta_grupos:
        for sentencia in _GRUPOS:
            conn.execute(text(sentencia))
        cambios.append("user_group, user_group_member, user_group_permission")

    _asegurar_columnas_de_encuestas(conn, cambios)
    _asegurar_indices(conn, cambios)
    return cambios


# Las tablas de encuestas ya existen en Supabase con el diseño original: la HU-30 les suma el
# período de la encuesta y un código estable en preguntas y opciones (los lee el tablero de la HU-31).
_COLUMNAS_DE_ENCUESTAS = (
    ("survey", "period", "ALTER TABLE survey ADD COLUMN IF NOT EXISTS period varchar(40) NOT NULL DEFAULT ''"),
    ("survey_question", "code", "ALTER TABLE survey_question ADD COLUMN IF NOT EXISTS code varchar(40)"),
    ("survey_question_option", "code", "ALTER TABLE survey_question_option ADD COLUMN IF NOT EXISTS code varchar(40)"),
)


def _asegurar_columnas_de_encuestas(conn: Connection, cambios: list[str]) -> None:
    """Agrega las columnas que faltan. En una base nueva las tablas las crea create_all ya completas."""
    for tabla, columna, sentencia in _COLUMNAS_DE_ENCUESTAS:
        if conn.execute(text("SELECT to_regclass(:t)"), {"t": f"public.{tabla}"}).scalar() is None:
            continue
        tiene = conn.execute(
            text("SELECT 1 FROM information_schema.columns WHERE table_name = :t AND column_name = :c"),
            {"t": tabla, "c": columna},
        ).first()
        if tiene is None:
            conn.execute(text(sentencia))
            cambios.append(f"{tabla}.{columna}")


def _asegurar_indices(conn: Connection, cambios: list[str]) -> None:
    """Crea los índices que faltan. Cada uno en su savepoint: si uno falla, los demás y el resto
    del esquema siguen igual."""
    for nombre, tabla, sentencia in _INDICES:
        if conn.execute(text("SELECT to_regclass(:t)"), {"t": f"public.{tabla}"}).scalar() is None:
            continue
        if conn.execute(text("SELECT to_regclass(:i)"), {"i": f"public.{nombre}"}).scalar() is not None:
            continue
        try:
            with conn.begin_nested():
                conn.execute(text(sentencia))
            cambios.append(nombre)
        except Exception:  # noqa: BLE001 - un índice es una optimización: si no se puede crear, se sigue
            logger.warning("No se pudo crear el índice %s", nombre, exc_info=True)
