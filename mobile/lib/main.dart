import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'core/services/api_http.dart';
import 'core/services/push_service.dart';
import 'core/theme/app_theme.dart';
import 'features/auth/login_screen.dart';

/// Para volver al login desde fuera de una pantalla (cuando vence la sesión).
final navegadorGlobal = GlobalKey<NavigatorState>();
bool _volviendoAlLogin = false;

/// La sesión venció: se deja de recibir push de esa cuenta y se vuelve al login una sola vez,
/// aunque varias pantallas reciban el 401 a la vez.
void _sesionVencida() {
  if (_volviendoAlLogin) return;
  _volviendoAlLogin = true;
  unawaited(PushService.instancia.desactivar());
  navegadorGlobal.currentState?.pushAndRemoveUntil(
    MaterialPageRoute(builder: (_) => const LoginScreen()),
    (_) => false,
  );
  mensajeroGlobal.currentState?.showSnackBar(
    const SnackBar(content: Text('Tu sesión expiró. Iniciá sesión de nuevo.')),
  );
  Future.delayed(const Duration(seconds: 3), () => _volviendoAlLogin = false);
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await PushService.inicializarFirebase();
  alVencerLaSesion = _sesionVencida;
  runApp(const EgresaApp());
}

class EgresaApp extends StatelessWidget {
  const EgresaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'EGRESA',
      debugShowCheckedModeBanner: false,
      scaffoldMessengerKey: mensajeroGlobal,
      navigatorKey: navegadorGlobal,
      theme: AppTheme.claro(),
      locale: const Locale('es'),
      supportedLocales: const [Locale('es')],
      localizationsDelegates: GlobalMaterialLocalizations.delegates,
      // Android dibuja la app detrás de la barra de navegación del sistema:
      // se reserva ese espacio para que no tape el final de las pantallas.
      builder: (context, child) => AnnotatedRegion<SystemUiOverlayStyle>(
        value: AppTheme.barrasSistema,
        child: ColoredBox(
          color: AppColors.superficie,
          child: SafeArea(top: false, left: false, right: false, child: child!),
        ),
      ),
      home: const LoginScreen(),
    );
  }
}
