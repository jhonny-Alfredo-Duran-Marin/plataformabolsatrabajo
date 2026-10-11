import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/services/auth_service.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/marca.dart';
import '../vacantes/vacantes_screen.dart';
import 'home_screen.dart';
import 'registro_egresado_screen.dart';

/// HU-02 — Inicio de sesión. Desde acá también se pueden explorar las ofertas
/// sin cuenta (HU-34).
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _correoCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _authService = AuthService();

  bool _cargando = false;
  String? _error;
  bool _ocultarPassword = true;

  @override
  void dispose() {
    _correoCtrl.dispose();
    _passwordCtrl.dispose();
    super.dispose();
  }

  Future<void> _iniciarSesion() async {
    if (!_formKey.currentState!.validate()) return;
    FocusScope.of(context).unfocus();

    setState(() {
      _cargando = true;
      _error = null;
    });

    try {
      final sesion = await _authService.login(_correoCtrl.text.trim(), _passwordCtrl.text);
      if (!mounted) return;
      Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => HomeScreen(sesion: sesion)));
    } on AuthException catch (e) {
      if (mounted) setState(() => _error = e.mensaje);
    } catch (_) {
      if (mounted) setState(() => _error = 'Ocurrió un error inesperado. Intentá de nuevo.');
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  void _explorarSinCuenta() {
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => const VacantesScreen()));
  }

  @override
  Widget build(BuildContext context) {
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: AppTheme.barrasSistemaSobreOscuro,
      child: Scaffold(
        backgroundColor: AppColors.primario,
        // La hoja del formulario se estira hasta el borde inferior aunque sobre espacio.
        body: LayoutBuilder(
          builder: (context, restricciones) => SingleChildScrollView(
            child: ConstrainedBox(
              constraints: BoxConstraints(minHeight: restricciones.maxHeight),
              child: IntrinsicHeight(
                child: Column(
                  children: [
                    SafeArea(
                      bottom: false,
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(28, 36, 28, 32),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const MarcaEgresa(sobreOscuro: true, tamano: 28),
                            const SizedBox(height: 28),
                            Text(
                              'Tu primer trabajo empieza en tu universidad',
                              style: Theme.of(
                                context,
                              ).textTheme.headlineSmall?.copyWith(color: Colors.white, height: 1.25),
                            ),
                            const SizedBox(height: 8),
                            const Text(
                              'Bolsa de trabajo universitaria: ofertas de empresas habilitadas por tu universidad.',
                              style: TextStyle(color: Color(0xFFC7D2FE), fontSize: 14.5, height: 1.4),
                            ),
                          ],
                        ),
                      ),
                    ),
                    Expanded(
                      child: Container(
                        width: double.infinity,
                        decoration: const BoxDecoration(
                          color: AppColors.fondo,
                          borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
                        ),
                        padding: const EdgeInsets.fromLTRB(24, 28, 24, 24),
                        child: SafeArea(
                          top: false,
                          child: Center(
                            child: ConstrainedBox(
                              constraints: const BoxConstraints(maxWidth: 420),
                              child: Form(
                                key: _formKey,
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.stretch,
                                  children: [
                                    Text('Ingresá a tu cuenta', style: Theme.of(context).textTheme.titleLarge),
                                    const SizedBox(height: 20),
                                    TextFormField(
                                      controller: _correoCtrl,
                                      keyboardType: TextInputType.emailAddress,
                                      textInputAction: TextInputAction.next,
                                      autocorrect: false,
                                      autofillHints: const [AutofillHints.email],
                                      decoration: const InputDecoration(
                                        labelText: 'Correo electrónico',
                                        prefixIcon: Icon(Icons.mail_outline_rounded),
                                      ),
                                      validator: (v) {
                                        if (v == null || v.trim().isEmpty) return 'Ingresá tu correo.';
                                        if (!v.contains('@')) return 'Correo inválido.';
                                        return null;
                                      },
                                    ),
                                    const SizedBox(height: 14),
                                    TextFormField(
                                      controller: _passwordCtrl,
                                      obscureText: _ocultarPassword,
                                      autofillHints: const [AutofillHints.password],
                                      decoration: InputDecoration(
                                        labelText: 'Contraseña',
                                        prefixIcon: const Icon(Icons.lock_outline_rounded),
                                        suffixIcon: IconButton(
                                          tooltip: _ocultarPassword ? 'Mostrar contraseña' : 'Ocultar contraseña',
                                          icon: Icon(
                                            _ocultarPassword
                                                ? Icons.visibility_off_outlined
                                                : Icons.visibility_outlined,
                                          ),
                                          onPressed: () => setState(() => _ocultarPassword = !_ocultarPassword),
                                        ),
                                      ),
                                      validator: (v) => (v == null || v.isEmpty) ? 'Ingresá tu contraseña.' : null,
                                      onFieldSubmitted: (_) => _iniciarSesion(),
                                    ),
                                    if (_error != null) ...[const SizedBox(height: 14), _AvisoError(_error!)],
                                    const SizedBox(height: 22),
                                    FilledButton(
                                      onPressed: _cargando ? null : _iniciarSesion,
                                      child: _cargando
                                          ? const SizedBox(
                                              height: 20,
                                              width: 20,
                                              child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white),
                                            )
                                          : const Text('Iniciar sesión'),
                                    ),
                                    const SizedBox(height: 8),
                                    TextButton(
                                      onPressed: _cargando
                                          ? null
                                          : () => Navigator.of(
                                              context,
                                            ).push(MaterialPageRoute(builder: (_) => const RegistroEgresadoScreen())),
                                      child: const Text('¿No tenés cuenta? Registrate como egresado'),
                                    ),
                                    const SizedBox(height: 18),
                                    const Row(
                                      children: [
                                        Expanded(child: Divider()),
                                        Padding(
                                          padding: EdgeInsets.symmetric(horizontal: 12),
                                          child: Text('o', style: TextStyle(color: AppColors.textoSuave)),
                                        ),
                                        Expanded(child: Divider()),
                                      ],
                                    ),
                                    const SizedBox(height: 18),
                                    OutlinedButton.icon(
                                      onPressed: _cargando ? null : _explorarSinCuenta,
                                      icon: const Icon(Icons.travel_explore_rounded),
                                      label: const Text('Explorar ofertas sin cuenta'),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
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

class _AvisoError extends StatelessWidget {
  final String mensaje;
  const _AvisoError(this.mensaje);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.peligroSuave,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.peligro.withValues(alpha: 0.25)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.error_outline_rounded, size: 20, color: AppColors.peligro),
          const SizedBox(width: 10),
          Expanded(
            child: Text(mensaje, style: const TextStyle(color: AppColors.peligro, fontSize: 13.5)),
          ),
        ],
      ),
    );
  }
}
