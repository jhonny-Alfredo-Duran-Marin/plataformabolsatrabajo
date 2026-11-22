import 'package:http/http.dart' as http;

import '../models/postulacion.dart';
import 'api_config.dart';
import 'api_http.dart';

/// Excepción con el mensaje de error legible que ya devuelve el backend.
class PostulacionException implements Exception {
  final String mensaje;
  final bool esErrorDeConexion;
  final bool yaPostulado;

  const PostulacionException(
    this.mensaje, {
    this.esErrorDeConexion = false,
    this.yaPostulado = false,
  });

  @override
  String toString() => mensaje;
}

/// Respuesta puntual de una postulación, tal como devuelve POST /postulaciones/
/// (incluye si fue descartada automáticamente por una pregunta eliminatoria).
class ResultadoPostulacion {
  final String? id;
  final String currentStatus;
  final String message;

  const ResultadoPostulacion({
    this.id,
    required this.currentStatus,
    required this.message,
  });
}

/// Una respuesta del egresado a una pregunta de filtro, lista para enviar.
class RespuestaPregunta {
  final String questionId;
  final String? selectedOptionId;
  final String? answerText;
  final num? answerNumber;

  const RespuestaPregunta({
    required this.questionId,
    this.selectedOptionId,
    this.answerText,
    this.answerNumber,
  });

  Map<String, dynamic> toJson() => {
        'question_id': questionId,
        'selected_option_id': selectedOptionId,
        'answer_text': answerText,
        'answer_number': answerNumber,
      };
}

/// Consume /postulaciones (backend/app/features/postulaciones/router.py),
/// el mismo API que usa el frontend web, sin mocks (HU-14 / HU-15 / HU-35).
class PostulacionService {
  final http.Client? _client;

  PostulacionService({http.Client? client}) : _client = client;

  Future<ResultadoPostulacion> postular(
    String accessToken,
    String jobId,
    List<RespuestaPregunta> respuestas,
  ) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}/postulaciones/');

    final http.Response respuesta;
    try {
      respuesta = await enviar(
        uri,
        accessToken: accessToken,
        cuerpo: {
          'job_id': jobId,
          'answers': respuestas.map((r) => r.toJson()).toList(),
        },
        client: _client,
      );
    } on ApiException catch (e) {
      throw PostulacionException(e.mensaje, esErrorDeConexion: true);
    }

    if (respuesta.statusCode == 200 || respuesta.statusCode == 201) {
      final cuerpo = decodificar(respuesta) as Map<String, dynamic>;
      return ResultadoPostulacion(
        id: cuerpo['id']?.toString(),
        currentStatus: cuerpo['current_status'] as String,
        message: cuerpo['message'] as String? ?? 'Postulación exitosa',
      );
    }

    final mensaje = mensajeDeError(respuesta, 'No se pudo completar la postulación.');
    final textoNormalizado = mensaje.toLowerCase();
    final esDuplicada = respuesta.statusCode == 409 ||
        textoNormalizado.contains('ya te has postulado') ||
        textoNormalizado.contains('ya existe la postulaci');
    throw PostulacionException(mensaje, yaPostulado: esDuplicada);
  }

  /// GET /postulaciones/ (HU-14 / HU-35): devuelve los IDs de vacantes donde
  /// el egresado ya tiene una postulación activa o en curso (no retirada).
  Future<Set<String>> obtenerVacantesPostuladasIds(String accessToken) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}/postulaciones/');

    final http.Response respuesta;
    try {
      respuesta = await obtener(uri, accessToken: accessToken, client: _client);
    } on ApiException catch (e) {
      throw PostulacionException(e.mensaje, esErrorDeConexion: true);
    }

    if (respuesta.statusCode != 200) {
      throw PostulacionException(
        mensajeDeError(respuesta, 'No se pudo verificar tus postulaciones existentes.'),
      );
    }

    final items = decodificar(respuesta) as List<dynamic>? ?? const [];
    final ids = <String>{};
    for (final item in items) {
      if (item is Map<String, dynamic>) {
        final estado = (item['current_status'] as String? ?? '').toLowerCase();
        final jobId = item['job_id']?.toString();
        if (jobId != null && jobId.isNotEmpty && estado != 'withdrawn') {
          ids.add(jobId);
        }
      }
    }
    return ids;
  }

  Future<ResumenPostulaciones> obtenerMisPostulaciones(String accessToken) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}/postulaciones/mis-postulaciones');

    final http.Response respuesta;
    try {
      respuesta = await obtener(uri, accessToken: accessToken, client: _client);
    } on ApiException catch (e) {
      throw PostulacionException(e.mensaje, esErrorDeConexion: true);
    }

    if (respuesta.statusCode == 200) {
      return ResumenPostulaciones.fromJson(decodificar(respuesta) as Map<String, dynamic>);
    }

    throw PostulacionException(mensajeDeError(respuesta, 'No se pudieron cargar tus postulaciones.'));
  }

  Future<DetallePostulacion> obtenerDetalle(String accessToken, String postulacionId) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}/postulaciones/$postulacionId');

    final http.Response respuesta;
    try {
      respuesta = await obtener(uri, accessToken: accessToken, client: _client);
    } on ApiException catch (e) {
      throw PostulacionException(e.mensaje, esErrorDeConexion: true);
    }

    if (respuesta.statusCode == 200) {
      return DetallePostulacion.fromJson(decodificar(respuesta) as Map<String, dynamic>);
    }

    throw PostulacionException(mensajeDeError(respuesta, 'No se pudo cargar el detalle de la postulación.'));
  }

  Future<void> retirar(String accessToken, String postulacionId, {String? motivo}) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}/postulaciones/$postulacionId/retirar');

    final http.Response respuesta;
    try {
      respuesta = await enviar(
        uri,
        accessToken: accessToken,
        cuerpo: {'motivo': motivo},
        client: _client,
      );
    } on ApiException catch (e) {
      throw PostulacionException(e.mensaje, esErrorDeConexion: true);
    }

    if (respuesta.statusCode == 200) return;

    throw PostulacionException(mensajeDeError(respuesta, 'No se pudo retirar la postulación.'));
  }
}
