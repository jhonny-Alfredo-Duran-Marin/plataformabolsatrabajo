import 'package:flutter/material.dart';

import '../../core/models/perfil_egresado.dart';
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
    super.dispose();
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
              Text(_error!, style: const TextStyle(color: Colors.red)),
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
            const SizedBox(height: 12),
            TextFormField(
              controller: _resumenCtrl,
              decoration: const InputDecoration(labelText: 'Resumen profesional'),
              maxLines: 4,
            ),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: _guardando ? null : _guardar,
              child: _guardando
                  ? const SizedBox(
                      width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Text('Guardar cambios'),
            ),
          ],
        ),
      ),
    );
  }
}
