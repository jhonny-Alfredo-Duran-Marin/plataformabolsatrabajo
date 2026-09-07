import 'dart:io' show Platform;

import 'package:flutter/foundation.dart' show kIsWeb;

/// Resuelve la URL base de la API FastAPI según la plataforma en la que
/// corre la app. El emulador de Android no puede usar "localhost" para
/// llegar a la máquina host: necesita la IP especial 10.0.2.2.
class ApiConfig {
  ApiConfig._();

  /// Cambiá esto si el backend corre en otro host/puerto.
  static const String _hostLocal = '127.0.0.1:8000';

  /// IP de la PC en la red WiFi local, para probar desde un celular físico
  /// (el celular y la PC deben estar en la MISMA red WiFi). Actualizala si
  /// cambia la IP de tu PC (correr "ipconfig" y buscar "Dirección IPv4").
  static const String _hostRedLocal = '192.168.1.24:8000';

  /// true = compilando para probar en un celular físico por WiFi.
  /// false = emulador Android / Chrome / Windows en la misma PC del backend.
  static const bool _usarRedLocal = bool.fromEnvironment(
    'CELULAR_FISICO',
    defaultValue: false,
  );

  static String get baseUrl {
    if (_usarRedLocal) {
      return 'http://$_hostRedLocal/api';
    }
    if (kIsWeb) {
      return 'http://$_hostLocal/api';
    }
    if (Platform.isAndroid) {
      return 'http://10.0.2.2:8000/api';
    }
    return 'http://$_hostLocal/api';
  }
}
