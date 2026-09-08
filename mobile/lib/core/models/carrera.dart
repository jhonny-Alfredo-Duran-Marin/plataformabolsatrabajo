/// Carrera del catálogo institucional (ver backend/app/features/catalogo/schema.py::CarreraResponse).
class Carrera {
  final String id;
  final String nombre;
  final String? facultad;

  const Carrera({required this.id, required this.nombre, this.facultad});

  factory Carrera.fromJson(Map<String, dynamic> json) {
    return Carrera(
      id: json['id'] as String,
      nombre: json['nombre'] as String,
      facultad: json['facultad'] as String?,
    );
  }
}
