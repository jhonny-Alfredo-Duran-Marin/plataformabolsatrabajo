import 'package:egresa_app/core/models/notificacion.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('La hora de una notificación se muestra en la hora del teléfono, no en UTC', () {
    final enUtc = DateTime.utc(2026, 10, 7, 22, 0);
    final notificacion = Notificacion.fromJson({
      'id': 'n1',
      'user_id': 'u1',
      'notification_type': 'job_match',
      'title': 'Nueva oferta para vos',
      'created_at': enUtc.toIso8601String(),
    });

    expect(notificacion.createdAt.isUtc, isFalse);
    // Es el mismo instante, expresado en la zona del teléfono (en Bolivia, las 18:00).
    expect(notificacion.createdAt.isAtSameMomentAs(enUtc), isTrue);
    expect(notificacion.createdAt, enUtc.toLocal());
  });
}
