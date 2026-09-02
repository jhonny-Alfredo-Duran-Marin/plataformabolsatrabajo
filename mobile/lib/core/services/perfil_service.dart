import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/perfil_egresado.dart';
import 'api_config.dart';

class PerfilException implements Exception {
  final String mensaje;
  const PerfilException(this.mensaje);

  @override
  String toString() => mensaje;
}

/// Consume GET /perfiles/me (backend/app/features/perfil/router.py), el
/// mismo endpoint que usa el frontend web para el panel del egresado.
class PerfilService {
  Future<PerfilEgresado> obtenerMiPerfil(String accessToken) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}/perfiles/me');

    late final http.Response respuesta;
    try {
      respuesta = await http
          .get(uri, headers: {'Authorization': 'Bearer $accessToken'})
          .timeout(const Duration(seconds: 15));
    } catch (_) {
      throw const PerfilException(
        'No se pudo conectar con el servidor. Verificá que el backend esté corriendo y la URL configurada.',
      );
    }

    final cuerpo = jsonDecode(respuesta.body) as Map<String, dynamic>;

    if (respuesta.statusCode == 200) {
      return PerfilEgresado.fromJson(cuerpo);
    }

    final detalle = cuerpo['detail'];
    final mensaje = detalle is String ? detalle : 'No se pudo cargar el perfil.';
    throw PerfilException(mensaje);
  }
}
