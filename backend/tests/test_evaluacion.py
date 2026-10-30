"""Evaluador automático de respuestas (PB-10): núcleo de dominio puro."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.escenarios import Nivel
from app.domain.evaluacion import (
    AjustePuntaje,
    evaluar,
    puntaje_vigente,
    sin_respuesta,
    validar_ajuste,
)
from app.domain.sesiones import (
    OpcionRespuesta,
    PesosPuntuacion,
    ReglaSesionError,
    TareaSesion,
    TipoTarea,
)

PESOS = PesosPuntuacion(completitud=40, precision=40, tiempo=20)


def seleccion(puntaje=10, limite=300):
    return TareaSesion(
        "¿Qué hace primero?",
        "ti",
        Nivel.MEDIO,
        [],
        tipo=TipoTarea.SELECCION_MULTIPLE,
        opciones=[
            OpcionRespuesta("Aislar los servidores", correcta=True),
            OpcionRespuesta("Pagar el rescate"),
            OpcionRespuesta("Avisar al CISO", correcta=True),
            OpcionRespuesta("Apagar el internet de la empresa"),
        ],
        puntaje_maximo=puntaje,
        tiempo_limite_segundos=limite,
    )


def texto(criterios, esperada=None, puntaje=10):
    return TareaSesion(
        "¿A quién notifica?",
        "legal",
        Nivel.MEDIO,
        criterios,
        puntaje_maximo=puntaje,
        tiempo_limite_segundos=300,
        respuesta_esperada=esperada,
    )


# --- Selección múltiple -------------------------------------------------------------


def test_seleccion_perfecta_e_inmediata_da_el_maximo():
    e = evaluar(seleccion(), PESOS, None, [0, 2], segundos_usados=0)
    assert e.puntaje == 10 and e.puntaje_maximo == 10
    assert (e.completitud, e.precision, e.tiempo) == (1, 1, 1)
    assert e.aciertos == ["Aislar los servidores", "Avisar al CISO"]
    assert e.faltantes == [] and e.errores == []


def test_seleccion_perfecta_al_limite_conserva_la_mitad_del_tiempo():
    e = evaluar(seleccion(), PESOS, None, [0, 2], segundos_usados=300)
    assert e.tiempo == 0.5
    assert e.puntaje == 9  # 10 × (40 + 40 + 20·0,5) / 100


def test_respuesta_parcial_una_de_dos_correctas():
    e = evaluar(seleccion(), PESOS, None, [0], segundos_usados=0)
    assert e.completitud == 0.5 and e.precision == 1
    assert e.puntaje == 8  # 10 × (20 + 40 + 20) / 100
    assert e.faltantes == ["Avisar al CISO"]


def test_marcar_todas_las_opciones_no_da_puntaje_completo():
    e = evaluar(seleccion(), PESOS, None, [0, 1, 2, 3], segundos_usados=0)
    assert e.completitud == 1 and e.precision == 0.5
    assert e.puntaje == 8
    assert e.errores == [
        "Marcó una opción incorrecta: Pagar el rescate",
        "Marcó una opción incorrecta: Apagar el internet de la empresa",
    ]


def test_solo_opciones_incorrectas_da_cero_aunque_sea_rapido():
    e = evaluar(seleccion(), PESOS, None, [1], segundos_usados=0)
    assert e.puntaje == 0 and e.tiempo == 0
    assert e.errores == ["Marcó una opción incorrecta: Pagar el rescate"]


def test_indices_inexistentes_se_ignoran():
    e = evaluar(seleccion(), PESOS, None, [0, 2, 99, -1], segundos_usados=0)
    assert e.puntaje == 10


# --- Casos límite -------------------------------------------------------------------


def test_sin_respuesta_da_cero_y_lista_lo_esperado():
    e = sin_respuesta(seleccion())
    assert e.puntaje == 0 and e.puntaje_maximo == 10
    assert e.errores == ["Sin respuesta"]
    assert e.faltantes == ["Aislar los servidores", "Avisar al CISO"]
    assert sin_respuesta(texto(["Regulador"])).faltantes == ["Regulador"]


def test_fuera_de_tiempo_da_cero():
    # Dentro de la tolerancia de red (2 s) todavía cuenta.
    assert evaluar(seleccion(), PESOS, None, [0, 2], segundos_usados=302).puntaje == 9
    e = evaluar(seleccion(), PESOS, None, [0, 2], segundos_usados=303)
    assert e.puntaje == 0 and e.errores == ["Respuesta fuera de tiempo"]


def test_texto_vacio_da_cero():
    e = evaluar(texto(["Notificar al regulador"]), PESOS, "", [], segundos_usados=5)
    assert e.puntaje == 0 and e.faltantes == ["Notificar al regulador"]


# --- Texto libre --------------------------------------------------------------------


def test_texto_cumple_todos_los_criterios_sin_tildes_ni_mayusculas():
    tarea = texto(
        ["Notificar a la Superintendencia", "Informar a los clientes afectados"]
    )
    e = evaluar(
        tarea,
        PESOS,
        "Notifico a la SUPERINTENDENCIA y luego informo a cada cliente afectado.",
        [],
        segundos_usados=0,
    )
    assert e.completitud == 1 and e.precision == 1
    assert e.puntaje == 10
    assert e.aciertos == tarea.criterios


def test_texto_parcial_cumple_un_criterio_de_dos():
    tarea = texto(["Notificar al regulador", "Preservar evidencia forense"])
    e = evaluar(tarea, PESOS, "Hay que notificar al regulador.", [], segundos_usados=0)
    assert e.completitud == 0.5
    assert e.aciertos == ["Notificar al regulador"]
    assert e.faltantes == ["Preservar evidencia forense"]
    assert 0 < e.puntaje < 10


def test_texto_sin_relacion_con_los_criterios_da_cero():
    e = evaluar(
        texto(["Notificar al regulador"]), PESOS, "Esperamos a ver qué pasa", [], 0
    )
    assert e.puntaje == 0


def test_criterio_corto_se_reconoce():
    e = evaluar(texto(["TI"]), PESOS, "Escalo a TI de inmediato", [], segundos_usados=0)
    assert e.aciertos == ["TI"]


def test_la_respuesta_esperada_afecta_la_precision():
    tarea = texto(
        ["Notificar al regulador"], esperada="Notificar al regulador en 72 horas"
    )
    breve = evaluar(tarea, PESOS, "Notificar al regulador", [], 0)
    completa = evaluar(tarea, PESOS, "Notificar al regulador dentro de 72 horas", [], 0)
    assert breve.completitud == completa.completitud == 1
    assert breve.precision < completa.precision == 1


def test_los_pesos_cambian_el_puntaje():
    solo_completitud = PesosPuntuacion(completitud=100, precision=0, tiempo=0)
    e = evaluar(seleccion(), solo_completitud, None, [0, 1, 2, 3], segundos_usados=300)
    assert e.puntaje == 10  # todas las correctas marcadas: completitud 1


def test_puntaje_con_decimales_se_redondea():
    e = evaluar(seleccion(puntaje=7), PESOS, None, [0], segundos_usados=100)
    assert e.puntaje == round(7 * (20 + 40 + 20 * (1 - 0.5 * 100 / 300)) / 100, 2)


# --- Ajuste manual ------------------------------------------------------------------


def test_validar_ajuste():
    validar_ajuste(7.5, 10, "Respuesta correcta con otras palabras")
    with pytest.raises(ReglaSesionError) as e:
        validar_ajuste(11, 10, "ok")
    assert e.value.errores == [
        "El puntaje debe estar entre 0 y 10",
        "Explica el motivo del ajuste (al menos 5 caracteres)",
    ]
    with pytest.raises(ReglaSesionError):
        validar_ajuste(-1, 10, "Motivo válido")
    with pytest.raises(ReglaSesionError):
        validar_ajuste(float("nan"), 10, "Motivo válido")


def test_puntaje_vigente_es_el_del_ultimo_ajuste():
    e = evaluar(seleccion(), PESOS, None, [0], segundos_usados=0)
    assert puntaje_vigente(e, []) == 8
    ahora = datetime(2026, 11, 2, 15, 0, tzinfo=UTC)
    ajuste = lambda nuevo, minutos: AjustePuntaje(
        uuid4(), uuid4(), 8, nuevo, "Revisión", ahora + timedelta(minutes=minutos)
    )
    assert puntaje_vigente(e, [ajuste(10, 5), ajuste(9, 1)]) == 10
