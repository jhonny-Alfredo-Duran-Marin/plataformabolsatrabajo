import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/postulacion.dart';
import 'api_config.dart';

/// Excepción con el mensaje de error legible que ya devuelve el backend.
class PostulacionException implements Exception {
  final String mensaje;
  const PostulacionException(this.mensaje);

  @override
  String toString() => mensaje;
}

/// Respuesta puntual de una postulación, tal como devuelve POST /postulaciones/
/// (incluye si fue descartada automáticamente por una pregunta eliminatoria).
class ResultadoPostulacion {
  final String currentStatus;
  final String message;
  const ResultadoPostulacion({required this.currentStatus, required this.message});
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
/// el mismo API que usa el frontend web, sin mocks.
class PostulacionService {
  Future<ResultadoPostulacion> postular(
    String accessToken,
    String jobId,
    List<RespuestaPregunta> respuestas,
  ) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}/postulaciones/');

    late final http.Response respuesta;
    try {
      respuesta = await http
          .post(
            uri,
            headers: {
              'Authorization': 'Bearer $accessToken',
              'Content-Type': 'application/json',
            },
            body: jsonEncode({
              'job_id': jobId,
              'answers': respuestas.map((r) => r.toJson()).toList(),
            }),
          )
          .timeout(const Duration(seconds: 15));
    } catch (_) {
      throw const PostulacionException(
        'No se pudo conectar con el servidor. Verificá que el backend esté corriendo y la URL configurada.',
      );
    }

    final cuerpo = jsonDecode(respuesta.body) as Map<String, dynamic>;

    if (respuesta.statusCode == 200) {
      return ResultadoPostulacion(
        currentStatus: cuerpo['current_status'] as String,
        message: cuerpo['message'] as String? ?? 'Postulación exitosa',
      );
    }

    final detalle = cuerpo['detail'];
    final mensaje = detalle is String ? detalle : 'No se pudo completar la postulación.';
    throw PostulacionException(mensaje);
  }

  Future<ResumenPostulaciones> obtenerMisPostulaciones(String accessToken) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}/postulaciones/mis-postulaciones');

    late final http.Response respuesta;
    try {
      respuesta = await http
          .get(uri, headers: {'Authorization': 'Bearer $accessToken'})
          .timeout(const Duration(seconds: 15));
    } catch (_) {
      throw const PostulacionException(
        'No se pudo conectar con el servidor. Verificá que el backend esté corriendo y la URL configurada.',
      );
    }

    if (respuesta.statusCode == 200) {
      return ResumenPostulaciones.fromJson(jsonDecode(respuesta.body) as Map<String, dynamic>);
    }

    throw const PostulacionException('No se pudieron cargar tus postulaciones.');
  }

  Future<DetallePostulacion> obtenerDetalle(String accessToken, String postulacionId) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}/postulaciones/$postulacionId');

    late final http.Response respuesta;
    try {
      respuesta = await http
          .get(uri, headers: {'Authorization': 'Bearer $accessToken'})
          .timeout(const Duration(seconds: 15));
    } catch (_) {
      throw const PostulacionException(
        'No se pudo conectar con el servidor. Verificá que el backend esté corriendo y la URL configurada.',
      );
    }

    if (respuesta.statusCode == 200) {
      return DetallePostulacion.fromJson(jsonDecode(respuesta.body) as Map<String, dynamic>);
    }

    throw const PostulacionException('No se pudo cargar el detalle de la postulación.');
  }

  Future<void> retirar(String accessToken, String postulacionId, {String? motivo}) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}/postulaciones/$postulacionId/retirar');

    late final http.Response respuesta;
    try {
      respuesta = await http
          .post(
            uri,
            headers: {
              'Authorization': 'Bearer $accessToken',
              'Content-Type': 'application/json',
            },
            body: jsonEncode({'motivo': motivo}),
          )
          .timeout(const Duration(seconds: 15));
    } catch (_) {
      throw const PostulacionException(
        'No se pudo conectar con el servidor. Verificá que el backend esté corriendo y la URL configurada.',
      );
    }

    if (respuesta.statusCode == 200) return;

    final cuerpo = jsonDecode(respuesta.body) as Map<String, dynamic>;
    final detalle = cuerpo['detail'];
    final mensaje = detalle is String ? detalle : 'No se pudo retirar la postulación.';
    throw PostulacionException(mensaje);
  }
}
