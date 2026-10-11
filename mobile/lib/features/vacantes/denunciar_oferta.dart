import 'package:flutter/material.dart';

import '../../core/models/vacante.dart';
import '../../core/services/api_http.dart';
import '../../core/services/denuncia_service.dart';
import '../../core/theme/app_theme.dart';

/// Abre el formulario para denunciar [vacante] (HU-22) y avisa el resultado.
Future<void> denunciarOferta(BuildContext context, String accessToken, Vacante vacante) async {
  final mensaje = await showModalBottomSheet<String>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (_) => _HojaDenuncia(accessToken: accessToken, vacante: vacante),
  );
  if (mensaje == null || !context.mounted) return;
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(mensaje)));
}

class _HojaDenuncia extends StatefulWidget {
  final String accessToken;
  final Vacante vacante;
  const _HojaDenuncia({required this.accessToken, required this.vacante});

  @override
  State<_HojaDenuncia> createState() => _HojaDenunciaState();
}

class _HojaDenunciaState extends State<_HojaDenuncia> {
  final _servicio = DenunciaService();
  final _detalle = TextEditingController();
  String? _motivo;
  bool _enviando = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _detalle.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _detalle.dispose();
    super.dispose();
  }

  int get _largo => _detalle.text.trim().length;
  bool get _conFundamento => _largo >= minimoFundamento;
  bool get _puedeEnviar => _motivo != null && !_enviando && (_motivo != 'other' || _conFundamento);

  Future<void> _enviar() async {
    final motivo = _motivo;
    if (motivo == null || !_puedeEnviar) return;
    setState(() {
      _enviando = true;
      _error = null;
    });
    try {
      final texto = _detalle.text.trim();
      final mensaje = await _servicio.denunciar(
        widget.accessToken,
        widget.vacante.id,
        motivo,
        texto.isEmpty ? null : texto,
      );
      if (mounted) Navigator.of(context).pop(mensaje);
    } on ApiException catch (e) {
      if (!mounted) return;
      if (e.codigo == 409) {
        // Ya la había denunciado: no es un error que pueda corregir en el formulario.
        Navigator.of(context).pop(e.mensaje);
        return;
      }
      setState(() {
        _enviando = false;
        _error = e.mensaje;
      });
    } catch (_) {
      // Una respuesta que no se pudo leer no deja el botón bloqueado para siempre.
      if (!mounted) return;
      setState(() {
        _enviando = false;
        _error = 'No se pudo enviar la denuncia. Intentá de nuevo.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(20, 0, 20, 20 + MediaQuery.viewInsetsOf(context).bottom),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Denunciar oferta', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 4),
            Text(widget.vacante.title, style: const TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 6),
            const Text(
              'La universidad revisa cada denuncia. La empresa no sabe quién la hizo.',
              style: TextStyle(color: AppColors.textoSuave),
            ),
            const SizedBox(height: 14),
            for (final m in motivosDenuncia)
              _OpcionMotivo(
                etiqueta: m.etiqueta,
                ayuda: m.ayuda,
                elegida: _motivo == m.valor,
                onTap: _enviando ? null : () => setState(() => _motivo = m.valor),
              ),
            const SizedBox(height: 10),
            TextField(
              controller: _detalle,
              minLines: 2,
              maxLines: 5,
              maxLength: 1000,
              enabled: !_enviando,
              textCapitalization: TextCapitalization.sentences,
              decoration: InputDecoration(
                labelText: _motivo == 'other' ? 'Contá qué viste' : 'Contá qué viste (recomendado)',
                hintText: 'Ej.: me pidieron un depósito para reservar el puesto.',
                helperMaxLines: 3,
                helperText: _conFundamento
                    ? 'Con este detalle tu denuncia cuenta para ocultar la oferta.'
                    : '$_largo/$minimoFundamento caracteres. Sin detalle, la denuncia se registra '
                        'pero no oculta la oferta por sí sola.',
                helperStyle: TextStyle(color: _conFundamento ? AppColors.exito : AppColors.textoSuave),
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 8),
              Text(_error!, style: const TextStyle(color: AppColors.peligro)),
            ],
            const SizedBox(height: 12),
            FilledButton(
              style: FilledButton.styleFrom(backgroundColor: AppColors.peligro),
              onPressed: _puedeEnviar ? _enviar : null,
              child: _enviando
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : const Text('Enviar denuncia'),
            ),
          ],
        ),
      ),
    );
  }
}

class _OpcionMotivo extends StatelessWidget {
  final String etiqueta;
  final String ayuda;
  final bool elegida;
  final VoidCallback? onTap;
  const _OpcionMotivo({required this.etiqueta, required this.ayuda, required this.elegida, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Material(
        color: elegida ? AppColors.peligroSuave : AppColors.superficie,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
          side: BorderSide(color: elegida ? AppColors.peligro.withValues(alpha: 0.4) : AppColors.borde),
        ),
        child: ListTile(
          onTap: onTap,
          selected: elegida,
          selectedColor: AppColors.texto,
          dense: true,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          leading: Icon(
            elegida ? Icons.radio_button_checked_rounded : Icons.radio_button_unchecked_rounded,
            color: elegida ? AppColors.peligro : AppColors.textoTenue,
          ),
          title: Text(etiqueta, style: const TextStyle(fontWeight: FontWeight.w600)),
          subtitle: Text(ayuda),
        ),
      ),
    );
  }
}
