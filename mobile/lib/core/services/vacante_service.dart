import '../models/estadisticas_publicas.dart';
import '../models/pregunta_filtro.dart';
import '../models/vacante.dart';
import 'api_config.dart';
import 'api_http.dart';

/// Vacantes publicadas (backend/app/features/vacantes/router.py), las mismas
/// rutas que usa el buscador web.
class VacanteService {
  /// GET /vacantes/buscar (HU-13). Sin [accessToken] es la búsqueda pública de la
  /// HU-34: todas las vacantes vigentes y sin afinidad. El egresado autenticado
  /// ve solo las de empresas habilitadas en su universidad, con su afinidad.
  Future<List<Vacante>> buscar(String? accessToken, {String? q, String ordenarPor = 'fecha'}) async {
    final params = <String, String>{'ordenar_por': ordenarPor, 'limit': '30'};
    if (q != null && q.trim().isNotEmpty) params['q'] = q.trim();

    final respuesta = await obtener(
      Uri.parse('${ApiConfig.baseUrl}/vacantes/buscar').replace(queryParameters: params),
      accessToken: accessToken,
    );
    if (respuesta.statusCode != 200) {
      throw ApiException(mensajeDeError(respuesta, 'No se pudieron cargar las vacantes.'), codigo: respuesta.statusCode);
    }
    final items = (decodificar(respuesta) as Map<String, dynamic>)['items'] as List<dynamic>;
    return items.map((e) => Vacante.fromJson(e as Map<String, dynamic>)).toList();
  }

  /// GET /search/semantic (HU-25): Búsqueda Semántica de Vacantes con IA.
  /// Interpreta lenguaje natural, evalúa relevancia semántica (0-100) y explicabilidad.
  Future<BusquedaSemanticaResultado> buscarSemantica(
    String? accessToken, {
    required String consulta,
    String? ciudad,
    String? modalidad,
    int limit = 30,
  }) async {
    final params = <String, String>{
      'q': consulta.trim(),
      'limit': limit.toString(),
    };
    if (ciudad != null && ciudad.trim().isNotEmpty) params['ciudad'] = ciudad.trim();
    if (modalidad != null && modalidad.trim().isNotEmpty) params['modalidad'] = modalidad.trim();

    final respuesta = await obtener(
      Uri.parse('/search/semantic').replace(queryParameters: params),
      accessToken: accessToken,
    );
    if (respuesta.statusCode != 200) {
      throw ApiException(
        mensajeDeError(respuesta, 'No se pudo completar la búsqueda semántica.'),
        codigo: respuesta.statusCode,
      );
    }
    final data = decodificar(respuesta) as Map<String, dynamic>;
    final itemsJson = (data['items'] as List<dynamic>? ?? []);
    final items = itemsJson.map((e) => Vacante.fromJson(e as Map<String, dynamic>)).toList();
    final sugerencias = (data['sugerencias'] as List<dynamic>? ?? []).map((e) => e.toString()).toList();
    final iaDisponible = data['ia_disponible'] as bool? ?? true;

    return BusquedaSemanticaResultado(
      items: items,
      total: data['total'] as int? ?? items.length,
      sugerencias: sugerencias,
      iaDisponible: iaDisponible,
    );
  }

  /// GET /vacantes/estadisticas-publicas (HU-34): no requiere sesión.
  Future<EstadisticasPublicas> estadisticasPublicas() async {
    final respuesta = await obtener(Uri.parse('${ApiConfig.baseUrl}/vacantes/estadisticas-publicas'));
    if (respuesta.statusCode != 200) {
      throw ApiException(mensajeDeError(respuesta, 'No se pudieron cargar las estadísticas.'));
    }
    return EstadisticasPublicas.fromJson(decodificar(respuesta) as Map<String, dynamic>);
  }

  /// GET /vacantes/{id}/preguntas: preguntas de filtro configuradas por la
  /// empresa, que el egresado debe responder al postularse (HU-14).
  Future<List<PreguntaFiltro>> obtenerPreguntas(String accessToken, String vacanteId) async {
    final respuesta = await obtener(
      Uri.parse('${ApiConfig.baseUrl}/vacantes/$vacanteId/preguntas'),
      accessToken: accessToken,
    );
    if (respuesta.statusCode != 200) {
      throw ApiException(mensajeDeError(respuesta, 'No se pudieron cargar las preguntas de la vacante.'));
    }
    return (decodificar(respuesta) as List<dynamic>)
        .map((e) => PreguntaFiltro.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}


/// Resultado de búsqueda semántica con IA (HU-25).
class BusquedaSemanticaResultado {
  final List<Vacante> items;
  final int total;
  final List<String> sugerencias;
  final bool iaDisponible;

  const BusquedaSemanticaResultado({
    required this.items,
    required this.total,
    this.sugerencias = const [],
    this.iaDisponible = true,
  });
}
