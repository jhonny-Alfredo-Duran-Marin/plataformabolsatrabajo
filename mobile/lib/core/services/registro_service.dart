import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/carrera.dart';
import 'api_config.dart';
import 'auth_service.dart';

/// HU-01 — Registro de egresado (versión móvil).
/// Consume los mismos endpoints reales que usa el frontend web
/// (backend/app/features/auth/router.py y backend/app/features/catalogo/router.py).
class RegistroService {
  Future<List<Carrera>> listarCarreras() async {
    final uri = Uri.parse('${ApiConfig.baseUrl}/catalogos/carreras');

    late final http.Response respuesta;
    try {
      respuesta = await http.get(uri).timeout(const Duration(seconds: 15));
    } catch (_) {
      throw const AuthException('No se pudo cargar la lista de carreras. Verificá tu conexión.');
    }

    if (respuesta.statusCode != 200) {
      throw const AuthException('No se pudo cargar la lista de carreras.');
    }

    final lista = jsonDecode(respuesta.body) as List<dynamic>;
    return lista.map((e) => Carrera.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> registrarEgresado({
    required String nombres,
    required String apellidos,
    required String ci,
    required String correo,
    required String password,
    String? carreraId,
    int? anioEgreso,
    String? matricula,
  }) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}/auth/registro/egresado');

    late final http.Response respuesta;
    try {
      respuesta = await http
          .post(
            uri,
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'nombres': nombres,
              'apellidos': apellidos,
              'ci': ci,
              'correo': correo,
              'password': password,
              'carrera_id': carreraId,
              'anio_egreso': anioEgreso,
              'matricula': matricula,
            }),
          )
          .timeout(const Duration(seconds: 15));
    } catch (_) {
      throw const AuthException(
        'No se pudo conectar con el servidor. Verificá que el backend esté corriendo y la URL configurada.',
      );
    }

    if (respuesta.statusCode == 201) return;

    final cuerpo = jsonDecode(respuesta.body) as Map<String, dynamic>;
    final detalle = cuerpo['detail'];
    final mensaje = detalle is String ? detalle : 'Ocurrió un error inesperado al registrarte.';
    throw AuthException(mensaje);
  }
}
