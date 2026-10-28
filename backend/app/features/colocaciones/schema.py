import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

EstadoColocacion = Literal["suggested", "confirmed", "cancelled"]
OrigenColocacion = Literal["platform", "manual"]


def _limpiar(valor: str | None) -> str | None:
    valor = (valor or "").strip()
    return valor or None


class _DatosColocacion(BaseModel):
    @field_validator("moneda", check_fields=False)
    @classmethod
    def _moneda(cls, valor: str | None) -> str | None:
        valor = _limpiar(valor)
        if valor is None:
            return None
        if len(valor) != 3 or not valor.isalpha():
            raise ValueError("La moneda es un código de 3 letras, por ejemplo BOB o USD.")
        return valor.upper()

    @field_validator("empresa_nombre", "cargo", check_fields=False)
    @classmethod
    def _recortar(cls, valor: str | None) -> str | None:
        return _limpiar(valor)


class ColocacionCreateRequest(_DatosColocacion):
    egresado_id: uuid.UUID
    # Una empresa registrada o, si no lo está, su nombre escrito a mano.
    empresa_id: uuid.UUID | None = None
    empresa_nombre: str | None = Field(default=None, max_length=250)
    cargo: str = Field(min_length=2, max_length=200)
    fecha_inicio: date
    salario: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    moneda: str | None = Field(default=None, max_length=3)

    @model_validator(mode="after")
    def _empresa(self):
        if self.empresa_id is None and not self.empresa_nombre:
            raise ValueError("Elegí la empresa o escribí su nombre.")
        if self.salario is not None and not self.moneda:
            raise ValueError("Si indicás el salario, indicá también la moneda.")
        return self


class ColocacionUpdateRequest(_DatosColocacion):
    """Solo se cambian los campos enviados. El egresado no se cambia: se elimina y se registra de nuevo."""

    empresa_id: uuid.UUID | None = None
    empresa_nombre: str | None = Field(default=None, max_length=250)
    cargo: str | None = Field(default=None, min_length=2, max_length=200)
    fecha_inicio: date | None = None
    salario: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    moneda: str | None = Field(default=None, max_length=3)
    motivo: str = Field(min_length=3, max_length=1000)

    @field_validator("motivo")
    @classmethod
    def _motivo(cls, valor: str) -> str:
        valor = valor.strip()
        if len(valor) < 3:
            raise ValueError("Indicá el motivo del cambio.")
        return valor


class ColocacionDeleteRequest(BaseModel):
    motivo: str = Field(min_length=3, max_length=1000)

    @field_validator("motivo")
    @classmethod
    def _motivo(cls, valor: str) -> str:
        valor = valor.strip()
        if len(valor) < 3:
            raise ValueError("Indicá el motivo de la eliminación.")
        return valor


class ColocacionItem(BaseModel):
    id: uuid.UUID
    egresado_id: uuid.UUID
    egresado: str
    universidad_id: uuid.UUID
    universidad: str | None
    empresa_id: uuid.UUID | None
    empresa: str
    cargo: str
    fecha_inicio: date
    salario: Decimal | None
    moneda: str | None
    estado: EstadoColocacion
    origen: OrigenColocacion
    postulacion_id: uuid.UUID | None
    motivo_ultimo_cambio: str | None
    eliminada_el: datetime | None
    motivo_eliminacion: str | None
    registrada_el: datetime
    actualizada_el: datetime


class ColocacionesResponse(BaseModel):
    items: list[ColocacionItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    # Sugeridas por la plataforma que esperan confirmación (en todo el alcance, sin los filtros).
    sugeridas: int


class EgresadoOpcion(BaseModel):
    id: uuid.UUID
    nombre: str
    correo: str | None
    universidad: str | None


class EmpresaOpcion(BaseModel):
    id: uuid.UUID
    nombre: str
