import 'package:flutter/material.dart';

import 'features/auth/login_screen.dart';

void main() {
  runApp(const EgresaApp());
}

class EgresaApp extends StatelessWidget {
  const EgresaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'EGRESA',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorSchemeSeed: Colors.indigo, useMaterial3: true),
      home: const LoginScreen(),
    );
  }
}
