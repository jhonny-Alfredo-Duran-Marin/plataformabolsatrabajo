import 'package:flutter/material.dart';

import '../../core/services/api_http.dart';
import '../../core/services/ia_service.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/boton_ayuda.dart';
import '../../core/widgets/vistas_estado.dart';

class _Burbuja {
  final MensajeAsistente mensaje;
  final List<PostulacionAsistente> postulaciones;
  final bool esError;

  const _Burbuja(this.mensaje, {this.postulaciones = const [], this.esError = false});
}

/// Asistente de orientación del egresado (HU-28): responde dudas sobre la plataforma y sus postulaciones.
class AsistenteScreen extends StatefulWidget {
  final String accessToken;

  const AsistenteScreen({super.key, required this.accessToken});

  @override
  State<AsistenteScreen> createState() => _AsistenteScreenState();
}

class _AsistenteScreenState extends State<AsistenteScreen> {
  final _servicio = IaService();
  final _entrada = TextEditingController();
  final _scroll = ScrollController();

  String? _sesionId;
  final _burbujas = <_Burbuja>[];
  List<String> _sugerencias = const [];
  bool _cargando = true;
  bool _enviando = false;
  Object? _errorCarga;

  @override
  void initState() {
    super.initState();
    _abrir();
  }

  @override
  void dispose() {
    _entrada.dispose();
    _scroll.dispose();
    super.dispose();
  }

  /// Retoma la conversación abierta o, con [nueva], empieza otra.
  Future<void> _abrir({bool nueva = false}) async {
    setState(() {
      _cargando = true;
      _errorCarga = null;
    });
    try {
      final sesion = await _servicio.abrirConversacion(widget.accessToken, nueva: nueva);
      if (!mounted) return;
      setState(() {
        _sesionId = sesion.id;
        _burbujas
          ..clear()
          ..addAll([
            if (sesion.saludo.isNotEmpty) _Burbuja(MensajeAsistente('assistant', sesion.saludo)),
            ...sesion.mensajes.map((m) => _Burbuja(m)),
          ]);
        _sugerencias = sesion.sugerencias;
        _cargando = false;
      });
      _irAlFinal();
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorCarga = e;
          _cargando = false;
        });
      }
    }
  }

  Future<void> _preguntar(String texto) async {
    final pregunta = texto.trim();
    final sesionId = _sesionId;
    if (pregunta.isEmpty || sesionId == null || _enviando) return;
    _entrada.clear();
    setState(() {
      _enviando = true;
      _sugerencias = const [];
      _burbujas.add(_Burbuja(MensajeAsistente('user', pregunta)));
    });
    _irAlFinal();
    try {
      final respuesta = await _servicio.preguntar(widget.accessToken, sesionId, pregunta);
      if (!mounted) return;
      setState(() {
        _burbujas.add(_Burbuja(respuesta.respuesta, postulaciones: respuesta.postulaciones));
        _sugerencias = respuesta.sugerencias;
      });
    } on ApiException catch (e) {
      if (mounted) setState(() => _burbujas.add(_Burbuja(MensajeAsistente('assistant', e.mensaje), esError: true)));
    } finally {
      if (mounted) setState(() => _enviando = false);
      _irAlFinal();
    }
  }

  void _irAlFinal() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scroll.hasClients) return;
      _scroll.animateTo(
        _scroll.position.maxScrollExtent,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOut,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Asistente EGRESA'),
        actions: [
          IconButton(
            tooltip: 'Nueva conversación',
            icon: const Icon(Icons.add_comment_outlined),
            onPressed: _cargando || _enviando ? null : () => _abrir(nueva: true),
          ),
          const BotonAyuda('asistente'),
        ],
      ),
      body: _cargando
          ? const VistaCargando()
          : _errorCarga != null
              ? VistaMensaje(
                  icono: Icons.smart_toy_outlined,
                  titulo: 'El asistente no está disponible',
                  mensaje: '$_errorCarga',
                  textoAccion: 'Reintentar',
                  onAccion: _abrir,
                  color: AppColors.alerta,
                  fondo: AppColors.alertaSuave,
                )
              : _conversacion(),
    );
  }

  Widget _conversacion() {
    return Column(
      children: [
        Expanded(
          child: ListView.builder(
            controller: _scroll,
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            itemCount: _burbujas.length + (_enviando ? 1 : 0),
            itemBuilder: (_, i) => i == _burbujas.length ? const _Escribiendo() : _VistaBurbuja(_burbujas[i]),
          ),
        ),
        if (_sugerencias.isNotEmpty)
          SizedBox(
            height: 48,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              itemCount: _sugerencias.length,
              separatorBuilder: (_, _) => const SizedBox(width: 8),
              itemBuilder: (_, i) => ActionChip(
                label: Text(_sugerencias[i]),
                onPressed: _enviando ? null : () => _preguntar(_sugerencias[i]),
              ),
            ),
          ),
        SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 8, 8, 12),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _entrada,
                    minLines: 1,
                    maxLines: 4,
                    maxLength: 1000,
                    textInputAction: TextInputAction.send,
                    onSubmitted: _preguntar,
                    decoration: const InputDecoration(hintText: 'Escribí tu pregunta…', counterText: ''),
                  ),
                ),
                const SizedBox(width: 6),
                IconButton.filled(
                  tooltip: 'Enviar',
                  onPressed: _enviando ? null : () => _preguntar(_entrada.text),
                  icon: const Icon(Icons.send_rounded),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

/// Las respuestas traen markdown simple (**negrita**, *cursiva*, `ruta`): se muestran con estilo, sin los símbolos.
TextSpan _conFormato(String texto, Color color) {
  final patron = RegExp(r'\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`');
  final partes = <InlineSpan>[];
  var desde = 0;
  for (final m in patron.allMatches(texto)) {
    if (m.start > desde) partes.add(TextSpan(text: texto.substring(desde, m.start)));
    if (m.group(1) != null) {
      partes.add(TextSpan(text: m.group(1), style: const TextStyle(fontWeight: FontWeight.w700)));
    } else if (m.group(2) != null) {
      partes.add(TextSpan(text: m.group(2), style: const TextStyle(fontStyle: FontStyle.italic)));
    } else {
      partes.add(TextSpan(text: m.group(3), style: const TextStyle(fontFamily: 'monospace')));
    }
    desde = m.end;
  }
  if (desde < texto.length) partes.add(TextSpan(text: texto.substring(desde)));
  return TextSpan(style: TextStyle(color: color, height: 1.4), children: partes);
}

class _VistaBurbuja extends StatelessWidget {
  final _Burbuja burbuja;

  const _VistaBurbuja(this.burbuja);

  @override
  Widget build(BuildContext context) {
    final propia = burbuja.mensaje.esDelUsuario;
    final fondo = propia
        ? AppColors.primario
        : burbuja.esError
            ? AppColors.peligroSuave
            : AppColors.superficie;
    final colorTexto = propia
        ? Colors.white
        : burbuja.esError
            ? AppColors.peligro
            : AppColors.texto;
    return Align(
      alignment: propia ? Alignment.centerRight : Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * 0.82),
        child: Container(
          margin: const EdgeInsets.only(bottom: 10),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: fondo,
            borderRadius: BorderRadius.circular(16).copyWith(
              bottomRight: propia ? const Radius.circular(4) : null,
              bottomLeft: propia ? null : const Radius.circular(4),
            ),
            border: propia ? null : Border.all(color: AppColors.borde),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text.rich(_conFormato(burbuja.mensaje.texto, colorTexto)),
              for (final p in burbuja.postulaciones) ...[
                const SizedBox(height: 8),
                _TarjetaPostulacion(p),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _TarjetaPostulacion extends StatelessWidget {
  final PostulacionAsistente postulacion;

  const _TarjetaPostulacion(this.postulacion);

  @override
  Widget build(BuildContext context) {
    final etapa = postulacion.etapa;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(color: AppColors.primarioSuave, borderRadius: BorderRadius.circular(10)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(postulacion.puesto, style: const TextStyle(fontWeight: FontWeight.w700)),
          Text(postulacion.empresa, style: const TextStyle(color: AppColors.textoSuave, fontSize: 13)),
          const SizedBox(height: 4),
          Text(
            etapa != null && etapa.isNotEmpty ? '${postulacion.estado} · $etapa' : postulacion.estado,
            style: const TextStyle(color: AppColors.primario, fontSize: 13, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }
}

class _Escribiendo extends StatelessWidget {
  const _Escribiendo();

  @override
  Widget build(BuildContext context) {
    return const Align(
      alignment: Alignment.centerLeft,
      child: Padding(
        padding: EdgeInsets.only(bottom: 10),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
            SizedBox(width: 10),
            Text('El asistente está escribiendo…', style: TextStyle(color: AppColors.textoSuave)),
          ],
        ),
      ),
    );
  }
}
