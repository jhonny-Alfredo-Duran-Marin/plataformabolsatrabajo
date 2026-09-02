import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:egresa_app/main.dart';

void main() {
  testWidgets('La app arranca mostrando la pantalla de login', (WidgetTester tester) async {
    await tester.pumpWidget(const EgresaApp());

    expect(find.text('EGRESA'), findsOneWidget);
    expect(find.text('Iniciar sesión'), findsOneWidget);
    expect(find.byType(TextFormField), findsNWidgets(2));
  });
}
