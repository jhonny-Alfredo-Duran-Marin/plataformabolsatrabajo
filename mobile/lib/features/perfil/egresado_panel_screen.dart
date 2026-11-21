import 'package:flutter/material.dart';

import '../../core/models/sesion.dart';
import '../../core/services/push_service.dart';
import '../../core/theme/app_theme.dart';
import '../auth/login_screen.dart';
import '../inicio/inicio_tab.dart';
import '../postulaciones/mis_postulaciones_screen.dart';
import '../vacantes/vacantes_screen.dart';
import 'perfil_tab.dart';

/// Contenedor principal del egresado: barra inferior con Inicio, Vacantes,
/// Postulaciones y Perfil. Guarda la sesión, que cambia si el egresado
/// cambia su contraseña (el backend emite tokens nuevos).
class EgresadoPanelScreen extends StatefulWidget {
  final Sesion sesion;

  const EgresadoPanelScreen({super.key, required this.sesion});

  @override
  State<EgresadoPanelScreen> createState() => _EgresadoPanelScreenState();
}

class _EgresadoPanelScreenState extends State<EgresadoPanelScreen> {
  static const _inicio = 0;
  static const _vacantes = 1;

  late Sesion _sesion = widget.sesion;
  int _indice = _inicio;

  /// Cambia cuando el backend emite tokens nuevos: recrea todas las pestañas.
  int _versionSesion = 0;

  /// Las pestañas se construyen recién la primera vez que se visitan, para no
  /// disparar todas las consultas al abrir la app.
  final _visitadas = {_inicio};

  /// Al volver a Inicio, Postulaciones o Perfil se recargan, para mostrar por
  /// ejemplo una postulación recién enviada. Vacantes conserva la búsqueda.
  final _versiones = [0, 0, 0, 0];

  @override
  void initState() {
    super.initState();
    PushService.instancia.activar(_sesion.accessToken);
    // HU-36: si el egresado entró tocando un push, se abre ese detalle apenas termina de armarse el panel.
    final acceso = _sesion.accessToken;
    WidgetsBinding.instance.addPostFrameCallback((_) => PushService.instancia.destinos.iniciarSesion(acceso));
  }

  void _irA(int indice) {
    setState(() {
      if (!_visitadas.add(indice) && indice != _indice && indice != _vacantes) _versiones[indice]++;
      _indice = indice;
    });
  }

  void _cerrarSesion() {
    PushService.instancia.desactivar();
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const LoginScreen()),
      (_) => false,
    );
  }

  Key _clave(String nombre, int indice) => ValueKey('$nombre-${_versiones[indice]}-$_versionSesion');

  Widget _siVisitada(int indice, Widget pestana) => _visitadas.contains(indice) ? pestana : const SizedBox.shrink();

  @override
  Widget build(BuildContext context) {
    final token = _sesion.accessToken;
    return PopScope(
      // El botón atrás de Android vuelve primero a Inicio en vez de cerrar la app.
      canPop: _indice == _inicio,
      onPopInvokedWithResult: (seCerro, _) {
        if (!seCerro) _irA(_inicio);
      },
      child: Scaffold(
        body: IndexedStack(
          index: _indice,
          children: [
            InicioTab(key: _clave('inicio', 0), sesion: _sesion, onIrA: _irA),
            _siVisitada(1, VacantesScreen(key: ValueKey('vacantes-$_versionSesion'), accessToken: token)),
            _siVisitada(2, MisPostulacionesScreen(key: _clave('postulaciones', 2), accessToken: token)),
            _siVisitada(
              3,
              PerfilTab(
                key: _clave('perfil', 3),
                sesion: _sesion,
                onSesionActualizada: (nueva) {
                  setState(() {
                    _sesion = nueva;
                    _versionSesion++;
                  });
                  // Tokens nuevos tras cambiar la contraseña: el registro del celular sigue a la sesión.
                  PushService.instancia.activar(nueva.accessToken);
                },
                onCerrarSesion: _cerrarSesion,
              ),
            ),
          ],
        ),
        bottomNavigationBar: DecoratedBox(
          decoration: const BoxDecoration(border: Border(top: BorderSide(color: AppColors.borde))),
          child: NavigationBar(
            selectedIndex: _indice,
            onDestinationSelected: _irA,
            destinations: const [
              NavigationDestination(
                icon: Icon(Icons.space_dashboard_outlined),
                selectedIcon: Icon(Icons.space_dashboard_rounded),
                label: 'Inicio',
              ),
              NavigationDestination(
                icon: Icon(Icons.work_outline_rounded),
                selectedIcon: Icon(Icons.work_rounded),
                label: 'Vacantes',
              ),
              NavigationDestination(
                icon: Icon(Icons.assignment_outlined),
                selectedIcon: Icon(Icons.assignment_rounded),
                label: 'Postulaciones',
              ),
              NavigationDestination(
                icon: Icon(Icons.person_outline_rounded),
                selectedIcon: Icon(Icons.person_rounded),
                label: 'Perfil',
              ),
            ],
          ),
        ),
      ),
    );
  }
}
