import 'package:flutter/material.dart';

import '../../core/models/entrevista.dart';
import '../../core/models/mensaje.dart';
import '../../core/models/postulacion.dart';
import '../../core/services/entrevista_service.dart';
import '../../core/services/mensaje_service.dart';
import '../../core/services/postulacion_service.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/formatos.dart';
import '../../core/widgets/boton_ayuda.dart';
import '../../core/widgets/insignia.dart';
import '../../core/widgets/vistas_estado.dart';
import '../mensajes/chat_screen.dart';
import 'tarjeta_entrevista.dart';

class _Detalle {
  final DetallePostulacion detalle;
  final List<Entrevista> entrevistas;

  /// Conversación con la empresa, si ya hay mensajes (HU-19).
  final ResumenConversacion? conversacion;
  const _Detalle(this.detalle, this.entrevistas, this.conversacion);
}

/// Detalle de una postulación (HU-15): estado, mensajes con la empresa
/// (HU-19), entrevistas propuestas (HU-20), historial y la opción de retirarla
/// mientras siga activa.
class PostulacionDetalleScreen extends StatefulWidget {
  final String accessToken;
  final String postulacionId;

  const PostulacionDetalleScreen({super.key, required this.accessToken, required this.postulacionId});

  @override
  State<PostulacionDetalleScreen> createState() => _PostulacionDetalleScreenState();
}

class _PostulacionDetalleScreenState extends State<PostulacionDetalleScreen> {
  final _postulaciones = PostulacionService();
  final _entrevistas = EntrevistaService();
  late Future<_Detalle> _futuro = _cargar();
  bool _retirando = false;

  Future<_Detalle> _cargar() async {
    final resultados = await Future.wait<Object?>([
      _postulaciones.obtenerDetalle(widget.accessToken, widget.postulacionId),
      _entrevistas.listar(widget.accessToken, widget.postulacionId),
      _conversacion(),
    ]);
    final entrevistas = [...resultados[1] as List<Entrevista>]..sort(_porPrioridad);
    return _Detalle(resultados[0] as DetallePostulacion, entrevistas, resultados[2] as ResumenConversacion?);
  }

  /// Solo para la vista previa de la tarjeta de mensajes: si falla, el detalle carga igual.
  Future<ResumenConversacion?> _conversacion() async {
    try {
      final conversaciones = await MensajeService().conversaciones(widget.accessToken);
      return conversaciones.where((c) => c.postulacionId == widget.postulacionId).firstOrNull;
    } catch (_) {
      return null;
    }
  }

  Future<void> _abrirMensajes(String empresa) async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => ChatScreen(
          accessToken: widget.accessToken,
          postulacionId: widget.postulacionId,
          esEmpresa: false,
          titulo: empresa,
        ),
      ),
    );
    await _recargar();
  }

  /// Primero lo que espera respuesta, después lo confirmado por venir (ambos por
  /// fecha) y al final lo ya resuelto, de lo más reciente a lo más viejo.
  static int _porPrioridad(Entrevista a, Entrevista b) {
    int grupo(Entrevista e) => e.requiereRespuesta ? 0 : (e.confirmada && !e.yaPaso ? 1 : 2);
    final porGrupo = grupo(a).compareTo(grupo(b));
    if (porGrupo != 0) return porGrupo;
    return grupo(a) == 2 ? b.creada.compareTo(a.creada) : a.inicio.compareTo(b.inicio);
  }

  Future<void> _recargar() async {
    if (!mounted) return;
    final futuro = _cargar();
    setState(() { _futuro = futuro; });
    await futuro.then((_) {}, onError: (_) {});
  }

  void _avisar(String mensaje) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(mensaje)));
  }

  Future<void> _confirmar(Entrevista entrevista) async {
    try {
      await _entrevistas.confirmar(widget.accessToken, entrevista.id);
      _avisar('Confirmaste tu asistencia. ¡Éxitos en la entrevista!');
      await _recargar();
    } catch (e) {
      _avisar('$e');
    }
  }

  Future<void> _rechazar(Entrevista entrevista, String motivo) async {
    try {
      await _entrevistas.rechazar(widget.accessToken, entrevista.id, motivo);
      _avisar('Le avisamos a la empresa que no podés asistir.');
      await _recargar();
    } catch (e) {
      _avisar('$e');
    }
  }

  Future<void> _confirmarRetiro() async {
    final confirmado = await showDialog<bool>(
      context: context,
      builder: (contexto) => AlertDialog(
        title: const Text('Retirar postulación'),
        content: const Text('La empresa dejará de ver tu postulación. Esta acción no se puede deshacer.'),
        actions: [
          TextButton(onPressed: () => Navigator.of(contexto).pop(false), child: const Text('Cancelar')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: AppColors.peligro),
            onPressed: () => Navigator.of(contexto).pop(true),
            child: const Text('Retirar'),
          ),
        ],
      ),
    );
    if (confirmado != true || !mounted) return;

    setState(() => _retirando = true);
    try {
      await _postulaciones.retirar(widget.accessToken, widget.postulacionId);
      _avisar('Retiraste tu postulación.');
      await _recargar();
    } catch (e) {
      _avisar('$e');
    } finally {
      if (mounted) setState(() => _retirando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Postulación'), actions: const [BotonAyuda('postulaciones')]),
      body: FutureBuilder<_Detalle>(
        future: _futuro,
        builder: (context, snapshot) {
          // Tras confirmar o rechazar, la tarjeta se actualiza sin volver a mostrar el indicador de carga.
          if (snapshot.hasData) return RefreshIndicator(onRefresh: _recargar, child: _contenido(snapshot.data!));
          if (snapshot.connectionState == ConnectionState.waiting) return const VistaCargando();
          return VistaMensaje.error(snapshot.error, onReintentar: _recargar);
        },
      ),
    );
  }

  Widget _contenido(_Detalle datos) {
    final p = datos.detalle.postulacion;
    final entrevistas = datos.entrevistas;
    final ubicacion = [p.empresaNombre, if (p.empresaCiudad != null && p.empresaCiudad!.isNotEmpty) p.empresaCiudad!];

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    AvatarEmpresa(p.empresaNombre, tamano: 48),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(p.jobTitulo, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontSize: 17)),
                          const SizedBox(height: 2),
                          Text(ubicacion.join(' · '), style: const TextStyle(color: AppColors.textoSuave)),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                Wrap(
                  spacing: 10,
                  runSpacing: 8,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Insignia(p.estadoLabel, colores: coloresDeEstado(p.estadoColor)),
                    if (p.etapaActualNombre != null && p.etapaActualNombre!.isNotEmpty)
                      DatoConIcono(Icons.flag_outlined, 'Etapa: ${p.etapaActualNombre}'),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  'Te postulaste ${haceCuanto(p.fechaPostulacion)}',
                  style: const TextStyle(color: AppColors.textoSuave, fontSize: 13),
                ),
              ],
            ),
          ),
        ),
        // Una postulación retirada o descartada solo muestra la conversación si ya existía.
        if (datos.conversacion != null || !{'rejected', 'withdrawn'}.contains(p.estado)) ...[
          const SizedBox(height: 12),
          _TarjetaMensajes(
            empresa: p.empresaNombre,
            conversacion: datos.conversacion,
            onTap: () => _abrirMensajes(p.empresaNombre),
          ),
        ],
        if (entrevistas.isNotEmpty) ...[
          const SizedBox(height: 22),
          TituloSeccion(entrevistas.length == 1 ? 'Entrevista' : 'Entrevistas'),
          const SizedBox(height: 8),
          for (final e in entrevistas) ...[
            TarjetaEntrevista(entrevista: e, onConfirmar: _confirmar, onRechazar: _rechazar),
            const SizedBox(height: 12),
          ],
        ],
        if (datos.detalle.historialEstados.isNotEmpty) ...[
          const SizedBox(height: 10),
          const TituloSeccion('Seguimiento'),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
              child: _LineaDeTiempo(datos.detalle.historialEstados),
            ),
          ),
        ],
        if (datos.detalle.vacanteDescripcion.trim().isNotEmpty) ...[
          const SizedBox(height: 22),
          const TituloSeccion('Sobre la vacante'),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: _TextoExpandible(datos.detalle.vacanteDescripcion.trim()),
            ),
          ),
        ],
        if (p.puedeRetirar) ...[
          const SizedBox(height: 24),
          OutlinedButton(
            onPressed: _retirando ? null : _confirmarRetiro,
            style: OutlinedButton.styleFrom(
              foregroundColor: AppColors.peligro,
              side: BorderSide(color: AppColors.peligro.withValues(alpha: 0.35)),
            ),
            child: _retirando
                ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                : const Text('Retirar postulación'),
          ),
        ],
      ],
    );
  }
}

class _TarjetaMensajes extends StatelessWidget {
  final String empresa;
  final ResumenConversacion? conversacion;
  final VoidCallback onTap;
  const _TarjetaMensajes({required this.empresa, required this.conversacion, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final c = conversacion;
    final sinLeer = c != null && c.noLeidos > 0;
    final vista = c == null
        ? 'Escribile a la empresa sobre tu postulación.'
        : '${c.ultimoEsMio ? 'Vos: ' : ''}${c.ultimoMensaje.replaceAll('\n', ' ')}';

    return Card(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppTheme.radio),
        side: BorderSide(color: sinLeer ? AppColors.primarioBorde : AppColors.borde),
      ),
      child: ListTile(
        onTap: onTap,
        contentPadding: const EdgeInsets.fromLTRB(16, 6, 12, 6),
        leading: Container(
          width: 42,
          height: 42,
          decoration: const BoxDecoration(color: AppColors.primarioSuave, shape: BoxShape.circle),
          child: const Icon(Icons.forum_outlined, color: AppColors.primario, size: 22),
        ),
        title: Text('Mensajes con $empresa', maxLines: 1, overflow: TextOverflow.ellipsis),
        subtitle: Text(
          vista,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: sinLeer ? const TextStyle(color: AppColors.texto, fontWeight: FontWeight.w600) : null,
        ),
        trailing: sinLeer
            ? ContadorNoLeidos(c.noLeidos)
            : const Icon(Icons.chevron_right_rounded, color: AppColors.textoTenue),
      ),
    );
  }
}

class _LineaDeTiempo extends StatelessWidget {
  final List<HistorialEstado> historial;
  const _LineaDeTiempo(this.historial);

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        for (final (i, h) in historial.indexed)
          IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                SizedBox(
                  width: 16,
                  child: Column(
                    children: [
                      const SizedBox(height: 3),
                      Container(
                        width: 12,
                        height: 12,
                        decoration: BoxDecoration(
                          color: coloresDeEstado(h.haciaEstadoColor).color,
                          shape: BoxShape.circle,
                          border: Border.all(color: Colors.white, width: 2),
                        ),
                      ),
                      if (i < historial.length - 1) Expanded(child: Container(width: 2, color: AppColors.borde)),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(h.haciaEstadoLabel, style: const TextStyle(fontWeight: FontWeight.w600)),
                        if (h.motivo != null && h.motivo!.isNotEmpty)
                          Text(h.motivo!, style: const TextStyle(color: AppColors.textoSuave, fontSize: 13)),
                        const SizedBox(height: 2),
                        Text(
                          fechaCorta(h.fecha.toLocal()),
                          style: const TextStyle(color: AppColors.textoSuave, fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _TextoExpandible extends StatefulWidget {
  final String texto;
  const _TextoExpandible(this.texto);

  @override
  State<_TextoExpandible> createState() => _TextoExpandibleState();
}

class _TextoExpandibleState extends State<_TextoExpandible> {
  bool _abierto = false;

  @override
  Widget build(BuildContext context) {
    final largo = widget.texto.length > 220;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          widget.texto,
          maxLines: _abierto || !largo ? null : 4,
          overflow: _abierto || !largo ? null : TextOverflow.ellipsis,
        ),
        if (largo)
          TextButton(
            onPressed: () => setState(() => _abierto = !_abierto),
            style: TextButton.styleFrom(padding: EdgeInsets.zero, minimumSize: const Size(0, 36)),
            child: Text(_abierto ? 'Ver menos' : 'Ver más'),
          ),
      ],
    );
  }
}
