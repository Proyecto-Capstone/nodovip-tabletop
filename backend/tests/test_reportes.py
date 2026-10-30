"""Servicio de reportes (PB-14) con dobles en memoria."""

import dataclasses
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.adapters.outbound.en_vivo.memoria import EnVivoEnMemoria
from app.adapters.outbound.reportes.html import renderizar
from app.application.reportes import ServicioReportes
from app.application.sesiones import SesionNoEncontrada
from app.domain.escenarios import Inject, Nivel, RolEjercicio
from app.domain.evaluacion import AjustePuntaje, evaluar
from app.domain.reportes import EstadoReporte, Severidad, TipoBrecha
from app.domain.respuestas import Respuesta
from app.domain.sesiones import (
    EstadoSesion,
    OpcionRespuesta,
    ParticipanteSesion,
    SesionTabletop,
    TareaSesion,
    TipoTarea,
)
from app.domain.usuarios import RolNombre, Usuario
from tests.fakes import (
    GeneradorPdfFalso,
    RepoReportesEnMemoria,
    RepoRespuestasEnMemoria,
    RepoSesionesEnMemoria,
    RepoUsuariosEnMemoria,
)

ID_MODERADOR = uuid4()
ID_ANA = uuid4()
ID_LUIS = uuid4()
T0 = datetime(2026, 11, 2, 14, 0, tzinfo=UTC)


class CatalogoFalso:
    def roles_ejercicio(self):
        return [RolEjercicio("ti", "Responsable de TI"), RolEjercicio("legal", "Legal")]


@dataclasses.dataclass
class _Escenario:
    nombre: str = "Ransomware en sucursal"


class EscenariosFalsos:
    def obtener(self, escenario_id):
        return _Escenario()


def _sesion(cliente="Banco Andino", finalizada_en=T0 + timedelta(hours=1)):
    i1 = Inject("Detección", "Archivos cifrados", orden=1)
    i2 = Inject("Extorsión", "Piden rescate", orden=2)
    return SesionTabletop(
        nombre="Simulacro Q4",
        cliente=cliente,
        escenario_id=uuid4(),
        moderador_id=ID_MODERADOR,
        roles=["ti", "legal"],
        injects=[i1, i2],
        tareas=[
            TareaSesion(
                "¿Qué hace primero?",
                "ti",
                Nivel.ALTO,
                [],
                inject_id=i1.id,
                tipo=TipoTarea.SELECCION_MULTIPLE,
                opciones=[
                    OpcionRespuesta("Aislar los servidores", correcta=True),
                    OpcionRespuesta("Pagar el rescate"),
                ],
            ),
            TareaSesion(
                "¿A quién notifica?",
                "legal",
                Nivel.MEDIO,
                ["Notificar al regulador", "Informar a los clientes"],
                inject_id=i1.id,
            ),
            # Del inject 2, que no se lanzó: no cuenta.
            TareaSesion("¿Paga?", "ti", Nivel.BAJO, ["No pagar"], inject_id=i2.id),
        ],
        participantes=[
            ParticipanteSesion(ID_ANA, "ti"),
            ParticipanteSesion(ID_LUIS, "legal"),
        ],
        estado=EstadoSesion.FINALIZADA,
        iniciada_en=finalizada_en - timedelta(minutes=45),
        finalizada_en=finalizada_en,
        inject_actual=1,
    )


@pytest.fixture
def e():
    sesiones, respuestas = RepoSesionesEnMemoria(), RepoRespuestasEnMemoria()
    usuarios, reportes = RepoUsuariosEnMemoria(), RepoReportesEnMemoria()
    for uid, nombre, rol in [
        (ID_MODERADOR, "Mónica Moderadora", RolNombre.MODERADOR),
        (ID_ANA, "Ana López", RolNombre.PARTICIPANTE),
        (ID_LUIS, "Luis Paz", RolNombre.PARTICIPANTE),
    ]:
        usuarios.guardar(Usuario(f"{uid}@demo.test", nombre, "x", rol, id=uid))
    generador = GeneradorPdfFalso()
    servicio = ServicioReportes(
        sesiones,
        respuestas,
        CatalogoFalso(),
        usuarios,
        EscenariosFalsos(),
        EnVivoEnMemoria(),
        reportes,
        generador,
        reloj=lambda: T0 + timedelta(hours=2),
    )
    return {
        "sesiones": sesiones,
        "respuestas": respuestas,
        "reportes": reportes,
        "generador": generador,
        "servicio": servicio,
    }


def _responder(e, sesion, usuario_id, tarea, texto=None, opciones=(), segundos=30):
    evaluacion = evaluar(tarea, sesion.pesos, texto, list(opciones), segundos)
    r = Respuesta(
        sesion_id=sesion.id,
        tarea_id=tarea.id,
        inject_id=tarea.inject_id,
        usuario_id=usuario_id,
        rol_codigo=tarea.rol_codigo,
        recibida_en=sesion.iniciada_en + timedelta(seconds=segundos),
        segundos_usados=segundos,
        texto=texto,
        opciones_elegidas=list(opciones),
        evaluacion=evaluacion,
    )
    e["respuestas"].guardar(r)
    return r


def test_contenido_con_puntajes_brechas_trazabilidad_y_recomendaciones(e):
    sesion = _sesion()
    e["sesiones"].guardar(sesion)
    ti, legal = sesion.tareas[0], sesion.tareas[1]
    _responder(e, sesion, ID_ANA, ti, opciones=[1])  # opción incorrecta
    _responder(e, sesion, ID_LUIS, legal, texto="Hay que notificar al regulador")

    r = e["servicio"].contenido(sesion.id, ID_MODERADOR, es_moderador=True)
    assert (r.nombre, r.cliente, r.escenario, r.moderador) == (
        "Simulacro Q4",
        "Banco Andino",
        "Ransomware en sucursal",
        "Mónica Moderadora",
    )
    assert r.duracion_segundos == 45 * 60 and r.participantes == 2
    assert r.injects_lanzados == 1 and r.total_injects == 2
    assert [f.nombre for f in r.por_rol] == ["Legal", "Responsable de TI"]
    # Solo cuentan las tareas del inject 1 (el 2 no se lanzó).
    assert {b.tarea for b in r.brechas} == {"¿Qué hace primero?", "¿A quién notifica?"}
    tipos = {b.rol_nombre: (b.tipo, b.severidad) for b in r.brechas}
    assert tipos["Responsable de TI"] == (
        TipoBrecha.DECISION_INCORRECTA,
        Severidad.ALTA,
    )
    assert tipos["Legal"][0] == TipoBrecha.RESPUESTA_INCOMPLETA
    assert [x.contenido for x in r.respuestas] == [
        "Pagar el rescate",
        "Hay que notificar al regulador",
    ]
    assert len(r.recomendaciones) == 2 and r.sesiones_anteriores == 0


def test_tarea_sin_responder_es_brecha_y_un_ajuste_la_cierra(e):
    sesion = _sesion()
    e["sesiones"].guardar(sesion)
    ti = sesion.tareas[0]
    r = _responder(e, sesion, ID_ANA, ti, opciones=[1])
    contenido = e["servicio"].contenido(sesion.id, ID_MODERADOR, True)
    assert {b.participante: b.tipo for b in contenido.brechas}["Luis Paz"] == (
        TipoBrecha.SIN_RESPUESTA
    )
    # El moderador sube el puntaje de Ana a 10: deja de ser brecha.
    e["respuestas"].agregar_ajuste(
        AjustePuntaje(r.id, ID_MODERADOR, 0, 10, "Revisado", T0), sesion.id
    )
    contenido = e["servicio"].contenido(sesion.id, ID_MODERADOR, True)
    assert "Ana López" not in {b.participante for b in contenido.brechas}
    assert contenido.respuestas[0].ajustada


def test_historial_del_mismo_cliente_marca_recurrentes_y_superadas(e):
    anterior = _sesion(finalizada_en=T0 - timedelta(days=30))
    otro_cliente = _sesion(
        cliente="Otra Empresa", finalizada_en=T0 - timedelta(days=10)
    )
    actual = _sesion(cliente="  banco   ANDINO ")
    actual.cliente = "banco andino"  # el mismo cliente, escrito distinto
    for s in (anterior, otro_cliente, actual):
        e["sesiones"].guardar(s)
    # En la anterior nadie respondió; en la actual, Ana responde bien.
    _responder(e, actual, ID_ANA, actual.tareas[0], opciones=[0], segundos=1)

    r = e["servicio"].contenido(actual.id, ID_MODERADOR, True)
    assert r.sesiones_anteriores == 1  # la de otro cliente no cuenta
    [legal] = r.brechas
    assert legal.rol_nombre == "Legal" and legal.recurrente_en == 1
    assert [b.rol_nombre for b in r.superadas] == ["Responsable de TI"]
    assert r.recomendaciones[0].recurrente
    assert r.recomendaciones[0].prioridad == Severidad.ALTA


def test_sin_cliente_no_hay_historial(e):
    anterior = _sesion(cliente=None, finalizada_en=T0 - timedelta(days=30))
    actual = _sesion(cliente=None)
    e["sesiones"].guardar(anterior)
    e["sesiones"].guardar(actual)
    assert (
        e["servicio"].contenido(actual.id, ID_MODERADOR, True).sesiones_anteriores == 0
    )


def test_acceso_solo_a_sesiones_finalizadas_y_el_moderador_a_las_suyas(e):
    sesion = _sesion()
    en_curso = dataclasses.replace(_sesion(), id=uuid4(), estado=EstadoSesion.EN_CURSO)
    e["sesiones"].guardar(sesion)
    e["sesiones"].guardar(en_curso)
    servicio = e["servicio"]
    with pytest.raises(SesionNoEncontrada):
        servicio.contenido(sesion.id, uuid4(), es_moderador=True)  # moderador ajeno
    with pytest.raises(SesionNoEncontrada):
        servicio.contenido(en_curso.id, ID_MODERADOR, es_moderador=True)
    # Analista o administrador: cualquier sesión finalizada.
    assert servicio.contenido(sesion.id, uuid4(), es_moderador=False).nombre
    assert [x.sesion.id for x in servicio.visibles(uuid4(), False)] == [sesion.id]
    assert servicio.visibles(uuid4(), True) == []


def test_pdf_se_genera_una_vez_y_se_reutiliza(e):
    sesion = _sesion()
    e["sesiones"].guardar(sesion)
    servicio = e["servicio"]
    pdf = servicio.pdf(sesion.id, ID_MODERADOR, True)
    assert pdf.startswith(b"%PDF")
    assert servicio.pdf(sesion.id, ID_MODERADOR, True) == pdf
    assert len(e["generador"].recibidos) == 1
    guardado = e["reportes"].obtener(sesion.id)
    assert guardado.estado == EstadoReporte.GENERADO and guardado.generado_en
    servicio.regenerar(sesion.id, ID_MODERADOR, True)
    assert len(e["generador"].recibidos) == 2


def test_generar_al_cerrar_no_lanza_y_registra_el_fallo(e):
    sesion = _sesion()
    e["sesiones"].guardar(sesion)
    e["servicio"].generador = GeneradorPdfFalso(fallar=True)
    e["servicio"].generar_al_cerrar(sesion.id)  # no lanza
    guardado = e["reportes"].obtener(sesion.id)
    assert guardado.estado == EstadoReporte.FALLIDO
    assert "WeasyPrint no disponible" in guardado.error


def test_el_html_escapa_lo_que_escriben_los_participantes(e):
    sesion = _sesion()
    e["sesiones"].guardar(sesion)
    _responder(e, sesion, ID_LUIS, sesion.tareas[1], texto="<script>alert(1)</script>")
    html = renderizar(e["servicio"].contenido(sesion.id, ID_MODERADOR, True))
    assert "<script>alert" not in html and "&lt;script&gt;" in html
    for seccion in (
        "1. Resumen ejecutivo",
        "2. Puntajes finales",
        "3. Brechas detectadas por rol",
        "4. Trazabilidad",
        "5. Recomendaciones",
    ):
        assert seccion in html
    assert "Banco Andino" in html and "Mónica Moderadora" in html
