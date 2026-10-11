class Notificacion {
  final String id;
  final String userId;
  final String notificationType;
  final String title;
  final String? body;
  final String? link;
  final String? readAt;
  final DateTime createdAt;
  final bool leida;

  const Notificacion({
    required this.id,
    required this.userId,
    required this.notificationType,
    required this.title,
    this.body,
    this.link,
    this.readAt,
    required this.createdAt,
    required this.leida,
  });

  factory Notificacion.fromJson(Map<String, dynamic> json) {
    final readAtStr = json['read_at'] as String?;
    final createdAtStr = json['created_at'] as String? ?? DateTime.now().toIso8601String();
    return Notificacion(
      id: json['id']?.toString() ?? '',
      userId: json['user_id']?.toString() ?? '',
      notificationType: json['notification_type']?.toString() ?? 'system',
      title: json['title']?.toString() ?? '',
      body: json['body'] as String?,
      link: json['link'] as String?,
      readAt: readAtStr,
      // La API manda la hora en UTC: se muestra en la hora del teléfono (Bolivia), como en los demás modelos.
      createdAt: DateTime.tryParse(createdAtStr)?.toLocal() ?? DateTime.now(),
      leida: json['leida'] == true || readAtStr != null,
    );
  }
}

class NotificacionesListResponse {
  final int total;
  final int noLeidas;
  final List<Notificacion> items;

  const NotificacionesListResponse({
    required this.total,
    required this.noLeidas,
    required this.items,
  });

  factory NotificacionesListResponse.fromJson(Map<String, dynamic> json) {
    final list = json['items'] as List<dynamic>? ?? [];
    return NotificacionesListResponse(
      total: (json['total'] as num?)?.toInt() ?? 0,
      noLeidas: (json['no_leidas'] as num?)?.toInt() ?? 0,
      items: list.map((item) => Notificacion.fromJson(item as Map<String, dynamic>)).toList(),
    );
  }
}

class PreferenciasNotificacion {
  final bool emailEnabled;
  final bool pushEnabled;
  final bool inAppEnabled;
  final bool notifyStageChanges;
  final bool notifyJobMatches;
  final bool notifyInterviewEvents;
  final bool notifyMessages;

  const PreferenciasNotificacion({
    this.emailEnabled = true,
    this.pushEnabled = true,
    this.inAppEnabled = true,
    this.notifyStageChanges = true,
    this.notifyJobMatches = true,
    this.notifyInterviewEvents = true,
    this.notifyMessages = true,
  });

  factory PreferenciasNotificacion.fromJson(Map<String, dynamic> json) {
    return PreferenciasNotificacion(
      emailEnabled: json['email_enabled'] as bool? ?? json['email_notifications'] as bool? ?? true,
      pushEnabled: json['push_enabled'] as bool? ?? true,
      inAppEnabled: json['in_app_enabled'] as bool? ?? true,
      notifyStageChanges: json['notify_stage_changes'] as bool? ?? true,
      notifyJobMatches: json['notify_job_matches'] as bool? ?? true,
      notifyInterviewEvents: json['notify_interview_events'] as bool? ?? true,
      notifyMessages: json['notify_messages'] as bool? ?? true,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'email_enabled': emailEnabled,
      'email_notifications': emailEnabled,
      'push_enabled': pushEnabled,
      'in_app_enabled': inAppEnabled,
      'notify_stage_changes': notifyStageChanges,
      'notify_job_matches': notifyJobMatches,
      'notify_interview_events': notifyInterviewEvents,
      'notify_messages': notifyMessages,
    };
  }

  PreferenciasNotificacion copyWith({
    bool? emailEnabled,
    bool? pushEnabled,
    bool? inAppEnabled,
    bool? notifyStageChanges,
    bool? notifyJobMatches,
    bool? notifyInterviewEvents,
    bool? notifyMessages,
  }) {
    return PreferenciasNotificacion(
      emailEnabled: emailEnabled ?? this.emailEnabled,
      pushEnabled: pushEnabled ?? this.pushEnabled,
      inAppEnabled: inAppEnabled ?? this.inAppEnabled,
      notifyStageChanges: notifyStageChanges ?? this.notifyStageChanges,
      notifyJobMatches: notifyJobMatches ?? this.notifyJobMatches,
      notifyInterviewEvents: notifyInterviewEvents ?? this.notifyInterviewEvents,
      notifyMessages: notifyMessages ?? this.notifyMessages,
    );
  }
}
