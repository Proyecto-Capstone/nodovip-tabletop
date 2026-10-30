"""Brechas y recomendaciones del reporte (PB-14): núcleo de dominio puro."""

from uuid import uuid4

from app.domain.reportes import (
    ResultadoTarea,
    Severidad,
    TipoBrecha,
    detectar_brechas,
    marcar_recurrentes,
    recomendar,
    superadas,
)


def resultado(puntaje, *, maximo=10, rol="legal", tarea="Notificar al regulador", **kw):
    return ResultadoTarea(
        usuario_id=uuid4(),
        participante=kw.pop("participante", "Pedro"),
        rol_codigo=rol,
        rol_nombre=kw.pop("rol_nombre", "Legal"),
        tarea_id=uuid4(),
        tarea=tarea,
        inject_orden=kw.pop("inject", 1),
        puntaje_maximo=maximo,
        puntaje=puntaje,
        **kw,
    )


def test_sin_respuesta_es_brecha_alta():
    [b] = detectar_brechas([resultado(None, faltantes=["Avisar en 72 h"])])
    assert b.tipo == TipoBrecha.SIN_RESPUESTA and b.severidad == Severidad.ALTA
    assert b.porcentaje == 0 and b.detalle == ["Avisar en 72 h"]


def test_desde_el_85_por_ciento_no_hay_brecha():
    assert detectar_brechas([resultado(8.5), resultado(10)]) == []


def test_severidad_segun_el_porcentaje():
    brechas = detectar_brechas(
        [
            resultado(8, faltantes=["a"], participante="Baja"),
            resultado(5, faltantes=["a"], participante="Media"),
            resultado(3.9, faltantes=["a"], participante="Alta"),
        ]
    )
    assert [(b.participante, b.severidad) for b in brechas] == [
        ("Alta", Severidad.ALTA),
        ("Media", Severidad.MEDIA),
        ("Baja", Severidad.BAJA),
    ]
    assert all(b.tipo == TipoBrecha.RESPUESTA_INCOMPLETA for b in brechas)


def test_opciones_incorrectas_son_decision_incorrecta():
    [b] = detectar_brechas(
        [resultado(6, errores=["Marcó una opción incorrecta: Pagar el rescate"])]
    )
    assert b.tipo == TipoBrecha.DECISION_INCORRECTA
    assert b.detalle == ["Marcó una opción incorrecta: Pagar el rescate"]


def test_fuera_de_tiempo_es_siempre_alta():
    [b] = detectar_brechas([resultado(0, errores=["Respuesta fuera de tiempo"])])
    assert b.tipo == TipoBrecha.FUERA_DE_TIEMPO and b.severidad == Severidad.ALTA


def test_un_ajuste_del_moderador_cierra_la_brecha():
    # El puntaje que recibe es el vigente: si el moderador lo subió a 9, no hay brecha.
    assert detectar_brechas([resultado(9, faltantes=["a"])]) == []


def test_recurrentes_y_superadas_contra_el_historial():
    actual = detectar_brechas(
        [
            resultado(None, tarea="Notificar al regulador"),
            resultado(None, rol="ti", rol_nombre="TI", tarea="Aislar servidores"),
        ]
    )
    anterior_1 = detectar_brechas(
        [resultado(2, tarea="Notificar  al REGULADOR", faltantes=["a"])]
    )
    anterior_2 = detectar_brechas(
        [
            resultado(None, tarea="Notificar al regulador"),
            resultado(None, rol="ceo", rol_nombre="CEO", tarea="Activar continuidad"),
        ]
    )
    marcadas = marcar_recurrentes(actual, [anterior_1, anterior_2])
    por_rol = {b.rol_codigo: b.recurrente_en for b in marcadas}
    assert por_rol == {"legal": 2, "ti": 0}
    # Comparado con la sesión inmediatamente anterior, nada mejoró de Legal.
    assert superadas(actual, [anterior_1]) == []
    assert [b.rol_codigo for b in superadas(actual, [anterior_2])] == ["ceo"]


def test_recomendaciones_por_rol_y_tipo_con_prioridad():
    brechas = marcar_recurrentes(
        detectar_brechas(
            [
                resultado(5, faltantes=["Avisar en 72 h", "Informar a clientes"]),
                resultado(8, rol="ti", rol_nombre="TI", faltantes=["Aislar"]),
            ]
        ),
        [detectar_brechas([resultado(None, rol="ti", rol_nombre="TI")])],
    )
    recs = recomendar(brechas, sesiones_anteriores=1)
    # TI es baja por porcentaje, pero recurrente: sube a alta y va primero.
    assert [(r.rol_nombre, r.prioridad, r.recurrente) for r in recs] == [
        ("TI", Severidad.ALTA, True),
        ("Legal", Severidad.MEDIA, False),
    ]
    assert recs[0].texto.startswith("Brecha recurrente (también en 1 de 1")
    assert "Avisar en 72 h; Informar a clientes" in recs[1].texto


def test_sin_brechas_recomienda_mantener():
    [r] = recomendar([])
    assert r.prioridad == Severidad.BAJA and "No se detectaron brechas" in r.texto
