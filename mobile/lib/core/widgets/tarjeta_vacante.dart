import 'package:flutter/material.dart';

import '../models/vacante.dart';
import '../theme/app_theme.dart';
import '../utils/formatos.dart';
import 'insignia.dart';

/// Vacante en un listado: empresa, cargo, datos clave y afinidad si la hay.
class TarjetaVacante extends StatelessWidget {
  final Vacante vacante;
  final VoidCallback onTap;

  const TarjetaVacante({super.key, required this.vacante, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final afinidad = vacante.afinidadPorcentaje;
    final scoreRelevancia = vacante.scoreRelevancia;
    final razon = vacante.razonCoincidencia;
    final cierre = vacante.cierre;

    return Card(
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  AvatarEmpresa(vacante.companyName),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          vacante.companyName,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: AppColors.textoSuave,
                            fontSize: 13,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          vacante.title,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600, height: 1.3),
                        ),
                      ],
                    ),
                  ),
                  if (scoreRelevancia != null) ...[
                    const SizedBox(width: 8),
                    Insignia(
                      '$scoreRelevancia% Relevancia IA',
                      colores: (color: const Color(0xFF1D4ED8), fondo: const Color(0xFFEFF6FF)),
                      icono: Icons.auto_awesome_rounded,
                    ),
                  ] else if (afinidad != null) ...[
                    const SizedBox(width: 8),
                    Insignia('$afinidad%', colores: coloresDeAfinidad(afinidad), icono: Icons.bolt_rounded),
                  ],
                ],
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 14,
                runSpacing: 6,
                children: [
                  if (vacante.city.isNotEmpty) DatoConIcono(Icons.location_on_outlined, vacante.city),
                  if (vacante.modalidadLegible.isNotEmpty)
                    DatoConIcono(iconoDeModalidad(vacante.workModality), vacante.modalidadLegible),
                  if (vacante.jornadaLegible.isNotEmpty) DatoConIcono(Icons.schedule_rounded, vacante.jornadaLegible),
                  if (vacante.nivelLegible.isNotEmpty) DatoConIcono(Icons.trending_up_rounded, vacante.nivelLegible),
                ],
              ),
              if (razon != null && razon.trim().isNotEmpty) ...[
                const SizedBox(height: 10),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF0FDF4),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFFBBF7D0)),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.auto_awesome, size: 14, color: Color(0xFF16A34A)),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          razon.trim(),
                          style: const TextStyle(
                            fontSize: 12,
                            color: Color(0xFF15803D),
                            fontWeight: FontWeight.w500,
                            height: 1.3,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 12),
              const Divider(),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: Text(
                      vacante.tieneSalario ? vacante.salarioLegible : 'Salario a convenir',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: vacante.tieneSalario
                          ? const TextStyle(color: AppColors.exito, fontWeight: FontWeight.w700, fontSize: 14)
                          : const TextStyle(color: AppColors.textoSuave, fontSize: 13),
                    ),
                  ),
                  if (cierre != null) ...[
                    const SizedBox(width: 8),
                    Text(
                      'Cierra ${fechaCorta(cierre)}',
                      style: const TextStyle(color: AppColors.textoSuave, fontSize: 12),
                    ),
                  ],
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
