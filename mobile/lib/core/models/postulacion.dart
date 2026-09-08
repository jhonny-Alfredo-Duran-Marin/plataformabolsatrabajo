/// Espejo simplificado de PostulacionItemResponse
/// (backend/app/features/postulaciones/schema.py), usado en el seguimiento
/// de postulaciones del egresado (HU-15).
class PostulacionItem {
  final String id;
  final String jobId;
  final String jobTitulo;
  final String empresaNombre;
  final String? empresaCiudad;
  final String modalidadLabel;
  final String tipoEmpleoLabel;
  final String estado;
  final String estadoLabel;
  final String estadoColor;
  final String? etapaActualNombre;
  final DateTime fechaPostulacion;
  final bool puedeRetirar;

  const PostulacionItem({
    required this.id,
    required this.jobId,
    required this.jobTitulo,
    required this.empresaNombre,
    required this.empresaCiudad,
    required this.modalidadLabel,
    required this.tipoEmpleoLabel,
    required this.estado,
    required this.estadoLabel,
    required this.estadoColor,
    required this.etapaActualNombre,
    required this.fechaPostulacion,
    required this.puedeRetirar,
  });

  factory PostulacionItem.fromJson(Map<String, dynamic> json) {
    return PostulacionItem(
      id: json['id'] as String,
      jobId: json['job_id'] as String,
      jobTitulo: json['job_titulo'] as String,
      empresaNombre: json['empresa_nombre'] as String,
      empresaCiudad: json['empresa_ciudad'] as String?,
      modalidadLabel: json['modalidad_label'] as String? ?? '',
      tipoEmpleoLabel: json['tipo_empleo_label'] as String? ?? '',
      estado: json['estado'] as String,
      estadoLabel: json['estado_label'] as String? ?? json['estado'] as String,
      estadoColor: json['estado_color'] as String? ?? 'gray',
      etapaActualNombre: json['etapa_actual_nombre'] as String?,
      fechaPostulacion: DateTime.parse(json['fecha_postulacion'] as String),
      puedeRetirar: json['puede_retirar'] as bool? ?? false,
    );
  }
}

class ResumenPostulaciones {
  final int total;
  final int activas;
  final int enRevision;
  final int entrevistasOfertas;
  final int contratados;
  final int finalizadas;
  final List<PostulacionItem> postulaciones;

  const ResumenPostulaciones({
    required this.total,
    required this.activas,
    required this.enRevision,
    required this.entrevistasOfertas,
    required this.contratados,
    required this.finalizadas,
    required this.postulaciones,
  });

  factory ResumenPostulaciones.fromJson(Map<String, dynamic> json) {
    return ResumenPostulaciones(
      total: json['total'] as int? ?? 0,
      activas: json['activas'] as int? ?? 0,
      enRevision: json['en_revision'] as int? ?? 0,
      entrevistasOfertas: json['entrevistas_ofertas'] as int? ?? 0,
      contratados: json['contratados'] as int? ?? 0,
      finalizadas: json['finalizadas'] as int? ?? 0,
      postulaciones: (json['postulaciones'] as List<dynamic>? ?? [])
          .map((e) => PostulacionItem.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class HistorialEstado {
  final String haciaEstadoLabel;
  final String haciaEstadoColor;
  final String? motivo;
  final DateTime fecha;

  const HistorialEstado({
    required this.haciaEstadoLabel,
    required this.haciaEstadoColor,
    required this.motivo,
    required this.fecha,
  });

  factory HistorialEstado.fromJson(Map<String, dynamic> json) {
    return HistorialEstado(
      haciaEstadoLabel: json['hacia_estado_label'] as String,
      haciaEstadoColor: json['hacia_estado_color'] as String? ?? 'gray',
      motivo: json['motivo'] as String?,
      fecha: DateTime.parse(json['fecha'] as String),
    );
  }
}

class DetallePostulacion {
  final PostulacionItem postulacion;
  final String vacanteDescripcion;
  final List<HistorialEstado> historialEstados;

  const DetallePostulacion({
    required this.postulacion,
    required this.vacanteDescripcion,
    required this.historialEstados,
  });

  factory DetallePostulacion.fromJson(Map<String, dynamic> json) {
    return DetallePostulacion(
      postulacion: PostulacionItem.fromJson(json['postulacion'] as Map<String, dynamic>),
      vacanteDescripcion: (json['vacante'] as Map<String, dynamic>)['descripcion'] as String? ?? '',
      historialEstados: (json['historial_estados'] as List<dynamic>? ?? [])
          .map((e) => HistorialEstado.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}
