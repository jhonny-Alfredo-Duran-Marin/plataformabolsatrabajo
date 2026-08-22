import 'package:flutter/material.dart';

void main() {
  runApp(const EgresaApp());
}

class EgresaApp extends StatelessWidget {
  const EgresaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'EGRESA',
      theme: ThemeData(colorSchemeSeed: Colors.indigo, useMaterial3: true),
      home: const Scaffold(
        body: Center(child: Text('EGRESA — en construcción')),
      ),
    );
  }
}
