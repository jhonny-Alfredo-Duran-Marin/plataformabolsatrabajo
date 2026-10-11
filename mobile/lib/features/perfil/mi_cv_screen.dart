import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

import '../../core/models/cv_item.dart';
import '../../core/services/perfil_service.dart';
import '../../core/utils/formatos.dart';
import '../../core/widgets/vistas_estado.dart';

/// Pantalla con pestañas para las secciones del CV: formación, experiencia,
/// idiomas, certificaciones y habilidades (backend/app/features/perfil/router.py).
class MiCvScreen extends StatefulWidget {
  final String accessToken;

  const MiCvScreen({super.key, required this.accessToken});

  @override
  State<MiCvScreen> createState() => _MiCvScreenState();
}

class _MiCvScreenState extends State<MiCvScreen> {
  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 5,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Mi CV'),
          bottom: const TabBar(
            isScrollable: true,
            tabAlignment: TabAlignment.start,
            tabs: [
              Tab(text: 'Formación'),
              Tab(text: 'Experiencia'),
              Tab(text: 'Idiomas'),
              Tab(text: 'Certificaciones'),
              Tab(text: 'Habilidades'),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            _FormacionTab(accessToken: widget.accessToken),
            _ExperienciaTab(accessToken: widget.accessToken),
            _IdiomasTab(accessToken: widget.accessToken),
            _CertificacionesTab(accessToken: widget.accessToken),
            _HabilidadesTab(accessToken: widget.accessToken),
          ],
        ),
      ),
    );
  }
}

/// Estado y comportamiento común a las listas de la sección CV: cargar,
/// mostrar error, eliminar y abrir el formulario de alta.
abstract class _SeccionCvState<T, W extends StatefulWidget> extends State<W> {
  String get accessToken;

  List<T> items = [];
  bool cargando = true;
  String? error;

  Future<List<T>> cargar();
  Future<void> eliminar(String id);
  String idDe(T item);
  Widget tituloDe(T item);
  Widget? subtituloDe(T item);
  Future<void> abrirFormularioAlta();
  IconData get iconoVacio;
  String get textoVacio;

  @override
  void initState() {
    super.initState();
    _recargar();
  }

  Future<void> _recargar() async {
    if (!mounted) return;
    setState(() {
      cargando = true;
      error = null;
    });
    try {
      final datos = await cargar();
      if (!mounted) return;
      setState(() {
        items = datos;
        cargando = false;
      });
    } catch (e) {
      // Cualquier error (también una respuesta que no se pudo leer) apaga el indicador de carga.
      if (!mounted) return;
      setState(() {
        error = e is PerfilException ? e.mensaje : 'No se pudo cargar esta sección. Intentá de nuevo.';
        cargando = false;
      });
    }
  }

  Future<void> _eliminar(T item) async {
    if (!await _confirmarEliminacion(context)) return;
    try {
      await eliminar(idDe(item));
      if (mounted) _recargar();
    } on PerfilException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.mensaje)));
    }
  }

  Future<void> _agregar() async {
    await abrirFormularioAlta();
    if (mounted) _recargar();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: RefreshIndicator(onRefresh: _recargar, child: _cuerpo()),
      floatingActionButton: _BotonAgregar(onPressed: _agregar),
    );
  }

  Widget _cuerpo() {
    if (cargando) return const VistaCargando();
    if (error != null) return VistaMensaje.error(error, onReintentar: _recargar);
    if (items.isEmpty) {
      return VistaMensaje(icono: iconoVacio, titulo: 'Todavía no agregaste nada', mensaje: textoVacio);
    }
    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
      itemCount: items.length,
      separatorBuilder: (_, _) => const SizedBox(height: 10),
      itemBuilder: (context, i) {
        final item = items[i];
        return Card(
          child: ListTile(
            contentPadding: const EdgeInsets.fromLTRB(16, 6, 6, 6),
            title: tituloDe(item),
            subtitle: subtituloDe(item),
            trailing: IconButton(
              tooltip: 'Eliminar',
              icon: const Icon(Icons.delete_outline_rounded, color: AppColors.textoSuave),
              onPressed: () => _eliminar(item),
            ),
          ),
        );
      },
    );
  }
}

Future<bool> _confirmarEliminacion(BuildContext context) async {
  final ok = await showDialog<bool>(
    context: context,
    builder: (contexto) => AlertDialog(
      title: const Text('Eliminar del CV'),
      content: const Text('Se va a quitar de tu CV y ya no lo verán las empresas.'),
      actions: [
        TextButton(onPressed: () => Navigator.of(contexto).pop(false), child: const Text('Cancelar')),
        FilledButton(
          style: FilledButton.styleFrom(backgroundColor: AppColors.peligro),
          onPressed: () => Navigator.of(contexto).pop(true),
          child: const Text('Eliminar'),
        ),
      ],
    ),
  );
  return ok == true;
}

class _BotonAgregar extends StatelessWidget {
  final VoidCallback onPressed;
  const _BotonAgregar({required this.onPressed});

  @override
  Widget build(BuildContext context) {
    return FloatingActionButton.extended(
      onPressed: onPressed,
      icon: const Icon(Icons.add_rounded),
      label: const Text('Agregar'),
    );
  }
}

Future<void> _mostrarFormulario(BuildContext context, {required String titulo, required Widget contenido}) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    builder: (context) => Padding(
      padding: EdgeInsets.only(left: 20, right: 20, top: 20, bottom: MediaQuery.of(context).viewInsets.bottom + 20),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(titulo, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),
            contenido,
          ],
        ),
      ),
    ),
  );
}

// ─── Formación ─────────────────────────────────────────────────────

class _FormacionTab extends StatefulWidget {
  final String accessToken;
  const _FormacionTab({required this.accessToken});

  @override
  State<_FormacionTab> createState() => _FormacionTabState();
}

class _FormacionTabState extends _SeccionCvState<Formacion, _FormacionTab> {
  final _servicio = PerfilService();

  @override
  String get accessToken => widget.accessToken;

  @override
  Future<List<Formacion>> cargar() => _servicio.listarFormacion(accessToken);

  @override
  Future<void> eliminar(String id) => _servicio.eliminarFormacion(accessToken, id);

  @override
  String idDe(Formacion item) => item.id;

  @override
  Widget tituloDe(Formacion item) => Text(item.programa);

  @override
  Widget? subtituloDe(Formacion item) {
    final partes = [
      item.institucion.trim(),
      if (item.estadoAcademico != null) _estadosAcademicos[item.estadoAcademico] ?? capitalizar(item.estadoAcademico!),
    ].where((p) => p.isNotEmpty);
    return partes.isEmpty ? null : Text(partes.join(' · '));
  }

  static const _estadosAcademicos = {
    'en_curso': 'En curso',
    'concluido': 'Concluido',
    'egresado': 'Egresado',
    'titulado': 'Titulado',
  };

  @override
  IconData get iconoVacio => Icons.school_outlined;

  @override
  String get textoVacio => 'Agregá tu carrera y otros estudios.';

  @override
  Future<void> abrirFormularioAlta() async {
    final institucionCtrl = TextEditingController();
    final programaCtrl = TextEditingController();
    String estado = 'en_curso';

    await _mostrarFormulario(
      context,
      titulo: 'Agregar formación académica',
      contenido: StatefulBuilder(
        builder: (context, setSheetState) => Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: institucionCtrl,
              decoration: const InputDecoration(labelText: 'Institución'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: programaCtrl,
              decoration: const InputDecoration(labelText: 'Programa / carrera'),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: estado,
              decoration: const InputDecoration(labelText: 'Estado'),
              items: const [
                DropdownMenuItem(value: 'en_curso', child: Text('En curso')),
                DropdownMenuItem(value: 'concluido', child: Text('Concluido')),
                DropdownMenuItem(value: 'titulado', child: Text('Titulado')),
              ],
              onChanged: (v) => setSheetState(() => estado = v ?? estado),
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: () async {
                if (institucionCtrl.text.trim().isEmpty || programaCtrl.text.trim().isEmpty) return;
                try {
                  await _servicio.crearFormacion(
                    accessToken,
                    institucion: institucionCtrl.text.trim(),
                    programa: programaCtrl.text.trim(),
                    estadoAcademico: estado,
                  );
                  if (context.mounted) Navigator.of(context).pop();
                } on PerfilException catch (e) {
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.mensaje)));
                  }
                }
              },
              child: const Text('Agregar'),
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Experiencia ───────────────────────────────────────────────────

class _ExperienciaTab extends StatefulWidget {
  final String accessToken;
  const _ExperienciaTab({required this.accessToken});

  @override
  State<_ExperienciaTab> createState() => _ExperienciaTabState();
}

class _ExperienciaTabState extends _SeccionCvState<Experiencia, _ExperienciaTab> {
  final _servicio = PerfilService();

  @override
  String get accessToken => widget.accessToken;

  @override
  Future<List<Experiencia>> cargar() => _servicio.listarExperiencia(accessToken);

  @override
  Future<void> eliminar(String id) => _servicio.eliminarExperiencia(accessToken, id);

  @override
  String idDe(Experiencia item) => item.id;

  @override
  Widget tituloDe(Experiencia item) => Text(item.cargo);

  @override
  Widget? subtituloDe(Experiencia item) => Text(item.empresa);

  @override
  IconData get iconoVacio => Icons.work_outline_rounded;

  @override
  String get textoVacio => 'Sumá pasantías, trabajos o proyectos en los que participaste.';

  @override
  Future<void> abrirFormularioAlta() async {
    final empresaCtrl = TextEditingController();
    final cargoCtrl = TextEditingController();
    final descripcionCtrl = TextEditingController();

    await _mostrarFormulario(
      context,
      titulo: 'Agregar experiencia laboral',
      contenido: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            controller: empresaCtrl,
            decoration: const InputDecoration(labelText: 'Empresa'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: cargoCtrl,
            decoration: const InputDecoration(labelText: 'Cargo'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: descripcionCtrl,
            decoration: const InputDecoration(labelText: 'Descripción (opcional)'),
            maxLines: 3,
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: () async {
              if (empresaCtrl.text.trim().isEmpty || cargoCtrl.text.trim().isEmpty) return;
              try {
                await _servicio.crearExperiencia(
                  accessToken,
                  empresa: empresaCtrl.text.trim(),
                  cargo: cargoCtrl.text.trim(),
                  descripcion: descripcionCtrl.text.trim().isEmpty ? null : descripcionCtrl.text.trim(),
                );
                if (context.mounted) Navigator.of(context).pop();
              } on PerfilException catch (e) {
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.mensaje)));
                }
              }
            },
            child: const Text('Agregar'),
          ),
        ],
      ),
    );
  }
}

// ─── Idiomas ───────────────────────────────────────────────────────

class _IdiomasTab extends StatefulWidget {
  final String accessToken;
  const _IdiomasTab({required this.accessToken});

  @override
  State<_IdiomasTab> createState() => _IdiomasTabState();
}

class _IdiomasTabState extends _SeccionCvState<Idioma, _IdiomasTab> {
  final _servicio = PerfilService();

  @override
  String get accessToken => widget.accessToken;

  @override
  Future<List<Idioma>> cargar() => _servicio.listarIdiomas(accessToken);

  @override
  Future<void> eliminar(String id) => _servicio.eliminarIdioma(accessToken, id);

  @override
  String idDe(Idioma item) => item.id;

  @override
  Widget tituloDe(Idioma item) => Text(item.idioma);

  @override
  Widget? subtituloDe(Idioma item) => Text(_nivelLegible(item.nivel));

  @override
  IconData get iconoVacio => Icons.translate_rounded;

  @override
  String get textoVacio => 'Indicá los idiomas que manejás y tu nivel.';

  String _nivelLegible(String nivel) {
    const etiquetas = {'basico': 'Básico', 'intermedio': 'Intermedio', 'avanzado': 'Avanzado', 'nativo': 'Nativo'};
    return etiquetas[nivel] ?? nivel;
  }

  @override
  Future<void> abrirFormularioAlta() async {
    final idiomaCtrl = TextEditingController();
    String nivel = 'basico';

    await _mostrarFormulario(
      context,
      titulo: 'Agregar idioma',
      contenido: StatefulBuilder(
        builder: (context, setSheetState) => Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: idiomaCtrl,
              decoration: const InputDecoration(labelText: 'Idioma'),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: nivel,
              decoration: const InputDecoration(labelText: 'Nivel'),
              items: const [
                DropdownMenuItem(value: 'basico', child: Text('Básico')),
                DropdownMenuItem(value: 'intermedio', child: Text('Intermedio')),
                DropdownMenuItem(value: 'avanzado', child: Text('Avanzado')),
                DropdownMenuItem(value: 'nativo', child: Text('Nativo')),
              ],
              onChanged: (v) => setSheetState(() => nivel = v ?? nivel),
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: () async {
                if (idiomaCtrl.text.trim().isEmpty) return;
                try {
                  await _servicio.crearIdioma(accessToken, idioma: idiomaCtrl.text.trim(), nivel: nivel);
                  if (context.mounted) Navigator.of(context).pop();
                } on PerfilException catch (e) {
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.mensaje)));
                  }
                }
              },
              child: const Text('Agregar'),
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Certificaciones ─────────────────────────────────────────────────

class _CertificacionesTab extends StatefulWidget {
  final String accessToken;
  const _CertificacionesTab({required this.accessToken});

  @override
  State<_CertificacionesTab> createState() => _CertificacionesTabState();
}

class _CertificacionesTabState extends _SeccionCvState<Certificacion, _CertificacionesTab> {
  final _servicio = PerfilService();

  @override
  String get accessToken => widget.accessToken;

  @override
  Future<List<Certificacion>> cargar() => _servicio.listarCertificaciones(accessToken);

  @override
  Future<void> eliminar(String id) => _servicio.eliminarCertificacion(accessToken, id);

  @override
  String idDe(Certificacion item) => item.id;

  @override
  Widget tituloDe(Certificacion item) => Text(item.nombre);

  @override
  Widget? subtituloDe(Certificacion item) => item.entidadEmisora == null ? null : Text(item.entidadEmisora!);

  @override
  IconData get iconoVacio => Icons.workspace_premium_outlined;

  @override
  String get textoVacio => 'Cursos y certificaciones que respalden tus conocimientos.';

  @override
  Future<void> abrirFormularioAlta() async {
    final nombreCtrl = TextEditingController();
    final entidadCtrl = TextEditingController();

    await _mostrarFormulario(
      context,
      titulo: 'Agregar certificación',
      contenido: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            controller: nombreCtrl,
            decoration: const InputDecoration(labelText: 'Nombre'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: entidadCtrl,
            decoration: const InputDecoration(labelText: 'Entidad emisora (opcional)'),
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: () async {
              if (nombreCtrl.text.trim().isEmpty) return;
              try {
                await _servicio.crearCertificacion(
                  accessToken,
                  nombre: nombreCtrl.text.trim(),
                  entidadEmisora: entidadCtrl.text.trim().isEmpty ? null : entidadCtrl.text.trim(),
                );
                if (context.mounted) Navigator.of(context).pop();
              } on PerfilException catch (e) {
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.mensaje)));
                }
              }
            },
            child: const Text('Agregar'),
          ),
        ],
      ),
    );
  }
}

// ─── Habilidades ─────────────────────────────────────────────────────
// A diferencia de las demás secciones, PUT /me/habilidades reemplaza la
// lista completa en vez de agregar un ítem, así que se maneja aparte.

class _HabilidadesTab extends StatefulWidget {
  final String accessToken;
  const _HabilidadesTab({required this.accessToken});

  @override
  State<_HabilidadesTab> createState() => _HabilidadesTabState();
}

class _HabilidadesTabState extends State<_HabilidadesTab> {
  final _servicio = PerfilService();
  List<Habilidad> _habilidades = [];
  bool _cargando = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    setState(() {
      _cargando = true;
      _error = null;
    });
    try {
      final datos = await _servicio.listarHabilidades(widget.accessToken);
      setState(() {
        _habilidades = datos;
        _cargando = false;
      });
    } on PerfilException catch (e) {
      setState(() {
        _error = e.mensaje;
        _cargando = false;
      });
    }
  }

  Future<void> _guardarLista(List<String> nombres) async {
    try {
      final actualizadas = await _servicio.actualizarHabilidades(widget.accessToken, nombres);
      setState(() => _habilidades = actualizadas);
    } on PerfilException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.mensaje)));
    }
  }

  Future<void> _agregar() async {
    final ctrl = TextEditingController();
    await _mostrarFormulario(
      context,
      titulo: 'Agregar habilidad',
      contenido: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            controller: ctrl,
            decoration: const InputDecoration(labelText: 'Nombre de la habilidad'),
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: () async {
              final nombre = ctrl.text.trim();
              if (nombre.isEmpty) return;
              final nombres = [..._habilidades.map((h) => h.nombre), nombre];
              await _guardarLista(nombres);
              if (context.mounted) Navigator.of(context).pop();
            },
            child: const Text('Agregar'),
          ),
        ],
      ),
    );
  }

  Future<void> _quitar(Habilidad habilidad) async {
    if (!await _confirmarEliminacion(context)) return;
    final nombres = _habilidades.where((h) => h.id != habilidad.id).map((h) => h.nombre).toList();
    await _guardarLista(nombres);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: RefreshIndicator(
        onRefresh: _cargar,
        child: _cargando
            ? const VistaCargando()
            : _error != null
            ? VistaMensaje.error(_error, onReintentar: _cargar)
            : _habilidades.isEmpty
            ? const VistaMensaje(
                icono: Icons.psychology_outlined,
                titulo: 'Todavía no agregaste habilidades',
                mensaje: 'Son lo que más pesa en tu afinidad con cada vacante.',
              )
            : ListView(
                padding: const EdgeInsets.fromLTRB(16, 20, 16, 96),
                children: [
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: _habilidades
                        .map(
                          (h) => Chip(
                            label: Text(h.nombre),
                            deleteButtonTooltipMessage: 'Quitar',
                            onDeleted: () => _quitar(h),
                          ),
                        )
                        .toList(),
                  ),
                ],
              ),
      ),
      floatingActionButton: _BotonAgregar(onPressed: _agregar),
    );
  }
}
