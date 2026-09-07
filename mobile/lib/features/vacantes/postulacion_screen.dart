import 'package:flutter/material.dart';

import '../../core/models/pregunta_filtro.dart';
import '../../core/models/vacante.dart';
import '../../core/services/postulacion_service.dart';
import '../../core/services/vacante_service.dart';

/// Formulario de postulación (HU-14): carga las preguntas de filtro de la
/// vacante (si tiene) y las envía junto al job_id a POST /postulaciones/.
/// Si alguna respuesta no cumple una pregunta eliminatoria, el backend
/// descarta la postulación automáticamente y lo informa en el mensaje.
class PostulacionScreen extends StatefulWidget {
  final String accessToken;
  final Vacante vacante;

  const PostulacionScreen({super.key, required this.accessToken, required this.vacante});

  @override
  State<PostulacionScreen> createState() => _PostulacionScreenState();
}

class _PostulacionScreenState extends State<PostulacionScreen> {
  final _vacanteServicio = VacanteService();
  final _postulacionServicio = PostulacionService();

  late Future<List<PreguntaFiltro>> _futuroPreguntas;
  final Map<String, String> _respuestasTexto = {};
  final Map<String, String> _respuestasOpcion = {};

  bool _enviando = false;

  @override
  void initState() {
    super.initState();
    _futuroPreguntas = _vacanteServicio.obtenerPreguntas(widget.accessToken, widget.vacante.id);
  }

  Future<void> _postular(List<PreguntaFiltro> preguntas) async {
    for (final p in preguntas) {
      final respondida = p.questionType == 'single_choice'
          ? _respuestasOpcion[p.id] != null
          : (_respuestasTexto[p.id]?.trim().isNotEmpty ?? false);
      if (p.isRequired && !respondida) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Respondé: "${p.questionText}"')),
        );
        return;
      }
    }

    setState(() => _enviando = true);

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
      final fueDescartada = resultado.currentStatus == 'rejected';
      await showDialog<void>(
        context: context,
        builder: (_) => AlertDialog(
          title: Text(fueDescartada ? 'Postulación no seleccionada' : '¡Postulación enviada!'),
          content: Text(resultado.message),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Aceptar'),
            ),
          ],
        ),
      );
      if (!mounted) return;
      Navigator.of(context).pop(true);
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
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text('${snapshot.error}'));
          }

          final preguntas = snapshot.data ?? [];

          return ListView(
            padding: const EdgeInsets.all(20),
            children: [
              Text(
                'Vas a postularte a "${widget.vacante.title}" en ${widget.vacante.companyName}.',
                style: Theme.of(context).textTheme.titleSmall,
              ),
              if (preguntas.isEmpty) ...[
                const SizedBox(height: 16),
                const Text('Esta vacante no tiene preguntas adicionales.'),
              ],
              for (final p in preguntas) ...[
                const SizedBox(height: 24),
                _preguntaWidget(p),
              ],
              const SizedBox(height: 32),
              ElevatedButton(
                onPressed: _enviando ? null : () => _postular(preguntas),
                style: ElevatedButton.styleFrom(minimumSize: const Size.fromHeight(48)),
                child: _enviando
                    ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
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
              child: Text(
                p.questionText,
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
            ),
            if (p.isKnockout)
              Container(
                margin: const EdgeInsets.only(left: 8),
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(color: Colors.red.shade50, borderRadius: BorderRadius.circular(12)),
                child: Text('Eliminatoria', style: TextStyle(fontSize: 11, color: Colors.red.shade700)),
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
            keyboardType: p.questionType == 'number' ? TextInputType.number : TextInputType.text,
            decoration: const InputDecoration(border: OutlineInputBorder(), isDense: true),
            onChanged: (valor) => _respuestasTexto[p.id] = valor,
          ),
      ],
    );
  }
}
