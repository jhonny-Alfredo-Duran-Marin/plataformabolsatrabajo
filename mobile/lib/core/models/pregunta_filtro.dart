/// Pregunta de filtro de una vacante (ver GET /vacantes/{id}/preguntas),
/// usada al postularse (HU-14). Espejo simplificado del backend.
class PreguntaFiltro {
  final String id;
  final String questionText;
  final String questionType; // 'text' | 'number' | 'single_choice'
  final bool isRequired;
  final bool isKnockout;
  final List<OpcionPreguntaFiltro> options;

  const PreguntaFiltro({
    required this.id,
    required this.questionText,
    required this.questionType,
    required this.isRequired,
    required this.isKnockout,
    required this.options,
  });

  factory PreguntaFiltro.fromJson(Map<String, dynamic> json) {
    return PreguntaFiltro(
      id: json['id'] as String,
      questionText: json['question_text'] as String,
      questionType: json['question_type'] as String,
      isRequired: json['is_required'] as bool? ?? false,
      isKnockout: json['is_knockout'] as bool? ?? false,
      options: (json['options'] as List<dynamic>? ?? [])
          .map((e) => OpcionPreguntaFiltro.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class OpcionPreguntaFiltro {
  final String id;
  final String optionText;

  const OpcionPreguntaFiltro({required this.id, required this.optionText});

  factory OpcionPreguntaFiltro.fromJson(Map<String, dynamic> json) {
    return OpcionPreguntaFiltro(
      id: json['id'] as String,
      optionText: json['option_text'] as String,
    );
  }
}
