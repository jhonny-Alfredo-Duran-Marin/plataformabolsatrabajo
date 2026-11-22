import 'package:flutter/material.dart';

import '../../core/models/estadisticas_publicas.dart';
import '../../core/models/vacante.dart';
import '../../core/services/postulacion_service.dart';
import '../../core/services/vacante_service.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/formatos.dart';
import '../../core/widgets/boton_ayuda.dart';
import '../../core/widgets/tarjeta_vacante.dart';
import '../../core/widgets/vistas_estado.dart';
import '../auth/registro_egresado_screen.dart';
import '../recomendaciones/recomendaciones_screen.dart';
import 'vacante_detalle_screen.dart';

/// Búsqueda de vacantes móvil (HU-13 / HU-35) con palabras clave y filtros por
/// ciudad, modalidad y carrera. Sin [accessToken] es la vista pública de la
/// HU-34: todas las ofertas vigentes, las estadísticas de la plataforma y una
/// invitación a crear cuenta para postularse.
class VacantesScreen extends StatefulWidget {
  final String? accessToken;
  final VacanteService? vacanteService;
  final PostulacionService? postulacionService;

  const VacantesScreen({
    super.key,
    this.accessToken,
    this.vacanteService,
    this.postulacionService,
  });

  @override
  State<VacantesScreen> createState() => _VacantesScreenState();
}

class _VacantesScreenState extends State<VacantesScreen> {
  late final VacanteService _servicio = widget.vacanteService ?? VacanteService();
  late final PostulacionService _postulacionServicio = widget.postulacionService ?? PostulacionService();
  final _busquedaCtrl = TextEditingController();

  late Future<List<Vacante>> _futuro = _buscar();
  late final Future<EstadisticasPublicas>? _estadisticas = _anonimo ? _servicio.estadisticasPublicas() : null;

  FiltrosDisponiblesVacantes _filtros = const FiltrosDisponiblesVacantes();
  String? _ciudadSeleccionada;
  String? _modalidadSeleccionada;
  CarreraFiltro? _carreraSeleccionada;
  Set<String> _vacantesPostuladasIds = {};

  String _orden = 'fecha';
  bool _modoSemantico = false;
  List<String> _sugerenciasIa = [];
  bool _iaDisponible = true;

  bool get _anonimo => widget.accessToken == null;
  bool get _hayFiltrosActivos =>
      _ciudadSeleccionada != null || _modalidadSeleccionada != null || _carreraSeleccionada != null;

  @override
  void initState() {
    super.initState();
    _cargarFiltrosDisponibles();
    if (!_anonimo) {
      _cargarPostuladas();
    }
  }

  Future<void> _cargarFiltrosDisponibles() async {
    try {
      final filtros = await _servicio.obtenerFiltrosDisponibles();
      if (mounted) {
        setState(() => _filtros = filtros);
      }
    } catch (_) {
      // Si falla la carga de filtros, se mantienen las modalidades base sin bloquear la búsqueda.
    }
  }

  Future<void> _cargarPostuladas() async {
    final token = widget.accessToken;
    if (token == null) return;
    try {
      final ids = await _postulacionServicio.obtenerVacantesPostuladasIds(token);
      if (mounted) {
        setState(() => _vacantesPostuladasIds = ids);
      }
    } catch (_) {
      // No bloquea el listado si falla la consulta auxiliar.
    }
  }

  Future<List<Vacante>> _buscar() async {
    final query = _busquedaCtrl.text.trim();
    if (_modoSemantico && query.isNotEmpty) {
      try {
        final res = await _servicio.buscarSemantica(
          widget.accessToken,
          consulta: query,
          ciudad: _ciudadSeleccionada,
          modalidad: _modalidadSeleccionada,
          carreraId: _carreraSeleccionada?.id,
        );
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
        // Fallback elegante a búsqueda tradicional conservando todos los filtros seleccionados
        return _servicio.buscar(
          widget.accessToken,
          q: query,
          ciudad: _ciudadSeleccionada,
          modalidad: _modalidadSeleccionada,
          carreraId: _carreraSeleccionada?.id,
          ordenarPor: _orden,
        );
      }
    } else {
      if (mounted && _sugerenciasIa.isNotEmpty) {
        setState(() {
          _sugerenciasIa = [];
          _iaDisponible = true;
        });
      }
      return _servicio.buscar(
        widget.accessToken,
        q: query,
        ciudad: _ciudadSeleccionada,
        modalidad: _modalidadSeleccionada,
        carreraId: _carreraSeleccionada?.id,
        ordenarPor: _orden,
      );
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
    setState(() {
      _futuro = futuro;
    });
    if (!_anonimo) {
      _cargarPostuladas();
    }
    await futuro.catchError((_) => <Vacante>[]);
  }

  void _ordenarPor(String orden) {
    if (orden == _orden) return;
    _orden = orden;
    _recargar();
  }

  void _limpiarFiltros() {
    setState(() {
      _ciudadSeleccionada = null;
      _modalidadSeleccionada = null;
      _carreraSeleccionada = null;
    });
    _recargar();
  }

  Future<void> _seleccionarCiudad() async {
    final resultado = await _mostrarSelector<String>(
      titulo: 'Filtrar por ciudad',
      opcionTodas: 'Todas las ciudades',
      opciones: _filtros.ciudades,
      seleccionActual: _ciudadSeleccionada,
      etiqueta: (c) => c,
      permitirBuscar: _filtros.ciudades.length > 6,
    );
    if (resultado == null) return;
    setState(() => _ciudadSeleccionada = resultado.valor);
    _recargar();
  }

  Future<void> _seleccionarModalidad() async {
    final resultado = await _mostrarSelector<String>(
      titulo: 'Filtrar por modalidad',
      opcionTodas: 'Todas las modalidades',
      opciones: _filtros.modalidades,
      seleccionActual: _modalidadSeleccionada,
      etiqueta: Vacante.etiquetaModalidad,
    );
    if (resultado == null) return;
    setState(() => _modalidadSeleccionada = resultado.valor);
    _recargar();
  }

  Future<void> _seleccionarCarrera() async {
    final resultado = await _mostrarSelector<CarreraFiltro>(
      titulo: 'Filtrar por carrera',
      opcionTodas: 'Todas las carreras',
      opciones: _filtros.carreras,
      seleccionActual: _carreraSeleccionada,
      etiqueta: (c) => c.name,
      sonIguales: (a, b) => a.id == b.id,
      permitirBuscar: _filtros.carreras.length > 6,
    );
    if (resultado == null) return;
    setState(() => _carreraSeleccionada = resultado.valor);
    _recargar();
  }

  Future<_ResultadoSelector<T>?> _mostrarSelector<T>({
    required String titulo,
    required String opcionTodas,
    required List<T> opciones,
    required T? seleccionActual,
    required String Function(T) etiqueta,
    bool Function(T, T)? sonIguales,
    bool permitirBuscar = false,
  }) {
    final iguales = sonIguales ?? (a, b) => a == b;
    return showModalBottomSheet<_ResultadoSelector<T>>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (ctx) {
        var filtroTexto = '';
        return StatefulBuilder(
          builder: (ctx, setModalState) {
            final filtradas = filtroTexto.trim().isEmpty
                ? opciones
                : opciones
                    .where((o) => etiqueta(o).toLowerCase().contains(filtroTexto.trim().toLowerCase()))
                    .toList();
            return SafeArea(
              child: ConstrainedBox(
                constraints: BoxConstraints(maxHeight: MediaQuery.of(ctx).size.height * 0.72),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
                      child: Text(titulo, style: Theme.of(ctx).textTheme.titleMedium),
                    ),
                    if (permitirBuscar)
                      Padding(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
                        child: TextField(
                          decoration: const InputDecoration(
                            hintText: 'Buscar opción...',
                            prefixIcon: Icon(Icons.search_rounded),
                            isDense: true,
                          ),
                          onChanged: (v) => setModalState(() => filtroTexto = v),
                        ),
                      ),
                    Flexible(
                      child: ListView(
                        shrinkWrap: true,
                        children: [
                          ListTile(
                            title: Text(opcionTodas),
                            trailing: seleccionActual == null
                                ? const Icon(Icons.check_rounded, color: AppColors.primario)
                                : null,
                            onTap: () => Navigator.of(ctx).pop(_ResultadoSelector<T>(null)),
                          ),
                          if (filtradas.isEmpty)
                            const Padding(
                              padding: EdgeInsets.all(20),
                              child: Text(
                                'No hay opciones disponibles con ese criterio.',
                                style: TextStyle(color: AppColors.textoSuave),
                              ),
                            )
                          else
                            for (final opcion in filtradas)
                              ListTile(
                                title: Text(etiqueta(opcion)),
                                trailing: seleccionActual != null && iguales(opcion, seleccionActual)
                                    ? const Icon(Icons.check_rounded, color: AppColors.primario)
                                    : null,
                                onTap: () => Navigator.of(ctx).pop(_ResultadoSelector<T>(opcion)),
                              ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _abrir(Vacante vacante) async {
    final postulo = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => VacanteDetalleScreen(
          accessToken: widget.accessToken,
          vacante: vacante,
          yaPostulado: _vacantesPostuladasIds.contains(vacante.id),
          vacanteService: _servicio,
          postulacionService: _postulacionServicio,
        ),
      ),
    );
    if (!mounted) return;
    if (postulo == true) {
      setState(() => _vacantesPostuladasIds = {..._vacantesPostuladasIds, vacante.id});
    }
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
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
            child: ValueListenableBuilder<TextEditingValue>(
              valueListenable: _busquedaCtrl,
              builder: (context, valor, _) => TextField(
                controller: _busquedaCtrl,
                textInputAction: TextInputAction.search,
                onSubmitted: (_) => _recargar(),
                decoration: InputDecoration(
                  hintText: _modoSemantico
                      ? 'Describí en lenguaje natural (ej. programador remoto)'
                      : 'Cargo, palabra clave o tecnología',
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
          // Filtros combinables HU-35: Ciudad, Modalidad y Carrera
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 6),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _ChipFiltroDesplegable(
                    icono: Icons.location_on_outlined,
                    etiqueta: _ciudadSeleccionada ?? 'Ciudad',
                    activo: _ciudadSeleccionada != null,
                    onTap: _seleccionarCiudad,
                  ),
                  const SizedBox(width: 8),
                  _ChipFiltroDesplegable(
                    icono: Icons.work_outline_rounded,
                    etiqueta: _modalidadSeleccionada != null
                        ? Vacante.etiquetaModalidad(_modalidadSeleccionada!)
                        : 'Modalidad',
                    activo: _modalidadSeleccionada != null,
                    onTap: _seleccionarModalidad,
                  ),
                  const SizedBox(width: 8),
                  _ChipFiltroDesplegable(
                    icono: Icons.school_outlined,
                    etiqueta: _carreraSeleccionada?.name ?? 'Carrera',
                    activo: _carreraSeleccionada != null,
                    onTap: _seleccionarCarrera,
                  ),
                  if (_hayFiltrosActivos) ...[
                    const SizedBox(width: 8),
                    ActionChip(
                      avatar: const Icon(Icons.filter_alt_off_outlined, size: 16, color: AppColors.peligro),
                      label: const Text('Limpiar filtros'),
                      onPressed: _limpiarFiltros,
                      side: const BorderSide(color: AppColors.borde),
                      labelStyle: const TextStyle(
                        fontFamily: 'Inter',
                        fontSize: 12.5,
                        fontWeight: FontWeight.w600,
                        color: AppColors.peligro,
                      ),
                    ),
                  ],
                ],
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
    final query = _busquedaCtrl.text.trim();
    final buscando = query.isNotEmpty || _hayFiltrosActivos;
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
                  ? (query.isNotEmpty
                      ? 'No encontramos vacantes para "$query" con los filtros actuales. Probá ajustando tu búsqueda.'
                      : 'No encontramos vacantes que coincidan con los filtros seleccionados.')
                  : 'Cuando las empresas publiquen ofertas, las vas a ver acá.',
              textoAccion: _hayFiltrosActivos ? 'Limpiar filtros' : null,
              onAccion: _hayFiltrosActivos ? _limpiarFiltros : null,
            ),
          )
        else ...[
          Text(
            vacantes.length == 1 ? '1 vacante' : '${vacantes.length} vacantes',
            style: const TextStyle(color: AppColors.textoSuave, fontSize: 13, fontWeight: FontWeight.w500),
          ),
          const SizedBox(height: 10),
          for (final vacante in vacantes) ...[
            TarjetaVacante(
              vacante: vacante,
              yaPostulado: _vacantesPostuladasIds.contains(vacante.id),
              onTap: () => _abrir(vacante),
            ),
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

class _ResultadoSelector<T> {
  final T? valor;
  const _ResultadoSelector(this.valor);
}

class _ChipFiltroDesplegable extends StatelessWidget {
  final IconData icono;
  final String etiqueta;
  final bool activo;
  final VoidCallback onTap;

  const _ChipFiltroDesplegable({
    required this.icono,
    required this.etiqueta,
    required this.activo,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InputChip(
      avatar: Icon(icono, size: 16, color: activo ? AppColors.primario : AppColors.textoSuave),
      label: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 160),
            child: Text(etiqueta, overflow: TextOverflow.ellipsis),
          ),
          const SizedBox(width: 2),
          Icon(Icons.keyboard_arrow_down_rounded, size: 16, color: activo ? AppColors.primario : AppColors.textoSuave),
        ],
      ),
      selected: activo,
      showCheckmark: false,
      onPressed: onTap,
      selectedColor: AppColors.primarioSuave,
      side: BorderSide(color: activo ? AppColors.primarioBorde : AppColors.borde),
      labelStyle: TextStyle(
        fontFamily: 'Inter',
        fontSize: 12.5,
        fontWeight: activo ? FontWeight.w600 : FontWeight.w500,
        color: activo ? AppColors.primario : AppColors.textoSuave,
      ),
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
