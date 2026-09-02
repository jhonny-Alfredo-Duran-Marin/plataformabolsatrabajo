import 'package:flutter/material.dart';

import '../../core/models/sesion.dart';
import '../vacantes/vacantes_screen.dart';
import 'login_screen.dart';

/// Pantalla mínima post-login: confirma visualmente que la sesión real
/// (token + rol) llegó del backend. Placeholder hasta HU-35 (búsqueda
/// móvil) y el resto de features móviles de Sprint 4.
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
              if (sesion.rol == 'candidate')
                ElevatedButton.icon(
                  icon: const Icon(Icons.work_outline),
                  label: const Text('Ver vacantes disponibles'),
                  onPressed: () {
                    Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => VacantesScreen(accessToken: sesion.accessToken),
                      ),
                    );
                  },
                )
              else
                const Text(
                  'El resto de las pantallas móviles (postulación, '
                  'notificaciones push) están planificadas para el '
                  'Sprint 4 según el roadmap del proyecto.',
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
