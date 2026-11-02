/// Contenido de la ayuda en línea de la app (requisito general 4).
///
/// Cada pantalla abre su tema con el botón de ayuda de la barra superior; la pantalla
/// «Ayuda» los muestra todos con un buscador.
class PreguntaAyuda {
  final String pregunta;
  final String respuesta;
  const PreguntaAyuda(this.pregunta, this.respuesta);
}

class TemaAyuda {
  final String id;
  final String titulo;

  /// null: sirve para egresados y empresas.
  final bool? paraEmpresa;
  final String resumen;
  final List<String> pasos;
  final List<PreguntaAyuda> preguntas;

  const TemaAyuda({
    required this.id,
    required this.titulo,
    this.paraEmpresa,
    required this.resumen,
    this.pasos = const [],
    this.preguntas = const [],
  });

  bool sirvePara({required bool esEmpresa}) => paraEmpresa == null || paraEmpresa == esEmpresa;
}

const temasAyuda = <TemaAyuda>[
  TemaAyuda(
    id: 'inicio',
    titulo: 'Tu inicio',
    paraEmpresa: false,
    resumen: 'Un resumen de tus postulaciones, las entrevistas que tenés que responder y tus mensajes nuevos.',
    pasos: [
      'Arriba están las notificaciones (campana) y los mensajes.',
      'Si una empresa te propuso una entrevista, aparece arriba: tocala para confirmar o avisar que no podés asistir.',
      'Deslizá hacia abajo para actualizar los datos.',
    ],
  ),
  TemaAyuda(
    id: 'vacantes',
    titulo: 'Buscar vacantes',
    paraEmpresa: false,
    resumen: 'Buscá ofertas por puesto o habilidad. Cada una muestra tu porcentaje de afinidad.',
    pasos: [
      'Escribí un puesto o una habilidad en el buscador.',
      'Tocá ✨ para ver las vacantes recomendadas para tu perfil.',
      'Abrí una vacante para ver el detalle y postularte.',
    ],
    preguntas: [
      PreguntaAyuda(
        '¿Qué es el porcentaje de afinidad?',
        'Compara tu carrera, habilidades, experiencia e idiomas con lo que pide la vacante. Cuanto más completo tu perfil, más preciso.',
      ),
      PreguntaAyuda('¿Por qué no veo ofertas de cierta empresa?', 'Solo ves ofertas de empresas habilitadas por tu universidad.'),
    ],
  ),
  TemaAyuda(
    id: 'vacante',
    titulo: 'Postularte a una vacante',
    paraEmpresa: false,
    resumen: 'Revisá los requisitos, tu afinidad y las habilidades que pide la empresa antes de postularte.',
    pasos: [
      'Las habilidades marcadas en azul son requeridas; el resto suma puntos.',
      'Tocá «Postularme» y respondé las preguntas de la empresa si las hay.',
      'Si la oferta te parece sospechosa, usá el menú ⋮ y elegí «Denunciar oferta».',
    ],
    preguntas: [
      PreguntaAyuda(
        '¿Qué pasa cuando denuncio una oferta?',
        'La universidad la revisa. La empresa no sabe quién la denunció. Con varias denuncias con detalle la oferta se oculta hasta que se decida.',
      ),
    ],
  ),
  TemaAyuda(
    id: 'postulaciones',
    titulo: 'Mis postulaciones y entrevistas',
    paraEmpresa: false,
    resumen: 'En qué etapa está cada postulación, tus entrevistas y la conversación con la empresa.',
    pasos: [
      'Tocá una postulación para ver su historial y las entrevistas.',
      'Cuando te proponen una entrevista, tocá «Confirmar asistencia» o «No puedo asistir».',
      'Si ya no te interesa, podés retirar la postulación.',
    ],
    preguntas: [
      PreguntaAyuda(
        '¿Qué significa cada estado?',
        'Postulado: la empresa todavía no la revisó. En revisión o Preseleccionado: avanzás. Entrevista y Pruebas: etapas con la empresa. Contratado o No seleccionado: el proceso terminó.',
      ),
    ],
  ),
  TemaAyuda(
    id: 'recomendaciones',
    titulo: 'Vacantes recomendadas',
    paraEmpresa: false,
    resumen: 'Las ofertas vigentes ordenadas según tu afinidad, con los criterios que cumplís y los que te faltan.',
    pasos: [
      'Las primeras son las que mejor coinciden con tu perfil.',
      'Si ves un aviso de perfil incompleto, completá esa sección para mejorar las recomendaciones.',
      'Cada mañana EGRESA también te avisa las ofertas nuevas del día que coinciden con vos.',
    ],
  ),
  TemaAyuda(
    id: 'perfil',
    titulo: 'Tu perfil y tu CV',
    paraEmpresa: false,
    resumen: 'Tu carta de presentación: datos personales, formación, experiencia, habilidades e idiomas.',
    pasos: [
      'En «Datos personales» actualizá tu nombre, contacto, ciudad y disponibilidad.',
      'En «Mi CV» cargá tu formación, experiencia, idiomas y habilidades: pesan en la afinidad.',
      'En «Editar perfil», «Redactar con IA» te propone un resumen profesional con tus datos: editalo y guardalo si te sirve.',
      'Desde acá también cambiás tu contraseña o cerrás sesión.',
    ],
  ),
  TemaAyuda(
    id: 'notificaciones',
    titulo: 'Notificaciones',
    resumen: 'Avisos de tus postulaciones, entrevistas, mensajes y ofertas. También llegan al celular aunque la app esté cerrada.',
    pasos: [
      'Tocá un aviso para abrirlo; se marca como leído.',
      'En «Preferencias de Notificación» elegí qué avisos querés recibir.',
      'Si no te llegan al celular, revisá que la app tenga permiso de notificaciones en los ajustes de Android.',
    ],
  ),
  TemaAyuda(
    id: 'mensajes',
    titulo: 'Mensajes',
    resumen: 'Conversaciones entre egresados y empresas sobre una postulación.',
    pasos: [
      'Tocá una conversación para abrirla y responder.',
      'Los mensajes nuevos también llegan como notificación.',
    ],
  ),
  TemaAyuda(
    id: 'postulantes',
    titulo: 'Postulantes nuevos',
    paraEmpresa: true,
    resumen: 'Los postulantes que nadie de tu empresa revisó todavía, de todas tus vacantes.',
    pasos: [
      'Tocá un postulante para ver sus datos y las formas de contactarlo.',
      'Podés escribirle por mensaje desde la ficha.',
      'Para avanzar etapas o descartar, abrí el panel web desde el menú de tu cuenta.',
    ],
  ),
  TemaAyuda(
    id: 'agenda',
    titulo: 'Agenda de entrevistas',
    paraEmpresa: true,
    resumen: 'Las entrevistas de hoy primero y después las de la semana.',
    pasos: [
      'Desde cada entrevista podés unirte a la videollamada, ver cómo llegar o mandarle un mensaje al egresado.',
      'Proponer, reprogramar o cancelar entrevistas se hace desde el panel web.',
    ],
  ),
  TemaAyuda(
    id: 'encuestas',
    titulo: 'Encuestas laborales',
    paraEmpresa: false,
    resumen: 'Tu universidad te pide cada tanto unos minutos para saber tu situación laboral. Con eso mide la inserción de sus egresados.',
    pasos: [
      'Cuando llega una encuesta te avisa la app; también la ves en «Encuestas» desde el inicio.',
      'Si trabajás, te pregunta dónde, en qué y cuánto se relaciona con tu carrera.',
      'Se responde una sola vez por período y hasta la fecha de cierre.',
    ],
  ),
  TemaAyuda(
    id: 'asistente',
    titulo: 'Asistente EGRESA',
    paraEmpresa: false,
    resumen: 'Un asistente que responde dudas sobre la plataforma: cómo postularte, el estado de tus postulaciones, tu perfil y más.',
    pasos: [
      'Escribí tu pregunta o tocá una de las sugerencias.',
      'Si le preguntás por tus postulaciones, te muestra cada una con su estado.',
      'Con el botón de arriba empezás una conversación nueva.',
    ],
  ),
  TemaAyuda(
    id: 'web',
    titulo: 'Lo que está en la web',
    resumen:
      'La app tiene lo del día a día. En la web están también la publicación de vacantes, el proceso de selección completo, los reportes personalizados y la administración de la universidad.',
    pasos: [
      'Empresas: el menú de tu cuenta tiene «Abrir el panel web».',
      'En la web, el botón «?» de cada pantalla abre su ayuda.',
    ],
  ),
];

TemaAyuda temaAyuda(String id) => temasAyuda.firstWhere((t) => t.id == id, orElse: () => temasAyuda.last);

String _normalizar(String texto) {
  const conAcento = 'áéíóúüñ';
  const sinAcento = 'aeiouun';
  final minuscula = texto.toLowerCase();
  final buffer = StringBuffer();
  for (final letra in minuscula.split('')) {
    final i = conAcento.indexOf(letra);
    buffer.write(i >= 0 ? sinAcento[i] : letra);
  }
  return buffer.toString();
}

/// Búsqueda simple sin acentos en títulos, resúmenes, pasos y preguntas.
List<TemaAyuda> buscarTemasAyuda(String consulta, {required bool esEmpresa}) {
  final propios = temasAyuda.where((t) => t.sirvePara(esEmpresa: esEmpresa)).toList();
  final palabras = _normalizar(consulta).split(RegExp(r'\s+')).where((p) => p.isNotEmpty).toList();
  if (palabras.isEmpty) return propios;
  return propios.where((t) {
    final texto = _normalizar(
      [t.titulo, t.resumen, ...t.pasos, for (final p in t.preguntas) ...[p.pregunta, p.respuesta]].join(' '),
    );
    return palabras.every(texto.contains);
  }).toList();
}
