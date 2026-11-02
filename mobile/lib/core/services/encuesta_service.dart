import '../models/encuesta.dart';
import 'api_config.dart';
import 'api_http.dart';

/// Respuesta a una pregunta: según el tipo va la opción elegida, el texto o el número.
class RespuestaPregunta {
  final String preguntaId;
  final String? opcionId;
  final String? texto;
  final num? numero;

  const RespuestaPregunta(this.preguntaId, {this.opcionId, this.texto, this.numero});

  Map<String, dynamic> toJson() => {
        'pregunta_id': preguntaId,
        if (opcionId != null) 'opcion_id': opcionId,
        if (texto != null) 'texto': texto,
        if (numero != null) 'numero': numero,
      };
}

/// Encuestas de situación laboral del egresado (HU-30, backend/app/features/encuestas).
class EncuestaService {
  Uri _uri(String ruta) => Uri.parse('${ApiConfig.baseUrl}/encuestas$ruta');

  /// GET /encuestas/mias: las de su universidad, respondidas o no.
  Future<List<MiEncuesta>> mias(String accessToken) async {
    final respuesta = await obtener(_uri('/mias'), accessToken: accessToken);
    if (respuesta.statusCode != 200) {
      throw ApiException(mensajeDeError(respuesta, 'No se pudieron cargar tus encuestas.'), codigo: respuesta.statusCode);
    }
    return (decodificar(respuesta) as List<dynamic>)
        .map((e) => MiEncuesta.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// GET /encuestas/{id}/formulario. Si ya la respondió o cerró, lanza [ApiException] (409 o 400).
  Future<FormularioEncuesta> formulario(String accessToken, String encuestaId) async {
    final respuesta = await obtener(_uri('/$encuestaId/formulario'), accessToken: accessToken);
    if (respuesta.statusCode != 200) {
      throw ApiException(mensajeDeError(respuesta, 'No se pudo abrir la encuesta.'), codigo: respuesta.statusCode);
    }
    return FormularioEncuesta.fromJson(decodificar(respuesta) as Map<String, dynamic>);
  }

  /// POST /encuestas/{id}/respuestas. Devuelve el mensaje para mostrar.
  Future<String> responder(String accessToken, String encuestaId, List<RespuestaPregunta> respuestas) async {
    final respuesta = await enviar(
      _uri('/$encuestaId/respuestas'),
      accessToken: accessToken,
      cuerpo: {'respuestas': respuestas.map((r) => r.toJson()).toList()},
    );
    if (respuesta.statusCode != 201) {
      throw ApiException(mensajeDeError(respuesta, 'No se pudo enviar la encuesta. Intentá de nuevo.'), codigo: respuesta.statusCode);
    }
    final cuerpo = decodificar(respuesta) as Map<String, dynamic>;
    return cuerpo['mensaje'] as String? ?? '¡Gracias! Tu respuesta quedó registrada.';
  }
}
