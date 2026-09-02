import 'package:flutter/material.dart';

import '../../core/models/vacante.dart';

class VacanteDetalleScreen extends StatelessWidget {
  final Vacante vacante;

  const VacanteDetalleScreen({super.key, required this.vacante});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(vacante.title)),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            vacante.companyName,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.grey[700]),
          ),
          const SizedBox(height: 4),
          Text(vacante.city, style: TextStyle(color: Colors.grey[600])),
          const SizedBox(height: 16),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _chip(vacante.seniorityLevel),
              _chip(vacante.employmentType),
              _chip(vacante.workModality),
              _chip('${vacante.positionsAvailable} vacante(s)'),
            ],
          ),
          const SizedBox(height: 20),
          Text('Salario', style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 4),
          Text(vacante.salarioLegible),
          const SizedBox(height: 20),
          Text('Descripción', style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 4),
          Text(vacante.description),
          if (vacante.skills.isNotEmpty) ...[
            const SizedBox(height: 20),
            Text('Habilidades requeridas', style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: vacante.skills
                  .map((s) => Chip(
                        label: Text('${s.skillName} (${_importanciaLegible(s.importance)})'),
                        backgroundColor: Colors.blue.shade50,
                      ))
                  .toList(),
            ),
          ],
          if (vacante.applicationDeadline != null) ...[
            const SizedBox(height: 20),
            Text(
              'Fecha límite de postulación: ${vacante.applicationDeadline!.substring(0, 10)}',
              style: TextStyle(color: Colors.grey[600]),
            ),
          ],
        ],
      ),
    );
  }

  String _importanciaLegible(String importance) {
    switch (importance) {
      case 'required':
        return 'requerida';
      case 'preferred':
        return 'preferida';
      default:
        return 'opcional';
    }
  }

  Widget _chip(String texto) {
    if (texto.isEmpty) return const SizedBox.shrink();
    return Chip(label: Text(texto));
  }
}
