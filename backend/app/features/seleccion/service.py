import uuid
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException, ResourceNotFoundException
from app.features.seleccion.repository import SeleccionRepository
from app.features.seleccion.schema import (
    CandidatoEnTableroDTO,
    ColumnaEtapaTableroDTO,
    ConfigurarEtapasRequest,
    DescartarCandidatoRequest,
    EtapaResponse,
    HistorialEtapaItemResponse,
    HistorialPostulacionResponse,
    MoverCandidatoRequest,
    NotaInternaCreateRequest,
    NotaInternaResponse,
    TableroSeleccionResponse,
)
from app.models.oferta import JobPosting


class SeleccionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = SeleccionRepository(db)

    def obtener_tablero(self, vacante_id: uuid.UUID) -> TableroSeleccionResponse:
        """Obtiene el tablero Kanban con todas las etapas y postulantes agrupados."""
        vacante = self.db.query(JobPosting).filter(JobPosting.id == vacante_id).one_or_none()
        if not vacante:
            raise ResourceNotFoundException("La vacante solicitada no existe.")

        etapas = self.repo.obtener_etapas_vacante(vacante_id)
        if not etapas:
            etapas = self.repo.inicializar_etapas_por_defecto(vacante_id)

        postulaciones = self.repo.obtener_postulaciones_vacante(vacante_id)

        # Mapear postulaciones a DTO
        candidatos_por_etapa: dict[uuid.UUID, list[CandidatoEnTableroDTO]] = {e.id: [] for e in etapas}
        candidatos_descartados: list[CandidatoEnTableroDTO] = []

        primera_etapa_id = etapas[0].id if etapas else None

        for app in postulaciones:
            cand = app.candidate
            user = cand.user if cand and hasattr(cand, "user") else None
            dto = CandidatoEnTableroDTO(
                application_id=app.id,
                candidate_id=app.candidate_id,
                user_id=cand.user_id if cand else None,
                first_name=cand.first_name if cand else "Candidato",
                last_name=cand.last_name if cand else "",
                phone=cand.phone if cand else None,
                city=cand.city if cand else None,
                professional_headline=cand.professional_headline if cand else None,
                current_stage_id=app.current_stage_id,
                current_status=app.current_status,
                applied_at=app.applied_at,
                notas_count=len(app.notes),
                cover_letter=app.cover_letter,
            )

            if app.current_status == "rejected":
                candidatos_descartados.append(dto)
            else:
                stage_target_id = app.current_stage_id or primera_etapa_id
                if stage_target_id and stage_target_id in candidatos_por_etapa:
                    candidatos_por_etapa[stage_target_id].append(dto)
                elif primera_etapa_id:
                    candidatos_por_etapa[primera_etapa_id].append(dto)

        columnas: list[ColumnaEtapaTableroDTO] = []
        for e in etapas:
            columnas.append(
                ColumnaEtapaTableroDTO(
                    stage=EtapaResponse.model_validate(e),
                    candidatos=candidatos_por_etapa.get(e.id, []),
                )
            )

        empresa_nombre = (
            vacante.company.trade_name or vacante.company.legal_name
            if vacante.company
            else "Empresa"
        )

        return TableroSeleccionResponse(
            job_posting_id=vacante.id,
            job_title=vacante.title,
            company_id=vacante.company_id,
            company_name=empresa_nombre,
            total_candidatos=len(postulaciones),
            columnas=columnas,
            candidatos_descartados=candidatos_descartados,
        )

    def obtener_etapas(self, vacante_id: uuid.UUID) -> list[EtapaResponse]:
        """Obtiene la lista de etapas configuradas de una vacante."""
        etapas = self.repo.obtener_etapas_vacante(vacante_id)
        if not etapas:
            etapas = self.repo.inicializar_etapas_por_defecto(vacante_id)
        return [EtapaResponse.model_validate(e) for e in etapas]

    def configurar_etapas(
        self, vacante_id: uuid.UUID, req: ConfigurarEtapasRequest
    ) -> list[EtapaResponse]:
        """Actualiza o redefine las etapas del proceso para una vacante."""
        vacante = self.db.query(JobPosting).filter(JobPosting.id == vacante_id).one_or_none()
        if not vacante:
            raise ResourceNotFoundException("La vacante no existe.")

        etapas = self.repo.configurar_etapas_vacante(vacante_id, req.etapas)
        return [EtapaResponse.model_validate(e) for e in etapas]

    def mover_candidato(
        self,
        application_id: uuid.UUID,
        req: MoverCandidatoRequest,
        usuario_id: uuid.UUID | None,
    ) -> CandidatoEnTableroDTO:
        """Mueve un candidato a una nueva etapa respetando la regla de descarte."""
        application = self.repo.obtener_postulacion_por_id(application_id)
        if not application:
            raise ResourceNotFoundException("La postulación no existe.")

        # Regla de negocio HU-17: Un candidato descartado no puede volver a avanzar
        if application.current_status == "rejected":
            raise BusinessException(
                "Un candidato descartado no puede volver a avanzar en el mismo proceso de selección."
            )

        etapas_vacante = self.repo.obtener_etapas_vacante(application.job_id)
        nueva_etapa = next((e for e in etapas_vacante if e.id == req.nueva_etapa_id), None)
        if not nueva_etapa:
            raise ResourceNotFoundException("La etapa de destino no pertenece a esta vacante.")

        app_actualizada = self.repo.mover_candidato_etapa(
            application=application,
            nueva_etapa=nueva_etapa,
            usuario_id=usuario_id,
            observacion=req.observacion,
        )

        cand = app_actualizada.candidate
        return CandidatoEnTableroDTO(
            application_id=app_actualizada.id,
            candidate_id=app_actualizada.candidate_id,
            user_id=cand.user_id if cand else None,
            first_name=cand.first_name if cand else "Candidato",
            last_name=cand.last_name if cand else "",
            phone=cand.phone if cand else None,
            city=cand.city if cand else None,
            professional_headline=cand.professional_headline if cand else None,
            current_stage_id=app_actualizada.current_stage_id,
            current_status=app_actualizada.current_status,
            applied_at=app_actualizada.applied_at,
            notas_count=len(app_actualizada.notes),
            cover_letter=app_actualizada.cover_letter,
        )

    def descartar_candidato(
        self,
        application_id: uuid.UUID,
        req: DescartarCandidatoRequest,
        usuario_id: uuid.UUID | None,
    ) -> CandidatoEnTableroDTO:
        """Descarta a un candidato en el proceso de selección."""
        application = self.repo.obtener_postulacion_por_id(application_id)
        if not application:
            raise ResourceNotFoundException("La postulación no existe.")

        app_actualizada = self.repo.descartar_candidato(
            application=application,
            usuario_id=usuario_id,
            motivo=req.motivo,
        )

        cand = app_actualizada.candidate
        return CandidatoEnTableroDTO(
            application_id=app_actualizada.id,
            candidate_id=app_actualizada.candidate_id,
            user_id=cand.user_id if cand else None,
            first_name=cand.first_name if cand else "Candidato",
            last_name=cand.last_name if cand else "",
            phone=cand.phone if cand else None,
            city=cand.city if cand else None,
            professional_headline=cand.professional_headline if cand else None,
            current_stage_id=app_actualizada.current_stage_id,
            current_status=app_actualizada.current_status,
            applied_at=app_actualizada.applied_at,
            notas_count=len(app_actualizada.notes),
            cover_letter=app_actualizada.cover_letter,
        )

    def obtener_historial(self, application_id: uuid.UUID) -> HistorialPostulacionResponse:
        """Obtiene la auditoría completa de etapas de un candidato."""
        application = self.repo.obtener_postulacion_por_id(application_id)
        if not application:
            raise ResourceNotFoundException("La postulación no existe.")

        items: list[HistorialEtapaItemResponse] = []
        for h in application.stage_history:
            changed_by_name = (
                h.changed_by_user.email
                if h.changed_by_user
                else "Sistema"
            )
            items.append(
                HistorialEtapaItemResponse(
                    id=h.id,
                    stage_id=h.stage_id,
                    stage_name=h.stage.name if h.stage else "Etapa",
                    entered_at=h.entered_at,
                    left_at=h.left_at,
                    changed_by_id=h.changed_by,
                    changed_by_name=changed_by_name,
                    result=h.result,
                    notes=h.notes,
                )
            )

        return HistorialPostulacionResponse(
            application_id=application.id,
            current_status=application.current_status,
            historial=items,
        )

    def agregar_nota(
        self,
        application_id: uuid.UUID,
        req: NotaInternaCreateRequest,
        usuario_id: uuid.UUID,
    ) -> NotaInternaResponse:
        """Registra una nota interna confidencial."""
        application = self.repo.obtener_postulacion_por_id(application_id)
        if not application:
            raise ResourceNotFoundException("La postulación no existe.")

        nota = self.repo.agregar_nota_interna(application_id, usuario_id, req.content)
        author_name = nota.author.email if nota.author else "Reclutador"

        return NotaInternaResponse(
            id=nota.id,
            application_id=nota.application_id,
            author_id=nota.company_member_id,
            author_name=author_name,
            content=nota.content,
            created_at=nota.created_at,
        )

    def obtener_notas(self, application_id: uuid.UUID) -> list[NotaInternaResponse]:
        """Obtiene las notas internas de una postulación."""
        application = self.repo.obtener_postulacion_por_id(application_id)
        if not application:
            raise ResourceNotFoundException("La postulación no existe.")

        notas = self.repo.obtener_notas_postulacion(application_id)
        return [
            NotaInternaResponse(
                id=n.id,
                application_id=n.application_id,
                author_id=n.company_member_id,
                author_name=n.author.email if n.author else "Reclutador",
                content=n.content,
                created_at=n.created_at,
            )
            for n in notas
        ]

