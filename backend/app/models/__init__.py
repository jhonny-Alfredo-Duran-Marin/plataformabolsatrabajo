"""Importa todas las entidades para que Alembic (autogenerate) detecte el metadata completo."""

from app.models.auditoria import AuditoriaLog
from app.models.catalogo import CategoriaOferta, Carrera, Ciudad, Habilidad
from app.models.comunicacion import Entrevista, Mensaje
from app.models.egresado import (
    CertificacionEgresado,
    ExperienciaLaboral,
    FormacionAdicional,
    HabilidadEgresado,
    IdiomaEgresado,
    PerfilEgresado,
)
from app.models.empresa import Empresa
from app.models.moderacion import Denuncia
from app.models.notificacion import Notificacion
from app.models.oferta import Oferta, PreguntaFiltro
from app.models.postulacion import EtapaSeleccion, Postulacion, PostulacionEtapa, RespuestaFiltro
from app.models.reporte import Colocacion, EncuestaSituacionLaboral, ReporteInstitucional
from app.models.usuario import Usuario

__all__ = [
    "AuditoriaLog",
    "CategoriaOferta",
    "Carrera",
    "Ciudad",
    "Habilidad",
    "Entrevista",
    "Mensaje",
    "CertificacionEgresado",
    "ExperienciaLaboral",
    "FormacionAdicional",
    "HabilidadEgresado",
    "IdiomaEgresado",
    "PerfilEgresado",
    "Empresa",
    "Denuncia",
    "Notificacion",
    "Oferta",
    "PreguntaFiltro",
    "EtapaSeleccion",
    "Postulacion",
    "PostulacionEtapa",
    "RespuestaFiltro",
    "Colocacion",
    "EncuestaSituacionLaboral",
    "ReporteInstitucional",
    "Usuario",
]
