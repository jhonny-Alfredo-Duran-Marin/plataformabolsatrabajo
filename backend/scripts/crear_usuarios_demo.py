"""Crea o restablece los usuarios de prueba para iniciar sesión contra el esquema nuevo.

Uso (desde la carpeta backend):
    python -m scripts.crear_usuarios_demo

Contraseñas:
    admin@uagrm.bo          -> Admin1234!
    moderador@uagrm.bo      -> Moderador1234!
    resto de usuarios demo  -> Demo1234!

Los usuarios ya existentes en seed.sql se actualizan (contraseña y estado activo);
si no existen, se crean junto con su rol.
"""

import uuid

from app.core.database import SessionLocal
from app.models.usuario import AppUser, Role, UserRole
from app.security.password_hasher import hash_password

ROLES_FIJOS = {
    "candidate": uuid.UUID("10000000-0000-0000-0000-000000000001"),
    "moderator": uuid.UUID("10000000-0000-0000-0000-000000000002"),
    "platform_admin": uuid.UUID("10000000-0000-0000-0000-000000000003"),
}

USUARIOS = [
    ("admin@uagrm.bo", "Admin1234!", "platform_admin"),
    ("moderador@uagrm.bo", "Moderador1234!", "moderator"),
    ("maria.fernandez@example.bo", "Demo1234!", "candidate"),
    ("carlos.mamani@example.bo", "Demo1234!", "candidate"),
    ("lucia.rojas@example.bo", "Demo1234!", "candidate"),
    ("diego.suarez@example.bo", "Demo1234!", "candidate"),
    ("rrhh@tecnova.bo", "Demo1234!", None),  # miembro de empresa: rol sintético 'empresa'
    ("talento@finandina.bo", "Demo1234!", None),
]


def ejecutar() -> None:
    with SessionLocal() as db:
        for correo, password, rol in USUARIOS:
            usuario = db.query(AppUser).filter(AppUser.email == correo).one_or_none()
            if usuario is None:
                usuario = AppUser(email=correo)
                db.add(usuario)
                print(f"[crear ] {correo}")
            else:
                print(f"[update] {correo}")
            usuario.password_hash = hash_password(password)
            usuario.account_status = "active"
            usuario.deleted_at = None
            db.flush()
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
        print("Listo. Ya puedes iniciar sesión desde el frontend.")


if __name__ == "__main__":
    ejecutar()
