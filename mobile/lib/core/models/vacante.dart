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
  final int? afinidadPorcentaje;

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
    this.afinidadPorcentaje,
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
      skills: (json['skills'] as List<dynamic>? ?? [])
          .map((e) => VacanteSkill.fromJson(e as Map<String, dynamic>))
          .toList(),
      afinidadPorcentaje: json['afinidad_porcentaje'] as int?,
    );
  }

  String get salarioLegible {
    if (!salaryVisible || (salaryMin == null && salaryMax == null)) {
      return 'No especificado';
    }
    if (salaryMin != null && salaryMax != null) {
      return '$currency $salaryMin - $salaryMax';
    }
    return '$currency ${salaryMin ?? salaryMax}';
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
