import 'package:flutter/material.dart';

import '../../core/models/notificacion.dart';
import '../../core/services/notificacion_service.dart';
import '../../core/widgets/boton_ayuda.dart';
import 'preferencias_notificaciones_screen.dart';

class NotificacionesScreen extends StatefulWidget {
  final String accessToken;

  const NotificacionesScreen({super.key, required this.accessToken});

  @override
  State<NotificacionesScreen> createState() => _NotificacionesScreenState();
}

class _NotificacionesScreenState extends State<NotificacionesScreen> {
  final _servicio = NotificacionService();
  bool _cargando = true;
  bool _soloNoLeidas = false;
  List<Notificacion> _notificaciones = [];
  int _total = 0;
  int _noLeidas = 0;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    setState(() => _cargando = true);
    try {
      final res = await _servicio.listarNotificaciones(
        widget.accessToken,
        limit: 50,
        soloNoLeidas: _soloNoLeidas,
      );
      if (!mounted) return;
      setState(() {
        _notificaciones = res.items;
        _total = res.total;
        _noLeidas = res.noLeidas;
        _cargando = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _cargando = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString()), backgroundColor: Colors.red),
      );
    }
  }

  /// Corre una acción y recarga la lista; si la pantalla ya se cerró no toca el estado
  /// (setState después de dispose rompe la app) y un error de red se avisa en vez de quedar suelto.
  Future<bool> _accion(Future<void> Function() hacer) async {
    try {
      await hacer();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e'), backgroundColor: Colors.red),
        );
      }
      return false;
    }
    if (!mounted) return false;
    _cargar();
    return true;
  }

  Future<void> _marcarLeida(Notificacion notif) async {
    if (notif.leida) return;
    await _accion(() => _servicio.marcarComoLeida(widget.accessToken, notif.id));
  }

  Future<void> _marcarTodasLeidas() async {
    final ok = await _accion(() => _servicio.marcarTodasComoLeidas(widget.accessToken));
    if (!ok || !mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Todas las notificaciones marcadas como leídas')),
    );
  }

  Future<void> _eliminar(Notificacion notif) async {
    await _accion(() => _servicio.eliminarNotificacion(widget.accessToken, notif.id));
  }

  IconData _getIcono(String tipo) {
    switch (tipo) {
      case 'stage_change':
        return Icons.trending_up;
      case 'job_match':
        return Icons.auto_awesome;
      case 'interview_scheduled':
      case 'interview_status':
        return Icons.event;
      case 'message_received':
        return Icons.chat_bubble;
      default:
        return Icons.notifications;
    }
  }

  Color _getColor(String tipo) {
    switch (tipo) {
      case 'stage_change':
        return Colors.teal;
      case 'job_match':
        return Colors.amber.shade700;
      case 'interview_scheduled':
      case 'interview_status':
        return Colors.purple;
      case 'message_received':
        return Colors.cyan.shade700;
      default:
        return Colors.indigo;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notificaciones'),
        actions: [
          const BotonAyuda('notificaciones'),
          IconButton(
            icon: const Icon(Icons.tune),
            tooltip: 'Preferencias de alertas',
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => PreferenciasNotificacionesScreen(accessToken: widget.accessToken),
                ),
              );
            },
          ),
          if (_noLeidas > 0)
            IconButton(
              icon: const Icon(Icons.done_all),
              tooltip: 'Marcar todas como leídas',
              onPressed: _marcarTodasLeidas,
            ),
        ],
      ),
      body: Column(
        children: [
          // Barra de filtros
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            color: Colors.grey.shade100,
            child: Row(
              children: [
                ChoiceChip(
                  label: Text('Todas ($_total)'),
                  selected: !_soloNoLeidas,
                  onSelected: (val) {
                    if (val) {
                      setState(() => _soloNoLeidas = false);
                      _cargar();
                    }
                  },
                ),
                const SizedBox(width: 8),
                ChoiceChip(
                  label: Text('No leídas ($_noLeidas)'),
                  selected: _soloNoLeidas,
                  onSelected: (val) {
                    if (val) {
                      setState(() => _soloNoLeidas = true);
                      _cargar();
                    }
                  },
                ),
              ],
            ),
          ),
          Expanded(
            child: _cargando
                ? const Center(child: CircularProgressIndicator())
                : _notificaciones.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.mark_email_read_outlined, size: 64, color: Colors.grey.shade400),
                            const SizedBox(height: 12),
                            Text(
                              _soloNoLeidas ? 'No tienes notificaciones pendientes' : 'No tienes notificaciones',
                              style: TextStyle(fontSize: 16, color: Colors.grey.shade600),
                            ),
                          ],
                        ),
                      )
                    : RefreshIndicator(
                        onRefresh: _cargar,
                        child: ListView.separated(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          itemCount: _notificaciones.length,
                          separatorBuilder: (_, __) => const Divider(height: 1),
                          itemBuilder: (context, index) {
                            final n = _notificaciones[index];
                            final color = _getColor(n.notificationType);

                            return Dismissible(
                              key: Key(n.id),
                              direction: DismissDirection.endToStart,
                              background: Container(
                                color: Colors.red,
                                alignment: Alignment.centerRight,
                                padding: const EdgeInsets.only(right: 16),
                                child: const Icon(Icons.delete, color: Colors.white),
                              ),
                              onDismissed: (_) => _eliminar(n),
                              child: ListTile(
                                tileColor: n.leida ? null : Colors.indigo.shade50.withOpacity(0.4),
                                leading: CircleAvatar(
                                  backgroundColor: color.withOpacity(0.15),
                                  child: Icon(_getIcono(n.notificationType), color: color, size: 20),
                                ),
                                title: Text(
                                  n.title,
                                  style: TextStyle(
                                    fontWeight: n.leida ? FontWeight.normal : FontWeight.bold,
                                    fontSize: 14,
                                  ),
                                ),
                                subtitle: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    if (n.body != null && n.body!.isNotEmpty) ...[
                                      const SizedBox(height: 4),
                                      Text(n.body!, style: const TextStyle(fontSize: 13, color: Colors.black87)),
                                    ],
                                    const SizedBox(height: 4),
                                    Text(
                                      '${n.createdAt.day.toString().padLeft(2, '0')}/${n.createdAt.month.toString().padLeft(2, '0')}/${n.createdAt.year} ${n.createdAt.hour.toString().padLeft(2, '0')}:${n.createdAt.minute.toString().padLeft(2, '0')}',
                                      style: TextStyle(fontSize: 11, color: Colors.grey.shade500),
                                    ),
                                  ],
                                ),
                                trailing: !n.leida
                                    ? Container(
                                        width: 8,
                                        height: 8,
                                        decoration: const BoxDecoration(
                                          color: Colors.indigo,
                                          shape: BoxShape.circle,
                                        ),
                                      )
                                    : null,
                                onTap: () => _marcarLeida(n),
                              ),
                            );
                          },
                        ),
                      ),
          ),
        ],
      ),
    );
  }
}
