/**
 * Contenido de la ayuda en línea (requisito general 4).
 *
 * Cada tema dice a quién le sirve y en qué pantallas aparece: el botón de ayuda abre el
 * tema de la pantalla actual y el centro de ayuda (/ayuda) los muestra todos.
 */

export type Audiencia = 'egresado' | 'empresa' | 'universidad' | 'todos';

export interface PreguntaAyuda {
  pregunta: string;
  respuesta: string;
}

export interface TemaAyuda {
  id: string;
  titulo: string;
  audiencia: Audiencia;
  /** Rutas donde se abre este tema; la más larga que coincide gana. '=' al inicio exige coincidencia exacta. */
  rutas: string[];
  resumen: string;
  pasos: string[];
  preguntas: PreguntaAyuda[];
}

export const AUDIENCIAS: { clave: Audiencia; nombre: string; icono: string }[] = [
  { clave: 'egresado', nombre: 'Egresados', icono: '🎓' },
  { clave: 'empresa', nombre: 'Empresas', icono: '🏢' },
  { clave: 'universidad', nombre: 'Universidades', icono: '🏛️' },
  { clave: 'todos', nombre: 'Para todos', icono: '💡' },
];

export const TEMAS_AYUDA: TemaAyuda[] = [
  // ─── Para todos ──────────────────────────────────────────────────────────
  {
    id: 'primeros-pasos',
    titulo: 'Primeros pasos en EGRESA',
    audiencia: 'todos',
    rutas: [
      '/auth/login',
      '/auth/registro',
      '/auth/registro-empresa',
      '/auth/registro-universidad',
    ],
    resumen:
      'EGRESA conecta a los egresados de cada universidad con empresas que buscan talento. Cada tipo de cuenta tiene su propio panel.',
    pasos: [
      'Egresados: creá tu cuenta con «Regístrate como egresado», elegí tu universidad y completá tus datos. Tu universidad valida que seas egresado.',
      'Empresas: registrate con «¿Eres una empresa? Regístrate aquí». Después pedí permiso para reclutar en cada universidad que te interese.',
      'Universidades: pedí el alta con «Sumala a EGRESA» y elegí un plan. El equipo de EGRESA aprueba la solicitud.',
      'Iniciá sesión con tu correo y contraseña: el sistema te lleva al panel que te corresponde.',
    ],
    preguntas: [
      {
        pregunta: '¿Por qué mi cuenta dice «pendiente de validación»?',
        respuesta:
          'Las cuentas de egresado las valida la universidad y las de empresa se verifican antes de publicar. Mientras tanto podés completar tu perfil.',
      },
      {
        pregunta: 'Me bloqueó el inicio de sesión, ¿qué hago?',
        respuesta:
          'Después de varios intentos fallidos la cuenta se bloquea unos minutos por seguridad. Esperá y probá de nuevo.',
      },
      {
        pregunta: '¿Puedo ver ofertas sin cuenta?',
        respuesta:
          'Sí: el listado de vacantes es público. Para postularte necesitás una cuenta de egresado.',
      },
    ],
  },
  {
    id: 'notificaciones',
    titulo: 'Notificaciones y avisos al celular',
    audiencia: 'todos',
    rutas: ['/notificaciones', '/admin/notificaciones'],
    resumen:
      'La campana muestra tus avisos: cambios en tus postulaciones, entrevistas, mensajes y ofertas que coinciden con tu perfil. También pueden llegarte como aviso del navegador o del celular.',
    pasos: [
      'Tocá la campana para ver los avisos nuevos; al abrir uno se marca como leído.',
      'En «Preferencias» elegí qué avisos querés recibir (etapas, entrevistas, mensajes, ofertas).',
      'Para recibirlos aunque no tengas EGRESA abierto, tocá «Activar en este navegador» y permití las notificaciones.',
      'En la app del celular los avisos se activan solos al iniciar sesión.',
    ],
    preguntas: [
      {
        pregunta: 'Activé los avisos pero no me llegan',
        respuesta:
          'Revisá que el navegador no tenga bloqueadas las notificaciones de este sitio (ícono del candado junto a la dirección) y usá «Enviar un aviso de prueba».',
      },
      {
        pregunta: '¿Qué es el boletín diario de ofertas?',
        respuesta:
          'Cada mañana EGRESA revisa las ofertas publicadas el día anterior y te avisa las que tienen buena afinidad con tu perfil.',
      },
    ],
  },
  {
    id: 'cuenta',
    titulo: 'Tu cuenta y tu contraseña',
    audiencia: 'todos',
    rutas: ['/cuenta/contrasena'],
    resumen:
      'Cambiá tu contraseña cuando quieras. Las cuentas creadas por la universidad deben cambiarla en el primer ingreso.',
    pasos: [
      'Escribí tu contraseña actual y la nueva dos veces.',
      'La nueva debe tener al menos 8 caracteres y ser distinta de la actual.',
      'Al guardar, la sesión sigue abierta con la nueva contraseña.',
    ],
    preguntas: [
      {
        pregunta: '¿Por qué se cerró mi sesión sola?',
        respuesta:
          'Por seguridad la sesión se cierra después de un rato sin actividad. Volvé a iniciar sesión.',
      },
    ],
  },

  // ─── Egresados ───────────────────────────────────────────────────────────
  {
    id: 'buscar-vacantes',
    titulo: 'Buscar vacantes y postularte',
    audiencia: 'egresado',
    rutas: ['/vacantes', '/empleos'],
    resumen:
      'Buscá ofertas por palabra, ciudad, modalidad o nivel. Con tu sesión iniciada cada vacante muestra tu porcentaje de afinidad.',
    pasos: [
      'Escribí un puesto o habilidad en el buscador y usá los filtros de la izquierda.',
      'Abrí una vacante para ver la descripción, los requisitos y la afinidad con tu perfil.',
      'Tocá «Postularme», respondé las preguntas de la empresa (si las hay) y confirmá.',
      'Seguí el avance en «Mis postulaciones».',
    ],
    preguntas: [
      {
        pregunta: '¿Qué significa el porcentaje de afinidad?',
        respuesta:
          'Compara tu carrera, habilidades, experiencia e idiomas con lo que pide la vacante. Cuanto más completo tu perfil, más preciso.',
      },
      {
        pregunta: 'Una oferta me parece sospechosa',
        respuesta:
          'Abrila y usá «Denunciar oferta». La universidad la revisa; con varias denuncias fundamentadas la oferta se oculta hasta que se decida.',
      },
      {
        pregunta: '¿Por qué no veo ofertas de cierta empresa?',
        respuesta: 'Solo ves ofertas de empresas habilitadas por tu universidad.',
      },
    ],
  },
  {
    id: 'mis-postulaciones',
    titulo: 'Mis postulaciones y entrevistas',
    audiencia: 'egresado',
    rutas: ['/postulaciones'],
    resumen:
      'Acá ves en qué etapa está cada postulación, tus entrevistas y los mensajes de las empresas.',
    pasos: [
      'Filtrá por estado para encontrar rápido una postulación.',
      'Cuando una empresa te propone una entrevista, confirmala o pedí otro horario desde la postulación.',
      'Si ya no te interesa, usá «Retirar postulación» e indicá el motivo.',
    ],
    preguntas: [
      {
        pregunta: '¿Qué significa cada estado?',
        respuesta:
          'Postulado: la empresa todavía no la revisó. En revisión / Preseleccionado: avanzás en el proceso. Entrevista y Pruebas: etapas con la empresa. Contratado o No seleccionado: el proceso terminó.',
      },
      {
        pregunta: '¿Puedo volver a postularme después de retirarme?',
        respuesta: 'Sí, mientras la vacante siga abierta.',
      },
    ],
  },
  {
    id: 'recomendaciones',
    titulo: 'Vacantes recomendadas',
    audiencia: 'egresado',
    rutas: ['/recomendaciones'],
    resumen:
      'EGRESA ordena las ofertas vigentes según tu afinidad y te explica qué criterios cumplís y cuáles te faltan.',
    pasos: [
      'Revisá las primeras: son las que mejor coinciden con tu perfil.',
      'Abrí «Por qué» para ver los criterios que cumplís y los que no.',
      'Si aparece un aviso de perfil incompleto, completá esa sección para mejorar las recomendaciones.',
    ],
    preguntas: [
      {
        pregunta: 'Dice que las recomendaciones no están disponibles',
        respuesta:
          'El servicio de IA puede estar apagado un momento. Mientras tanto podés buscar y postularte normalmente.',
      },
    ],
  },
  {
    id: 'perfil',
    titulo: 'Tu perfil profesional y tu CV',
    audiencia: 'egresado',
    rutas: ['/perfil'],
    resumen:
      'Tu perfil es tu carta de presentación: formación, experiencia, habilidades e idiomas.',
    pasos: [
      'En «Perfil profesional» completá cada sección; las habilidades y la carrera pesan mucho en la afinidad.',
      'En «Visibilidad» elegí quién ve tu perfil y si las empresas pueden ver tu contacto.',
      'Mantené actualizado tu estado de búsqueda (buscando, abierto a ofertas o sin buscar).',
    ],
    preguntas: [
      {
        pregunta: '¿Las empresas ven mi correo?',
        respuesta:
          'Solo si activás la visibilidad del contacto. Si no, se comunican por la mensajería de EGRESA.',
      },
    ],
  },

  // ─── Empresas ────────────────────────────────────────────────────────────
  {
    id: 'publicar-vacantes',
    titulo: 'Publicar y administrar vacantes',
    audiencia: 'empresa',
    rutas: ['/vacantes/crear', '/vacantes/mis-vacantes'],
    resumen: 'Creá ofertas con requisitos claros. La universidad las revisa antes de publicarlas.',
    pasos: [
      'En «Publicar vacante» completá el puesto, las condiciones, las habilidades requeridas y, si querés, preguntas de filtro.',
      'La vacante queda «En revisión» hasta que la universidad la aprueba.',
      'Desde «Mis vacantes» podés pausarla, reactivarla, editar sus preguntas de filtro o eliminarla. Al llegar la fecha límite se cierra sola.',
    ],
    preguntas: [
      {
        pregunta: 'Mi vacante dice «Oculta por denuncias»',
        respuesta:
          'Varios egresados la denunciaron con fundamento. Queda oculta hasta que la universidad revise el caso y decida mantenerla, suspenderla o retirarla.',
      },
      {
        pregunta: '¿Por qué rechazaron mi vacante?',
        respuesta: 'El motivo aparece en la vacante. Corregila y volvé a enviarla a revisión.',
      },
    ],
  },
  {
    id: 'seleccion',
    titulo: 'Proceso de selección',
    audiencia: 'empresa',
    rutas: ['/seleccion'],
    resumen:
      'Un tablero por vacante con las etapas de tu proceso. Mové a cada postulante a medida que avanza.',
    pasos: [
      'Elegí la vacante y configurá sus etapas (por ejemplo: revisión de CV, entrevista, prueba técnica).',
      'Avanzá o descartá postulantes; cada cambio le llega como aviso al egresado.',
      'Dejá notas internas y comparás hasta tres candidatos lado a lado.',
      'Proponé entrevistas con fecha y hora desde la ficha del postulante.',
    ],
    preguntas: [
      {
        pregunta: '¿El egresado ve mis notas internas?',
        respuesta: 'No. Las notas solo las ve tu empresa.',
      },
    ],
  },
  {
    id: 'sugerencias-ia',
    titulo: 'Sugerencias de candidatos con IA',
    audiencia: 'empresa',
    rutas: ['/empresa/sugerencias-ia', '/ia/sugerencias-candidatos'],
    resumen: 'Para cada vacante, EGRESA sugiere egresados con buena afinidad y explica por qué.',
    pasos: [
      'Elegí una de tus vacantes.',
      'Revisá la lista ordenada por afinidad y los criterios que cumple cada candidato.',
      'Abrí el proceso de selección para seguir con los postulantes.',
    ],
    preguntas: [
      {
        pregunta: '¿Por qué no aparece un egresado que conozco?',
        respuesta:
          'Solo se sugieren egresados validados, con perfil visible y de universidades donde tu empresa está habilitada.',
      },
    ],
  },
  {
    id: 'panel-empresa',
    titulo: 'Panel de tu empresa',
    audiencia: 'empresa',
    rutas: ['=/dashboard'],
    resumen:
      'Desde el panel accedés a tus vacantes, al proceso de selección, a las sugerencias de IA y a los reportes.',
    pasos: [
      'Revisá las universidades donde reclutás y pedí permiso en otras nuevas.',
      'Publicá vacantes y seguí a los postulantes desde «Gestionar candidatos».',
      'Usá «Reportes» para sacar listados de tus vacantes y postulantes.',
    ],
    preguntas: [
      {
        pregunta: '¿Por qué no puedo reclutar en una universidad?',
        respuesta:
          'Cada universidad aprueba a las empresas que reclutan a sus egresados. Pedí el permiso y esperá su respuesta.',
      },
    ],
  },

  // ─── Reportes (empresas y universidades) ─────────────────────────────────
  {
    id: 'reportes',
    titulo: 'Reportes personalizados',
    audiencia: 'todos',
    rutas: ['/reportes', '/admin/reportes'],
    resumen:
      'Armá tu propio reporte: elegí qué datos ver, filtrá, elegí las columnas y su orden, y exportalo a Excel, PDF o HTML, o mandalo por correo.',
    pasos: [
      'Elegí qué querés reportar (egresados, empresas, vacantes o postulaciones).',
      'Completá solo los filtros que te interesen: fechas, estados, textos o rangos de números.',
      'Elegí las columnas y ordenalas con las flechas. Definí por qué columnas se ordenan las filas.',
      'Tocá «Generar reporte» para ver la vista previa y después exportala o enviala por correo.',
    ],
    preguntas: [
      {
        pregunta: '¿Cuántas filas puedo exportar?',
        respuesta:
          'Hasta 5.000 por archivo. Si hay más, el archivo lo indica: usá filtros para dividir el reporte.',
      },
      {
        pregunta: 'Dice que mi plan no incluye reportes',
        respuesta:
          'Los reportes están incluidos en los planes Profesional e Institucional de la universidad.',
      },
      {
        pregunta: 'El botón de correo está deshabilitado',
        respuesta:
          'El envío por correo todavía no está configurado en el servidor. Descargá el archivo y envialo vos.',
      },
    ],
  },

  // ─── Universidades ───────────────────────────────────────────────────────
  {
    id: 'panel-admin',
    titulo: 'Panel de la universidad',
    audiencia: 'universidad',
    rutas: ['=/admin'],
    resumen:
      'Resumen de tu universidad: egresados, empresas, vacantes, tareas pendientes y actividad reciente.',
    pasos: [
      'Las tarjetas de «Pendientes» te llevan directo a lo que hay que revisar.',
      'Los números coinciden con los de cada pantalla a la que llevan.',
      'La actividad reciente sale de la bitácora: si está protegida, abrila con la clave de desarrollador.',
    ],
    preguntas: [],
  },
  {
    id: 'validacion-egresados',
    titulo: 'Validar egresados',
    audiencia: 'universidad',
    rutas: ['/admin/validacion-egresados'],
    resumen:
      'Confirmá que quien se registra es egresado de tu universidad antes de que pueda postularse.',
    pasos: [
      'Filtrá las solicitudes pendientes.',
      'Revisá los datos y documentos del egresado.',
      'Aprobá o rechazá indicando el motivo; el egresado recibe el aviso.',
    ],
    preguntas: [
      {
        pregunta: 'Llegué al límite de egresados',
        respuesta:
          'Cada plan tiene un cupo de egresados. Para sumar más, la universidad tiene que subir de plan.',
      },
    ],
  },
  {
    id: 'empresas-universidad',
    titulo: 'Gestión de empresas',
    audiencia: 'universidad',
    rutas: ['/admin/empresas'],
    resumen: 'Decidí qué empresas pueden reclutar a tus egresados.',
    pasos: [
      'Revisá las solicitudes pendientes y los datos de cada empresa.',
      'Habilitá, rechazá o suspendé el permiso para reclutar en tu universidad.',
    ],
    preguntas: [],
  },
  {
    id: 'moderacion',
    titulo: 'Moderación de ofertas',
    audiencia: 'universidad',
    rutas: ['/admin/moderacion-vacantes'],
    resumen: 'Las vacantes nuevas pasan por acá antes de publicarse.',
    pasos: [
      'Abrí cada oferta en revisión y comprobá que sea clara y legítima.',
      'Aprobala para publicarla o rechazala con un motivo para que la empresa la corrija.',
    ],
    preguntas: [],
  },
  {
    id: 'denuncias',
    titulo: 'Denuncias de ofertas',
    audiencia: 'universidad',
    rutas: ['/admin/denuncias'],
    resumen:
      'Ofertas denunciadas por egresados. Con tres denuncias fundamentadas la oferta se oculta sola hasta que decidas.',
    pasos: [
      'Leé los motivos y los detalles de cada denuncia.',
      'Mantené la oferta, suspendela o retirala; dejá una nota con el motivo.',
      'La empresa y quienes denunciaron reciben el aviso de tu decisión.',
    ],
    preguntas: [],
  },
  {
    id: 'bitacora',
    titulo: 'Bitácora confidencial',
    audiencia: 'universidad',
    rutas: ['/admin/bitacora'],
    resumen:
      'Registra quién hizo qué, cuándo y desde qué IP. Se guarda cifrada: ni el administrador de la base de datos puede leerla.',
    pasos: [
      'Ingresá la clave de desarrollador para abrirla. No se guarda: al recargar hay que volver a escribirla.',
      'Filtrá por usuario, módulo, acción o fechas.',
      'Exportá el resultado a Excel o PDF para una auditoría.',
      'Al terminar, tocá «Cerrar bitácora».',
    ],
    preguntas: [
      {
        pregunta: 'Puse mal la clave varias veces',
        respuesta:
          'Después de cinco intentos fallidos hay que esperar 15 minutos. Cada intento queda registrado.',
      },
      {
        pregunta: '¿Quién tiene la clave de desarrollador?',
        respuesta:
          'Solo el equipo responsable del sistema. Si se pierde, las entradas cifradas no se pueden recuperar.',
      },
    ],
  },
  {
    id: 'respaldos',
    titulo: 'Copias de seguridad',
    audiencia: 'universidad',
    rutas: ['/admin/respaldos'],
    resumen:
      'Respaldá y restaurá toda la plataforma. Además, el sistema hace una copia automática todos los días.',
    pasos: [
      'Creá una copia antes de cambios grandes y descargala para guardarla fuera del servidor.',
      'Para restaurar, primero usá «Verificar» (no cambia nada) y después «Restaurar» con tu contraseña.',
      'Antes de restaurar se guarda sola una copia del estado actual por si hay que volver atrás.',
    ],
    preguntas: [
      {
        pregunta: '¿Se pierde la bitácora al restaurar?',
        respuesta: 'No: las entradas posteriores a la copia se conservan.',
      },
    ],
  },
  {
    id: 'tareas',
    titulo: 'Tareas automáticas',
    audiencia: 'universidad',
    rutas: ['/admin/tareas'],
    resumen:
      'Procesos que corren solos todos los días: copia de seguridad, cierre de vacantes vencidas, boletín de ofertas y recordatorios de lo que vence en las próximas 24 horas.',
    pasos: [
      'Revisá cuándo corrió cada tarea por última vez y su resultado.',
      'Usá «Ejecutar ahora» para correrla en el momento (no reemplaza la ejecución automática del día).',
      'Abrí el historial para ver las últimas ejecuciones.',
    ],
    preguntas: [
      {
        pregunta: '¿Qué avisan los recordatorios?',
        respuesta:
          'Las vacantes que cierran en las próximas 24 horas (a la empresa y a los egresados afines que no se postularon) y las entrevistas de las próximas 24 horas (al egresado y a la empresa). No repiten el mismo aviso en el día.',
      },
      {
        pregunta: '¿Qué pasa si el servidor estaba apagado a la hora programada?',
        respuesta: 'La tarea corre apenas el servidor vuelve, una sola vez por día.',
      },
    ],
  },
  {
    id: 'roles-universidades',
    titulo: 'Roles, universidades y planes',
    audiencia: 'universidad',
    rutas: ['/admin/roles', '/admin/universidades'],
    resumen:
      'Administrá las cuentas institucionales y, como superadmin, las universidades y sus planes.',
    pasos: [
      'En «Gestión de roles» creá cuentas de moderador o administrador para tu universidad.',
      'En «Universidades» el superadmin aprueba altas, cambia planes y registra pagos.',
    ],
    preguntas: [
      {
        pregunta: '¿Qué incluye cada plan?',
        respuesta:
          'Los planes fijan el cupo de egresados y moderadores y si la universidad tiene reportes personalizados.',
      },
    ],
  },
  {
    id: 'grupos',
    titulo: 'Grupos y permisos',
    audiencia: 'universidad',
    rutas: ['/admin/grupos'],
    resumen:
      'Agrupá a administradores y moderadores y elegí qué menús, formularios, botones y etiquetas del panel ve cada grupo.',
    pasos: [
      'Tocá «Nuevo grupo», ponele un nombre y marcá a las personas que lo forman.',
      'Marcá los componentes que el grupo puede usar. «Empezar desde» copia lo que ve cada rol y desde ahí ajustás.',
      'Guardá: el cambio vale al instante, también en el servidor (un botón oculto tampoco funciona por otro camino).',
      'En «Lo que ve cada persona» revisá el resultado de cada cuenta con «Ver detalle».',
    ],
    preguntas: [
      {
        pregunta: '¿Qué ve alguien que no está en ningún grupo?',
        respuesta:
          'Lo que corresponde a su rol: el administrador ve todo el panel y el moderador, todo menos usuarios, grupos y plan.',
      },
      {
        pregunta: '¿Y si una persona está en dos grupos?',
        respuesta: 'Ve la suma de los permisos de sus grupos.',
      },
      {
        pregunta: 'Le di «Gestión de roles» a un moderador y no la ve',
        respuesta:
          'Los componentes marcados «solo admin» no se aplican a moderadores aunque su grupo los tenga. Y el administrador conserva siempre «Grupos y permisos» para no quedar afuera.',
      },
    ],
  },
];

function coincide(ruta: string, patron: string): number {
  if (patron.startsWith('=')) return ruta === patron.slice(1) ? patron.length : -1;
  return ruta === patron || ruta.startsWith(patron + '/') || ruta.startsWith(patron + '?')
    ? patron.length
    : -1;
}

/** Audiencia del usuario según su rol. */
export function audienciaDeRol(rol: string): Audiencia | null {
  if (rol === 'candidate') return 'egresado';
  if (rol === 'empresa') return 'empresa';
  if (rol === 'platform_admin' || rol === 'moderator') return 'universidad';
  return null;
}

/** El tema que corresponde a una pantalla: el de la ruta más específica para ese usuario. */
export function temaParaRuta(url: string, rol: string): TemaAyuda {
  const ruta = url.split(/[?#]/)[0] || '/';
  const audiencia = audienciaDeRol(rol);
  let mejor: TemaAyuda | null = null;
  let largo = -1;
  for (const tema of TEMAS_AYUDA) {
    if (audiencia && tema.audiencia !== 'todos' && tema.audiencia !== audiencia) continue;
    for (const patron of tema.rutas) {
      const n = coincide(ruta, patron);
      if (n > largo) {
        mejor = tema;
        largo = n;
      }
    }
  }
  if (mejor) return mejor;
  const porDefecto =
    audiencia === 'empresa'
      ? 'panel-empresa'
      : audiencia === 'universidad'
        ? 'panel-admin'
        : 'buscar-vacantes';
  return TEMAS_AYUDA.find((t) => t.id === (audiencia ? porDefecto : 'primeros-pasos'))!;
}

function normalizar(texto: string): string {
  return texto.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
}

/** Búsqueda simple sin acentos en títulos, resúmenes, pasos y preguntas. */
export function buscarTemas(consulta: string, temas: TemaAyuda[] = TEMAS_AYUDA): TemaAyuda[] {
  const palabras = normalizar(consulta).split(/\s+/).filter(Boolean);
  if (!palabras.length) return temas;
  return temas.filter((t) => {
    const texto = normalizar(
      [
        t.titulo,
        t.resumen,
        ...t.pasos,
        ...t.preguntas.flatMap((p) => [p.pregunta, p.respuesta]),
      ].join(' '),
    );
    return palabras.every((p) => texto.includes(p));
  });
}
