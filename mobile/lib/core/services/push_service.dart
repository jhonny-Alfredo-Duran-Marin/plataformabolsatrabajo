import 'dart:async';
import 'dart:io' show Platform;

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart' show debugPrint, kIsWeb;
import 'package:flutter/material.dart';

import '../firebase_options.dart';
import 'api_config.dart';
import 'api_http.dart';

/// Para mostrar avisos desde fuera de una pantalla (los push con la app abierta).
final mensajeroGlobal = GlobalKey<ScaffoldMessengerState>();

/// Avisos push con Firebase Cloud Messaging (HU-21). Con la app cerrada o en segundo
/// plano, Android muestra el aviso solo; con la app abierta se muestra un SnackBar.
class PushService {
  PushService._();
  static final instancia = PushService._();

  static bool get _disponible => !kIsWeb && Platform.isAndroid;

  String? _accessToken;
  String? _token;
  StreamSubscription<String>? _renovacion;
  StreamSubscription<RemoteMessage>? _primerPlano;

  /// Se llama una vez al abrir la app. Si falla, la app sigue funcionando sin push.
  static Future<void> inicializarFirebase() async {
    if (!_disponible) return;
    try {
      await Firebase.initializeApp(options: opcionesFirebaseAndroid);
    } catch (e) {
      debugPrint('Firebase no se pudo inicializar: $e');
    }
  }

  /// Al entrar con una cuenta: pide el permiso la primera vez (Android 13+) y
  /// registra el token del celular para esa cuenta.
  Future<void> activar(String accessToken) async {
    if (!_disponible || Firebase.apps.isEmpty) return;
    _accessToken = accessToken;
    try {
      final mensajeria = FirebaseMessaging.instance;
      final ajustes = await mensajeria.requestPermission();
      if (ajustes.authorizationStatus == AuthorizationStatus.denied) return;
      final token = await mensajeria.getToken();
      if (token != null) await _registrar(token);
      _renovacion ??= mensajeria.onTokenRefresh.listen(_registrar);
      _primerPlano ??= FirebaseMessaging.onMessage.listen(_mostrarEnPrimerPlano);
    } catch (e) {
      // Sin Google Play Services o sin conexión: la campana de la app sigue funcionando.
      debugPrint('No se pudieron activar los avisos push: $e');
    }
  }

  Future<void> _registrar(String token) async {
    final acceso = _accessToken;
    if (acceso == null) return;
    // También lo llama onTokenRefresh: un error acá no puede quedar suelto (cerraría la app en
    // modo debug) y el token nuevo se vuelve a registrar en el próximo activar().
    try {
      final respuesta = await enviar(
        Uri.parse('${ApiConfig.baseUrl}/notificaciones/fcm/registrar-token'),
        accessToken: acceso,
        cuerpo: {'fcm_token': token, 'device_type': 'android', 'device_name': 'App Android'},
      );
      if (respuesta.statusCode == 200) {
        _token = token;
      } else {
        debugPrint('No se pudo registrar el token de avisos push (${respuesta.statusCode}).');
      }
    } catch (e) {
      debugPrint('No se pudo registrar el token de avisos push: $e');
    }
  }

  void _mostrarEnPrimerPlano(RemoteMessage mensaje) {
    final titulo = mensaje.notification?.title ?? mensaje.data['title'] as String? ?? 'EGRESA';
    final cuerpo = mensaje.notification?.body ?? mensaje.data['body'] as String? ?? '';
    mensajeroGlobal.currentState?.showSnackBar(
      SnackBar(
        content: Text(cuerpo.isEmpty ? titulo : '$titulo\n$cuerpo'),
        duration: const Duration(seconds: 6),
      ),
    );
  }

  /// Al cerrar sesión: el celular deja de recibir los avisos de esa cuenta.
  Future<void> desactivar() async {
    final acceso = _accessToken;
    final token = _token;
    _accessToken = null;
    _token = null;
    await _renovacion?.cancel();
    _renovacion = null;
    await _primerPlano?.cancel();
    _primerPlano = null;
    if (acceso == null || token == null) return;
    try {
      await enviar(
        Uri.parse('${ApiConfig.baseUrl}/notificaciones/fcm/eliminar-token'),
        accessToken: acceso,
        cuerpo: {'fcm_token': token},
      );
    } catch (_) {
      // Sin conexión: el token queda registrado y se reasigna al próximo que entre.
    }
  }
}
