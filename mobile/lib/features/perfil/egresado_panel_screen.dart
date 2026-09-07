import 'package:flutter/material.dart';

import '../../core/models/perfil_egresado.dart';
import '../../core/models/sesion.dart';
import '../../core/services/perfil_service.dart';
import '../auth/login_screen.dart';
import '../vacantes/vacantes_screen.dart';
import 'editar_perfil_screen.dart';
import 'mi_cv_screen.dart';

/// Panel principal del egresado: muestra su perfil real (GET /perfiles/me)
/// y accesos a las funcionalidades disponibles, en vez de una pantalla
/// genérica de "sesión iniciada".
class EgresadoPanelScreen extends StatefulWidget {
  final Sesion sesion;

  const EgresadoPanelScreen({super.key, required this.sesion});

  @override
  State<EgresadoPanelScreen> createState() => _EgresadoPanelScreenState();
}

class _EgresadoPanelScreenState extends State<EgresadoPanelScreen> {
  final _servicio = PerfilService();
  late Future<PerfilEgresado> _futuroPerfil;

  @override
  void initState() {
    super.initState();
    _futuroPerfil = _servicio.obtenerMiPerfil(widget.sesion.accessToken);
  }

  void _recargar() {
    setState(() {
      _futuroPerfil = _servicio.obtenerMiPerfil(widget.sesion.accessToken);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mi panel'),
        actions: [
          IconButton(
            icon: const Icon(Icons.edit_outlined),
            tooltip: 'Editar perfil',
            onPressed: () async {
              final perfilActual = await _futuroPerfil;
              if (!context.mounted) return;
              final actualizado = await Navigator.of(context).push<PerfilEgresado>(
                MaterialPageRoute(
                  builder: (_) => EditarPerfilScreen(accessToken: widget.sesion.accessToken, perfil: perfilActual),
                ),
              );
              if (actualizado != null) {
                setState(() => _futuroPerfil = Future.value(actualizado));
              }
            },
          ),
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
      body: FutureBuilder<PerfilEgresado>(
        future: _futuroPerfil,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.error_outline, color: Colors.red.shade400, size: 48),
                    const SizedBox(height: 12),
                    Text('${snapshot.error}', textAlign: TextAlign.center),
                    const SizedBox(height: 12),
                    ElevatedButton(onPressed: _recargar, child: const Text('Reintentar')),
                  ],
                ),
              ),
            );
          }

          final perfil = snapshot.data!;
          return RefreshIndicator(
            onRefresh: () async => _recargar(),
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                _tarjetaPerfil(context, perfil),
                const SizedBox(height: 20),
                Text('Accesos', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                const SizedBox(height: 12),
                _accesoMiCv(context),
                const SizedBox(height: 12),
                _accesoVacantes(context),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _tarjetaPerfil(BuildContext context, PerfilEgresado perfil) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  radius: 28,
                  backgroundColor: Colors.indigo.shade100,
                  child: Text(
                    perfil.nombres.isNotEmpty ? perfil.nombres[0].toUpperCase() : '?',
                    style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.indigo.shade700),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        perfil.nombreCompleto,
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                      ),
                      if (perfil.tituloProfesional != null && perfil.tituloProfesional!.isNotEmpty)
                        Text(perfil.tituloProfesional!, style: TextStyle(color: Colors.grey[700])),
                      if (perfil.ciudad != null && perfil.ciudad!.isNotEmpty)
                        Text(perfil.ciudad!, style: TextStyle(color: Colors.grey[500], fontSize: 13)),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                _etiquetaEstado(perfil.estadoValidacion),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Perfil completo: ${perfil.porcentajeCompletitud}%', style: const TextStyle(fontSize: 12)),
                      const SizedBox(height: 4),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: perfil.porcentajeCompletitud / 100,
                          minHeight: 6,
                          backgroundColor: Colors.grey.shade200,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            if (perfil.resumenProfesional != null && perfil.resumenProfesional!.isNotEmpty) ...[
              const SizedBox(height: 16),
              Text(perfil.resumenProfesional!),
            ],
          ],
        ),
      ),
    );
  }

  Widget _etiquetaEstado(String estado) {
    final Color color;
    final String texto;
    switch (estado) {
      case 'APROBADO':
        color = Colors.green;
        texto = 'Validado';
        break;
      case 'RECHAZADO':
        color = Colors.red;
        texto = 'Rechazado';
        break;
      default:
        color = Colors.orange;
        texto = 'Pendiente';
    }
    return Chip(
      label: Text(texto, style: const TextStyle(color: Colors.white, fontSize: 12)),
      backgroundColor: color,
      visualDensity: VisualDensity.compact,
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
    );
  }

  Widget _accesoMiCv(BuildContext context) {
    return Card(
      child: ListTile(
        leading: const Icon(Icons.description_outlined),
        title: const Text('Mi CV'),
        subtitle: const Text('Formación, experiencia, idiomas, certificaciones y habilidades'),
        trailing: const Icon(Icons.chevron_right),
        onTap: () {
          Navigator.of(context).push(
            MaterialPageRoute(
              builder: (_) => MiCvScreen(accessToken: widget.sesion.accessToken),
            ),
          );
        },
      ),
    );
  }

  Widget _accesoVacantes(BuildContext context) {
    return Card(
      child: ListTile(
        leading: const Icon(Icons.work_outline),
        title: const Text('Vacantes disponibles'),
        subtitle: const Text('Explorá las ofertas publicadas por las empresas'),
        trailing: const Icon(Icons.chevron_right),
        onTap: () {
          Navigator.of(context).push(
            MaterialPageRoute(
              builder: (_) => VacantesScreen(accessToken: widget.sesion.accessToken),
            ),
          );
        },
      ),
    );
  }
}
