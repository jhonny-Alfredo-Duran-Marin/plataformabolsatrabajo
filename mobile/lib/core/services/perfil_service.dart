import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/cv_item.dart';
import '../models/perfil_egresado.dart';
import 'api_config.dart';

class PerfilException implements Exception {
  final String mensaje;
  const PerfilException(this.mensaje);

  @override
  String toString() => mensaje;
}

/// Consume /perfiles/me y sus subrecursos (backend/app/features/perfil/router.py),
/// los mismos endpoints que usa el frontend web para el panel del egresado.
class PerfilService {
  Uri _uri(String path) => Uri.parse('${ApiConfig.baseUrl}/perfiles/me$path');

  Map<String, String> _headers(String accessToken, {bool conJson = false}) => {
        'Authorization': 'Bearer $accessToken',
        if (conJson) 'Content-Type': 'application/json',
      };

  Future<http.Response> _enviar(
    Future<http.Response> Function() peticion,
  ) async {
    try {
      return await peticion().timeout(const Duration(seconds: 15));
    } catch (_) {
      throw const PerfilException(
        'No se pudo conectar con el servidor. Verificá que el backend esté corriendo y la URL configurada.',
      );
    }
  }

  Never _lanzarError(http.Response respuesta, String mensajePorDefecto) {
    dynamic cuerpo;
    try {
      cuerpo = jsonDecode(respuesta.body);
    } catch (_) {
      cuerpo = null;
    }
    final detalle = cuerpo is Map<String, dynamic> ? cuerpo['detail'] : null;
    throw PerfilException(detalle is String ? detalle : mensajePorDefecto);
  }

  // ─── Perfil básico ───────────────────────────────────────────────

  Future<PerfilEgresado> obtenerMiPerfil(String accessToken) async {
    final respuesta = await _enviar(
      () => http.get(_uri(''), headers: _headers(accessToken)),
    );
    if (respuesta.statusCode == 200) {
      return PerfilEgresado.fromJson(jsonDecode(respuesta.body) as Map<String, dynamic>);
    }
    _lanzarError(respuesta, 'No se pudo cargar el perfil.');
  }

  Future<PerfilEgresado> actualizarMiPerfil(
    String accessToken, {
    String? telefono,
    String? disponibilidad,
    String? tituloProfesional,
    String? resumenProfesional,
    String? ciudad,
    int? anioEgreso,
    String? matricula,
  }) async {
    final body = <String, dynamic>{
      if (telefono != null) 'telefono': telefono,
      if (disponibilidad != null) 'disponibilidad': disponibilidad,
      if (tituloProfesional != null) 'titulo_profesional': tituloProfesional,
      if (resumenProfesional != null) 'resumen_profesional': resumenProfesional,
      if (ciudad != null) 'ciudad': ciudad,
      if (anioEgreso != null) 'anio_egreso': anioEgreso,
      if (matricula != null) 'matricula': matricula,
    };
    final respuesta = await _enviar(
      () => http.patch(_uri(''), headers: _headers(accessToken, conJson: true), body: jsonEncode(body)),
    );
    if (respuesta.statusCode == 200) {
      return PerfilEgresado.fromJson(jsonDecode(respuesta.body) as Map<String, dynamic>);
    }
    _lanzarError(respuesta, 'No se pudo actualizar el perfil.');
  }

  // ─── Formación ───────────────────────────────────────────────────

  Future<List<Formacion>> listarFormacion(String accessToken) async {
    final respuesta = await _enviar(() => http.get(_uri('/formacion'), headers: _headers(accessToken)));
    if (respuesta.statusCode == 200) {
      return (jsonDecode(respuesta.body) as List).map((e) => Formacion.fromJson(e)).toList();
    }
    _lanzarError(respuesta, 'No se pudo cargar la formación académica.');
  }

  Future<Formacion> crearFormacion(
    String accessToken, {
    required String institucion,
    required String programa,
    String? estadoAcademico,
  }) async {
    final body = {
      'institucion': institucion,
      'programa': programa,
      if (estadoAcademico != null) 'estado_academico': estadoAcademico,
    };
    final respuesta = await _enviar(
      () => http.post(_uri('/formacion'), headers: _headers(accessToken, conJson: true), body: jsonEncode(body)),
    );
    if (respuesta.statusCode == 201) {
      return Formacion.fromJson(jsonDecode(respuesta.body) as Map<String, dynamic>);
    }
    _lanzarError(respuesta, 'No se pudo agregar la formación académica.');
  }

  Future<void> eliminarFormacion(String accessToken, String id) async {
    final respuesta = await _enviar(() => http.delete(_uri('/formacion/$id'), headers: _headers(accessToken)));
    if (respuesta.statusCode != 204) {
      _lanzarError(respuesta, 'No se pudo eliminar la formación académica.');
    }
  }

  // ─── Experiencia ─────────────────────────────────────────────────

  Future<List<Experiencia>> listarExperiencia(String accessToken) async {
    final respuesta = await _enviar(() => http.get(_uri('/experiencia'), headers: _headers(accessToken)));
    if (respuesta.statusCode == 200) {
      return (jsonDecode(respuesta.body) as List).map((e) => Experiencia.fromJson(e)).toList();
    }
    _lanzarError(respuesta, 'No se pudo cargar la experiencia laboral.');
  }

  Future<Experiencia> crearExperiencia(
    String accessToken, {
    required String empresa,
    required String cargo,
    String? descripcion,
  }) async {
    final body = {
      'empresa': empresa,
      'cargo': cargo,
      if (descripcion != null) 'descripcion': descripcion,
    };
    final respuesta = await _enviar(
      () => http.post(_uri('/experiencia'), headers: _headers(accessToken, conJson: true), body: jsonEncode(body)),
    );
    if (respuesta.statusCode == 201) {
      return Experiencia.fromJson(jsonDecode(respuesta.body) as Map<String, dynamic>);
    }
    _lanzarError(respuesta, 'No se pudo agregar la experiencia laboral.');
  }

  Future<void> eliminarExperiencia(String accessToken, String id) async {
    final respuesta = await _enviar(() => http.delete(_uri('/experiencia/$id'), headers: _headers(accessToken)));
    if (respuesta.statusCode != 204) {
      _lanzarError(respuesta, 'No se pudo eliminar la experiencia laboral.');
    }
  }

  // ─── Idiomas ─────────────────────────────────────────────────────

  Future<List<Idioma>> listarIdiomas(String accessToken) async {
    final respuesta = await _enviar(() => http.get(_uri('/idiomas'), headers: _headers(accessToken)));
    if (respuesta.statusCode == 200) {
      return (jsonDecode(respuesta.body) as List).map((e) => Idioma.fromJson(e)).toList();
    }
    _lanzarError(respuesta, 'No se pudieron cargar los idiomas.');
  }

  Future<Idioma> crearIdioma(String accessToken, {required String idioma, required String nivel}) async {
    final body = {'idioma': idioma, 'nivel': nivel};
    final respuesta = await _enviar(
      () => http.post(_uri('/idiomas'), headers: _headers(accessToken, conJson: true), body: jsonEncode(body)),
    );
    if (respuesta.statusCode == 201) {
      return Idioma.fromJson(jsonDecode(respuesta.body) as Map<String, dynamic>);
    }
    _lanzarError(respuesta, 'No se pudo agregar el idioma.');
  }

  Future<void> eliminarIdioma(String accessToken, String id) async {
    final respuesta = await _enviar(() => http.delete(_uri('/idiomas/$id'), headers: _headers(accessToken)));
    if (respuesta.statusCode != 204) {
      _lanzarError(respuesta, 'No se pudo eliminar el idioma.');
    }
  }

  // ─── Certificaciones ─────────────────────────────────────────────

  Future<List<Certificacion>> listarCertificaciones(String accessToken) async {
    final respuesta = await _enviar(() => http.get(_uri('/certificaciones'), headers: _headers(accessToken)));
    if (respuesta.statusCode == 200) {
      return (jsonDecode(respuesta.body) as List).map((e) => Certificacion.fromJson(e)).toList();
    }
    _lanzarError(respuesta, 'No se pudieron cargar las certificaciones.');
  }

  Future<Certificacion> crearCertificacion(
    String accessToken, {
    required String nombre,
    String? entidadEmisora,
  }) async {
    final body = {
      'nombre': nombre,
      if (entidadEmisora != null) 'entidad_emisora': entidadEmisora,
    };
    final respuesta = await _enviar(
      () =>
          http.post(_uri('/certificaciones'), headers: _headers(accessToken, conJson: true), body: jsonEncode(body)),
    );
    if (respuesta.statusCode == 201) {
      return Certificacion.fromJson(jsonDecode(respuesta.body) as Map<String, dynamic>);
    }
    _lanzarError(respuesta, 'No se pudo agregar la certificación.');
  }

  Future<void> eliminarCertificacion(String accessToken, String id) async {
    final respuesta = await _enviar(() => http.delete(_uri('/certificaciones/$id'), headers: _headers(accessToken)));
    if (respuesta.statusCode != 204) {
      _lanzarError(respuesta, 'No se pudo eliminar la certificación.');
    }
  }

  // ─── Habilidades ─────────────────────────────────────────────────

  Future<List<Habilidad>> listarHabilidades(String accessToken) async {
    final respuesta = await _enviar(() => http.get(_uri('/habilidades'), headers: _headers(accessToken)));
    if (respuesta.statusCode == 200) {
      return (jsonDecode(respuesta.body) as List).map((e) => Habilidad.fromJson(e)).toList();
    }
    _lanzarError(respuesta, 'No se pudieron cargar las habilidades.');
  }

  /// Reemplaza la lista completa de habilidades (PUT, según el backend).
  Future<List<Habilidad>> actualizarHabilidades(String accessToken, List<String> nombres) async {
    final respuesta = await _enviar(
      () => http.put(
        _uri('/habilidades'),
        headers: _headers(accessToken, conJson: true),
        body: jsonEncode({'habilidades': nombres}),
      ),
    );
    if (respuesta.statusCode == 200) {
      return (jsonDecode(respuesta.body) as List).map((e) => Habilidad.fromJson(e)).toList();
    }
    _lanzarError(respuesta, 'No se pudieron actualizar las habilidades.');
  }
}
