// HU-35 — Búsqueda y postulación móvil (app Flutter).
// Casos de prueba de caja negra cubiertos:
// - CP01: Búsqueda por palabra clave y filtros (ciudad, modalidad, carrera).
// - CP02: Detalle de vacante y postulación con perfil registrado, con confirmación.
// - CP03: Postulación repetida a la misma vacante -> informa y no permite duplicar.
// - CP04: Pérdida de conexión durante la postulación -> informa el error, conserva
//   respuestas y permite reintentar sin duplicar la postulación.
import 'dart:convert';
import 'dart:io';

import 'package:egresa_app/core/models/vacante.dart';
import 'package:egresa_app/core/services/postulacion_service.dart';
import 'package:egresa_app/core/services/vacante_service.dart';
import 'package:egresa_app/features/vacantes/postulacion_screen.dart';
import 'package:egresa_app/features/vacantes/vacante_detalle_screen.dart';
import 'package:egresa_app/features/vacantes/vacantes_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const _token = 'token-egresado-hu35';
const _vacanteId1 = '11111111-1111-4111-8111-111111111111';
const _vacanteId2 = '22222222-2222-4222-8222-222222222222';
const _carreraSistemasId = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';

http.Response _jsonResponse(Object body, {int status = 200}) => http.Response.bytes(
      utf8.encode(jsonEncode(body)),
      status,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );

Map<String, dynamic> _vacanteJson({
  required String id,
  required String title,
  required String city,
  required String modality,
  String company = 'Tech Bolivia SRL',
}) =>
    {
      'id': id,
      'company': {'id': 'c1', 'legal_name': company, 'trade_name': company},
      'title': title,
      'description': 'Desarrollo de servicios REST con Python y Flutter.',
      'seniority_level': 'junior',
      'employment_type': 'permanent',
      'work_modality': modality,
      'city': city,
      'salary_min': 5000,
      'salary_max': 7000,
      'currency': 'BOB',
      'salary_visible': true,
      'positions_available': 2,
      'skills': [
        {'skill_id': 's1', 'name': 'Python', 'importance': 'required', 'min_proficiency': 'intermediate'},
      ],
      'education_preferences': [
        {'field_of_study_id': _carreraSistemasId, 'name': 'Ingeniería en Sistemas', 'is_required': true},
      ],
      'afinidad_porcentaje': 88,
    };

Vacante _vacantePrueba({String id = _vacanteId1}) => Vacante.fromJson(
      _vacanteJson(id: id, title: 'Desarrollador Python Backend', city: 'Santa Cruz', modality: 'remote'),
    );

void main() {
  group('HU-35 CP01: Búsqueda móvil con palabra clave y filtros (ciudad, modalidad, carrera)', () {
    test('VacanteService.buscar envía q, ciudad, modalidad y carrera_id al endpoint compartido /vacantes/buscar',
        () async {
      Uri? ultimaUri;
      final client = MockClient((req) async {
        ultimaUri = req.url;
        if (req.url.path.endsWith('/vacantes/buscar/filtros')) {
          return _jsonResponse({
            'ciudades': ['Santa Cruz', 'La Paz'],
            'modalidades': ['onsite', 'remote', 'hybrid'],
            'carreras': [
              {'id': _carreraSistemasId, 'name': 'Ingeniería en Sistemas', 'category': 'Tecnología'},
            ],
          });
        }
        return _jsonResponse({
          'total': 1,
          'limit': 30,
          'offset': 0,
          'items': [
            _vacanteJson(
              id: _vacanteId1,
              title: 'Desarrollador Python Backend',
              city: 'Santa Cruz',
              modality: 'remote',
            ),
          ],
        });
      });

      final servicio = VacanteService(client: client);
      final filtros = await servicio.obtenerFiltrosDisponibles();
      expect(filtros.ciudades, ['Santa Cruz', 'La Paz']);
      expect(filtros.carreras.single.id, _carreraSistemasId);

      final resultados = await servicio.buscar(
        _token,
        q: 'Python',
        ciudad: 'Santa Cruz',
        modalidad: 'remote',
        carreraId: _carreraSistemasId,
      );

      expect(ultimaUri?.path, endsWith('/vacantes/buscar'));
      expect(ultimaUri?.queryParameters['q'], 'Python');
      expect(ultimaUri?.queryParameters['ciudad'], 'Santa Cruz');
      expect(ultimaUri?.queryParameters['modalidad'], 'remote');
      expect(ultimaUri?.queryParameters['carrera_id'], _carreraSistemasId);
      expect(resultados.length, 1);
      expect(resultados.first.city, 'Santa Cruz');
      expect(resultados.first.educationPreferences.first.name, 'Ingeniería en Sistemas');
    });

    testWidgets('VacantesScreen aplica filtros de palabra clave, ciudad, modalidad y carrera', (tester) async {
      final consultas = <Map<String, String>>[];
      final client = MockClient((req) async {
        if (req.url.path.endsWith('/vacantes/buscar/filtros')) {
          return _jsonResponse({
            'ciudades': ['Santa Cruz', 'Cochabamba'],
            'modalidades': ['remote', 'onsite'],
            'carreras': [
              {'id': _carreraSistemasId, 'name': 'Ingeniería en Sistemas'},
            ],
          });
        }
        if (req.url.path.endsWith('/postulaciones/')) {
          return _jsonResponse([]);
        }
        if (req.url.path.endsWith('/vacantes/buscar')) {
          consultas.add(Map<String, String>.from(req.url.queryParameters));
          final ciudad = req.url.queryParameters['ciudad'];
          final q = req.url.queryParameters['q'] ?? '';
          final items = [
            _vacanteJson(id: _vacanteId1, title: 'Desarrollador Python', city: 'Santa Cruz', modality: 'remote'),
            _vacanteJson(id: _vacanteId2, title: 'Contador Junior', city: 'Cochabamba', modality: 'onsite'),
          ].where((v) {
            final okCiudad = ciudad == null || v['city'] == ciudad;
            final okQ = q.isEmpty || (v['title'] as String).toLowerCase().contains(q.toLowerCase());
            return okCiudad && okQ;
          }).toList();
          return _jsonResponse({'total': items.length, 'limit': 30, 'offset': 0, 'items': items});
        }
        return _jsonResponse({}, status: 404);
      });

      await tester.pumpWidget(
        MaterialApp(
          home: VacantesScreen(
            accessToken: _token,
            vacanteService: VacanteService(client: client),
            postulacionService: PostulacionService(client: client),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Desarrollador Python'), findsOneWidget);
      expect(find.text('Contador Junior'), findsOneWidget);

      // Escribir palabra clave "Python" y enviar búsqueda
      await tester.enterText(find.byType(TextField).first, 'Python');
      await tester.testTextInput.receiveAction(TextInputAction.search);
      await tester.pumpAndSettle();

      // Abrir filtro Ciudad y seleccionar "Santa Cruz"
      await tester.tap(find.text('Ciudad'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Santa Cruz').last);
      await tester.pumpAndSettle();

      // Abrir filtro Modalidad y seleccionar "Remoto"
      await tester.tap(find.text('Modalidad'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Remoto').last);
      await tester.pumpAndSettle();

      // Abrir filtro Carrera y seleccionar "Ingeniería en Sistemas"
      await tester.tap(find.text('Carrera'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Ingeniería en Sistemas').last);
      await tester.pumpAndSettle();

      expect(find.text('Desarrollador Python'), findsOneWidget);
      expect(find.text('Contador Junior'), findsNothing);
      expect(consultas.last['q'], 'Python');
      expect(consultas.last['ciudad'], 'Santa Cruz');
      expect(consultas.last['modalidad'], 'remote');
      expect(consultas.last['carrera_id'], _carreraSistemasId);
      expect(find.text('Limpiar filtros'), findsOneWidget);
    });
  });

  group('HU-35 CP02 y CP03: Postulación móvil confirmada y prevención de duplicados', () {
    testWidgets('CP02: muestra detalle, postula con el perfil y luego marca la vacante como ya postulada',
        (tester) async {
      final postulacionesEnviadas = <String>[];
      final client = MockClient((req) async {
        if (req.method == 'GET' && req.url.path.endsWith('/postulaciones/')) {
          return _jsonResponse(
            postulacionesEnviadas
                .map((id) => {'id': 'app-1', 'job_id': id, 'current_status': 'applied'})
                .toList(),
          );
        }
        if (req.method == 'GET' && req.url.path.endsWith('/preguntas')) {
          return _jsonResponse([]);
        }
        if (req.method == 'POST' && req.url.path.endsWith('/postulaciones/')) {
          final body = jsonDecode(req.body) as Map<String, dynamic>;
          postulacionesEnviadas.add(body['job_id'] as String);
          return _jsonResponse({
            'id': 'app-1',
            'job_id': body['job_id'],
            'current_status': 'applied',
            'message': 'Postulación exitosa',
          });
        }
        return _jsonResponse({}, status: 404);
      });

      final vacanteSrv = VacanteService(client: client);
      final postSrv = PostulacionService(client: client);

      await tester.pumpWidget(
        MaterialApp(
          home: VacanteDetalleScreen(
            accessToken: _token,
            vacante: _vacantePrueba(),
            vacanteService: vacanteSrv,
            postulacionService: postSrv,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Desarrollador Python Backend'), findsOneWidget);
      await tester.scrollUntilVisible(find.text('Ingeniería en Sistemas'), 200);
      expect(find.text('Ingeniería en Sistemas'), findsOneWidget);
      expect(find.text('Postularme'), findsOneWidget);

      await tester.tap(find.text('Postularme'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Confirmar postulación'));
      await tester.pumpAndSettle();

      expect(find.text('¡Postulación enviada!'), findsOneWidget);
      await tester.tap(find.text('Aceptar'));
      await tester.pumpAndSettle();

      // Al volver al detalle, informa que ya está postulado y ya no muestra el botón para duplicar.
      expect(postulacionesEnviadas, [_vacanteId1]);
      expect(find.text('Ya te postulaste a esta vacante'), findsOneWidget);
      expect(find.text('Postularme'), findsNothing);
    });

    testWidgets('CP03: si el egresado ya se postuló previamente, el detalle lo informa y bloquea duplicar',
        (tester) async {
      final client = MockClient((req) async {
        if (req.method == 'GET' && req.url.path.endsWith('/postulaciones/')) {
          return _jsonResponse([
            {'id': 'app-previa', 'job_id': _vacanteId1, 'current_status': 'in_review'},
          ]);
        }
        return _jsonResponse({}, status: 404);
      });

      await tester.pumpWidget(
        MaterialApp(
          home: VacanteDetalleScreen(
            accessToken: _token,
            vacante: _vacantePrueba(),
            postulacionService: PostulacionService(client: client),
            vacanteService: VacanteService(client: client),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Ya te postulaste a esta vacante'), findsOneWidget);
      expect(find.text('Postularme'), findsNothing);
    });

    testWidgets('CP03: si POST /postulaciones/ informa duplicado (HTTP 400), muestra diálogo y cierra sin duplicar',
        (tester) async {
      final client = MockClient((req) async {
        if (req.method == 'GET' && req.url.path.endsWith('/preguntas')) {
          return _jsonResponse([]);
        }
        if (req.method == 'POST' && req.url.path.endsWith('/postulaciones/')) {
          return _jsonResponse({'detail': 'Ya te has postulado a esta vacante.'}, status: 400);
        }
        return _jsonResponse({}, status: 404);
      });

      await tester.pumpWidget(
        MaterialApp(
          home: PostulacionScreen(
            accessToken: _token,
            vacante: _vacantePrueba(),
            vacanteService: VacanteService(client: client),
            postulacionService: PostulacionService(client: client),
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Confirmar postulación'));
      await tester.pumpAndSettle();

      expect(find.text('Ya te postulaste'), findsOneWidget);
      expect(find.text('Ya te has postulado a esta vacante.'), findsOneWidget);
    });
  });

  group('HU-35 CP04: Pérdida de conexión durante la postulación y reintento sin duplicar', () {
    testWidgets('informa error de red, conserva respuestas ingresadas y permite reintentar con éxito', (tester) async {
      var intentosPost = 0;
      String? textoEnviadoEnExito;

      final client = MockClient((req) async {
        if (req.method == 'GET' && req.url.path.endsWith('/preguntas')) {
          return _jsonResponse([
            {
              'id': 'q-exp',
              'question_text': 'Contanos tu experiencia con APIs REST',
              'question_type': 'text',
              'is_required': true,
              'is_knockout': false,
              'options': [],
            },
          ]);
        }
        if (req.method == 'POST' && req.url.path.endsWith('/postulaciones/')) {
          intentosPost++;
          if (intentosPost == 1) {
            throw const SocketException('Sin conexión a internet');
          }
          final body = jsonDecode(req.body) as Map<String, dynamic>;
          final answers = body['answers'] as List<dynamic>;
          textoEnviadoEnExito = (answers.first as Map<String, dynamic>)['answer_text'] as String?;
          return _jsonResponse({
            'id': 'app-reintento',
            'job_id': _vacanteId1,
            'current_status': 'applied',
            'message': 'Postulación exitosa',
          });
        }
        return _jsonResponse({}, status: 404);
      });

      await tester.pumpWidget(
        MaterialApp(
          home: PostulacionScreen(
            accessToken: _token,
            vacante: _vacantePrueba(),
            vacanteService: VacanteService(client: client),
            postulacionService: PostulacionService(client: client),
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), '2 años desarrollando APIs con FastAPI');
      await tester.tap(find.text('Confirmar postulación'));
      await tester.pumpAndSettle();

      // Intento 1 falló por red: muestra el error, conserva el texto y habilita el botón de reintento.
      expect(intentosPost, 1);
      expect(find.text('Reintentar postulación'), findsOneWidget);
      expect(find.text('2 años desarrollando APIs con FastAPI'), findsOneWidget);

      // Intento 2: reintento exitoso con las mismas respuestas, sin duplicar.
      await tester.tap(find.text('Reintentar postulación'));
      await tester.pumpAndSettle();

      expect(intentosPost, 2);
      expect(textoEnviadoEnExito, '2 años desarrollando APIs con FastAPI');
      expect(find.text('¡Postulación enviada!'), findsOneWidget);
    });
  });
}
