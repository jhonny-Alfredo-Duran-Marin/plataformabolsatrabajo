import enum


class RolNombre(str, enum.Enum):
    """Los cuatro perfiles del sistema (módulo 5.1.1 del perfil de proyecto)."""

    EGRESADO = "EGRESADO"
    ESTUDIANTE = "ESTUDIANTE"
    EMPRESA = "EMPRESA"
    ADMINISTRADOR = "ADMINISTRADOR"


class EstadoValidacionEgresado(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"


class EstadoVerificacionEmpresa(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    VERIFICADA = "VERIFICADA"
    RECHAZADA = "RECHAZADA"
    SUSPENDIDA = "SUSPENDIDA"


class EstadoOferta(str, enum.Enum):
    EN_REVISION = "EN_REVISION"
    ACTIVA = "ACTIVA"
    PAUSADA = "PAUSADA"
    CERRADA = "CERRADA"
    RECHAZADA = "RECHAZADA"


class ModalidadTrabajo(str, enum.Enum):
    PRESENCIAL = "PRESENCIAL"
    REMOTO = "REMOTO"
    HIBRIDO = "HIBRIDO"


class TipoContrato(str, enum.Enum):
    INDEFINIDO = "INDEFINIDO"
    TEMPORAL = "TEMPORAL"
    POR_PROYECTO = "POR_PROYECTO"
    PASANTIA = "PASANTIA"


class NivelExperiencia(str, enum.Enum):
    JUNIOR = "JUNIOR"
    SEMI_SENIOR = "SEMI_SENIOR"
    SENIOR = "SENIOR"
    JEFE = "JEFE"
    GERENTE = "GERENTE"


class EstadoPostulacion(str, enum.Enum):
    POSTULADO = "POSTULADO"
    EN_REVISION = "EN_REVISION"
    PRESELECCIONADO = "PRESELECCIONADO"
    ENTREVISTA = "ENTREVISTA"
    PRUEBAS = "PRUEBAS"
    OFERTA = "OFERTA"
    CONTRATADO = "CONTRATADO"
    RECHAZADO = "RECHAZADO"


class TipoNotificacion(str, enum.Enum):
    NUEVA_OFERTA_AFIN = "NUEVA_OFERTA_AFIN"
    CAMBIO_ESTADO_POSTULACION = "CAMBIO_ESTADO_POSTULACION"
    MENSAJE = "MENSAJE"
    ALERTA_OFERTA_SOSPECHOSA = "ALERTA_OFERTA_SOSPECHOSA"
    RECORDATORIO = "RECORDATORIO"


class EstadoDenuncia(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    EN_REVISION = "EN_REVISION"
    RESUELTA = "RESUELTA"
    DESESTIMADA = "DESESTIMADA"
