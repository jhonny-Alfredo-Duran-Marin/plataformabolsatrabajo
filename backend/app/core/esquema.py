"""Cambios de esquema aditivos e idempotentes que el backend asegura al arrancar.

Solo agregan lo que falta (nunca borran datos) y antes de cada ALTER se consulta el
catálogo, así un arranque normal no toma candados sobre tablas con tráfico. Sirve para que
un despliegue no dependa de que alguien haya corrido antes la migración a mano.
"""

import logging

from sqlalchemy import Connection, text

from app.core.tenancy import INSTITUCION_POR_DEFECTO_ID

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

_CHATBOT = (
    """CREATE TABLE IF NOT EXISTS chatbot_session (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES app_user(id) ON DELETE SET NULL,
    started_at timestamptz NOT NULL DEFAULT now(),
    ended_at timestamptz
)""",
    """CREATE TABLE IF NOT EXISTS chatbot_message (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES chatbot_session(id) ON DELETE CASCADE,
    message_role varchar(20) NOT NULL,
    content text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_chatbot_message_role CHECK (message_role IN ('user', 'assistant', 'system'))
)""",
    "CREATE INDEX IF NOT EXISTS ix_chatbot_session_user ON chatbot_session (user_id, started_at DESC)",
    "CREATE INDEX IF NOT EXISTS ix_chatbot_message_session_created ON chatbot_message (session_id, created_at)",
    "ALTER TABLE chatbot_session ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE chatbot_message ENABLE ROW LEVEL SECURITY",
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

    # HU-28: Sesiones y mensajes del chatbot de orientación.
    falta_chatbot = conn.execute(text("SELECT to_regclass('public.chatbot_message')")).scalar() is None
    if existe_base and falta_chatbot:
        for sentencia in _CHATBOT:
            conn.execute(text(sentencia))
        cambios.append("chatbot_session, chatbot_message")

    _asegurar_columnas_de_encuestas(conn, cambios)
    _adaptar_colocaciones(conn, cambios)
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


# La tabla placement ya existe en Supabase con el diseño V3: siempre atada a una postulación y con
# estados active/completed/cancelled. La HU-29 también registra contrataciones hechas fuera de la
# plataforma, por universidad, sugeridas o confirmadas y con baja lógica.
_COLOCACIONES = (
    "ALTER TABLE placement ADD COLUMN IF NOT EXISTS candidate_id uuid "
    "REFERENCES candidate_profile(id) ON DELETE RESTRICT",
    "ALTER TABLE placement ADD COLUMN IF NOT EXISTS institution_id uuid "
    "REFERENCES educational_institution(id) ON DELETE RESTRICT",
    "ALTER TABLE placement ADD COLUMN IF NOT EXISTS company_id uuid REFERENCES company(id) ON DELETE RESTRICT",
    "ALTER TABLE placement ADD COLUMN IF NOT EXISTS company_name varchar(250)",
    "ALTER TABLE placement ADD COLUMN IF NOT EXISTS source varchar(20) NOT NULL DEFAULT 'manual'",
    "ALTER TABLE placement ADD COLUMN IF NOT EXISTS updated_reason text",
    "ALTER TABLE placement ADD COLUMN IF NOT EXISTS deleted_at timestamptz",
    "ALTER TABLE placement ADD COLUMN IF NOT EXISTS deleted_reason text",
    "ALTER TABLE placement ADD COLUMN IF NOT EXISTS created_by uuid REFERENCES app_user(id) ON DELETE SET NULL",
    "ALTER TABLE placement ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now()",
    # Una colocación cargada a mano no tiene postulación ni una fecha de contratación aparte.
    "ALTER TABLE placement ALTER COLUMN application_id DROP NOT NULL",
    "ALTER TABLE placement ALTER COLUMN hire_date DROP NOT NULL",
    # Las filas del diseño anterior vienen de una postulación: se completan con sus datos.
    """UPDATE placement p
       SET candidate_id = a.candidate_id, company_id = j.company_id,
           start_date = COALESCE(p.start_date, p.hire_date), source = 'platform'
       FROM application a JOIN job_posting j ON j.id = a.job_id
       WHERE a.id = p.application_id AND p.candidate_id IS NULL""",
    """UPDATE placement p
       SET institution_id = COALESCE(c.institution_id,
                                     (SELECT i.id FROM educational_institution i WHERE i.id = :por_defecto))
       FROM candidate_profile c
       WHERE c.id = p.candidate_id AND p.institution_id IS NULL""",
    "ALTER TABLE placement DROP CONSTRAINT IF EXISTS ck_placement_status",
    "UPDATE placement SET status = 'confirmed' WHERE status IN ('active', 'completed')",
    "ALTER TABLE placement ALTER COLUMN status SET DEFAULT 'confirmed'",
    "ALTER TABLE placement ADD CONSTRAINT ck_placement_status "
    "CHECK (status IN ('suggested', 'confirmed', 'cancelled'))",
    "ALTER TABLE placement ADD CONSTRAINT ck_placement_source CHECK (source IN ('platform', 'manual'))",
    "ALTER TABLE placement ADD CONSTRAINT ck_placement_company "
    "CHECK (company_id IS NOT NULL OR company_name IS NOT NULL) NOT VALID",
    "ALTER TABLE placement ADD CONSTRAINT ck_placement_salary "
    "CHECK (salary_amount IS NULL OR salary_amount >= 0) NOT VALID",
    "CREATE INDEX IF NOT EXISTS ix_placement_candidate ON placement (candidate_id)",
    "CREATE INDEX IF NOT EXISTS ix_placement_institution ON placement (institution_id)",
)


def _adaptar_colocaciones(conn: Connection, cambios: list[str]) -> None:
    """Lleva placement del diseño V3 al de la HU-29. En una base nueva la crea create_all ya completa.

    Va en su savepoint: si algo falla, el resto del esquema sigue y el módulo queda como estaba.
    """
    if conn.execute(text("SELECT to_regclass('public.placement')")).scalar() is None:
        return
    adaptada = conn.execute(
        text("SELECT 1 FROM information_schema.columns WHERE table_name = 'placement' AND column_name = 'source'")
    ).first()
    if adaptada is not None:
        return
    try:
        with conn.begin_nested():
            for sentencia in _COLOCACIONES:
                conn.execute(text(sentencia), {"por_defecto": INSTITUCION_POR_DEFECTO_ID})
        cambios.append("placement (diseño de la HU-29)")
    except Exception:  # noqa: BLE001 - sin la adaptación solo falla el módulo de colocaciones
        logger.exception("No se pudo adaptar la tabla placement a la HU-29")


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
