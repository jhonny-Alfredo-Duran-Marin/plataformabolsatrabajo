import 'package:flutter/material.dart';

import '../../core/models/postulacion.dart';
import '../../core/services/postulacion_service.dart';

const Map<String, Color> _coloresHistorial = {
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

/// Detalle de una postulación (HU-15): vacante, estado actual, historial de
/// cambios de estado y opción de retirarla si todavía sigue activa.
/// Consume GET /postulaciones/{id} y POST /postulaciones/{id}/retirar.
class PostulacionDetalleScreen extends StatefulWidget {
  final String accessToken;
  final String postulacionId;

  const PostulacionDetalleScreen({super.key, required this.accessToken, required this.postulacionId});

  @override
  State<PostulacionDetalleScreen> createState() => _PostulacionDetalleScreenState();
}

class _PostulacionDetalleScreenState extends State<PostulacionDetalleScreen> {
  final _servicio = PostulacionService();
  late Future<DetallePostulacion> _futuroDetalle;
  bool _retirando = false;

  @override
  void initState() {
    super.initState();
    _futuroDetalle = _servicio.obtenerDetalle(widget.accessToken, widget.postulacionId);
  }

  void _recargar() {
    setState(() => _futuroDetalle = _servicio.obtenerDetalle(widget.accessToken, widget.postulacionId));
  }

  Future<void> _confirmarRetiro() async {
    final confirmado = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Retirar postulación'),
        content: const Text('¿Estás seguro de que querés retirar esta postulación? Esta acción no se puede deshacer.'),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Cancelar')),
          TextButton(onPressed: () => Navigator.of(context).pop(true), child: const Text('Retirar')),
        ],
      ),
    );
    if (confirmado != true) return;

    setState(() => _retirando = true);
    try {
      await _servicio.retirar(widget.accessToken, widget.postulacionId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Postulación retirada.')));
      _recargar();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _retirando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Detalle de postulación')),
      body: FutureBuilder<DetallePostulacion>(
        future: _futuroDetalle,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text('${snapshot.error}'));
          }

          final detalle = snapshot.data!;
          final p = detalle.postulacion;
          final color = _coloresHistorial[p.estadoColor] ?? Colors.grey;

          return ListView(
            padding: const EdgeInsets.all(20),
            children: [
              Text(p.jobTitulo, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
              const SizedBox(height: 4),
              Text('${p.empresaNombre} · ${p.empresaCiudad ?? ''}', style: TextStyle(color: Colors.grey[700])),
              const SizedBox(height: 12),
              Chip(
                label: Text(p.estadoLabel, style: const TextStyle(color: Colors.white)),
                backgroundColor: color,
              ),
              if (p.etapaActualNombre != null) ...[
                const SizedBox(height: 8),
                Text('Etapa actual: ${p.etapaActualNombre}'),
              ],
              const SizedBox(height: 20),
              Text('Descripción de la vacante', style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold)),
              const SizedBox(height: 4),
              Text(detalle.vacanteDescripcion),
              const SizedBox(height: 24),
              Text('Historial', style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              for (final h in detalle.historialEstados)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        margin: const EdgeInsets.only(top: 4),
                        width: 10,
                        height: 10,
                        decoration: BoxDecoration(
                          color: _coloresHistorial[h.haciaEstadoColor] ?? Colors.grey,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(h.haciaEstadoLabel, style: const TextStyle(fontWeight: FontWeight.w600)),
                            if (h.motivo != null && h.motivo!.isNotEmpty)
                              Text(h.motivo!, style: TextStyle(color: Colors.grey[600], fontSize: 13)),
                            Text(
                              '${h.fecha.day}/${h.fecha.month}/${h.fecha.year}',
                              style: TextStyle(color: Colors.grey[500], fontSize: 12),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              if (p.puedeRetirar) ...[
                const SizedBox(height: 12),
                OutlinedButton(
                  onPressed: _retirando ? null : _confirmarRetiro,
                  style: OutlinedButton.styleFrom(foregroundColor: Colors.red, minimumSize: const Size.fromHeight(48)),
                  child: _retirando
                      ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('Retirar postulación'),
                ),
              ],
            ],
          );
        },
      ),
    );
  }
}
