/// Encuesta de situación laboral (HU-30), tal como la ve el egresado.
class MiEncuesta {
  final String id;
  final String titulo;
  final String? descripcion;
  final String periodo;
  final DateTime? venceEl;
  final bool respondida;
  final DateTime? respondidaEl;

  const MiEncuesta({
    required this.id,
    required this.titulo,
    required this.descripcion,
    required this.periodo,
    required this.venceEl,
    required this.respondida,
    required this.respondidaEl,
  });

  bool get vencida => venceEl != null && venceEl!.isBefore(DateTime.now());

  /// Todavía se puede responder.
  bool get pendiente => !respondida && !vencida;

  factory MiEncuesta.fromJson(Map<String, dynamic> json) => MiEncuesta(
        id: json['id'] as String,
        titulo: json['titulo'] as String? ?? 'Encuesta laboral',
        descripcion: json['descripcion'] as String?,
        periodo: json['periodo'] as String? ?? '',
        // La API manda la hora en UTC: se muestra en la hora del teléfono (Bolivia).
        venceEl: DateTime.tryParse(json['vence_el'] as String? ?? '')?.toLocal(),
        respondida: json['respondida'] == true,
        respondidaEl: DateTime.tryParse(json['respondida_el'] as String? ?? '')?.toLocal(),
      );
}

class OpcionEncuesta {
  final String id;
  final String? codigo;
  final String texto;

  const OpcionEncuesta({required this.id, required this.codigo, required this.texto});

  factory OpcionEncuesta.fromJson(Map<String, dynamic> json) => OpcionEncuesta(
        id: json['id'] as String,
        codigo: json['codigo'] as String?,
        texto: json['texto'] as String? ?? '',
      );
}

class PreguntaEncuesta {
  final String id;
  final String? codigo;
  final String texto;

  /// single_choice, text, number o scale (1 a 5).
  final String tipo;
  final bool obligatoria;
  final List<OpcionEncuesta> opciones;

  const PreguntaEncuesta({
    required this.id,
    required this.codigo,
    required this.texto,
    required this.tipo,
    required this.obligatoria,
    required this.opciones,
  });

  factory PreguntaEncuesta.fromJson(Map<String, dynamic> json) => PreguntaEncuesta(
        id: json['id'] as String,
        codigo: json['codigo'] as String?,
        texto: json['texto'] as String? ?? '',
        tipo: json['tipo'] as String? ?? 'text',
        obligatoria: json['obligatoria'] == true,
        opciones: (json['opciones'] as List<dynamic>? ?? const [])
            .map((o) => OpcionEncuesta.fromJson(o as Map<String, dynamic>))
            .toList(),
      );
}

class FormularioEncuesta {
  final String id;
  final String titulo;
  final String? descripcion;
  final String periodo;
  final DateTime? venceEl;
  final List<PreguntaEncuesta> preguntas;

  const FormularioEncuesta({
    required this.id,
    required this.titulo,
    required this.descripcion,
    required this.periodo,
    required this.venceEl,
    required this.preguntas,
  });

  factory FormularioEncuesta.fromJson(Map<String, dynamic> json) => FormularioEncuesta(
        id: json['id'] as String,
        titulo: json['titulo'] as String? ?? 'Encuesta laboral',
        descripcion: json['descripcion'] as String?,
        periodo: json['periodo'] as String? ?? '',
        venceEl: DateTime.tryParse(json['vence_el'] as String? ?? '')?.toLocal(),
        preguntas: (json['preguntas'] as List<dynamic>? ?? const [])
            .map((p) => PreguntaEncuesta.fromJson(p as Map<String, dynamic>))
            .toList(),
      );
}
