/// Perfil del egresado autenticado (ver backend/app/features/perfil/schema.py::PerfilEgresadoResponse).
class PerfilEgresado {
  final String nombres;
  final String apellidos;
  final String? tituloProfesional;
  final String? ciudad;
  final String? resumenProfesional;
  final String estadoValidacion;
  final int porcentajeCompletitud;

  const PerfilEgresado({
    required this.nombres,
    required this.apellidos,
    required this.tituloProfesional,
    required this.ciudad,
    required this.resumenProfesional,
    required this.estadoValidacion,
    required this.porcentajeCompletitud,
  });

  factory PerfilEgresado.fromJson(Map<String, dynamic> json) {
    return PerfilEgresado(
      nombres: json['nombres'] as String,
      apellidos: json['apellidos'] as String,
      tituloProfesional: json['titulo_profesional'] as String?,
      ciudad: json['ciudad'] as String?,
      resumenProfesional: json['resumen_profesional'] as String?,
      estadoValidacion: json['estado_validacion'] as String? ?? 'PENDIENTE',
      porcentajeCompletitud: json['porcentaje_completitud'] as int? ?? 0,
    );
  }

  String get nombreCompleto => '$nombres $apellidos';
}
