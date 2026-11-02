import 'package:flutter/material.dart';

import '../../core/models/encuesta.dart';
import '../../core/services/api_http.dart';
import '../../core/services/encuesta_service.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/formatos.dart';
import '../../core/widgets/boton_ayuda.dart';
import '../../core/widgets/vistas_estado.dart';

/// Quienes trabajan responden además dónde, en qué y cuánto se relaciona con su carrera (igual que la API).
const _situacionesConTrabajo = {'empleado', 'independiente'};
const _preguntasDeTrabajo = {'empresa', 'cargo', 'relacion_carrera'};
const _maxMeses = 600;

/// Formulario de la encuesta de situación laboral (HU-30). Al enviarla devuelve true.
class EncuestaFormularioScreen extends StatefulWidget {
  final String accessToken;
  final String encuestaId;

  const EncuestaFormularioScreen({super.key, required this.accessToken, required this.encuestaId});

  @override
  State<EncuestaFormularioScreen> createState() => _EncuestaFormularioScreenState();
}

class _EncuestaFormularioScreenState extends State<EncuestaFormularioScreen> {
  final _servicio = EncuestaService();
  late Future<FormularioEncuesta> _futuro = _servicio.formulario(widget.accessToken, widget.encuestaId);

  /// Pregunta -> opción elegida (single_choice) o valor de 1 a 5 (scale).
  final _opciones = <String, String>{};
  final _escalas = <String, int>{};
  final _textos = <String, TextEditingController>{};

  bool _enviando = false;
  String? _error;

  @override
  void dispose() {
    for (final controlador in _textos.values) {
      controlador.dispose();
    }
    super.dispose();
  }

  TextEditingController _controlador(String preguntaId) =>
      _textos.putIfAbsent(preguntaId, TextEditingController.new);

  bool _esDeTrabajo(PreguntaEncuesta p) => _preguntasDeTrabajo.contains(p.codigo);

  bool _trabaja(FormularioEncuesta f) {
    final situacion = f.preguntas.where((p) => p.codigo == 'situacion_laboral').firstOrNull;
    if (situacion == null) return false;
    final elegida = situacion.opciones.where((o) => o.id == _opciones[situacion.id]).firstOrNull;
    return _situacionesConTrabajo.contains(elegida?.codigo);
  }

  List<PreguntaEncuesta> _visibles(FormularioEncuesta f) {
    final trabaja = _trabaja(f);
    return f.preguntas.where((p) => !_esDeTrabajo(p) || trabaja).toList();
  }

  /// Las respuestas listas para enviar, o el motivo por el que todavía no se puede.
  (List<RespuestaPregunta>, String?) _armar(FormularioEncuesta f) {
    final trabaja = _trabaja(f);
    final respuestas = <RespuestaPregunta>[];
    for (final p in _visibles(f)) {
      RespuestaPregunta? respuesta;
      switch (p.tipo) {
        case 'single_choice':
          final opcion = _opciones[p.id];
          if (opcion != null) respuesta = RespuestaPregunta(p.id, opcionId: opcion);
        case 'scale':
          final valor = _escalas[p.id];
          if (valor != null) respuesta = RespuestaPregunta(p.id, numero: valor);
        case 'number':
          final texto = _controlador(p.id).text.trim();
          if (texto.isNotEmpty) {
            final numero = int.tryParse(texto);
            if (numero == null || numero < 0 || numero > _maxMeses) {
              return (const [], 'Los meses tienen que ser un número entre 0 y $_maxMeses.');
            }
            respuesta = RespuestaPregunta(p.id, numero: numero);
          }
        default:
          final texto = _controlador(p.id).text.trim();
          if (texto.isNotEmpty) respuesta = RespuestaPregunta(p.id, texto: texto);
      }
      if (respuesta != null) {
        respuestas.add(respuesta);
      } else if (p.obligatoria || (_esDeTrabajo(p) && trabaja)) {
        return (const [], 'Falta responder: ${p.texto}');
      }
    }
    return (respuestas, null);
  }

  Future<void> _enviar(FormularioEncuesta f) async {
    final (respuestas, falta) = _armar(f);
    if (falta != null) {
      setState(() => _error = falta);
      return;
    }
    setState(() {
      _enviando = true;
      _error = null;
    });
    try {
      final mensaje = await _servicio.responder(widget.accessToken, f.id, respuestas);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(mensaje)));
      Navigator.of(context).pop(true);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.mensaje);
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Encuesta laboral'), actions: const [BotonAyuda('encuestas')]),
      body: FutureBuilder<FormularioEncuesta>(
        future: _futuro,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return const VistaCargando();
          final error = snapshot.error;
          // Ya respondida (409) o cerrada: no hay nada que reintentar.
          if (error is ApiException && error.codigo != null && error.codigo! >= 400 && error.codigo! < 500) {
            return VistaMensaje(
              icono: error.codigo == 409 ? Icons.check_circle_outline : Icons.event_busy_outlined,
              titulo: error.mensaje,
              textoAccion: 'Volver',
              onAccion: () => Navigator.of(context).pop(),
              color: error.codigo == 409 ? AppColors.exito : AppColors.alerta,
              fondo: error.codigo == 409 ? AppColors.exitoSuave : AppColors.alertaSuave,
            );
          }
          if (error != null) {
            return VistaMensaje.error(
              error,
              onReintentar: () => setState(() {
                _futuro = _servicio.formulario(widget.accessToken, widget.encuestaId);
              }),
            );
          }
          return _formulario(snapshot.data!);
        },
      ),
    );
  }

  Widget _formulario(FormularioEncuesta f) {
    final vence = f.venceEl;
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
      children: [
        Text(f.titulo, style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 4),
        Text(
          [
            if (f.periodo.isNotEmpty) 'Período ${f.periodo}',
            if (vence != null) 'cierra el ${fechaCorta(vence)}',
          ].join(' · '),
          style: const TextStyle(color: AppColors.textoSuave),
        ),
        if (f.descripcion != null && f.descripcion!.isNotEmpty) ...[
          const SizedBox(height: 10),
          Text(f.descripcion!),
        ],
        const SizedBox(height: 22),
        for (final p in _visibles(f)) ...[_pregunta(p), const SizedBox(height: 22)],
        if (_error != null) ...[
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.peligroSuave,
              borderRadius: BorderRadius.circular(AppTheme.radio),
            ),
            child: Text(_error!, style: const TextStyle(color: AppColors.peligro)),
          ),
          const SizedBox(height: 12),
        ],
        FilledButton(
          onPressed: _enviando ? null : () => _enviar(f),
          child: _enviando
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                )
              : const Text('Enviar respuestas'),
        ),
      ],
    );
  }

  Widget _pregunta(PreguntaEncuesta p) {
    final campo = switch (p.tipo) {
      'single_choice' => Column(
          children: [
            for (final o in p.opciones)
              _Opcion(
                texto: o.texto,
                elegida: _opciones[p.id] == o.id,
                onTap: () => setState(() => _opciones[p.id] = o.id),
              ),
          ],
        ),
      'scale' => Wrap(
          spacing: 10,
          children: [
            for (var valor = 1; valor <= 5; valor++)
              ChoiceChip(
                label: Text('$valor'),
                selected: _escalas[p.id] == valor,
                onSelected: (_) => setState(() => _escalas[p.id] = valor),
              ),
          ],
        ),
      'number' => TextField(
          controller: _controlador(p.id),
          keyboardType: TextInputType.number,
          decoration: InputDecoration(
            hintText: 'Ej. 6',
            suffixText: p.codigo == 'meses_primer_empleo' ? 'meses' : null,
          ),
        ),
      _ => TextField(
          controller: _controlador(p.id),
          maxLength: 500,
          decoration: const InputDecoration(hintText: 'Tu respuesta'),
        ),
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('${p.texto}${p.obligatoria ? ' *' : ''}', style: const TextStyle(fontWeight: FontWeight.w600)),
        const SizedBox(height: 10),
        campo,
      ],
    );
  }
}

/// Opción de una pregunta de selección única.
class _Opcion extends StatelessWidget {
  final String texto;
  final bool elegida;
  final VoidCallback onTap;

  const _Opcion({required this.texto, required this.elegida, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final borde = BorderRadius.circular(12);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Material(
        color: elegida ? AppColors.primarioSuave : AppColors.superficie,
        shape: RoundedRectangleBorder(
          borderRadius: borde,
          side: BorderSide(color: elegida ? AppColors.primario : AppColors.borde),
        ),
        child: InkWell(
          onTap: onTap,
          borderRadius: borde,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
            child: Row(
              children: [
                Icon(
                  elegida ? Icons.radio_button_checked : Icons.radio_button_unchecked,
                  color: elegida ? AppColors.primario : AppColors.textoTenue,
                ),
                const SizedBox(width: 10),
                Expanded(child: Text(texto)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
