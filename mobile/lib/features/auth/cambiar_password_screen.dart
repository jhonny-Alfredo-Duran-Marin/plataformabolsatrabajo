import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

import '../../core/models/sesion.dart';
import '../../core/services/auth_service.dart';

/// Cambio de contraseña del usuario autenticado (mismo endpoint que la web).
/// Al terminar devuelve la [Sesion] nueva con los tokens que emite el backend.
class CambiarPasswordScreen extends StatefulWidget {
  final String accessToken;

  const CambiarPasswordScreen({super.key, required this.accessToken});

  @override
  State<CambiarPasswordScreen> createState() => _CambiarPasswordScreenState();
}

class _CambiarPasswordScreenState extends State<CambiarPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _actualCtrl = TextEditingController();
  final _nuevaCtrl = TextEditingController();
  final _confirmarCtrl = TextEditingController();
  final _authService = AuthService();

  bool _guardando = false;
  bool _ocultar = true;
  String? _error;

  @override
  void dispose() {
    _actualCtrl.dispose();
    _nuevaCtrl.dispose();
    _confirmarCtrl.dispose();
    super.dispose();
  }

  Future<void> _guardar() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _guardando = true;
      _error = null;
    });

    try {
      final sesion = await _authService.cambiarPassword(widget.accessToken, _actualCtrl.text, _nuevaCtrl.text);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Contraseña actualizada.')));
      Navigator.of(context).pop<Sesion>(sesion);
    } on AuthException catch (e) {
      if (mounted) setState(() => _error = e.mensaje);
    } catch (_) {
      if (mounted) setState(() => _error = 'Ocurrió un error inesperado. Intentá de nuevo.');
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Cambiar contraseña')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _campo(
                _actualCtrl,
                'Contraseña actual',
                (v) => (v == null || v.isEmpty) ? 'Ingresá tu contraseña actual.' : null,
              ),
              const SizedBox(height: 16),
              _campo(_nuevaCtrl, 'Nueva contraseña', (v) {
                if (v == null || v.length < 8) return 'Debe tener al menos 8 caracteres.';
                if (v == _actualCtrl.text) return 'Debe ser distinta de la actual.';
                return null;
              }),
              const SizedBox(height: 16),
              _campo(
                _confirmarCtrl,
                'Repetí la nueva contraseña',
                (v) => v != _nuevaCtrl.text ? 'Las contraseñas no coinciden.' : null,
              ),
              if (_error != null) ...[
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.peligroSuave,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppColors.peligro.withValues(alpha: 0.25)),
                  ),
                  child: Text(_error!, style: TextStyle(color: AppColors.peligro, fontSize: 13)),
                ),
              ],
              const SizedBox(height: 24),
              FilledButton(
                onPressed: _guardando ? null : _guardar,
                style: FilledButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 16)),
                child: _guardando
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white),
                      )
                    : const Text('Guardar contraseña'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _campo(TextEditingController ctrl, String etiqueta, String? Function(String?) validador) {
    return TextFormField(
      controller: ctrl,
      obscureText: _ocultar,
      decoration: InputDecoration(
        labelText: etiqueta,
        prefixIcon: const Icon(Icons.lock_outline),
        suffixIcon: IconButton(
          icon: Icon(_ocultar ? Icons.visibility_off : Icons.visibility),
          onPressed: () => setState(() => _ocultar = !_ocultar),
        ),
      ),
      validator: validador,
    );
  }
}
