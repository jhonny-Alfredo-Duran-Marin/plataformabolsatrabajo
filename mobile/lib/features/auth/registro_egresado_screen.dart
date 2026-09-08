import 'package:flutter/material.dart';

import '../../core/models/carrera.dart';
import '../../core/services/auth_service.dart';
import '../../core/services/registro_service.dart';

/// HU-01 — Registro de un nuevo egresado/candidato (versión móvil).
/// Solo egresados se registran desde la app; empresas y administradores
/// se gestionan por la web.
class RegistroEgresadoScreen extends StatefulWidget {
  const RegistroEgresadoScreen({super.key});

  @override
  State<RegistroEgresadoScreen> createState() => _RegistroEgresadoScreenState();
}

class _RegistroEgresadoScreenState extends State<RegistroEgresadoScreen> {
  final _formKey = GlobalKey<FormState>();
  final _registroService = RegistroService();

  final _nombresCtrl = TextEditingController();
  final _apellidosCtrl = TextEditingController();
  final _ciCtrl = TextEditingController();
  final _correoCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _matriculaCtrl = TextEditingController();
  final _anioEgresoCtrl = TextEditingController();

  List<Carrera> _carreras = [];
  String? _carreraSeleccionadaId;
  bool _cargandoCarreras = true;
  bool _enviando = false;
  bool _ocultarPassword = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _cargarCarreras();
  }

  @override
  void dispose() {
    _nombresCtrl.dispose();
    _apellidosCtrl.dispose();
    _ciCtrl.dispose();
    _correoCtrl.dispose();
    _passwordCtrl.dispose();
    _matriculaCtrl.dispose();
    _anioEgresoCtrl.dispose();
    super.dispose();
  }

  Future<void> _cargarCarreras() async {
    try {
      final carreras = await _registroService.listarCarreras();
      if (!mounted) return;
      setState(() {
        _carreras = carreras;
        _cargandoCarreras = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _cargandoCarreras = false;
        _error = e is AuthException ? e.mensaje : 'No se pudo cargar la lista de carreras.';
      });
    }
  }

  Future<void> _registrar() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _enviando = true;
      _error = null;
    });

    try {
      await _registroService.registrarEgresado(
        nombres: _nombresCtrl.text.trim(),
        apellidos: _apellidosCtrl.text.trim(),
        ci: _ciCtrl.text.trim(),
        correo: _correoCtrl.text.trim(),
        password: _passwordCtrl.text,
        carreraId: _carreraSeleccionadaId,
        anioEgreso: _anioEgresoCtrl.text.trim().isEmpty ? null : int.tryParse(_anioEgresoCtrl.text.trim()),
        matricula: _matriculaCtrl.text.trim().isEmpty ? null : _matriculaCtrl.text.trim(),
      );

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Registro exitoso. Ya podés iniciar sesión.')),
      );
      Navigator.of(context).pop();
    } on AuthException catch (e) {
      setState(() => _error = e.mensaje);
    } catch (_) {
      setState(() => _error = 'Ocurrió un error inesperado. Intentá de nuevo.');
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final anioActual = DateTime.now().year;

    return Scaffold(
      appBar: AppBar(title: const Text('Crear cuenta de egresado')),
      backgroundColor: const Color(0xFFF4F6FB),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      'Registrate como egresado',
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Tus datos quedarán pendientes de validación institucional.',
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey[600]),
                    ),
                    const SizedBox(height: 24),

                    TextFormField(
                      controller: _nombresCtrl,
                      decoration: const InputDecoration(labelText: 'Nombres', border: OutlineInputBorder()),
                      validator: (v) => (v == null || v.trim().isEmpty) ? 'Ingresá tus nombres.' : null,
                    ),
                    const SizedBox(height: 12),

                    TextFormField(
                      controller: _apellidosCtrl,
                      decoration: const InputDecoration(labelText: 'Apellidos', border: OutlineInputBorder()),
                      validator: (v) => (v == null || v.trim().isEmpty) ? 'Ingresá tus apellidos.' : null,
                    ),
                    const SizedBox(height: 12),

                    TextFormField(
                      controller: _ciCtrl,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(labelText: 'Carnet de identidad', border: OutlineInputBorder()),
                      validator: (v) {
                        if (v == null || v.trim().isEmpty) return 'Ingresá tu CI.';
                        if (v.trim().length < 5) return 'El CI parece incompleto.';
                        return null;
                      },
                    ),
                    const SizedBox(height: 12),

                    TextFormField(
                      controller: _correoCtrl,
                      keyboardType: TextInputType.emailAddress,
                      autocorrect: false,
                      decoration: const InputDecoration(labelText: 'Correo electrónico', border: OutlineInputBorder()),
                      validator: (v) {
                        if (v == null || v.trim().isEmpty) return 'Ingresá tu correo.';
                        if (!v.contains('@')) return 'Correo inválido.';
                        return null;
                      },
                    ),
                    const SizedBox(height: 12),

                    TextFormField(
                      controller: _passwordCtrl,
                      obscureText: _ocultarPassword,
                      decoration: InputDecoration(
                        labelText: 'Contraseña',
                        border: const OutlineInputBorder(),
                        suffixIcon: IconButton(
                          icon: Icon(_ocultarPassword ? Icons.visibility_off : Icons.visibility),
                          onPressed: () => setState(() => _ocultarPassword = !_ocultarPassword),
                        ),
                      ),
                      validator: (v) {
                        if (v == null || v.isEmpty) return 'Ingresá una contraseña.';
                        if (v.length < 8) return 'Debe tener al menos 8 caracteres.';
                        return null;
                      },
                    ),
                    const SizedBox(height: 12),

                    if (_cargandoCarreras)
                      const Padding(
                        padding: EdgeInsets.symmetric(vertical: 8),
                        child: Center(child: CircularProgressIndicator(strokeWidth: 2.5)),
                      )
                    else
                      DropdownButtonFormField<String>(
                        initialValue: _carreraSeleccionadaId,
                        decoration: const InputDecoration(labelText: 'Carrera', border: OutlineInputBorder()),
                        items: _carreras
                            .map((c) => DropdownMenuItem(value: c.id, child: Text(c.nombre, overflow: TextOverflow.ellipsis)))
                            .toList(),
                        onChanged: (v) => setState(() => _carreraSeleccionadaId = v),
                      ),
                    const SizedBox(height: 12),

                    TextFormField(
                      controller: _anioEgresoCtrl,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(labelText: 'Año de egreso (opcional)', border: OutlineInputBorder()),
                      validator: (v) {
                        if (v == null || v.trim().isEmpty) return null;
                        final anio = int.tryParse(v.trim());
                        if (anio == null || anio < 1950 || anio > anioActual) return 'Año inválido.';
                        return null;
                      },
                    ),
                    const SizedBox(height: 12),

                    TextFormField(
                      controller: _matriculaCtrl,
                      decoration: const InputDecoration(labelText: 'Matrícula (opcional)', border: OutlineInputBorder()),
                    ),

                    if (_error != null) ...[
                      const SizedBox(height: 16),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.red.shade50,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.red.shade200),
                        ),
                        child: Text(_error!, style: TextStyle(color: Colors.red.shade800, fontSize: 13)),
                      ),
                    ],

                    const SizedBox(height: 20),
                    FilledButton(
                      onPressed: _enviando ? null : _registrar,
                      style: FilledButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 16)),
                      child: _enviando
                          ? const SizedBox(
                              height: 20,
                              width: 20,
                              child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white),
                            )
                          : const Text('Crear cuenta'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
