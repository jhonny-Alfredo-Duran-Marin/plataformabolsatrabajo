"""IA generativa con Gemini: el cliente (cascada de modelos, errores y formato) y los reportes
pedidos en lenguaje natural, escritos o dictados.

Gemini nunca se llama de verdad: se reemplaza httpx.post o ia_generativa.generar_json.
"""

import json
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

from app.common.exceptions import BusinessException, ServiceUnavailableException
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.tenancy import INSTITUCION_POR_DEFECTO_ID
from app.features.reportes.catalogo import Contexto
from app.features.reportes.interprete import InterpreteReportes
from app.features.reportes.service import ReporteService
from app.main import app
from app.models.institucion import Institution
from app.security.jwt_provider import create_access_token
from app.shared import ia_generativa

_UNIVERSIDAD = Contexto(rol="staff", institution_id=INSTITUCION_POR_DEFECTO_ID)
_SUPERADMIN = Contexto(rol="staff")


@pytest.fixture
def db():
    sesion = SessionLocal()
    try:
        yield sesion
    finally:
        sesion.close()


@pytest.fixture
def con_claves(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "gemini_api_key_asistente", "clave-prueba")
    monkeypatch.setattr(s, "gemini_api_key_reportes", "clave-prueba")
    monkeypatch.setattr(s, "gemini_modelos", ["modelo-a", "modelo-b"])


def _respuesta_gemini(datos) -> httpx.Response:
    texto = datos if isinstance(datos, str) else json.dumps(datos)
    return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": texto}]}}]})


def _gemini_de_reportes(monkeypatch, datos, capturado: dict | None = None):
    monkeypatch.setattr(get_settings(), "gemini_api_key_reportes", "clave-prueba")

    def falso(uso, instrucciones, mensajes, esquema, temperatura=0.4):
        if capturado is not None:
            capturado.update(uso=uso, instrucciones=instrucciones, mensajes=mensajes, esquema=esquema)
        return datos, "modelo-prueba"

    monkeypatch.setattr(ia_generativa, "generar_json", falso)


def _pedido(**cambios) -> dict:
    datos = {
        "entendido": True,
        "fuente": "postulaciones",
        "columnas": [],
        "filtros": [],
        "orden": [],
        "titulo": "",
        "formato": "ninguno",
        "explicacion": "",
    }
    datos.update(cambios)
    return datos


# ─── Cliente de Gemini ───────────────────────────────────────────────────────


def test_sin_clave_no_se_llama_a_gemini(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: pytest.fail("No debía llamar a Gemini."))
    assert not ia_generativa.disponible("reportes")
    with pytest.raises(ia_generativa.IAGenerativaNoDisponible):
        ia_generativa.generar_json("reportes", "x", [("user", "hola")], {"type": "object"})


def test_si_un_modelo_se_queda_sin_cupo_responde_el_siguiente(con_claves, monkeypatch):
    llamados = []

    def post(url, **kwargs):
        llamados.append(url)
        assert kwargs["headers"]["x-goog-api-key"] == "clave-prueba"
        if "modelo-a" in url:
            return httpx.Response(429, json={"error": {"code": 429, "message": "cupo diario agotado"}})
        return _respuesta_gemini({"ok": True})

    monkeypatch.setattr(httpx, "post", post)
    datos, modelo = ia_generativa.generar_json("asistente", "x", [("user", "hola")], {"type": "object"})
    assert datos == {"ok": True}
    assert modelo == "modelo-b"
    assert len(llamados) == 2


def test_un_modelo_sobrecargado_se_reintenta_una_vez(con_claves, monkeypatch):
    respuestas = iter([httpx.Response(503), _respuesta_gemini({"ok": True})])
    monkeypatch.setattr(httpx, "post", lambda url, **k: next(respuestas))
    assert ia_generativa.generar_json("asistente", "x", [("user", "hola")], {"type": "object"}) == ({"ok": True}, "modelo-a")


def test_un_error_de_clave_no_prueba_otros_modelos(con_claves, monkeypatch):
    llamados = []
    monkeypatch.setattr(
        httpx, "post", lambda url, **k: llamados.append(url) or httpx.Response(400, json={"error": {"code": 400}})
    )
    with pytest.raises(ia_generativa.IAGenerativaNoDisponible):
        ia_generativa.generar_json("asistente", "x", [("user", "hola")], {"type": "object"})
    assert len(llamados) == 1


def test_una_respuesta_que_no_es_json_no_se_usa(con_claves, monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda url, **k: _respuesta_gemini("esto no es JSON"))
    with pytest.raises(ia_generativa.IAGenerativaNoDisponible):
        ia_generativa.generar_json("asistente", "x", [("user", "hola")], {"type": "object"})


def test_el_texto_del_chat_queda_con_el_formato_que_muestran_la_web_y_la_app():
    crudo = "## Pasos\n- uno\n* dos con *cursiva* y **negrita**\n\n\n\nfin  "
    assert ia_generativa.texto_para_chat(crudo) == "Pasos\n• uno\n• dos con cursiva y **negrita**\n\nfin"


# ─── Reportes pedidos en lenguaje natural ────────────────────────────────────


def test_el_pedido_se_convierte_en_una_consulta_valida_del_catalogo(db, monkeypatch):
    capturado: dict = {}
    _gemini_de_reportes(
        monkeypatch,
        _pedido(
            columnas=["egresado", "carrera", "universidad", "inventada", "estado", "carrera"],
            filtros=[
                {"clave": "estado", "opciones": ["Contratado", "inexistente"]},
                {"clave": "postulado", "desde": "2026-12-31", "hasta": "2026-01-01"},
                {"clave": "carrera", "texto": "  Sistemas "},
                {"clave": "universidad", "opciones": ["UAGRM"]},
                {"clave": "ciudad", "texto": "La Paz"},
            ],
            orden=[{"columna": "postulado", "direccion": "desc"}, {"columna": "salario", "direccion": "asc"}],
            titulo="Colocados de Sistemas 2026",
            formato="excel",
            explicacion="Postulaciones contratadas de Sistemas en 2026.",
        ),
        capturado,
    )
    r = InterpreteReportes(db).interpretar(_UNIVERSIDAD, "colocados de sistemas del 2026 en excel")

    c = r.consulta
    assert c.fuente == "postulaciones"
    # La columna y el filtro de universidad son solo del superadmin; lo inventado se descarta.
    assert c.columnas == ["egresado", "carrera", "estado"]
    assert c.filtros == {
        "estado": ["hired"],
        "postulado": {"desde": "2026-01-01", "hasta": "2026-12-31"},
        "carrera": "Sistemas",
    }
    assert [(o.columna, o.direccion) for o in c.orden] == [("postulado", "desc")]
    assert (r.formato, r.motor, c.titulo) == ("excel", "modelo-prueba", "Colocados de Sistemas 2026")

    # El generador acepta la consulta tal cual.
    vista = ReporteService(db).vista_previa(_UNIVERSIDAD, c, 1, 5)
    assert "Estado: Contratado" in vista.descripcion[0]
    assert "Carrera: contiene «Sistemas»" in vista.descripcion[0]

    # A Gemini le llega el pedido y el catálogo, nada más.
    assert capturado["uso"] == "reportes"
    assert capturado["mensajes"] == [("user", "colocados de sistemas del 2026 en excel")]


def test_el_superadmin_puede_filtrar_las_postulaciones_por_universidad(db, monkeypatch):
    nombre = db.get(Institution, INSTITUCION_POR_DEFECTO_ID).name
    _gemini_de_reportes(
        monkeypatch,
        _pedido(
            columnas=["egresado", "universidad"],
            filtros=[{"clave": "universidad", "opciones": [nombre.upper()]}, {"clave": "estado", "opciones": ["hired"]}],
        ),
    )
    r = InterpreteReportes(db).interpretar(_SUPERADMIN, "colocados de la UAGRM")
    # Gemini puede devolver el nombre que se muestra: se traduce al valor del filtro.
    assert r.consulta.filtros["universidad"] == [str(INSTITUCION_POR_DEFECTO_ID)]
    assert r.consulta.columnas == ["egresado", "universidad"]
    vista = ReporteService(db).vista_previa(_SUPERADMIN, r.consulta, 1, 5)
    assert f"Universidad: {nombre}" in vista.descripcion[0]


def test_cada_quien_le_pasa_a_gemini_solo_su_catalogo(db, monkeypatch):
    capturado: dict = {}
    _gemini_de_reportes(monkeypatch, _pedido(fuente="vacantes"), capturado)
    r = InterpreteReportes(db).interpretar(Contexto(rol="empresa", company_id=uuid.uuid4()), "mis vacantes")

    propiedades = capturado["esquema"]["properties"]
    assert propiedades["fuente"]["enum"] == ["vacantes", "postulaciones"]
    filtros = propiedades["filtros"]["items"]["properties"]["clave"]["enum"]
    assert "universidad" not in filtros and "empresa" not in filtros
    assert '"clave":"egresados"' not in capturado["instrucciones"]
    # Sin columnas pedidas, van las de siempre de la fuente.
    assert r.consulta.columnas == ["titulo", "estado", "publicada", "postulaciones"]


def test_un_pedido_que_no_es_un_reporte_se_explica(db, monkeypatch):
    explicacion = "Solo puedo armar reportes de egresados, empresas, vacantes o postulaciones."
    _gemini_de_reportes(monkeypatch, _pedido(entendido=False, explicacion=explicacion))
    with pytest.raises(BusinessException, match="Solo puedo armar reportes"):
        InterpreteReportes(db).interpretar(_UNIVERSIDAD, "¿cuál es la capital de Francia?")


def test_sin_clave_o_sin_respuesta_de_gemini_se_arma_a_mano(db, monkeypatch):
    with pytest.raises(ServiceUnavailableException, match="armarlo a mano"):
        InterpreteReportes(db).interpretar(_UNIVERSIDAD, "egresados validados")

    monkeypatch.setattr(get_settings(), "gemini_api_key_reportes", "clave-prueba")

    def caido(*args, **kwargs):
        raise ia_generativa.IAGenerativaNoDisponible("sin cupo")

    monkeypatch.setattr(ia_generativa, "generar_json", caido)
    with pytest.raises(ServiceUnavailableException, match="armarlo a mano"):
        InterpreteReportes(db).interpretar(_UNIVERSIDAD, "egresados validados")


def test_un_egresado_no_puede_pedir_reportes(monkeypatch):
    monkeypatch.setattr(ia_generativa, "generar_json", lambda *a, **k: pytest.fail("No debía llamar a Gemini."))
    token = create_access_token(
        "90000000-0000-0000-0000-000000000003", "candidate", extra_claims={"roles": ["candidate"]}
    )
    res = TestClient(app).post(
        "/api/reportes/interpretar", json={"pedido": "todos los egresados"}, headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 403
