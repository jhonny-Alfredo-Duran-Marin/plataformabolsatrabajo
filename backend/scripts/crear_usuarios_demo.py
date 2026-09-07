"""Crea o restablece los usuarios de prueba, empresas y catálogos para pruebas.

Uso (desde la carpeta backend):
    python -m scripts.crear_usuarios_demo

Contraseñas:
    admin@uagrm.bo          -> Admin1234!
    moderador@uagrm.bo      -> Moderador1234!
    resto de usuarios demo  -> Demo1234!
"""

import uuid

from app.core.database import Base, SessionLocal, engine
import app.models  # noqa: F401 - Registra todos los modelos ORM en Base.metadata
from app.models.catalogo import JobCategory, Skill
from app.models.empresa import Company, CompanyMember
from app.models.usuario import AppUser, Role, UserRole
from app.security.password_hasher import hash_password

ROLES_FIJOS = {
    "candidate": uuid.UUID("10000000-0000-0000-0000-000000000001"),
    "moderator": uuid.UUID("10000000-0000-0000-0000-000000000002"),
    "platform_admin": uuid.UUID("10000000-0000-0000-0000-000000000003"),
    "empresa": uuid.UUID("10000000-0000-0000-0000-000000000004"),
}

USUARIOS = [
    ("admin@uagrm.bo", "Admin1234!", "platform_admin"),
    ("moderador@uagrm.bo", "Moderador1234!", "moderator"),
    ("maria.fernandez@example.bo", "Demo1234!", "candidate"),
    ("carlos.mamani@example.bo", "Demo1234!", "candidate"),
    ("lucia.rojas@example.bo", "Demo1234!", "candidate"),
    ("diego.suarez@example.bo", "Demo1234!", "candidate"),
    ("rrhh@tecnova.bo", "Demo1234!", "empresa"),
    ("talento@finandina.bo", "Demo1234!", "empresa"),
]


def ejecutar() -> None:
    print("[1/5] Creando tablas en la base de datos si no existen...")
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        print("[2/5] Verificando catalogo de roles...")
        for rol_nombre, rol_id in ROLES_FIJOS.items():
            rol = db.query(Role).filter(Role.name == rol_nombre).one_or_none()
            if rol is None:
                db.add(Role(id=rol_id, name=rol_nombre))
        db.commit()

        print("[3/5] Creando / actualizando usuarios de prueba...")
        usuarios_guardados = {}
        for correo, password, rol in USUARIOS:
            usuario = db.query(AppUser).filter(AppUser.email == correo).one_or_none()
            if usuario is None:
                usuario = AppUser(email=correo)
                db.add(usuario)
                print(f"  [+] Creado: {correo}")
            else:
                print(f"  [*] Actualizado: {correo}")
            usuario.password_hash = hash_password(password)
            usuario.account_status = "active"
            usuario.deleted_at = None
            db.flush()
            usuarios_guardados[correo] = usuario

            if rol is not None:
                role_id = ROLES_FIJOS[rol]
                existe = (
                    db.query(UserRole)
                    .filter(UserRole.user_id == usuario.id, UserRole.role_id == role_id)
                    .one_or_none()
                )
                if existe is None:
                    db.add(UserRole(user_id=usuario.id, role_id=role_id))
        db.commit()

        print("[4/5] Creando / verificando empresas demo y miembros...")
        tecnova = db.query(Company).filter(Company.tax_id == "1029384756").one_or_none()
        if not tecnova:
            tecnova = Company(
                id=uuid.uuid4(),
                legal_name="Tecnova Soluciones Tecnologicas S.R.L.",
                trade_name="Tecnova Solutions",
                tax_id="1029384756",
                verification_status="verified",
                account_status="active",
                city="Santa Cruz de la Sierra",
                country_code="BO",
                contact_email="rrhh@tecnova.bo",
                description="Empresa lider en desarrollo de software e innovacion tecnologica en Bolivia.",
            )
            db.add(tecnova)
            db.flush()
            print("  [+] Empresa creada: Tecnova Solutions")
        else:
            tecnova.verification_status = "verified"
            tecnova.account_status = "active"

        user_tecnova = usuarios_guardados.get("rrhh@tecnova.bo")
        if user_tecnova:
            mem = db.query(CompanyMember).filter(CompanyMember.user_id == user_tecnova.id).one_or_none()
            if not mem:
                db.add(
                    CompanyMember(
                        user_id=user_tecnova.id,
                        company_id=tecnova.id,
                        member_type="owner",
                        job_title="Gerente de Talento Humano",
                        is_active=True,
                    )
                )
                print("  [+] Miembro vinculado: rrhh@tecnova.bo -> Tecnova Solutions")

        finandina = db.query(Company).filter(Company.tax_id == "5948372610").one_or_none()
        if not finandina:
            finandina = Company(
                id=uuid.uuid4(),
                legal_name="Banco Finandina S.A.",
                trade_name="Finandina",
                tax_id="5948372610",
                verification_status="verified",
                account_status="active",
                city="La Paz",
                country_code="BO",
                contact_email="talento@finandina.bo",
                description="Entidad financiera comprometida con el desarrollo economico y la inclusion digital.",
            )
            db.add(finandina)
            db.flush()
            print("  [+] Empresa creada: Finandina")
        else:
            finandina.verification_status = "verified"
            finandina.account_status = "active"

        user_finandina = usuarios_guardados.get("talento@finandina.bo")
        if user_finandina:
            mem2 = db.query(CompanyMember).filter(CompanyMember.user_id == user_finandina.id).one_or_none()
            if not mem2:
                db.add(
                    CompanyMember(
                        user_id=user_finandina.id,
                        company_id=finandina.id,
                        member_type="owner",
                        job_title="Reclutador Senior",
                        is_active=True,
                    )
                )
                print("  [+] Miembro vinculado: talento@finandina.bo -> Finandina")
        db.commit()

        print("[5/5] Sembrando catalogos de categorias y habilidades...")
        categorias = [
            "Desarrollo de Software y Web",
            "Ciencia de Datos e Inteligencia Artificial",
            "Infraestructura, Cloud y DevOps",
            "Ciberseguridad y Redes",
            "Gestion de Proyectos TI y Producto",
            "Diseno UI/UX y Multimedia",
            "Soporte Tecnico y Telecomunicaciones",
            "Base de Datos y BI",
        ]
        for c_nombre in categorias:
            if not db.query(JobCategory).filter(JobCategory.name == c_nombre).one_or_none():
                db.add(JobCategory(name=c_nombre, is_active=True))

        skills = [
            ("Python", "backend"),
            ("TypeScript", "frontend"),
            ("Angular", "frontend"),
            ("FastAPI", "backend"),
            ("PostgreSQL", "database"),
            ("Docker", "devops"),
            ("Git & GitHub", "tools"),
            ("React", "frontend"),
            ("Node.js", "backend"),
            ("Java / Spring Boot", "backend"),
            ("SQL / Modelado de Datos", "database"),
            ("Linux / Bash", "devops"),
            ("AWS / Cloud", "cloud"),
            ("Trabajo en Equipo", "soft"),
            ("Comunicacion Asertiva", "soft"),
            ("Resolucion de Problemas", "soft"),
            ("Ingles Tecnico", "language"),
        ]
        for s_name, s_cat in skills:
            if not db.query(Skill).filter(Skill.name == s_name).one_or_none():
                db.add(Skill(name=s_name, category=s_cat, is_active=True))

        db.commit()
        print("\n Listo! Base de datos inicializada, empresas vinculadas y catalogos sembrados.")


if __name__ == "__main__":
    ejecutar()
