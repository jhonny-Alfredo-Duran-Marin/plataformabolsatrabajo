import 'api_config.dart';
import 'api_http.dart';

/// Borrador de resumen profesional armado con los datos del perfil (HU-26).
class BorradorResumen {
  final String texto;
  final String advertencia;
  final int variante;
  final int totalVariantes;

  const BorradorResumen({
    required this.texto,
    required this.advertencia,
    required this.variante,
    required this.totalVariantes,
  });

  factory BorradorResumen.fromJson(Map<String, dynamic> json) => BorradorResumen(
        texto: json['borrador'] as String? ?? '',
        advertencia: json['advertencia'] as String? ?? 'Borrador generado por IA. Revisalo antes de guardarlo.',
        variante: (json['variante'] as num?)?.toInt() ?? 1,
        totalVariantes: (json['total_variantes'] as num?)?.toInt() ?? 3,
      );
}

class MensajeAsistente {
  /// user o assistant.
  final String rol;
  final String texto;

  const MensajeAsistente(this.rol, this.texto);

  bool get esDelUsuario => rol == 'user';

  factory MensajeAsistente.fromJson(Map<String, dynamic> json) =>
      MensajeAsistente(json['role'] as String? ?? 'assistant', json['content'] as String? ?? '');
}

/// Conversación con el asistente de orientación (HU-28).
class SesionAsistente {
  final String id;
  final String saludo;
  final List<String> sugerencias;
  final List<MensajeAsistente> mensajes;

  const SesionAsistente({required this.id, required this.saludo, required this.sugerencias, required this.mensajes});

  factory SesionAsistente.fromJson(Map<String, dynamic> json) => SesionAsistente(
        id: json['session_id'] as String,
        saludo: json['saludo'] as String? ?? '',
        sugerencias: _textos(json['sugerencias']),
        mensajes: (json['mensajes'] as List<dynamic>? ?? const [])
            .map((m) => MensajeAsistente.fromJson(m as Map<String, dynamic>))
            .toList(),
      );
}

/// Postulación que el asistente muestra cuando se le pregunta por el estado de las postulaciones.
class PostulacionAsistente {
  final String puesto;
  final String empresa;
  final String estado;
  final String? etapa;

  const PostulacionAsistente({required this.puesto, required this.empresa, required this.estado, required this.etapa});

  factory PostulacionAsistente.fromJson(Map<String, dynamic> json) => PostulacionAsistente(
        puesto: json['job_title'] as String? ?? '',
        empresa: json['company_name'] as String? ?? '',
        estado: json['status_label'] as String? ?? '',
        etapa: json['etapa_actual'] as String?,
      );
}

class RespuestaAsistente {
  final MensajeAsistente respuesta;
  final List<String> sugerencias;
  final List<PostulacionAsistente> postulaciones;

  const RespuestaAsistente({required this.respuesta, required this.sugerencias, required this.postulaciones});

  factory RespuestaAsistente.fromJson(Map<String, dynamic> json) => RespuestaAsistente(
        respuesta: MensajeAsistente.fromJson(json['respuesta'] as Map<String, dynamic>),
        sugerencias: _textos(json['sugerencias']),
        postulaciones: (json['postulaciones'] as List<dynamic>? ?? const [])
            .map((p) => PostulacionAsistente.fromJson(p as Map<String, dynamic>))
            .toList(),
      );
}

List<String> _textos(Object? lista) => (lista as List<dynamic>? ?? const []).map((s) => '$s').toList();

/// Asistentes de IA del egresado (backend/app/features/ia/router.py).
class IaService {
  Uri _uri(String ruta) => Uri.parse('${ApiConfig.baseUrl}/ia$ruta');

  /// POST /ia/resumen-profesional/generar. Con la IA apagada responde 503 con un mensaje para redactar a mano.
  Future<BorradorResumen> generarResumen(String accessToken, {int variante = 1}) async {
    final respuesta = await enviar(
      _uri('/resumen-profesional/generar'),
      accessToken: accessToken,
      cuerpo: {'variante': variante, 'enfoque': 'general'},
    );
    if (respuesta.statusCode != 200) {
      throw ApiException(
        mensajeDeError(respuesta, 'No se pudo generar el borrador. Podés redactar tu resumen a mano.'),
        codigo: respuesta.statusCode,
      );
    }
    return BorradorResumen.fromJson(decodificar(respuesta) as Map<String, dynamic>);
  }

  /// GET /ia/chatbot/sesion (retoma la conversación abierta) o POST /ia/chatbot/nueva-sesion.
  Future<SesionAsistente> abrirConversacion(String accessToken, {bool nueva = false}) async {
    final respuesta = nueva
        ? await enviar(_uri('/chatbot/nueva-sesion'), accessToken: accessToken)
        : await obtener(_uri('/chatbot/sesion'), accessToken: accessToken);
    if (respuesta.statusCode != 200) {
      throw ApiException(
        mensajeDeError(respuesta, 'El asistente no está disponible en este momento.'),
        codigo: respuesta.statusCode,
      );
    }
    return SesionAsistente.fromJson(decodificar(respuesta) as Map<String, dynamic>);
  }

  /// POST /ia/chatbot/mensajes.
  Future<RespuestaAsistente> preguntar(String accessToken, String sesionId, String mensaje) async {
    final respuesta = await enviar(
      _uri('/chatbot/mensajes'),
      accessToken: accessToken,
      cuerpo: {'mensaje': mensaje, 'session_id': sesionId},
    );
    if (respuesta.statusCode != 200) {
      throw ApiException(
        mensajeDeError(respuesta, 'El asistente no pudo responder. Intentá de nuevo.'),
        codigo: respuesta.statusCode,
      );
    }
    return RespuestaAsistente.fromJson(decodificar(respuesta) as Map<String, dynamic>);
  }
}
