import 'package:flutter/material.dart';

import '../../core/models/vacante.dart';
import '../../core/services/postulacion_service.dart';
import '../../core/services/vacante_service.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/formatos.dart';
import '../../core/widgets/boton_ayuda.dart';
import '../../core/widgets/insignia.dart';
import '../auth/registro_egresado_screen.dart';
import 'denunciar_oferta.dart';
import 'postulacion_screen.dart';

/// Detalle de una vacante (HU-13 / HU-35). Sin [accessToken] (visitante, HU-34)
/// invita a iniciar sesión o crear una cuenta en lugar de postularse.
/// Si el egresado ya se postuló a esta vacante, lo informa y no permite duplicar (CP03).
class VacanteDetalleScreen extends StatefulWidget {
  final String? accessToken;
  final Vacante vacante;
  final bool yaPostulado;
  final PostulacionService? postulacionService;
  final VacanteService? vacanteService;

  const VacanteDetalleScreen({
    super.key,
    this.accessToken,
    required this.vacante,
    this.yaPostulado = false,
    this.postulacionService,
    this.vacanteService,
  });

  @override
  State<VacanteDetalleScreen> createState() => _VacanteDetalleScreenState();
}

class _VacanteDetalleScreenState extends State<VacanteDetalleScreen> {
  late final PostulacionService _postulacionServicio = widget.postulacionService ?? PostulacionService();
  late bool _yaPostulado = widget.yaPostulado;
  bool _cambioEstadoPostulacion = false;

  @override
  void initState() {
    super.initState();
    if (widget.accessToken != null && !_yaPostulado) {
      _verificarSiYaPostulo();
    }
  }

  Future<void> _verificarSiYaPostulo() async {
    final token = widget.accessToken;
    if (token == null) return;
    try {
      final ids = await _postulacionServicio.obtenerVacantesPostuladasIds(token);
      if (!mounted) return;
      if (ids.contains(widget.vacante.id)) {
        setState(() {
          _yaPostulado = true;
          _cambioEstadoPostulacion = true;
        });
      }
    } catch (_) {
      // Si falla la consulta previa de verificación, el backend igual protege contra duplicados en POST /postulaciones/.
    }
  }

  Future<void> _abrirPostulacion(String token) async {
    final postulo = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => PostulacionScreen(
          accessToken: token,
          vacante: widget.vacante,
          vacanteService: widget.vacanteService,
          postulacionService: _postulacionServicio,
        ),
      ),
    );
    if (!mounted) return;
    if (postulo == true) {
      setState(() {
        _yaPostulado = true;
        _cambioEstadoPostulacion = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final vacante = widget.vacante;
    final afinidad = vacante.afinidadPorcentaje;
    final cierre = vacante.cierre;
    final datos = <(IconData, String, String)>[
      (Icons.schedule_rounded, 'Jornada', vacante.jornadaLegible),
      (iconoDeModalidad(vacante.workModality), 'Modalidad', vacante.modalidadLegible),
      (Icons.trending_up_rounded, 'Nivel', vacante.nivelLegible),
      (Icons.payments_outlined, 'Salario', vacante.salarioLegible),
      (Icons.people_outline_rounded, 'Puestos', '${vacante.positionsAvailable}'),
      (Icons.event_outlined, 'Cierre', cierre == null ? 'Sin fecha límite' : fechaCorta(cierre)),
    ].where((d) => d.$3.isNotEmpty).toList();

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) {
          Navigator.of(context).pop(_cambioEstadoPostulacion);
        }
      },
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Detalle de la vacante'),
          actions: [
            const BotonAyuda('vacante'),
            if (widget.accessToken case final token?)
              PopupMenuButton<void>(
                tooltip: 'Más opciones',
                itemBuilder: (_) => [
                  PopupMenuItem(
                    onTap: () => denunciarOferta(context, token, vacante),
                    child: const ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: Icon(Icons.outlined_flag_rounded, color: AppColors.peligro),
                      title: Text('Denunciar oferta'),
                    ),
                  ),
                ],
              ),
          ],
        ),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                AvatarEmpresa(vacante.companyName, tamano: 52),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        vacante.companyName,
                        style: const TextStyle(color: AppColors.textoSuave, fontWeight: FontWeight.w500),
                      ),
                      const SizedBox(height: 2),
                      Text(vacante.title, style: Theme.of(context).textTheme.titleLarge?.copyWith(height: 1.25)),
                    ],
                  ),
                ),
              ],
            ),
            if (vacante.city.isNotEmpty) ...[
              const SizedBox(height: 12),
              DatoConIcono(Icons.location_on_outlined, vacante.city),
            ],
            if (vacante.scoreRelevancia != null) ...[
              const SizedBox(height: 18),
              _RelevanciaSemantica(
                score: vacante.scoreRelevancia!,
                razon: vacante.razonCoincidencia,
              ),
            ] else if (afinidad != null) ...[
              const SizedBox(height: 18),
              _Afinidad(afinidad),
            ],
            const SizedBox(height: 18),
            Card(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: Column(
                  children: [
                    for (var i = 0; i < datos.length; i += 2)
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(child: _Dato(datos[i])),
                            const SizedBox(width: 12),
                            Expanded(child: i + 1 < datos.length ? _Dato(datos[i + 1]) : const SizedBox.shrink()),
                          ],
                        ),
                      ),
                  ],
                ),
              ),
            ),
            if (vacante.description.trim().isNotEmpty) ...[
              const SizedBox(height: 22),
              Text('Descripción', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              Text(vacante.description.trim()),
            ],
            if (vacante.educationPreferences.isNotEmpty) ...[
              const SizedBox(height: 22),
              Text('Carreras afines', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final c in vacante.educationPreferences)
                    Insignia(
                      c.name,
                      colores: coloresDeEstado(c.isRequired ? 'blue' : 'gray'),
                      icono: Icons.school_outlined,
                    ),
                ],
              ),
            ],
            if (vacante.skills.isNotEmpty) ...[
              const SizedBox(height: 22),
              Text('Habilidades', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 4),
              const Text(
                'Las marcadas en azul son requeridas; el resto suma puntos.',
                style: TextStyle(color: AppColors.textoSuave, fontSize: 13),
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final s in vacante.skills)
                    Insignia(
                      s.skillName,
                      colores: coloresDeEstado(s.importance == 'required' ? 'blue' : 'gray'),
                      icono: s.importance == 'required' ? Icons.check_circle_outline_rounded : null,
                    ),
                ],
              ),
            ],
          ],
        ),
        bottomNavigationBar: _BarraAccion(
          accessToken: widget.accessToken,
          yaPostulado: _yaPostulado,
          onPostular: widget.accessToken == null ? null : () => _abrirPostulacion(widget.accessToken!),
        ),
      ),
    );
  }
}

class _Dato extends StatelessWidget {
  final (IconData, String, String) dato;
  const _Dato(this.dato);

  @override
  Widget build(BuildContext context) {
    final (icono, etiqueta, valor) = dato;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icono, size: 18, color: AppColors.textoTenue),
        const SizedBox(width: 8),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(etiqueta, style: const TextStyle(color: AppColors.textoSuave, fontSize: 12)),
              const SizedBox(height: 1),
              Text(valor, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
            ],
          ),
        ),
      ],
    );
  }
}

class _Afinidad extends StatelessWidget {
  final int porcentaje;
  const _Afinidad(this.porcentaje);

  @override
  Widget build(BuildContext context) {
    final colores = coloresDeAfinidad(porcentaje);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: colores.fondo, borderRadius: BorderRadius.circular(AppTheme.radio)),
      child: Row(
        children: [
          Icon(Icons.bolt_rounded, color: colores.color),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '$porcentaje% de afinidad con tu perfil',
                  style: TextStyle(color: colores.color, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 6),
                ClipRRect(
                  borderRadius: BorderRadius.circular(99),
                  child: LinearProgressIndicator(
                    value: porcentaje / 100,
                    minHeight: 6,
                    color: colores.color,
                    backgroundColor: Colors.white,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _BarraAccion extends StatelessWidget {
  final String? accessToken;
  final bool yaPostulado;
  final VoidCallback? onPostular;

  const _BarraAccion({
    required this.accessToken,
    required this.yaPostulado,
    required this.onPostular,
  });

  @override
  Widget build(BuildContext context) {
    final token = accessToken;
    return DecoratedBox(
      decoration: const BoxDecoration(
        color: AppColors.superficie,
        border: Border(top: BorderSide(color: AppColors.borde)),
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 12),
          child: token != null
              ? (yaPostulado
                  ? Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                      decoration: BoxDecoration(
                        color: AppColors.exitoSuave,
                        borderRadius: BorderRadius.circular(AppTheme.radio),
                        border: Border.all(color: AppColors.exito),
                      ),
                      child: const Row(
                        children: [
                          Icon(Icons.check_circle_rounded, color: AppColors.exito, size: 22),
                          SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Ya te postulaste a esta vacante',
                                  style: TextStyle(
                                    color: AppColors.exito,
                                    fontWeight: FontWeight.w700,
                                    fontSize: 14,
                                  ),
                                ),
                                SizedBox(height: 2),
                                Text(
                                  'Podés ver su seguimiento en Postulaciones (móvil y web).',
                                  style: TextStyle(color: AppColors.textoSuave, fontSize: 12),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    )
                  : FilledButton(
                      onPressed: onPostular,
                      child: const Text('Postularme'),
                    ))
              : Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    FilledButton(
                      // La vista pública se abre desde el login: volver al inicio es volver a iniciar sesión.
                      onPressed: () => Navigator.of(context).popUntil((ruta) => ruta.isFirst),
                      child: const Text('Iniciar sesión para postularme'),
                    ),
                    TextButton(
                      onPressed: () =>
                          Navigator.of(context).push(MaterialPageRoute(builder: (_) => const RegistroEgresadoScreen())),
                      child: const Text('Crear cuenta de egresado'),
                    ),
                  ],
                ),
        ),
      ),
    );
  }
}

class _RelevanciaSemantica extends StatelessWidget {
  final int score;
  final String? razon;

  const _RelevanciaSemantica({required this.score, this.razon});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFEFF6FF),
        borderRadius: BorderRadius.circular(AppTheme.radio),
        border: Border.all(color: const Color(0xFFBFDBFE)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.auto_awesome, color: Color(0xFF1D4ED8), size: 20),
              const SizedBox(width: 8),
              Text(
                '$score% Relevancia Semántica (IA)',
                style: const TextStyle(
                  color: Color(0xFF1E3A8A),
                  fontWeight: FontWeight.w700,
                  fontSize: 15,
                ),
              ),
            ],
          ),
          if (razon != null && razon!.trim().isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              razon!.trim(),
              style: const TextStyle(
                color: Color(0xFF1E40AF),
                fontSize: 13,
                height: 1.35,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
