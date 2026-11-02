import 'package:flutter/material.dart';

import '../../core/models/encuesta.dart';
import '../../core/services/encuesta_service.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/formatos.dart';
import '../../core/widgets/boton_ayuda.dart';
import '../../core/widgets/insignia.dart';
import '../../core/widgets/vistas_estado.dart';
import 'encuesta_formulario_screen.dart';

/// Encuestas de situación laboral que envió la universidad del egresado (HU-30).
class EncuestasScreen extends StatefulWidget {
  final String accessToken;

  const EncuestasScreen({super.key, required this.accessToken});

  @override
  State<EncuestasScreen> createState() => _EncuestasScreenState();
}

class _EncuestasScreenState extends State<EncuestasScreen> {
  late Future<List<MiEncuesta>> _futuro = EncuestaService().mias(widget.accessToken);

  Future<void> _recargar() async {
    final futuro = EncuestaService().mias(widget.accessToken);
    setState(() => _futuro = futuro);
    await futuro.then((_) {}, onError: (_) {});
  }

  Future<void> _responder(MiEncuesta encuesta) async {
    final respondida = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => EncuestaFormularioScreen(accessToken: widget.accessToken, encuestaId: encuesta.id),
      ),
    );
    if (respondida == true && mounted) _recargar();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Encuestas laborales'), actions: const [BotonAyuda('encuestas')]),
      body: FutureBuilder<List<MiEncuesta>>(
        future: _futuro,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting && !snapshot.hasData) {
            return const VistaCargando();
          }
          if (snapshot.hasError) return VistaMensaje.error(snapshot.error, onReintentar: _recargar);
          final encuestas = snapshot.data!;
          if (encuestas.isEmpty) {
            return const VistaMensaje(
              icono: Icons.fact_check_outlined,
              titulo: 'No tenés encuestas',
              mensaje: 'Cuando tu universidad envíe una encuesta de situación laboral, la vas a ver acá.',
            );
          }
          return RefreshIndicator(
            onRefresh: _recargar,
            child: ListView.separated(
              padding: const EdgeInsets.all(20),
              itemCount: encuestas.length,
              separatorBuilder: (_, _) => const SizedBox(height: 12),
              itemBuilder: (_, i) => _TarjetaEncuesta(
                encuesta: encuestas[i],
                onResponder: () => _responder(encuestas[i]),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _TarjetaEncuesta extends StatelessWidget {
  final MiEncuesta encuesta;
  final VoidCallback onResponder;

  const _TarjetaEncuesta({required this.encuesta, required this.onResponder});

  @override
  Widget build(BuildContext context) {
    final (estado, colores) = encuesta.respondida
        ? ('Respondida', coloresDeEstado('green'))
        : encuesta.vencida
            ? ('Cerrada', coloresDeEstado('gray'))
            : ('Pendiente', coloresDeEstado('yellow'));
    final vence = encuesta.venceEl;
    final respondidaEl = encuesta.respondidaEl;
    return Card(
      child: InkWell(
        onTap: encuesta.pendiente ? onResponder : null,
        borderRadius: BorderRadius.circular(AppTheme.radio),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(child: Text(encuesta.titulo, style: Theme.of(context).textTheme.titleMedium)),
                  const SizedBox(width: 8),
                  Insignia(estado, colores: colores),
                ],
              ),
              if (encuesta.periodo.isNotEmpty) ...[
                const SizedBox(height: 6),
                Text('Período ${encuesta.periodo}', style: const TextStyle(color: AppColors.textoSuave)),
              ],
              if (encuesta.descripcion != null && encuesta.descripcion!.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(encuesta.descripcion!),
              ],
              const SizedBox(height: 10),
              if (respondidaEl != null)
                DatoConIcono(Icons.check_circle_outline, 'Respondiste el ${fechaCorta(respondidaEl)}')
              else if (vence != null)
                DatoConIcono(Icons.event_outlined, '${encuesta.vencida ? 'Cerró' : 'Cierra'} el ${fechaCorta(vence)}'),
              if (encuesta.pendiente) ...[
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: onResponder,
                    icon: const Icon(Icons.edit_note_rounded),
                    label: const Text('Responder'),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
