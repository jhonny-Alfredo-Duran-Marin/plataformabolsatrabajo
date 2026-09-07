/// Perfil del egresado autenticado (ver backend/app/features/perfil/schema.py::PerfilEgresadoResponse).
class PerfilEgresado {
  final String nombres;
  final String apellidos;
  final String? tituloProfesional;
  final String? ciudad;
  final String? resumenProfesional;
  final String estadoValidacion;
  final int porcentajeCompletitud;
  final String? telefono;
  final String? disponibilidad;
  final int? anioEgreso;
  final String? matricula;

  const PerfilEgresado({
    required this.nombres,
    required this.apellidos,
    required this.tituloProfesional,
    required this.ciudad,
    required this.resumenProfesional,
    required this.estadoValidacion,
    required this.porcentajeCompletitud,
    this.telefono,
    this.disponibilidad,
    this.anioEgreso,
    this.matricula,
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
      telefono: json['telefono'] as String?,
      disponibilidad: json['disponibilidad'] as String?,
      anioEgreso: json['anio_egreso'] as int?,
      matricula: json['matricula'] as String?,
    );
  }

  String get nombreCompleto => '$nombres $apellidos';
}
