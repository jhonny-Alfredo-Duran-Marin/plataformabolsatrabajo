"""HU-29: registro de colocaciones (contrataciones de egresados) de cada universidad."""

import math
import uuid
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException, ConflictException, ResourceNotFoundException
from app.core.tenancy import institucion_efectiva
from app.features.bitacora.service import BitacoraService
from app.features.colocaciones.repository import ColocacionRepository
from app.features.colocaciones.schema import (
    ColocacionCreateRequest,
    ColocacionDeleteRequest,
    ColocacionesResponse,
    ColocacionItem,
    ColocacionUpdateRequest,
    EgresadoOpcion,
    EmpresaOpcion,
)
from app.features.notificaciones.emisor import emitir_notificacion
from app.models.candidato import CandidateProfile
from app.models.colocacion import Placement
from app.models.empresa import Company
from app.models.postulacion import Application
from app.security.tenant import AlcanceStaff
from app.shared.exportacion import ZONA_BOLIVIA

TIPO_AVISO = "colocacion_sugerida"
_LIMITE_OPCIONES = 20


def _nombre_empresa(empresa: Company) -> str:
    return empresa.trade_name or empresa.legal_name


class ColocacionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ColocacionRepository(db)
        self.bitacora = BitacoraService(db)

    # ─── Consulta ────────────────────────────────────────────────────────

    def listar(
        self,
        alcance: AlcanceStaff,
        page: int,
        page_size: int,
        estado: str | None = None,
        texto: str | None = None,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> ColocacionesResponse:
        filas, total = self.repo.listar(
            alcance.institution_id, page, page_size, estado, (texto or "").strip() or None, desde, hasta
        )
        return ColocacionesResponse(
            items=[self._item(f) for f in filas],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=max(1, math.ceil(total / page_size)),
            sugeridas=self.repo.contar_sugeridas(alcance.institution_id),
        )

    def egresados(self, alcance: AlcanceStaff, texto: str | None) -> list[EgresadoOpcion]:
        filas = self.repo.buscar_egresados(alcance.institution_id, (texto or "").strip() or None, _LIMITE_OPCIONES)
        return [EgresadoOpcion(id=i, nombre=nombre, correo=correo, universidad=uni) for i, nombre, correo, uni in filas]

    def empresas(self, texto: str | None) -> list[EmpresaOpcion]:
        empresas = self.repo.buscar_empresas((texto or "").strip() or None, _LIMITE_OPCIONES)
        return [EmpresaOpcion(id=e.id, nombre=_nombre_empresa(e)) for e in empresas]

    # ─── Alta, edición, confirmación y baja ──────────────────────────────

    def crear(self, data: ColocacionCreateRequest, alcance: AlcanceStaff, ip: str | None = None) -> ColocacionItem:
        candidato = self.db.get(CandidateProfile, data.egresado_id)
        # Un egresado de otra universidad se trata como inexistente.
        if candidato is None or (
            alcance.institution_id is not None and institucion_efectiva(candidato.institution_id) != alcance.institution_id
        ):
            raise ResourceNotFoundException("El egresado no existe.")
        empresa_id, empresa_nombre = self._empresa(data.empresa_id, data.empresa_nombre)
        if self.repo.existe_igual(candidato.id, data.cargo, data.fecha_inicio, empresa_id, empresa_nombre):
            raise ConflictException("Ya hay una colocación igual (mismo egresado, empresa, cargo y fecha de inicio).")

        colocacion = Placement(
            candidate_id=candidato.id,
            institution_id=institucion_efectiva(candidato.institution_id),
            company_id=empresa_id,
            company_name=empresa_nombre,
            position_title=data.cargo,
            start_date=data.fecha_inicio,
            salary=data.salario,
            currency=data.moneda,
            status="confirmed",
            source="manual",
            created_by=alcance.usuario.id_usuario,
        )
        self.db.add(colocacion)
        self.db.flush()
        self.bitacora.registrar(
            modulo="colocaciones",
            accion="registrar_colocacion",
            usuario_id=alcance.usuario.id_usuario,
            ip=ip,
            detalles=f"colocacion_id={colocacion.id} egresado_id={candidato.id} cargo={colocacion.position_title}",
        )
        self.db.commit()
        return self._item(self.repo.obtener(colocacion.id))

    def editar(
        self, colocacion_id: uuid.UUID, data: ColocacionUpdateRequest, alcance: AlcanceStaff, ip: str | None = None
    ) -> ColocacionItem:
        colocacion = self._obtener_de_staff(colocacion_id, alcance)
        if colocacion.status == "cancelled":
            raise ConflictException("La colocación está eliminada y no se puede editar.")
        enviados = data.model_fields_set
        cambios: list[str] = []

        if "empresa_id" in enviados or "empresa_nombre" in enviados:
            empresa_id, empresa_nombre = self._empresa(data.empresa_id, data.empresa_nombre)
            if (empresa_id, empresa_nombre) != (colocacion.company_id, colocacion.company_name):
                colocacion.company_id, colocacion.company_name = empresa_id, empresa_nombre
                cambios.append("empresa")
        if data.cargo is not None and data.cargo != colocacion.position_title:
            colocacion.position_title = data.cargo
            cambios.append("cargo")
        if data.fecha_inicio is not None and data.fecha_inicio != colocacion.start_date:
            colocacion.start_date = data.fecha_inicio
            cambios.append("fecha_inicio")
        if "salario" in enviados and data.salario != colocacion.salary:
            colocacion.salary = data.salario
            cambios.append("salario")
        if "moneda" in enviados and data.moneda != colocacion.currency:
            colocacion.currency = data.moneda
            cambios.append("moneda")

        if not cambios:
            raise BusinessException("No cambiaste ningún dato de la colocación.")
        if colocacion.salary is not None and not colocacion.currency:
            raise BusinessException("Si indicás el salario, indicá también la moneda.")

        colocacion.updated_reason = data.motivo
        self.bitacora.registrar(
            modulo="colocaciones",
            accion="editar_colocacion",
            usuario_id=alcance.usuario.id_usuario,
            ip=ip,
            detalles=f"colocacion_id={colocacion.id} cambios={','.join(cambios)} motivo={data.motivo}",
        )
        self.db.commit()
        return self._item(self.repo.obtener(colocacion.id))

    def confirmar(self, colocacion_id: uuid.UUID, alcance: AlcanceStaff, ip: str | None = None) -> ColocacionItem:
        colocacion = self._obtener_de_staff(colocacion_id, alcance)
        if colocacion.status == "cancelled":
            raise ConflictException("La colocación está eliminada y no se puede confirmar.")
        if colocacion.status == "confirmed":
            raise ConflictException("La colocación ya estaba confirmada.")
        colocacion.status = "confirmed"
        self.bitacora.registrar(
            modulo="colocaciones",
            accion="confirmar_colocacion",
            usuario_id=alcance.usuario.id_usuario,
            ip=ip,
            detalles=f"colocacion_id={colocacion.id} egresado_id={colocacion.candidate_id}",
        )
        self.db.commit()
        return self._item(self.repo.obtener(colocacion.id))

    def eliminar(
        self, colocacion_id: uuid.UUID, data: ColocacionDeleteRequest, alcance: AlcanceStaff, ip: str | None = None
    ) -> ColocacionItem:
        """Baja lógica: la fila se conserva con su motivo y deja de contar para los indicadores."""
        colocacion = self._obtener_de_staff(colocacion_id, alcance)
        if colocacion.status == "cancelled":
            raise ConflictException("La colocación ya estaba eliminada.")
        colocacion.status = "cancelled"
        colocacion.deleted_at = datetime.now(timezone.utc)
        colocacion.deleted_reason = data.motivo
        self.bitacora.registrar(
            modulo="colocaciones",
            accion="eliminar_colocacion",
            usuario_id=alcance.usuario.id_usuario,
            ip=ip,
            detalles=f"colocacion_id={colocacion.id} egresado_id={colocacion.candidate_id} motivo={data.motivo}",
        )
        self.db.commit()
        return self._item(self.repo.obtener(colocacion.id))

    # ─── Sugerencia automática (CP02) ────────────────────────────────────

    def sugerir_desde_postulacion(self, postulacion: Application, user_id: uuid.UUID | None) -> Placement | None:
        """Crea la colocación «sugerida» de una postulación que pasó a Contratado y avisa a los admins.

        Idempotente: si la postulación ya tiene colocación (sugerida, confirmada o eliminada) no hace nada.
        No hace commit: queda en la transacción de quien llama.
        """
        candidato = postulacion.candidate
        vacante = postulacion.job_posting
        if candidato is None or vacante is None or self.repo.por_postulacion(postulacion.id) is not None:
            return None
        universidad = institucion_efectiva(candidato.institution_id)
        colocacion = Placement(
            application_id=postulacion.id,
            candidate_id=candidato.id,
            institution_id=universidad,
            company_id=vacante.company_id,
            position_title=vacante.title[:200],
            # Fecha provisoria: el administrador la corrige con la real al confirmar.
            start_date=datetime.now(ZONA_BOLIVIA).date(),
            status="suggested",
            source="platform",
            created_by=user_id,
        )
        self.db.add(colocacion)
        self.db.flush()
        self.bitacora.registrar(
            modulo="colocaciones",
            accion="sugerir_colocacion",
            usuario_id=user_id,
            detalles=f"colocacion_id={colocacion.id} postulacion_id={postulacion.id} egresado_id={candidato.id}",
        )
        nombre = f"{candidato.first_name} {candidato.last_name}".strip()
        for admin_id in self.repo.admins_de_institucion(universidad):
            emitir_notificacion(
                self.db,
                admin_id,
                TIPO_AVISO,
                "Colocación por confirmar",
                f"{nombre} figura como contratado/a para «{colocacion.position_title}». Revisá y confirmá la colocación.",
                "/admin/colocaciones",
            )
        return colocacion

    # ─── Internos ────────────────────────────────────────────────────────

    def _empresa(self, empresa_id: uuid.UUID | None, nombre: str | None) -> tuple[uuid.UUID | None, str | None]:
        """Empresa registrada o, si no lo está, el nombre escrito a mano (nunca las dos)."""
        if empresa_id is not None:
            if self.db.get(Company, empresa_id) is None:
                raise ResourceNotFoundException("La empresa elegida no existe.")
            return empresa_id, None
        nombre = (nombre or "").strip()
        if not nombre:
            raise BusinessException("Elegí la empresa o escribí su nombre.")
        return None, nombre

    def _obtener_de_staff(self, colocacion_id: uuid.UUID, alcance: AlcanceStaff) -> Placement:
        colocacion = self.repo.obtener(colocacion_id)
        # Una colocación de otra universidad se trata como inexistente.
        if colocacion is None or (
            alcance.institution_id is not None and colocacion.institution_id != alcance.institution_id
        ):
            raise ResourceNotFoundException("La colocación no existe.")
        return colocacion

    def _item(self, c: Placement) -> ColocacionItem:
        candidato = c.candidate
        return ColocacionItem(
            id=c.id,
            egresado_id=c.candidate_id,
            egresado=f"{candidato.first_name} {candidato.last_name}".strip(),
            universidad_id=c.institution_id,
            universidad=c.institution.name if c.institution else None,
            empresa_id=c.company_id,
            empresa=_nombre_empresa(c.company) if c.company else (c.company_name or ""),
            cargo=c.position_title,
            fecha_inicio=c.start_date,
            salario=c.salary,
            moneda=c.currency,
            estado=c.status,
            origen=c.source,
            postulacion_id=c.application_id,
            motivo_ultimo_cambio=c.updated_reason,
            eliminada_el=c.deleted_at,
            motivo_eliminacion=c.deleted_reason,
            registrada_el=c.created_at,
            actualizada_el=c.updated_at,
        )
