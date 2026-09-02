import 'package:flutter/material.dart';

import '../../core/models/sesion.dart';
import '../perfil/egresado_panel_screen.dart';
import 'login_screen.dart';

/// Punto de entrada post-login: si el usuario es egresado, muestra su
/// panel real (perfil + accesos). Para el resto de roles (empresa,
/// moderador, admin) todavía no hay pantallas móviles dedicadas
/// (Sprint 4 según el roadmap), así que se muestra una vista informativa.
class HomeScreen extends StatelessWidget {
  final Sesion sesion;

  const HomeScreen({super.key, required this.sesion});

  String get _rolLegible {
    switch (sesion.rol) {
      case 'candidate':
        return 'Egresado';
      case 'empresa':
        return 'Empresa';
      case 'moderator':
        return 'Moderador';
      case 'platform_admin':
        return 'Administrador de plataforma';
      default:
        return sesion.rol;
    }
  }

  @override
  Widget build(BuildContext context) {
    if (sesion.rol == 'candidate') {
      return EgresadoPanelScreen(sesion: sesion);
    }
    return Scaffold(
      appBar: AppBar(
        title: const Text('EGRESA'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Cerrar sesión',
            onPressed: () {
              Navigator.of(context).pushReplacement(
                MaterialPageRoute(builder: (_) => const LoginScreen()),
              );
            },
          ),
        ],
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.check_circle, size: 64, color: Colors.green.shade600),
              const SizedBox(height: 16),
              Text(
                '¡Sesión iniciada!',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Text(
                'Rol: $_rolLegible',
                style: Theme.of(context).textTheme.bodyLarge,
              ),
              if (sesion.roles.length > 1) ...[
                const SizedBox(height: 4),
                Text(
                  'Roles asignados: ${sesion.roles.join(", ")}',
                  style: TextStyle(color: Colors.grey[600], fontSize: 13),
                ),
              ],
              const SizedBox(height: 24),
              const Text(
                'Las pantallas móviles para este rol todavía están '
                'planificadas para el Sprint 4 según el roadmap del '
                'proyecto.',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
