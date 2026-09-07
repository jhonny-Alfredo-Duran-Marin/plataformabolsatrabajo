import 'package:flutter/material.dart';

import '../../core/models/vacante.dart';
import '../../core/services/vacante_service.dart';
import 'vacante_detalle_screen.dart';

/// Pantalla de exploración de vacantes para el egresado (HU-35, versión
/// mínima sin filtros de búsqueda todavía). Consume el mismo endpoint
/// público que el buscador web, contra la Supabase real.
class VacantesScreen extends StatefulWidget {
  final String accessToken;

  const VacantesScreen({super.key, required this.accessToken});

  @override
  State<VacantesScreen> createState() => _VacantesScreenState();
}

class _VacantesScreenState extends State<VacantesScreen> {
  final _servicio = VacanteService();

  late Future<List<Vacante>> _futuroVacantes;

  @override
  void initState() {
    super.initState();
    _futuroVacantes = _servicio.listarPublicadas(widget.accessToken);
  }

  void _recargar() {
    setState(() {
      _futuroVacantes = _servicio.listarPublicadas(widget.accessToken);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Vacantes disponibles')),
      body: FutureBuilder<List<Vacante>>(
        future: _futuroVacantes,
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

          final vacantes = snapshot.data ?? [];
          if (vacantes.isEmpty) {
            return const Center(child: Text('No hay vacantes publicadas por el momento.'));
          }

          return RefreshIndicator(
            onRefresh: () async => _recargar(),
            child: ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: vacantes.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (context, i) {
                final vacante = vacantes[i];
                return Card(
                  child: ListTile(
                    contentPadding: const EdgeInsets.all(16),
                    title: Text(vacante.title, style: const TextStyle(fontWeight: FontWeight.bold)),
                    subtitle: Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Text(
                        '${vacante.companyName} · ${vacante.city}\n${vacante.workModality} · ${vacante.employmentType}',
                      ),
                    ),
                    isThreeLine: true,
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () {
                      Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => VacanteDetalleScreen(vacante: vacante)),
                      );
                    },
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}
