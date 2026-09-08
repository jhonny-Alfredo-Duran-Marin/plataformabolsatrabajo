import 'package:flutter/material.dart';

import '../../core/models/postulacion.dart';
import '../../core/services/postulacion_service.dart';
import 'postulacion_detalle_screen.dart';

const Map<String, Color> _coloresEstado = {
  'blue': Colors.blue,
  'yellow': Colors.amber,
  'purple': Colors.purple,
  'indigo': Colors.indigo,
  'cyan': Colors.cyan,
  'emerald': Colors.teal,
  'green': Colors.green,
  'red': Colors.red,
  'gray': Colors.grey,
};

/// Seguimiento de postulaciones del egresado (HU-15): consume
/// GET /postulaciones/mis-postulaciones, el mismo endpoint que usa el
/// frontend web para el tablero de seguimiento.
class MisPostulacionesScreen extends StatefulWidget {
  final String accessToken;

  const MisPostulacionesScreen({super.key, required this.accessToken});

  @override
  State<MisPostulacionesScreen> createState() => _MisPostulacionesScreenState();
}

class _MisPostulacionesScreenState extends State<MisPostulacionesScreen> {
  final _servicio = PostulacionService();
  late Future<ResumenPostulaciones> _futuroResumen;

  @override
  void initState() {
    super.initState();
    _futuroResumen = _servicio.obtenerMisPostulaciones(widget.accessToken);
  }

  void _recargar() {
    setState(() => _futuroResumen = _servicio.obtenerMisPostulaciones(widget.accessToken));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Mis postulaciones')),
      body: FutureBuilder<ResumenPostulaciones>(
        future: _futuroResumen,
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

          final resumen = snapshot.data!;
          if (resumen.postulaciones.isEmpty) {
            return const Center(child: Text('Todavía no te postulaste a ninguna vacante.'));
          }

          return RefreshIndicator(
            onRefresh: () async => _recargar(),
            child: ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: resumen.postulaciones.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (context, i) {
                final p = resumen.postulaciones[i];
                final color = _coloresEstado[p.estadoColor] ?? Colors.grey;
                return Card(
                  child: ListTile(
                    contentPadding: const EdgeInsets.all(16),
                    title: Text(p.jobTitulo, style: const TextStyle(fontWeight: FontWeight.bold)),
                    subtitle: Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Text('${p.empresaNombre} · ${p.empresaCiudad ?? ''}'),
                    ),
                    isThreeLine: false,
                    trailing: Chip(
                      label: Text(p.estadoLabel, style: const TextStyle(color: Colors.white, fontSize: 12)),
                      backgroundColor: color,
                      visualDensity: VisualDensity.compact,
                    ),
                    onTap: () async {
                      await Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => PostulacionDetalleScreen(
                            accessToken: widget.accessToken,
                            postulacionId: p.id,
                          ),
                        ),
                      );
                      _recargar();
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
