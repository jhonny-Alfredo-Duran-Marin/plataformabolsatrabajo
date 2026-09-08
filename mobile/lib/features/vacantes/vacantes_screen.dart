import 'package:flutter/material.dart';

import '../../core/models/vacante.dart';
import '../../core/services/vacante_service.dart';
import 'vacante_detalle_screen.dart';

/// Pantalla de exploración de vacantes para el egresado. Consume
/// GET /vacantes/buscar (HU-13): admite búsqueda por palabra clave y
/// ordenar por afinidad calculada según la carrera/habilidades del
/// egresado autenticado, contra la Supabase real.
class VacantesScreen extends StatefulWidget {
  final String accessToken;

  const VacantesScreen({super.key, required this.accessToken});

  @override
  State<VacantesScreen> createState() => _VacantesScreenState();
}

class _VacantesScreenState extends State<VacantesScreen> {
  final _servicio = VacanteService();
  final _busquedaCtrl = TextEditingController();

  late Future<List<Vacante>> _futuroVacantes;
  String _ordenarPor = 'fecha';

  @override
  void initState() {
    super.initState();
    _futuroVacantes = _servicio.buscar(widget.accessToken, ordenarPor: _ordenarPor);
  }

  @override
  void dispose() {
    _busquedaCtrl.dispose();
    super.dispose();
  }

  void _recargar() {
    setState(() {
      _futuroVacantes = _servicio.buscar(widget.accessToken, q: _busquedaCtrl.text, ordenarPor: _ordenarPor);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Vacantes disponibles')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _busquedaCtrl,
                    decoration: const InputDecoration(
                      hintText: 'Buscar por título o palabra clave',
                      prefixIcon: Icon(Icons.search),
                      isDense: true,
                      border: OutlineInputBorder(),
                    ),
                    onSubmitted: (_) => _recargar(),
                  ),
                ),
                const SizedBox(width: 8),
                PopupMenuButton<String>(
                  icon: const Icon(Icons.sort),
                  tooltip: 'Ordenar',
                  initialValue: _ordenarPor,
                  onSelected: (valor) {
                    setState(() => _ordenarPor = valor);
                    _recargar();
                  },
                  itemBuilder: (_) => const [
                    PopupMenuItem(value: 'fecha', child: Text('Más recientes')),
                    PopupMenuItem(value: 'afinidad', child: Text('Mayor afinidad')),
                  ],
                ),
              ],
            ),
          ),
          Expanded(child: _listado()),
        ],
      ),
    );
  }

  Widget _listado() {
    return FutureBuilder<List<Vacante>>(
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
                    trailing: vacante.afinidadPorcentaje != null
                        ? Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text('${vacante.afinidadPorcentaje}%', style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.indigo)),
                              const Text('afín', style: TextStyle(fontSize: 11, color: Colors.grey)),
                            ],
                          )
                        : const Icon(Icons.chevron_right),
                    onTap: () {
                      Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => VacanteDetalleScreen(accessToken: widget.accessToken, vacante: vacante),
                        ),
                      );
                    },
                  ),
                );
              },
            ),
          );
        });
  }
}
