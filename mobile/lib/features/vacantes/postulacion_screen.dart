import 'package:flutter/material.dart';

import '../../core/models/pregunta_filtro.dart';
import '../../core/models/vacante.dart';
import '../../core/services/postulacion_service.dart';
import '../../core/services/vacante_service.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/vistas_estado.dart';

/// Formulario de postulación móvil (HU-14 / HU-35): carga las preguntas de filtro
/// de la vacante (si tiene) y las envía junto al job_id a POST /postulaciones/.
/// - CP02: registra la postulación y confirma al egresado.
/// - CP03: si el egresado ya se postuló, informa y evita duplicar.
/// - CP04: ante pérdida de conexión conserva las respuestas y permite reintentar
///   sin duplicar la postulación.
class PostulacionScreen extends StatefulWidget {
  final String accessToken;
  final Vacante vacante;
  final VacanteService? vacanteService;
  final PostulacionService? postulacionService;

  const PostulacionScreen({
    super.key,
    required this.accessToken,
    required this.vacante,
    this.vacanteService,
    this.postulacionService,
  });

  @override
  State<PostulacionScreen> createState() => _PostulacionScreenState();
}

class _PostulacionScreenState extends State<PostulacionScreen> {
  late final VacanteService _vacanteServicio = widget.vacanteService ?? VacanteService();
  late final PostulacionService _postulacionServicio = widget.postulacionService ?? PostulacionService();

  late Future<List<PreguntaFiltro>> _futuroPreguntas;
  final Map<String, TextEditingController> _controllersTexto = {};
  final Map<String, String> _respuestasTexto = {};
  final Map<String, String> _respuestasOpcion = {};

  bool _enviando = false;
  String? _errorConexion;

  @override
  void initState() {
    super.initState();
    _futuroPreguntas = _vacanteServicio.obtenerPreguntas(widget.accessToken, widget.vacante.id);
  }

  @override
  void dispose() {
    for (final ctrl in _controllersTexto.values) {
      ctrl.dispose();
    }
    super.dispose();
  }

  TextEditingController _controllerDe(String preguntaId) {
    return _controllersTexto.putIfAbsent(
      preguntaId,
      () => TextEditingController(text: _respuestasTexto[preguntaId] ?? ''),
    );
  }

  void _recargarPreguntas() {
    setState(() {
      _futuroPreguntas = _vacanteServicio.obtenerPreguntas(widget.accessToken, widget.vacante.id);
    });
  }

  Future<void> _postular(List<PreguntaFiltro> preguntas) async {
    if (_enviando) return;

    for (final p in preguntas) {
      final respondida = p.questionType == 'single_choice'
          ? _respuestasOpcion[p.id] != null
          : (_respuestasTexto[p.id]?.trim().isNotEmpty ?? false);
      if (p.isRequired && !respondida) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Respondé: "${p.questionText}"')));
        return;
      }
    }

    setState(() {
      _enviando = true;
      _errorConexion = null;
    });

    final respuestas = preguntas.map((p) {
      if (p.questionType == 'single_choice') {
        return RespuestaPregunta(questionId: p.id, selectedOptionId: _respuestasOpcion[p.id]);
      }
      if (p.questionType == 'number') {
        final texto = _respuestasTexto[p.id];
        return RespuestaPregunta(
          questionId: p.id,
          answerNumber: texto != null && texto.trim().isNotEmpty ? num.tryParse(texto.trim()) : null,
        );
      }
      return RespuestaPregunta(questionId: p.id, answerText: _respuestasTexto[p.id]);
    }).toList();

    try {
      final resultado = await _postulacionServicio.postular(widget.accessToken, widget.vacante.id, respuestas);
      if (!mounted) return;
      setState(() => _enviando = false);
      final fueDescartada = resultado.currentStatus == 'rejected';
      final mensajeDialogo = fueDescartada
          ? resultado.message
          : '${resultado.message}. Ya podés verla en tu seguimiento de postulaciones desde el móvil y la web.';
      await showDialog<void>(
        context: context,
        builder: (_) => AlertDialog(
          title: Text(fueDescartada ? 'Postulación no seleccionada' : '¡Postulación enviada!'),
          content: Text(mensajeDialogo),
          actions: [TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Aceptar'))],
        ),
      );
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } on PostulacionException catch (e) {
      if (!mounted) return;
      setState(() => _enviando = false);
      if (e.yaPostulado) {
        await showDialog<void>(
          context: context,
          builder: (_) => AlertDialog(
            title: const Text('Ya te postulaste'),
            content: Text(e.mensaje),
            actions: [TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Entendido'))],
          ),
        );
        if (!mounted) return;
        Navigator.of(context).pop(true);
        return;
      }
      if (e.esErrorDeConexion) {
        setState(() => _errorConexion = e.mensaje);
        ScaffoldMessenger.of(context)
          ..hideCurrentSnackBar()
          ..showSnackBar(
            SnackBar(
              content: Text(e.mensaje),
              action: SnackBarAction(
                label: 'Reintentar',
                onPressed: () => _postular(preguntas),
              ),
            ),
          );
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.mensaje)));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Postularme a ${widget.vacante.title}')),
      body: FutureBuilder<List<PreguntaFiltro>>(
        future: _futuroPreguntas,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const VistaCargando();
          }
          if (snapshot.hasError) {
            return VistaMensaje.error(snapshot.error, onReintentar: _recargarPreguntas);
          }

          final preguntas = snapshot.data ?? [];

          return ListView(
            padding: const EdgeInsets.all(20),
            children: [
              Text(
                'Vas a postularte a "${widget.vacante.title}" en ${widget.vacante.companyName} usando tu perfil registrado.',
                style: Theme.of(context).textTheme.titleSmall,
              ),
              if (preguntas.isEmpty) ...[
                const SizedBox(height: 16),
                const Text(
                  'Esta vacante no tiene preguntas adicionales. Confirmá para enviar tu postulación.',
                  style: TextStyle(color: AppColors.textoSuave),
                ),
              ],
              for (final p in preguntas) ...[const SizedBox(height: 24), _preguntaWidget(p)],
              if (_errorConexion != null) ...[
                const SizedBox(height: 24),
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: AppColors.alertaSuave,
                    borderRadius: BorderRadius.circular(AppTheme.radio),
                    border: Border.all(color: AppColors.alerta),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Icon(Icons.wifi_off_rounded, color: AppColors.alerta, size: 20),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              _errorConexion!,
                              style: const TextStyle(color: AppColors.texto, fontSize: 13.5, height: 1.35),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      OutlinedButton.icon(
                        onPressed: _enviando ? null : () => _postular(preguntas),
                        icon: const Icon(Icons.refresh_rounded, size: 18),
                        label: const Text('Reintentar postulación'),
                      ),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 28),
              FilledButton(
                onPressed: _enviando ? null : () => _postular(preguntas),
                style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
                child: _enviando
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Text('Confirmar postulación'),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _preguntaWidget(PreguntaFiltro p) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Text(p.questionText, style: const TextStyle(fontWeight: FontWeight.bold)),
            ),
            if (p.isKnockout)
              Container(
                margin: const EdgeInsets.only(left: 8),
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(color: AppColors.peligroSuave, borderRadius: BorderRadius.circular(12)),
                child: const Text('Eliminatoria', style: TextStyle(fontSize: 11, color: AppColors.peligro)),
              ),
          ],
        ),
        const SizedBox(height: 8),
        if (p.questionType == 'single_choice')
          ...p.options.map(
            (o) => RadioListTile<String>(
              contentPadding: EdgeInsets.zero,
              dense: true,
              title: Text(o.optionText),
              value: o.id,
              groupValue: _respuestasOpcion[p.id],
              onChanged: (valor) => setState(() => _respuestasOpcion[p.id] = valor!),
            ),
          )
        else
          TextField(
            controller: _controllerDe(p.id),
            keyboardType: p.questionType == 'number' ? TextInputType.number : TextInputType.text,
            decoration: const InputDecoration(hintText: 'Tu respuesta'),
            onChanged: (valor) => _respuestasTexto[p.id] = valor,
          ),
      ],
    );
  }
}
