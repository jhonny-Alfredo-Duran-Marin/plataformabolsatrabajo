import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/pregunta_filtro.dart';
import '../models/vacante.dart';
import 'api_config.dart';

/// Excepción con el mensaje de error legible que ya devuelve el backend.
class VacanteException implements Exception {
  final String mensaje;
  const VacanteException(this.mensaje);

  @override
  String toString() => mensaje;
}

/// Consume GET /vacantes (backend/app/features/vacantes/router.py::listar_vacantes_publicas),
/// el mismo endpoint que usa el buscador web. Requiere estar autenticado
/// (cualquier rol), sin mocks: es la misma Supabase compartida.
class VacanteService {
  Future<List<Vacante>> listarPublicadas(String accessToken) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}/vacantes?page=1&page_size=20');

    late final http.Response respuesta;
    try {
      respuesta = await http
          .get(uri, headers: {'Authorization': 'Bearer $accessToken'})
          .timeout(const Duration(seconds: 15));
    } catch (_) {
      throw const VacanteException(
        'No se pudo conectar con el servidor. Verificá que el backend esté corriendo y la URL configurada.',
      );
    }

    final cuerpo = jsonDecode(respuesta.body);

    if (respuesta.statusCode == 200) {
      final items = (cuerpo as Map<String, dynamic>)['items'] as List<dynamic>;
      return items.map((e) => Vacante.fromJson(e as Map<String, dynamic>)).toList();
    }

    final detalle = (cuerpo as Map<String, dynamic>)['detail'];
    final mensaje = detalle is String ? detalle : 'No se pudieron cargar las vacantes.';
    throw VacanteException(mensaje);
  }

  /// Consume GET /vacantes/buscar (HU-13): búsqueda por palabra clave y
  /// ordenamiento por afinidad calculada según carrera/habilidades del
  /// egresado autenticado.
  Future<List<Vacante>> buscar(
    String accessToken, {
    String? q,
    String ordenarPor = 'fecha',
  }) async {
    final params = <String, String>{
      'ordenar_por': ordenarPor,
      'limit': '30',
    };
    if (q != null && q.trim().isNotEmpty) params['q'] = q.trim();

    final uri = Uri.parse('${ApiConfig.baseUrl}/vacantes/buscar').replace(queryParameters: params);

    late final http.Response respuesta;
    try {
      respuesta = await http
          .get(uri, headers: {'Authorization': 'Bearer $accessToken'})
          .timeout(const Duration(seconds: 15));
    } catch (_) {
      throw const VacanteException(
        'No se pudo conectar con el servidor. Verificá que el backend esté corriendo y la URL configurada.',
      );
    }

    final cuerpo = jsonDecode(respuesta.body);

    if (respuesta.statusCode == 200) {
      final items = (cuerpo as Map<String, dynamic>)['items'] as List<dynamic>;
      return items.map((e) => Vacante.fromJson(e as Map<String, dynamic>)).toList();
    }

    final detalle = (cuerpo as Map<String, dynamic>)['detail'];
    final mensaje = detalle is String ? detalle : 'No se pudieron buscar las vacantes.';
    throw VacanteException(mensaje);
  }

  /// Consume GET /vacantes/{id}/preguntas: preguntas de filtro configuradas
  /// por la empresa, que el egresado debe responder al postularse (HU-14).
  Future<List<PreguntaFiltro>> obtenerPreguntas(String accessToken, String vacanteId) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}/vacantes/$vacanteId/preguntas');

    late final http.Response respuesta;
    try {
      respuesta = await http
          .get(uri, headers: {'Authorization': 'Bearer $accessToken'})
          .timeout(const Duration(seconds: 15));
    } catch (_) {
      throw const VacanteException(
        'No se pudo conectar con el servidor. Verificá que el backend esté corriendo y la URL configurada.',
      );
    }

    if (respuesta.statusCode == 200) {
      final items = jsonDecode(respuesta.body) as List<dynamic>;
      return items.map((e) => PreguntaFiltro.fromJson(e as Map<String, dynamic>)).toList();
    }

    throw const VacanteException('No se pudieron cargar las preguntas de la vacante.');
  }
}
