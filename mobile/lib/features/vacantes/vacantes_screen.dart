import 'package:flutter/material.dart';

import '../../core/models/estadisticas_publicas.dart';
import '../../core/models/vacante.dart';
import '../../core/services/vacante_service.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/formatos.dart';
import '../../core/widgets/boton_ayuda.dart';
import '../../core/widgets/tarjeta_vacante.dart';
import '../../core/widgets/vistas_estado.dart';
import '../auth/registro_egresado_screen.dart';
import '../recomendaciones/recomendaciones_screen.dart';
import 'vacante_detalle_screen.dart';

/// Búsqueda de vacantes (HU-13). Sin [accessToken] es la vista pública de la
/// HU-34: todas las ofertas vigentes, las estadísticas de la plataforma y una
/// invitación a crear cuenta para postularse.
class VacantesScreen extends StatefulWidget {
  final String? accessToken;

  const VacantesScreen({super.key, this.accessToken});

  @override
  State<VacantesScreen> createState() => _VacantesScreenState();
}

class _VacantesScreenState extends State<VacantesScreen> {
  final _servicio = VacanteService();
  final _busquedaCtrl = TextEditingController();

  late Future<List<Vacante>> _futuro = _buscar();
  late final Future<EstadisticasPublicas>? _estadisticas = _anonimo ? _servicio.estadisticasPublicas() : null;
  String _orden = 'fecha';
  bool _modoSemantico = false;
  List<String> _sugerenciasIa = [];
  bool _iaDisponible = true;

  bool get _anonimo => widget.accessToken == null;

  Future<List<Vacante>> _buscar() async {
    final query = _busquedaCtrl.text.trim();
    if (_modoSemantico && query.isNotEmpty) {
      try {
        final res = await _servicio.buscarSemantica(widget.accessToken, consulta: query);
        if (mounted) {
          setState(() {
            _sugerenciasIa = res.sugerencias;
            _iaDisponible = res.iaDisponible;
          });
        }
        return res.items;
      } catch (e) {
        if (mounted) {
          setState(() {
            _sugerenciasIa = [];
            _iaDisponible = false;
          });
        }
        // Fallback elegante a búsqueda tradicional
        return _servicio.buscar(widget.accessToken, q: query, ordenarPor: _orden);
      }
    } else {
      if (mounted && _sugerenciasIa.isNotEmpty) {
        setState(() {
          _sugerenciasIa = [];
          _iaDisponible = true;
        });
      }
      return _servicio.buscar(widget.accessToken, q: query, ordenarPor: _orden);
    }
  }

  @override
  void dispose() {
    _busquedaCtrl.dispose();
    super.dispose();
  }

  Future<void> _recargar() async {
    if (!mounted) return;
    final futuro = _buscar();
    setState(() { _futuro = futuro; });
    await futuro.catchError((_) => <Vacante>[]);
  }

  void _ordenarPor(String orden) {
    if (orden == _orden) return;
    _orden = orden;
    _recargar();
  }

  void _abrir(Vacante vacante) {
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => VacanteDetalleScreen(accessToken: widget.accessToken, vacante: vacante)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_anonimo ? 'Ofertas laborales' : 'Vacantes'),
        actions: [
          const BotonAyuda('vacantes'),
          if (!_anonimo)
            IconButton(
              tooltip: 'Recomendadas para vos',
              icon: const Icon(Icons.auto_awesome_outlined),
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => RecomendacionesScreen(accessToken: widget.accessToken!)),
              ),
            ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 10),
            child: ValueListenableBuilder<TextEditingValue>(
              valueListenable: _busquedaCtrl,
              builder: (context, valor, _) => TextField(
                controller: _busquedaCtrl,
                textInputAction: TextInputAction.search,
                onSubmitted: (_) => _recargar(),
                decoration: InputDecoration(
                  hintText: _modoSemantico ? 'Describí en lenguaje natural (ej. programador remoto)' : 'Cargo, palabra clave o tecnología',
                  prefixIcon: const Icon(Icons.search_rounded),
                  suffixIcon: valor.text.isEmpty
                      ? null
                      : IconButton(
                          tooltip: 'Limpiar búsqueda',
                          icon: const Icon(Icons.close_rounded),
                          onPressed: () {
                            _busquedaCtrl.clear();
                            _recargar();
                          },
                        ),
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 6),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  FilterChip(
                    avatar: Icon(
                      Icons.auto_awesome,
                      size: 15,
                      color: _modoSemantico ? Colors.white : const Color(0xFF1D4ED8),
                    ),
                    label: const Text('Búsqueda Semántica IA'),
                    selected: _modoSemantico,
                    onSelected: (val) {
                      setState(() {
                        _modoSemantico = val;
                        _sugerenciasIa = [];
                      });
                      _recargar();
                    },
                    selectedColor: const Color(0xFF1D4ED8),
                    backgroundColor: const Color(0xFFEFF6FF),
                    side: const BorderSide(color: Color(0xFFBFDBFE)),
                    showCheckmark: false,
                    labelStyle: TextStyle(
                      fontFamily: 'Inter',
                      fontSize: 12.5,
                      fontWeight: _modoSemantico ? FontWeight.w600 : FontWeight.w500,
                      color: _modoSemantico ? Colors.white : const Color(0xFF1D4ED8),
                    ),
                  ),
                  if (!_modoSemantico && !_anonimo) ...[
                    const SizedBox(width: 8),
                    _ChipOrden('Más recientes', seleccionado: _orden == 'fecha', onTap: () => _ordenarPor('fecha')),
                    const SizedBox(width: 8),
                    _ChipOrden('Mayor afinidad', seleccionado: _orden == 'afinidad', onTap: () => _ordenarPor('afinidad')),
                  ],
                ],
              ),
            ),
          ),
          if (_modoSemantico && !_iaDisponible)
            Container(
              margin: const EdgeInsets.fromLTRB(16, 4, 16, 6),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: const Color(0xFFFEF3C7),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFFFDE68A)),
              ),
              child: const Row(
                children: [
                  Icon(Icons.info_outline, size: 16, color: Color(0xFFB45309)),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Servicio IA temporalmente inactivo. Usando coincidencia estructurada.',
                      style: TextStyle(fontSize: 12, color: Color(0xFF92400E)),
                    ),
                  ),
                ],
              ),
            ),
          if (_modoSemantico && _sugerenciasIa.isNotEmpty)
            Container(
              margin: const EdgeInsets.fromLTRB(16, 4, 16, 6),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: const Color(0xFFEFF6FF),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFFBFDBFE)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.lightbulb_outline, size: 16, color: Color(0xFF1D4ED8)),
                      SizedBox(width: 6),
                      Text(
                        'Sugerencias para ampliar tu búsqueda:',
                        style: TextStyle(fontWeight: FontWeight.w600, fontSize: 12, color: Color(0xFF1E3A8A)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  for (final s in _sugerenciasIa)
                    GestureDetector(
                      onTap: () {
                        _busquedaCtrl.text = s;
                        _recargar();
                      },
                      child: Padding(
                        padding: const EdgeInsets.symmetric(vertical: 2),
                        child: Text(
                          '• $s',
                          style: const TextStyle(
                            fontSize: 12,
                            color: Color(0xFF2563EB),
                            decoration: TextDecoration.underline,
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
          Expanded(
            child: FutureBuilder<List<Vacante>>(
              future: _futuro,
              builder: (context, snapshot) {
                final cargando = snapshot.connectionState == ConnectionState.waiting;
                if (snapshot.hasData) {
                  // Mientras llega una búsqueda nueva se mantiene la anterior con una barra de progreso.
                  return Column(
                    children: [
                      SizedBox(height: 2, child: cargando ? const LinearProgressIndicator() : null),
                      Expanded(child: RefreshIndicator(onRefresh: _recargar, child: _listado(snapshot.data!))),
                    ],
                  );
                }
                if (cargando) return const VistaCargando();
                return VistaMensaje.error(snapshot.error, onReintentar: _recargar);
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _listado(List<Vacante> vacantes) {
    final buscando = _busquedaCtrl.text.trim().isNotEmpty;
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 6, 16, 28),
      children: [
        if (_anonimo) ...[
          _BannerPublico(_estadisticas),
          const SizedBox(height: 14),
        ],
        if (vacantes.isEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 40),
            child: VistaMensaje(
              icono: Icons.search_off_rounded,
              titulo: buscando ? 'Sin resultados' : 'No hay vacantes publicadas',
              mensaje: buscando
                  ? 'No encontramos vacantes para "${_busquedaCtrl.text.trim()}". Probá con otras palabras.'
                  : 'Cuando las empresas publiquen ofertas, las vas a ver acá.',
            ),
          )
        else ...[
          Text(
            vacantes.length == 1 ? '1 vacante' : '${vacantes.length} vacantes',
            style: const TextStyle(color: AppColors.textoSuave, fontSize: 13, fontWeight: FontWeight.w500),
          ),
          const SizedBox(height: 10),
          for (final vacante in vacantes) ...[
            TarjetaVacante(vacante: vacante, onTap: () => _abrir(vacante)),
            const SizedBox(height: 12),
          ],
        ],
        if (_anonimo) ...[
          const SizedBox(height: 8),
          const _InvitacionRegistro(),
        ],
      ],
    );
  }
}

class _ChipOrden extends StatelessWidget {
  final String texto;
  final bool seleccionado;
  final VoidCallback onTap;
  const _ChipOrden(this.texto, {required this.seleccionado, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return ChoiceChip(
      label: Text(texto),
      selected: seleccionado,
      onSelected: (_) => onTap(),
      showCheckmark: false,
      selectedColor: AppColors.primarioSuave,
      side: BorderSide(color: seleccionado ? AppColors.primarioBorde : AppColors.borde),
      labelStyle: TextStyle(
        fontFamily: 'Inter',
        fontSize: 13,
        fontWeight: seleccionado ? FontWeight.w600 : FontWeight.w500,
        color: seleccionado ? AppColors.primario : AppColors.textoSuave,
      ),
    );
  }
}

/// Estadísticas públicas de la plataforma (HU-34) para quien todavía no tiene cuenta.
class _BannerPublico extends StatelessWidget {
  final Future<EstadisticasPublicas>? estadisticas;
  const _BannerPublico(this.estadisticas);

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<EstadisticasPublicas>(
      future: estadisticas,
      builder: (context, snapshot) {
        final datos = snapshot.data;
        if (datos == null) return const SizedBox.shrink();
        return Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(color: AppColors.primario, borderRadius: BorderRadius.circular(AppTheme.radio)),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              IntrinsicHeight(
                child: Row(
                  children: [
                    Expanded(child: _Cifra(valor: datos.vacantesActivas, etiqueta: 'vacantes activas')),
                    const VerticalDivider(color: Color(0x33FFFFFF), width: 24, thickness: 1),
                    Expanded(child: _Cifra(valor: datos.empresasVerificadas, etiqueta: 'empresas verificadas')),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'Datos al ${fechaCorta(datos.corte)}. Iniciá sesión para ver tu afinidad con cada oferta y postularte.',
                style: const TextStyle(color: Color(0xFFC7D2FE), fontSize: 12.5, height: 1.4),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _Cifra extends StatelessWidget {
  final int valor;
  final String etiqueta;
  const _Cifra({required this.valor, required this.etiqueta});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('$valor', style: const TextStyle(color: Colors.white, fontSize: 26, fontWeight: FontWeight.w700, height: 1.1)),
        const SizedBox(height: 2),
        Text(etiqueta, style: const TextStyle(color: Color(0xFFC7D2FE), fontSize: 13)),
      ],
    );
  }
}

class _InvitacionRegistro extends StatelessWidget {
  const _InvitacionRegistro();

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('¿Sos egresado?', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 4),
            const Text(
              'Creá tu cuenta para postularte, seguir tus procesos y recibir recomendaciones según tu perfil.',
              style: TextStyle(color: AppColors.textoSuave),
            ),
            const SizedBox(height: 14),
            FilledButton(
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const RegistroEgresadoScreen()),
              ),
              child: const Text('Crear mi cuenta'),
            ),
          ],
        ),
      ),
    );
  }
}
