// HU-36 — Notificaciones push (app Android). Casos de prueba cubiertos:
//
// - CP05: app en segundo plano o cerrada con sesión activa -> el egresado toca el push -> se abre
//   PostulacionDetalleScreen de esa postulación.
// - CP06: app cerrada (sin sesión) -> toca el push e inicia sesión -> se abre el detalle de esa postulación.
// - CP07: app abierta -> pulsa «Ver» en el aviso en primer plano -> se abre el detalle de esa postulación.
// - CP08: aviso de cambio de estado en la campanita -> el egresado lo toca -> se abre el detalle
//   (marcar como leído lo hace `_abrirAviso` con el servicio existente de HU-21).
import 'package:egresa_app/core/models/notificacion.dart';
import 'package:egresa_app/core/utils/destino_push.dart';
import 'package:egresa_app/features/postulaciones/postulacion_detalle_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

const _id = '3f2b1c9e-0000-4000-8000-000000000036';

Map<String, dynamic> _pushDeEstado() => {
      'tipo': 'application_status',
      'postulacion_id': _id,
      'link': '/postulaciones?id=$_id',
      'title': 'Tu postulación: Analista',
      'body': 'En entrevista',
    };

Notificacion _aviso({required String tipo, String? enlace}) => Notificacion(
      id: 'n1',
      userId: 'u1',
      notificationType: tipo,
      title: 'Tu postulación: Analista',
      link: enlace,
      createdAt: DateTime(2026, 11, 24),
      leida: false,
    );

void main() {
  group('Resolver el destino desde el payload o el enlace', () {
    test('CP05: el payload del push de estado apunta a la postulación', () {
      expect(postulacionIdDesdePush(_pushDeEstado()), _id);
    });

    test('CP05: sin postulacion_id se usa el enlace /postulaciones?id=<id>', () {
      final data = _pushDeEstado()..remove('postulacion_id');
      expect(postulacionIdDesdePush(data), _id);
    });

    test('CP05: un push de otro tipo no abre ninguna postulación', () {
      expect(postulacionIdDesdePush({'tipo': 'new_message', 'link': '/mensajes'}), isNull);
      expect(postulacionIdDesdePush({'link': '/postulaciones?id=$_id'}), isNull);
    });

    test('CP05: el enlace genérico /postulaciones no apunta a ninguna', () {
      expect(postulacionIdDesdeEnlace('/postulaciones'), isNull);
      expect(postulacionIdDesdeEnlace('/encuestas/$_id'), isNull);
      expect(postulacionIdDesdeEnlace(null), isNull);
    });
  });

  group('CP05: tocar el push con la app en segundo plano o cerrada, con sesión', () {
    test('abre el detalle de esa postulación con la sesión activa', () {
      final abiertas = <(String, String)>[];
      final gestor = GestorDestinoPush((token, id) => abiertas.add((token, id)));
      gestor.iniciarSesion('token-egresado');

      gestor.alTocar(_pushDeEstado());

      expect(abiertas, [('token-egresado', _id)]);
      expect(gestor.pendiente, isNull);
    });

    testWidgets('navega a PostulacionDetalleScreen de esa postulación', (tester) async {
      final navegador = GlobalKey<NavigatorState>();
      final gestor = GestorDestinoPush(
        (token, id) => navegador.currentState!.push(
          MaterialPageRoute(builder: (_) => PostulacionDetalleScreen(accessToken: token, postulacionId: id)),
        ),
      );
      await tester.pumpWidget(MaterialApp(navigatorKey: navegador, home: const Scaffold(body: Text('Inicio'))));
      gestor.iniciarSesion('token-egresado');

      gestor.alTocar(_pushDeEstado());
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 500));

      final pantalla = tester.widget<PostulacionDetalleScreen>(find.byType(PostulacionDetalleScreen));
      expect(pantalla.postulacionId, _id);
      expect(pantalla.accessToken, 'token-egresado');
    });
  });

  group('CP06: app cerrada sin sesión', () {
    test('el destino queda pendiente y se abre recién al iniciar sesión', () {
      final abiertas = <(String, String)>[];
      final gestor = GestorDestinoPush((token, id) => abiertas.add((token, id)));

      gestor.alTocar(_pushDeEstado()); // la app abre en el login: todavía no hay sesión
      expect(abiertas, isEmpty);
      expect(gestor.pendiente, _id);

      gestor.iniciarSesion('token-egresado'); // el egresado inicia sesión
      expect(abiertas, [('token-egresado', _id)]);
      expect(gestor.pendiente, isNull);
    });

    test('el destino se abre una sola vez', () {
      final abiertas = <String>[];
      final gestor = GestorDestinoPush((token, id) => abiertas.add(id));
      gestor.alTocar(_pushDeEstado());

      gestor.iniciarSesion('token-1');
      gestor.cerrarSesion();
      gestor.iniciarSesion('token-2');

      expect(abiertas, [_id]);
    });

    test('un push que no es de una postulación no deja destino pendiente', () {
      final gestor = GestorDestinoPush((token, id) {});
      gestor.alTocar({'tipo': 'new_message', 'link': '/mensajes'});
      expect(gestor.pendiente, isNull);
    });
  });

  group('CP07: aviso en primer plano con «Ver»', () {
    testWidgets('el SnackBar ofrece «Ver» y abre el detalle de esa postulación', (tester) async {
      final abiertas = <String>[];
      final gestor = GestorDestinoPush((token, id) => abiertas.add(id));
      gestor.iniciarSesion('token-egresado');
      final mensajero = GlobalKey<ScaffoldMessengerState>();
      await tester.pumpWidget(
        MaterialApp(scaffoldMessengerKey: mensajero, home: const Scaffold(body: Text('Inicio'))),
      );

      mensajero.currentState!.showSnackBar(
        snackBarDeAviso(
          titulo: 'Tu postulación: Analista',
          cuerpo: 'En entrevista',
          data: _pushDeEstado(),
          alVer: gestor.abrirAhora,
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 750));
      expect(find.text('Ver'), findsOneWidget);

      await tester.tap(find.text('Ver'));
      await tester.pump();

      expect(abiertas, [_id]);
    });

    testWidgets('un aviso que no es de una postulación no ofrece «Ver»', (tester) async {
      final mensajero = GlobalKey<ScaffoldMessengerState>();
      await tester.pumpWidget(
        MaterialApp(scaffoldMessengerKey: mensajero, home: const Scaffold(body: Text('Inicio'))),
      );

      mensajero.currentState!.showSnackBar(
        snackBarDeAviso(titulo: 'Mensaje nuevo', cuerpo: '', data: {'tipo': 'new_message'}, alVer: (_) {}),
      );
      await tester.pump();

      expect(find.text('Mensaje nuevo'), findsOneWidget);
      expect(find.text('Ver'), findsNothing);
    });
  });

  group('CP08: tocar el aviso en la campanita', () {
    test('un aviso application_status con enlace /postulaciones?id=<id> abre esa postulación', () {
      final aviso = _aviso(tipo: 'application_status', enlace: '/postulaciones?id=$_id');
      expect(postulacionIdDeAviso(aviso), _id);
    });

    test('un aviso de otro tipo, o con el enlace genérico, no abre ninguna postulación', () {
      expect(postulacionIdDeAviso(_aviso(tipo: 'new_message', enlace: '/postulaciones?id=$_id')), isNull);
      expect(postulacionIdDeAviso(_aviso(tipo: 'application_status', enlace: '/postulaciones')), isNull);
      expect(postulacionIdDeAviso(_aviso(tipo: 'application_status')), isNull);
    });
  });
}
