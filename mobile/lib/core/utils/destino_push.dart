import 'package:flutter/material.dart';

import '../models/notificacion.dart';

/// Tipo del aviso que el backend manda ante un cambio de estado de una postulación (HU-36).
const tipoEstadoPostulacion = 'application_status';

/// Id de la postulación a partir del enlace del aviso (`/postulaciones?id=<id>`), o null si no es uno.
String? postulacionIdDesdeEnlace(String? enlace) {
  if (enlace == null || enlace.isEmpty) return null;
  final uri = Uri.tryParse(enlace);
  if (uri == null || uri.path != '/postulaciones') return null;
  final id = uri.queryParameters['id'];
  return (id == null || id.isEmpty) ? null : id;
}

/// Id de la postulación que indica el payload `data` de un push. Solo los push de cambio de estado
/// (`tipo=application_status`) abren el detalle; el resto de los avisos siguen como estaban.
String? postulacionIdDesdePush(Map<String, dynamic> data) {
  if (data['tipo'] != tipoEstadoPostulacion) return null;
  final id = data['postulacion_id']?.toString();
  if (id != null && id.isNotEmpty) return id;
  return postulacionIdDesdeEnlace(data['link']?.toString());
}

/// Id de la postulación que abre un aviso de la campanita, o null si ese aviso no lleva a una.
String? postulacionIdDeAviso(Notificacion aviso) =>
    aviso.notificationType == tipoEstadoPostulacion ? postulacionIdDesdeEnlace(aviso.link) : null;

typedef AbrirPostulacion = void Function(String accessToken, String postulacionId);

/// Decide cuándo abrir el detalle de la postulación de un push tocado (HU-36).
///
/// Con sesión iniciada lo abre al instante; sin sesión (la app no la guarda: al abrirse en frío
/// empieza en el login) deja el destino pendiente y lo abre al iniciar sesión.
class GestorDestinoPush {
  GestorDestinoPush(this._abrir);

  final AbrirPostulacion _abrir;
  String? _accessToken;
  String? _pendiente;

  /// Destino que espera a que el egresado inicie sesión.
  String? get pendiente => _pendiente;

  /// El egresado inició sesión: si había un destino pendiente, se abre.
  void iniciarSesion(String accessToken) {
    _accessToken = accessToken;
    _abrirPendiente();
  }

  void cerrarSesion() => _accessToken = null;

  /// El egresado tocó un push (con la app en segundo plano o cerrada).
  void alTocar(Map<String, dynamic> data) {
    final id = postulacionIdDesdePush(data);
    if (id == null) return;
    _pendiente = id;
    _abrirPendiente();
  }

  /// El egresado pulsó «Ver» en el aviso con la app abierta.
  void abrirAhora(String postulacionId) {
    _pendiente = postulacionId;
    _abrirPendiente();
  }

  void _abrirPendiente() {
    final id = _pendiente;
    final acceso = _accessToken;
    if (id == null || acceso == null) return;
    _pendiente = null;
    _abrir(acceso, id);
  }
}

/// Aviso en primer plano de un push. Si es de una postulación, ofrece la acción «Ver».
SnackBar snackBarDeAviso({
  required String titulo,
  required String cuerpo,
  required Map<String, dynamic> data,
  required void Function(String postulacionId) alVer,
}) {
  final id = postulacionIdDesdePush(data);
  return SnackBar(
    content: Text(cuerpo.isEmpty ? titulo : '$titulo\n$cuerpo'),
    duration: const Duration(seconds: 6),
    action: id == null ? null : SnackBarAction(label: 'Ver', onPressed: () => alVer(id)),
  );
}
