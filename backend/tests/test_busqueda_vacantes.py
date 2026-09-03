import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.models.candidato import CandidateEducation, CandidateProfile, CandidateSkill
from app.models.catalogo import FieldOfStudy, JobCategory, Skill
from app.models.empresa import Company, Sector
from app.models.oferta import JobEducationPreference, JobPosting, JobSkill
from app.models.usuario import AppUser, Role, UserRole


def setup_datos_vacantes(db):
    # 1. Sector y Empresa
    sector = Sector(name="Tecnología e Información")
    db.add(sector)
    db.flush()

    empresa = Company(
        legal_name="InnovaTech S.R.L.",
        trade_name="InnovaTech",
        tax_id="1020304050",
        sector_id=sector.id,
        city="Santa Cruz de la Sierra",
        verification_status="verified",
        account_status="active",
    )
    db.add(empresa)

    # 2. Categoría, Carreras y Habilidades
    categoria = JobCategory(name="Desarrollo de Software", is_active=True)
    carrera_sistemas = FieldOfStudy(name="Ingeniería de Sistemas", category="Tecnología")
    carrera_comercial = FieldOfStudy(name="Ingeniería Comercial", category="Negocios")
    skill_python = Skill(name="Python", category="Backend", is_active=True)
    skill_angular = Skill(name="Angular", category="Frontend", is_active=True)
    skill_sql = Skill(name="SQL", category="Bases de Datos", is_active=True)

    db.add_all([categoria, carrera_sistemas, carrera_comercial, skill_python, skill_angular, skill_sql])
    db.flush()

    # 3. Vacante 1: Publicada y vigente (Desarrollador Full Stack)
    vacante1 = JobPosting(
        company_id=empresa.id,
        category_id=categoria.id,
        title="Desarrollador Full Stack Python & Angular",
        description="Buscamos desarrollador para construir aplicaciones web modernas en la nube.",
        responsibilities_json=["Desarrollar microservicios", "Construir interfaces reactivas"],
        requirements_json=["2+ años de experiencia con Python", "Dominio de Angular"],
        benefits_json=["Seguro médico privado", "Trabajo híbrido"],
        seniority_level="mid",
        employment_type="full_time",
        work_modality="hybrid",
        city="Santa Cruz de la Sierra",
        salary_min=Decimal("5000.00"),
        salary_max=Decimal("8000.00"),
        salary_visible=True,
        status="published",
        application_deadline=datetime.now(timezone.utc) + timedelta(days=30),
        published_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    db.add(vacante1)
    db.flush()

    # Habilidades y Carreras de Vacante 1
    db.add(JobSkill(job_posting_id=vacante1.id, skill_id=skill_python.id, importance="required"))
    db.add(JobSkill(job_posting_id=vacante1.id, skill_id=skill_angular.id, importance="required"))
    db.add(JobEducationPreference(job_posting_id=vacante1.id, field_of_study_id=carrera_sistemas.id, is_required=True))

    # 4. Vacante 2: Publicada pero de otra ciudad y modalidad
    vacante2 = JobPosting(
        company_id=empresa.id,
        category_id=categoria.id,
        title="Analista de Datos y Base de Datos",
        description="Encargado de análisis de información y reportes institucionales.",
        seniority_level="junior",
        employment_type="part_time",
        work_modality="remote",
        city="La Paz",
        salary_min=Decimal("3500.00"),
        salary_max=Decimal("4500.00"),
        salary_visible=True,
        status="published",
        application_deadline=datetime.now(timezone.utc) + timedelta(days=15),
        published_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db.add(vacante2)
    db.flush()
    db.add(JobSkill(job_posting_id=vacante2.id, skill_id=skill_sql.id, importance="required"))

    # 5. Vacante 3: En borrador (draft) -> No debe aparecer en búsqueda
    vacante3 = JobPosting(
        company_id=empresa.id,
        category_id=categoria.id,
        title="Vacante en Borrador Oculta",
        description="Esta vacante no debe verse en los resultados públicos.",
        seniority_level="senior",
        employment_type="full_time",
        work_modality="on_site",
        city="Santa Cruz de la Sierra",
        status="draft",
    )
    db.add(vacante3)

    # 6. Vacante 4: Expirada (deadline pasado) -> No debe aparecer en búsqueda vigente
    vacante4 = JobPosting(
        company_id=empresa.id,
        category_id=categoria.id,
        title="Vacante Vencida de Prueba",
        description="Esta vacante ya cerró su convocatoria.",
        seniority_level="junior",
        employment_type="full_time",
        work_modality="on_site",
        city="Santa Cruz de la Sierra",
        status="published",
        application_deadline=datetime.now(timezone.utc) - timedelta(days=5),
        published_at=datetime.now(timezone.utc) - timedelta(days=20),
    )
    db.add(vacante4)

    # 7. Crear un candidato de prueba con perfil
    user_cand = AppUser(email="candidato.test@uagrm.edu.bo", password_hash="hash123", account_status="active")
    db.add(user_cand)
    db.flush()

    perfil = CandidateProfile(
        user_id=user_cand.id,
        first_name="Mario",
        last_name="Gutiérrez",
        city="Santa Cruz de la Sierra",
    )
    db.add(perfil)
    db.flush()

    # El candidato sabe Python y estudió Sistemas
    db.add(CandidateSkill(candidate_id=perfil.id, skill_id=skill_python.id))
    db.add(CandidateEducation(candidate_id=perfil.id, field_of_study_id=carrera_sistemas.id, program_name="Ingeniería de Sistemas"))

    db.commit()

    return {
        "vacante1_id": str(vacante1.id),
        "vacante2_id": str(vacante2.id),
        "carrera_sistemas_id": str(carrera_sistemas.id),
        "user_cand_id": user_cand.id,
    }


def test_buscar_vacantes_filtros_combinados(client, db):
    datos = setup_datos_vacantes(db)

    # 1. Búsqueda sin filtros -> Retorna las 2 vacantes publicadas y vigentes
    res1 = client.get("/api/vacantes")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["total"] == 2
    assert len(data1["items"]) == 2

    # 2. Búsqueda por palabra clave "Python"
    res_q = client.get("/api/vacantes?q=Python")
    assert res_q.status_code == 200
    data_q = res_q.json()
    assert data_q["total"] == 1
    assert data_q["items"][0]["id"] == datos["vacante1_id"]

    # 3. Filtrar por ciudad "Santa Cruz de la Sierra"
    res_ciudad = client.get("/api/vacantes?ciudad=Santa Cruz de la Sierra")
    assert res_ciudad.status_code == 200
    data_ciudad = res_ciudad.json()
    assert data_ciudad["total"] == 1
    assert data_ciudad["items"][0]["city"] == "Santa Cruz de la Sierra"

    # 4. Filtrar por modalidad "remote"
    res_remoto = client.get("/api/vacantes?modalidad=remote")
    assert res_remoto.status_code == 200
    assert res_remoto.json()["total"] == 1
    assert res_remoto.json()["items"][0]["work_modality"] == "remote"

    # 5. Filtrar por carrera
    res_carrera = client.get(f"/api/vacantes?carrera_id={datos['carrera_sistemas_id']}")
    assert res_carrera.status_code == 200
    assert res_carrera.json()["total"] == 1


def test_filtros_disponibles(client, db):
    setup_datos_vacantes(db)

    res = client.get("/api/vacantes/filtros")
    assert res.status_code == 200
    data = res.json()
    assert "Santa Cruz de la Sierra" in data["ciudades"]
    assert "hybrid" in data["modalidades"]
    assert any(c["name"] == "Desarrollo de Software" for c in data["categorias"])
    assert any(c["name"] == "Ingeniería de Sistemas" for c in data["carreras"])


def test_obtener_detalle_vacante_e_incrementar_vistas(client, db):
    datos = setup_datos_vacantes(db)
    vacante_id = datos["vacante1_id"]

    # Consultar detalle
    res = client.get(f"/api/vacantes/{vacante_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "Desarrollador Full Stack Python & Angular"
    assert len(data["responsibilities"]) == 2
    assert len(data["requirements"]) == 2
    assert len(data["benefits"]) == 2
    assert data["company"]["legal_name"] == "InnovaTech S.R.L."
    assert data["view_count"] >= 1


def test_vacante_no_encontrada(client, db):
    id_falso = uuid.uuid4()
    res = client.get(f"/api/vacantes/{id_falso}")
    assert res.status_code == 404

