/// Ítems del CV del egresado (ver backend/app/features/perfil/schema.py).
/// Cada clase corresponde a una sección editable de /perfiles/me/*.

class Formacion {
  final String id;
  final String institucion;
  final String programa;
  final String? estadoAcademico;

  const Formacion({
    required this.id,
    required this.institucion,
    required this.programa,
    this.estadoAcademico,
  });

  factory Formacion.fromJson(Map<String, dynamic> json) => Formacion(
        id: json['id'] as String,
        institucion: json['institucion'] as String,
        programa: json['programa'] as String,
        estadoAcademico: json['estado_academico'] as String?,
      );
}

class Experiencia {
  final String id;
  final String empresa;
  final String cargo;
  final String? descripcion;

  const Experiencia({
    required this.id,
    required this.empresa,
    required this.cargo,
    this.descripcion,
  });

  factory Experiencia.fromJson(Map<String, dynamic> json) => Experiencia(
        id: json['id'] as String,
        empresa: json['empresa'] as String,
        cargo: json['cargo'] as String,
        descripcion: json['descripcion'] as String?,
      );
}

class Idioma {
  final String id;
  final String idioma;
  final String nivel;

  const Idioma({required this.id, required this.idioma, required this.nivel});

  factory Idioma.fromJson(Map<String, dynamic> json) => Idioma(
        id: json['id'] as String,
        idioma: json['idioma'] as String,
        nivel: json['nivel'] as String? ?? 'basico',
      );
}

class Certificacion {
  final String id;
  final String nombre;
  final String? entidadEmisora;

  const Certificacion({required this.id, required this.nombre, this.entidadEmisora});

  factory Certificacion.fromJson(Map<String, dynamic> json) => Certificacion(
        id: json['id'] as String,
        nombre: json['nombre'] as String,
        entidadEmisora: json['entidad_emisora'] as String?,
      );
}

class Habilidad {
  final String id;
  final String nombre;
  final String? categoria;

  const Habilidad({required this.id, required this.nombre, this.categoria});

  factory Habilidad.fromJson(Map<String, dynamic> json) => Habilidad(
        id: json['id'] as String,
        nombre: json['nombre'] as String,
        categoria: json['categoria'] as String?,
      );
}
