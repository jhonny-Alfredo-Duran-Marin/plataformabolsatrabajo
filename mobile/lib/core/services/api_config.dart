import 'dart:io' show Platform;

import 'package:flutter/foundation.dart' show kIsWeb;

/// Resuelve la URL base de la API FastAPI según la plataforma en la que
/// corre la app. El emulador de Android no puede usar "localhost" para
/// llegar a la máquina host: necesita la IP especial 10.0.2.2.
class ApiConfig {
  ApiConfig._();

  /// Cambiá esto si el backend corre en otro host/puerto (por ejemplo,
  /// una IP de red local para probar en un celular físico).
  static const String _hostLocal = '127.0.0.1:8000';

  static String get baseUrl {
    if (kIsWeb) {
      return 'http://$_hostLocal/api';
    }
    if (Platform.isAndroid) {
      return 'http://10.0.2.2:8000/api';
    }
    return 'http://$_hostLocal/api';
  }
}
