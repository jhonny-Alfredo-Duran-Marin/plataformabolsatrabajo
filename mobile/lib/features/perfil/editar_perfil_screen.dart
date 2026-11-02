import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

import '../../core/models/perfil_egresado.dart';
import '../../core/services/api_http.dart';
import '../../core/services/ia_service.dart';
import '../../core/services/perfil_service.dart';

/// Edita los campos básicos del perfil vía PATCH /perfiles/me.
class EditarPerfilScreen extends StatefulWidget {
  final String accessToken;
  final PerfilEgresado perfil;

  const EditarPerfilScreen({super.key, required this.accessToken, required this.perfil});

  @override
  State<EditarPerfilScreen> createState() => _EditarPerfilScreenState();
}

class _EditarPerfilScreenState extends State<EditarPerfilScreen> {
  final _formKey = GlobalKey<FormState>();
  final _servicio = PerfilService();
  final _ia = IaService();

  /// Borrador de resumen propuesto por el asistente (HU-26): editable antes de pasarlo al resumen.
  BorradorResumen? _borrador;
  final _borradorCtrl = TextEditingController();
  bool _generando = false;
  String? _errorIa;

  late final TextEditingController _tituloCtrl;
  late final TextEditingController _ciudadCtrl;
  late final TextEditingController _telefonoCtrl;
  late final TextEditingController _resumenCtrl;
  late final TextEditingController _anioEgresoCtrl;
  late final TextEditingController _matriculaCtrl;
  late String? _disponibilidad;

  bool _guardando = false;
  String? _error;

  static const _opcionesDisponibilidad = {
    'inmediata': 'Inmediata',
    '1_semana': '1 semana',
    '2_semanas': '2 semanas',
    '1_mes': '1 mes',
  };

  @override
  void initState() {
    super.initState();
    final p = widget.perfil;
    _tituloCtrl = TextEditingController(text: p.tituloProfesional ?? '');
    _ciudadCtrl = TextEditingController(text: p.ciudad ?? '');
    _telefonoCtrl = TextEditingController(text: p.telefono ?? '');
    _resumenCtrl = TextEditingController(text: p.resumenProfesional ?? '');
    _anioEgresoCtrl = TextEditingController(text: p.anioEgreso?.toString() ?? '');
    _matriculaCtrl = TextEditingController(text: p.matricula ?? '');
    _disponibilidad = p.disponibilidad;
  }

  @override
  void dispose() {
    _tituloCtrl.dispose();
    _ciudadCtrl.dispose();
    _telefonoCtrl.dispose();
    _resumenCtrl.dispose();
    _anioEgresoCtrl.dispose();
    _matriculaCtrl.dispose();
    _borradorCtrl.dispose();
    super.dispose();
  }

  /// Pide un borrador; con [otraVersion] rota a la siguiente variante de redacción (1 a 3).
  Future<void> _generarResumen({bool otraVersion = false}) async {
    final actual = _borrador?.variante ?? 0;
    final variante = otraVersion ? actual % 3 + 1 : 1;
    setState(() {
      _generando = true;
      _errorIa = null;
    });
    try {
      final borrador = await _ia.generarResumen(widget.accessToken, variante: variante);
      if (!mounted) return;
      setState(() {
        _borrador = borrador;
        _borradorCtrl.text = borrador.texto;
      });
    } on ApiException catch (e) {
      if (mounted) setState(() => _errorIa = e.mensaje);
    } finally {
      if (mounted) setState(() => _generando = false);
    }
  }

  void _usarBorrador() {
    final texto = _borradorCtrl.text.trim();
    if (texto.isEmpty) return;
    setState(() {
      _resumenCtrl.text = texto;
      _borrador = null;
    });
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Lo pasamos a tu resumen. Tocá «Guardar cambios» para guardarlo.')),
    );
  }

  Future<void> _guardar() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _guardando = true;
      _error = null;
    });

    try {
      final actualizado = await _servicio.actualizarMiPerfil(
        widget.accessToken,
        tituloProfesional: _tituloCtrl.text.trim(),
        ciudad: _ciudadCtrl.text.trim(),
        telefono: _telefonoCtrl.text.trim(),
        resumenProfesional: _resumenCtrl.text.trim(),
        disponibilidad: _disponibilidad,
        anioEgreso: _anioEgresoCtrl.text.trim().isEmpty ? null : int.tryParse(_anioEgresoCtrl.text.trim()),
        matricula: _matriculaCtrl.text.trim(),
      );
      if (!mounted) return;
      Navigator.of(context).pop(actualizado);
    } on PerfilException catch (e) {
      setState(() => _error = e.mensaje);
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Editar perfil')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            if (_error != null) ...[
              Text(_error!, style: const TextStyle(color: AppColors.peligro)),
              const SizedBox(height: 12),
            ],
            TextFormField(
              controller: _tituloCtrl,
              decoration: const InputDecoration(labelText: 'Título profesional'),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _ciudadCtrl,
              decoration: const InputDecoration(labelText: 'Ciudad'),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _telefonoCtrl,
              decoration: const InputDecoration(labelText: 'Teléfono'),
              keyboardType: TextInputType.phone,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _matriculaCtrl,
              decoration: const InputDecoration(labelText: 'Matrícula'),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _anioEgresoCtrl,
              decoration: const InputDecoration(labelText: 'Año de egreso'),
              keyboardType: TextInputType.number,
              validator: (v) {
                if (v == null || v.trim().isEmpty) return null;
                final anio = int.tryParse(v.trim());
                if (anio == null || anio < 1950 || anio > DateTime.now().year + 1) {
                  return 'Ingresá un año válido';
                }
                return null;
              },
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: _disponibilidad,
              decoration: const InputDecoration(labelText: 'Disponibilidad'),
              items: _opcionesDisponibilidad.entries
                  .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value)))
                  .toList(),
              onChanged: (v) => setState(() => _disponibilidad = v),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                const Expanded(child: Text('Resumen profesional', style: TextStyle(fontWeight: FontWeight.w600))),
                TextButton.icon(
                  onPressed: _generando ? null : _generarResumen,
                  icon: _generando
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.auto_awesome_outlined),
                  label: const Text('Redactar con IA'),
                ),
              ],
            ),
            if (_errorIa != null) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.alertaSuave,
                  borderRadius: BorderRadius.circular(AppTheme.radio),
                ),
                child: Text(_errorIa!, style: const TextStyle(color: AppColors.alerta)),
              ),
              const SizedBox(height: 10),
            ],
            if (_borrador != null) ...[
              _PanelBorrador(
                borrador: _borrador!,
                controlador: _borradorCtrl,
                generando: _generando,
                onUsar: _usarBorrador,
                onOtraVersion: () => _generarResumen(otraVersion: true),
                onDescartar: () => setState(() => _borrador = null),
              ),
              const SizedBox(height: 10),
            ],
            TextFormField(
              controller: _resumenCtrl,
              decoration: const InputDecoration(hintText: 'Contá brevemente tu formación, experiencia y lo que buscás'),
              maxLines: 4,
            ),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: _guardando ? null : _guardar,
              child: _guardando
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : const Text('Guardar cambios'),
            ),
          ],
        ),
      ),
    );
  }
}

/// Borrador del asistente (HU-26): se puede editar, pedir otra versión o descartar antes de usarlo.
class _PanelBorrador extends StatelessWidget {
  final BorradorResumen borrador;
  final TextEditingController controlador;
  final bool generando;
  final VoidCallback onUsar;
  final VoidCallback onOtraVersion;
  final VoidCallback onDescartar;

  const _PanelBorrador({
    required this.borrador,
    required this.controlador,
    required this.generando,
    required this.onUsar,
    required this.onOtraVersion,
    required this.onDescartar,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.violetaSuave,
        borderRadius: BorderRadius.circular(AppTheme.radio),
        border: Border.all(color: AppColors.violeta.withValues(alpha: 0.25)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.auto_awesome, color: AppColors.violeta, size: 20),
              const SizedBox(width: 8),
              const Expanded(
                child: Text('Borrador sugerido', style: TextStyle(fontWeight: FontWeight.w700, color: AppColors.violeta)),
              ),
              Text(
                'Versión ${borrador.variante} de ${borrador.totalVariantes}',
                style: const TextStyle(color: AppColors.textoSuave, fontSize: 12),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(borrador.advertencia, style: const TextStyle(color: AppColors.textoSuave, fontSize: 13)),
          const SizedBox(height: 10),
          TextField(
            controller: controlador,
            maxLines: 7,
            minLines: 4,
            decoration: const InputDecoration(fillColor: Colors.white, filled: true),
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: [
              FilledButton.icon(
                onPressed: generando ? null : onUsar,
                icon: const Icon(Icons.check_rounded),
                label: const Text('Usar este texto'),
              ),
              OutlinedButton.icon(
                onPressed: generando ? null : onOtraVersion,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Otra versión'),
              ),
              TextButton(onPressed: generando ? null : onDescartar, child: const Text('Descartar')),
            ],
          ),
        ],
      ),
    );
  }
}
