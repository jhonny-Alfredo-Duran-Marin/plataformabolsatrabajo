/// Resumen de una vacante publicada (ver backend/app/features/vacantes/schema.py::VacanteResponse).
/// Solo se mapean los campos que se muestran en la app móvil.
class Vacante {
  final String id;
  final String companyName;
  final String title;
  final String description;
  final String seniorityLevel;
  final String employmentType;
  final String workModality;
  final String city;
  final String? salaryMin;
  final String? salaryMax;
  final String currency;
  final bool salaryVisible;
  final int positionsAvailable;
  final String? applicationDeadline;
  final List<VacanteSkill> skills;
  final List<VacanteCarrera> educationPreferences;
  final int? afinidadPorcentaje;
  final int? scoreRelevancia;
  final String? razonCoincidencia;

  const Vacante({
    required this.id,
    required this.companyName,
    required this.title,
    required this.description,
    required this.seniorityLevel,
    required this.employmentType,
    required this.workModality,
    required this.city,
    required this.salaryMin,
    required this.salaryMax,
    required this.currency,
    required this.salaryVisible,
    required this.positionsAvailable,
    required this.applicationDeadline,
    required this.skills,
    this.educationPreferences = const [],
    this.afinidadPorcentaje,
    this.scoreRelevancia,
    this.razonCoincidencia,
  });

  /// Acepta tanto el shape de GET /vacantes (company_name plano) como el de
  /// GET /vacantes/buscar (objeto company anidado, con afinidad calculada).
  factory Vacante.fromJson(Map<String, dynamic> json) {
    final empresa = json['company'] as Map<String, dynamic>?;
    final nombreEmpresa = json['company_name'] as String? ??
        (empresa?['trade_name'] as String?) ??
        (empresa?['legal_name'] as String?) ??
        'Empresa';

    return Vacante(
      id: json['id'] as String,
      companyName: nombreEmpresa,
      title: json['title'] as String,
      description: json['description'] as String? ?? '',
      seniorityLevel: json['seniority_level'] as String? ?? '',
      employmentType: json['employment_type'] as String? ?? '',
      workModality: json['work_modality'] as String? ?? '',
      city: json['city'] as String? ?? '',
      salaryMin: json['salary_min']?.toString(),
      salaryMax: json['salary_max']?.toString(),
      currency: json['currency'] as String? ?? 'BOB',
      salaryVisible: json['salary_visible'] as bool? ?? false,
      positionsAvailable: json['positions_available'] as int? ?? 1,
      applicationDeadline: json['application_deadline'] as String?,
      skills: (json['skills'] as List<dynamic>? ?? []).map((e) {
        if (e is String) {
          return VacanteSkill(skillName: e, importance: 'required', minProficiency: 'intermediate');
        }
        return VacanteSkill.fromJson(e as Map<String, dynamic>);
      }).toList(),
      educationPreferences: (json['education_preferences'] as List<dynamic>? ?? [])
          .whereType<Map<String, dynamic>>()
          .map(VacanteCarrera.fromJson)
          .toList(),
      afinidadPorcentaje: json['afinidad_porcentaje'] as int?,
      scoreRelevancia: (json['score_relevancia'] as num?)?.toInt(),
      razonCoincidencia: json['razon_coincidencia'] as String?,
    );
  }

  /// Los códigos del backend vienen en inglés; en pantalla se muestran en español.
  static const _modalidades = {'onsite': 'Presencial', 'on_site': 'Presencial', 'remote': 'Remoto', 'hybrid': 'Híbrido'};
  static String etiquetaModalidad(String codigo) => _modalidades[codigo] ?? codigo;
  static const _jornadas = {
    'permanent': 'Tiempo completo',
    'full_time': 'Tiempo completo',
    'part_time': 'Medio tiempo',
    'temporary': 'Temporal',
    'contract': 'Por contrato',
    'contractor': 'Por contrato',
    'internship': 'Pasantía',
    'freelance': 'Freelance',
  };
  static const _niveles = {
    'internship': 'Pasantía',
    'junior': 'Junior',
    'mid': 'Semi senior',
    'senior': 'Senior',
    'lead': 'Líder',
  };

  String get modalidadLegible => _modalidades[workModality] ?? workModality;
  String get jornadaLegible => _jornadas[employmentType] ?? employmentType;
  String get nivelLegible => _niveles[seniorityLevel] ?? seniorityLevel;

  bool get tieneSalario => salaryVisible && (_monto(salaryMin) != null || _monto(salaryMax) != null);

  /// "Bs. 4.200 – 5.200"
  String get salarioLegible {
    final minimo = _monto(salaryMin);
    final maximo = _monto(salaryMax);
    if (!tieneSalario) return 'A convenir';
    final moneda = currency == 'BOB' ? 'Bs.' : currency;
    if (minimo != null && maximo != null) return '$moneda $minimo – $maximo';
    return '$moneda ${minimo ?? maximo}';
  }

  /// Fecha límite de postulación, en hora local.
  DateTime? get cierre {
    final fecha = applicationDeadline == null ? null : DateTime.tryParse(applicationDeadline!);
    return fecha?.toLocal();
  }

  /// "4200.00" -> "4.200"
  static String? _monto(String? valor) {
    final numero = num.tryParse(valor ?? '');
    if (numero == null) return null;
    return numero.round().toString().replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (_) => '.');
  }
}

class VacanteSkill {
  final String skillName;
  final String importance;
  final String minProficiency;

  const VacanteSkill({
    required this.skillName,
    required this.importance,
    required this.minProficiency,
  });

  factory VacanteSkill.fromJson(Map<String, dynamic> json) {
    return VacanteSkill(
      skillName: json['skill_name'] as String? ?? json['name'] as String? ?? '',
      importance: json['importance'] as String? ?? '',
      minProficiency: json['min_proficiency'] as String? ?? '',
    );
  }
}

/// Carrera preferida o requerida por una vacante (HU-13 / HU-35).
class VacanteCarrera {
  final String fieldOfStudyId;
  final String name;
  final bool isRequired;

  const VacanteCarrera({
    required this.fieldOfStudyId,
    required this.name,
    this.isRequired = true,
  });

  factory VacanteCarrera.fromJson(Map<String, dynamic> json) {
    return VacanteCarrera(
      fieldOfStudyId: (json['field_of_study_id'] ?? '').toString(),
      name: json['name'] as String? ?? '',
      isRequired: json['is_required'] as bool? ?? true,
    );
  }
}

/// Elemento del catálogo de carreras devuelto por GET /vacantes/buscar/filtros.
class CarreraFiltro {
  final String id;
  final String name;
  final String? category;

  const CarreraFiltro({
    required this.id,
    required this.name,
    this.category,
  });

  factory CarreraFiltro.fromJson(Map<String, dynamic> json) {
    return CarreraFiltro(
      id: (json['id'] ?? '').toString(),
      name: json['name'] as String? ?? '',
      category: json['category'] as String?,
    );
  }
}

/// Opciones vigentes para los filtros de búsqueda móvil y web (GET /vacantes/buscar/filtros).
class FiltrosDisponiblesVacantes {
  final List<String> ciudades;
  final List<String> modalidades;
  final List<CarreraFiltro> carreras;

  const FiltrosDisponiblesVacantes({
    this.ciudades = const [],
    this.modalidades = const ['onsite', 'remote', 'hybrid'],
    this.carreras = const [],
  });

  factory FiltrosDisponiblesVacantes.fromJson(Map<String, dynamic> json) {
    final ciudades = (json['ciudades'] as List<dynamic>? ?? [])
        .map((e) => e.toString().trim())
        .where((e) => e.isNotEmpty)
        .toList();
    final modalidadesRaw = (json['modalidades'] as List<dynamic>? ?? [])
        .map((e) => e.toString().trim())
        .where((e) => e.isNotEmpty)
        .toList();
    final carreras = (json['carreras'] as List<dynamic>? ?? [])
        .whereType<Map<String, dynamic>>()
        .map(CarreraFiltro.fromJson)
        .where((c) => c.id.isNotEmpty && c.name.isNotEmpty)
        .toList();

    return FiltrosDisponiblesVacantes(
      ciudades: ciudades,
      modalidades: modalidadesRaw.isEmpty ? const ['onsite', 'remote', 'hybrid'] : modalidadesRaw,
      carreras: carreras,
    );
  }
}
