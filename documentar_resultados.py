"""Tablas y figuras auxiliares del informe, derivadas solo de los lotes reales."""
import argparse
import csv
import hashlib
from collections import deque
import json
from pathlib import Path, PureWindowsPath
import numpy as np
from analizar import cargar, etiqueta, resumen_exito, plt, METRICAS
from puzzle.problema import Puzzle

RAIZ = Path("resultados")


def tabla(encabezados, filas):
    def texto(v):
        if v is None:
            return "—"
        if isinstance(v, (float, np.floating)):
            return f"{v:.4g}"
        return str(v)
    return "\n".join(["| " + " | ".join(encabezados) + " |",
                      "|" + "---|"*len(encabezados)] +
                     ["| " + " | ".join(texto(v) for v in fila) + " |" for fila in filas])


def principal():
    _, lote, grupos = cargar(RAIZ/"experimento1")
    analisis = json.loads((RAIZ/"analisis1/analisis.json").read_text(encoding="utf-8"))
    with (RAIZ/"analisis1/descriptivas.csv").open(encoding="utf-8", newline="") as f:
        descriptivas = list(csv.DictReader(f))
    claves = sorted(grupos, key=str)
    d = {(r["algoritmo"], r["heuristica"], r["metrica"], r["ambito"]): r for r in descriptivas}

    def med(c, m):
        return float(d[c[0], etiqueta(c), m, "resueltos"]["mediana"])

    filas = []
    for c in claves:
        r = grupos[c]
        filas.append([c[0], etiqueta(c), sum(x["estado"] == "resuelto" for x in r.values()),
                      *[med(c, m) for m in ("profundidad", "expandidos", "generados", "tiempo_cpu_ms", "tiempo_pared_ms", "memoria_max_nodos")]])
    secciones = ["## Resultados del experimento principal\n",
                 tabla(["Algoritmo", "Heurística", "Éxitos/1000", "Pasos med.", "Expandidos med.", "Generados med.",
                        "CPU med. ms", "Pared med. ms", "Memoria med. nodos"], filas)]
    calidad, dificultad = [], []
    for c in [c for c in claves if c[0] == "codicioso"]:
        referencia = grupos[("astar", c[1], c[2])]
        pares = [(r, referencia[i]) for i, r in grupos[c].items() if r["estado"] == referencia[i]["estado"] == "resuelto"]
        exceso = [r["profundidad"]-a["profundidad"] for r, a in pares]
        razones = [r["profundidad"]/a["profundidad"] for r, a in pares if a["profundidad"] > 0]
        assert all(v >= 0 for v in exceso)
        calidad.append([etiqueta(c), len(pares), sum(v == 0 for v in exceso),
                        100*np.mean(np.array(exceso) == 0), float(np.median(exceso)), float(np.mean(exceso)),
                        float(max(exceso)), float(np.median(razones)), float(max(razones))])
    secciones += ["\n### Calidad de las soluciones de Codicioso\n",
                   "Comparación pareada con A* en la misma instancia y heurística. La razón excluye profundidad óptima cero.\n",
                   tabla(["Heurística", "Pares", "Óptimas", "% óptimas", "Exceso med.", "Exceso medio", "Exceso máx.",
                          "Razón mediana", "Razón máxima"], calidad)]

    base = grupos[("astar", "H5", None)]
    problema = Puzzle()
    distancias, cola = {problema.meta: 0}, deque([problema.meta])
    while cola:
        estado = cola.popleft()
        for hijo in problema.generar_hijos(estado):
            if hijo not in distancias:
                distancias[hijo] = distancias[estado]+1
                cola.append(hijo)
    estados = {int(x["id"]): tuple(x["estado"]) for x in lote["instancias"]}
    assert len(set(estados.values())) == 1000
    for i, fila in base.items():
        assert fila["profundidad"] == distancias[estados[i]], "Profundidad distinta del oráculo BFS"
        assert all(grupos[c][i]["profundidad"] == fila["profundidad"] for c in claves if c[0] == "astar"), "A* discrepó en profundidad"
    intervalos = [(0, 15), (16, 20), (21, 25), (26, 31)]
    curvas = {}
    for c in claves:
        curvas[c] = []
        for inferior, superior in intervalos:
            ids = [i for i, r in base.items() if inferior <= r["profundidad"] <= superior and grupos[c][i]["estado"] == "resuelto"]
            if not ids:
                continue
            valores = [grupos[c][i]["expandidos"] for i in ids]
            tiempo = [grupos[c][i]["tiempo_pared_ms"] for i in ids]
            profundidad = [grupos[c][i]["profundidad"] for i in ids]
            dificultad.append([c[0], etiqueta(c), f"{inferior}–{superior}", len(ids),
                               float(np.median(valores)), float(np.median(tiempo)), float(np.median(profundidad))])
            curvas[c].append(float(np.median(valores)))
    secciones += ["\n### Dificultad y expansiones\n",
                  "Los estratos se definen por la profundidad óptima obtenida por A*. Todas sus configuraciones coincidieron.\n",
                  tabla(["Algoritmo", "Heurística", "Profundidad óptima", "Casos", "Expandidos med.", "Pared med. ms", "Pasos med."], dificultad)]
    figura, ejes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    for eje, algoritmo in zip(ejes, ("astar", "codicioso")):
        for c in claves:
            if c[0] == algoritmo and len(curvas[c]) == len(intervalos):
                eje.plot([f"{a}–{b}" for a, b in intervalos], curvas[c], "o-", label=etiqueta(c))
        eje.set(xlabel="Profundidad óptima", ylabel="Mediana de expansiones", title=algoritmo, yscale="log")
        eje.grid(alpha=.2)
        eje.legend(fontsize=8)
    figura.savefig(RAIZ/"analisis1/dificultad.png", dpi=170)
    plt.close(figura)

    encabezados = ["Algoritmo", "Métrica", "Bloques", "χ² Friedman", "p", "Pares significativos/28"]
    filas = []
    for a, metricas in analisis["contrastes"].items():
        for m, r in metricas.items():
            p = "<1e-300 (subdesbordamiento)" if r.get("p") == 0 else r.get("p")
            filas.append([a, m, r["bloques"], r.get("estadistico"), p,
                          sum(par["significativo"] for par in r["posthoc"]) if r["posthoc"] else "no procede"])
    secciones += ["\n### Contrastes globales y post-hoc\n", tabla(encabezados, filas),
                  "\nLos p registrados como cero por precisión numérica no son probabilidades exactamente nulas. "
                  "Bonferroni corrige 28 pares por familia; los intervalos del 95 % son individuales, no simultáneos.\n"]
    for a in ("astar", "codicioso"):
        r = analisis["contrastes"][a]["expandidos"]
        secciones += [f"\n#### {a}: post-hoc de expansiones\n",
                      tabla(["Par A", "Par B", "p ajustado", "Significativo", "Mediana A−B"],
                            [[x["a"], x["b"], x["p_bonferroni"], "sí" if x["significativo"] else "no",
                              x["mediana_diferencia_a_menos_b"]] for x in r["posthoc"]])]

    for metrica in ("expandidos", "generados", "tiempo_cpu_ms", "tiempo_pared_ms", "memoria_max_nodos", "rss_max_muestreado_mb", "profundidad"):
        filas = []
        for c in claves:
            r = d[c[0], etiqueta(c), metrica, "resueltos"]
            filas.append([c[0], etiqueta(c), *[float(r[k]) for k in
                          ("media", "desviacion", "minimo", "p25", "mediana", "p75", "maximo", "ic95_inferior", "ic95_superior")]])
        secciones += [f"\n### Descriptivas completas: {metrica}\n",
                      tabla(["Algoritmo", "Heurística", "Media", "DE", "Mín.", "P25", "Mediana", "P75", "Máx.", "IC95 inf.", "IC95 sup."], filas)]
    ceros = {f"{c[0]} {etiqueta(c)}": sum(r["tiempo_cpu_ms"] == 0 for r in grupos[c].values()) for c in claves}
    anomalas = []
    for c in claves:
        r = grupos[c]
        for i, fila in r.items():
            if fila["tiempo_pared_ms"] > 10000 and fila["tiempo_pared_ms"] > 20*max(fila["tiempo_cpu_ms"], 1):
                otros = [x["tiempo_pared_ms"] for j, x in r.items() if j != i]
                anomalas.append({"algoritmo": c[0], "heuristica": etiqueta(c), "instancia": i,
                                 "cpu_ms": fila["tiempo_cpu_ms"], "pared_ms": fila["tiempo_pared_ms"],
                                 "media_pared_sin_esta_observacion_ms": float(np.mean(otros)),
                                 "mediana_pared_sin_esta_observacion_ms": float(np.median(otros)),
                                 "nota": "sensibilidad descriptiva; observación conservada en todas las tablas y contrastes oficiales"})
    resumen = {"calidad_codicioso": calidad, "dificultad": dificultad, "tiempos_cpu_cero": ceros,
               "demoras_temporales_extremas": anomalas, "Astar_distancias_verificadas_BFS": 8000,
               "profundidad_optima_min": min(r["profundidad"] for r in base.values()),
               "profundidad_optima_max": max(r["profundidad"] for r in base.values()),
               "profundidad_optima_mediana": float(np.median([r["profundidad"] for r in base.values()])),
               "muestra": len(lote["instancias"]), "Astar_profundidades_coincidentes": True}
    (RAIZ/"analisis1/hallazgos_derivados.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    (RAIZ/"analisis1/tablas_informe.md").write_text("\n\n".join(secciones), encoding="utf-8")


def escalas():
    """Conserva separados los dos muestreos y distingue censura de soluciones."""
    for directorio in ("analisis_escalabilidad", "analisis_cercanos"):
        destino = RAIZ/directorio
        analisis = json.loads((destino/"analisis.json").read_text(encoding="utf-8"))
        filas_exito, preparacion, estados = [], [], []
        intervalos = []
        for d in analisis["tamanos"]:
            meta, _, grupos = cargar(Path(d["fuente"].replace("\\", "/")))
            r = resumen_exito([1]*d["resueltos"]+[0]*(d["intentos"]-d["resueltos"]))
            inferior, superior = 100*r["ic95_inferior"], 100*r["ic95_superior"]
            intervalos.append((inferior, superior))
            filas_exito.append([d["n"], d["intentos"], d["resueltos"], 100*d["tasa_exito"], inferior, superior])
            p = meta["preparacion"][0]
            preparacion.append([d["n"], "+".join(str(len(g)) for g in p["grupos"]), p["entradas"], p["segundos"]])
            conteos = {}
            for fila in next(iter(grupos.values())).values():
                conteos[fila["estado"]] = conteos.get(fila["estado"], 0)+1
            estados.append({"n": d["n"], "terminaciones": conteos, "ic95_exito_porcentaje": [inferior, superior]})
        texto = ["### Éxito y preparación\n",
                 tabla(["N", "Intentos", "Resueltos", "Éxito %", "Wilson95 inf. %", "Wilson95 sup. %"], filas_exito),
                 "\nLa preparación ocurre una vez por lote y queda fuera del tiempo de búsqueda.\n",
                 tabla(["N", "Tamaños de grupos H5", "Entradas PDB", "Preparación s"], preparacion)]
        for ambito, nombre in (("metricas_resueltos", "Soluciones encontradas"), ("consumo_intentos", "Consumo de todos los intentos")):
            texto += [f"\n### {nombre}\n",
                      "Los valores ausentes se muestran como —. El consumo de un intento interrumpido no es el costo de resolverlo.\n"]
            for m in METRICAS:
                if m == "profundidad" and ambito == "consumo_intentos":
                    continue
                filas = []
                for d in analisis["tamanos"]:
                    r = d[ambito][m]
                    filas.append([d["n"], r["n"], *[r.get(k) for k in
                        ("media", "desviacion", "minimo", "p25", "mediana", "p75", "maximo", "ic95_inferior", "ic95_superior")]])
                texto += [f"\n#### {m}\n", tabla(["N", "Casos", "Media", "DE", "Mín.", "P25", "Mediana", "P75", "Máx.", "IC95 inf.", "IC95 sup."], filas)]
        modelos = []
        for m, ajuste in analisis["modelos"].items():
            if ajuste["estado"] != "calculado":
                modelos.append([m, "sin ajuste", ajuste["puntos"], None, None, None, ajuste["estado"]])
            for modelo, r in ajuste.get("modelos", {}).items():
                par = r.get("parametros", [None, None])
                modelos.append([m, modelo, ajuste["puntos"], *par, r.get("r2"), r.get("error", "calculado")])
        texto += ["\n### Modelos sobre medianas de tamaños totalmente resueltos\n",
                  "Exponencial: a·b^N; potencial: a·N^c. La segunda constante es b o c, respectivamente.\n",
                  tabla(["Métrica", "Modelo", "Puntos", "a", "b / c", "R²", "Estado"], modelos)]
        (destino/"tablas_informe.md").write_text("\n\n".join(texto), encoding="utf-8")
        (destino/"exito_y_terminacion.json").write_text(json.dumps(estados, ensure_ascii=False, indent=2), encoding="utf-8")
        figura, ejes = plt.subplots(1, 3, figsize=(14, 4), layout="constrained")
        ns = [d["n"] for d in analisis["tamanos"]]
        tasa = [100*d["tasa_exito"] for d in analisis["tamanos"]]
        ejes[0].errorbar(ns, tasa, yerr=[[max(0, t-lo) for t, (lo, hi) in zip(tasa, intervalos)],
                                      [max(0, hi-t) for t, (lo, hi) in zip(tasa, intervalos)]], fmt="o-", capsize=4)
        ejes[0].axhline(50, color="gray", linestyle="--")
        ejes[0].set(ylabel="Éxito (%)", ylim=(-3, 105), title="Proporción e IC Wilson 95 %")
        for eje, m, titulo in zip(ejes[1:], ("expandidos", "tiempo_pared_ms"), ("Expansiones hasta terminar", "Tiempo hasta terminar (ms)")):
            eje.plot(ns, [d["consumo_intentos"][m]["mediana"] for d in analisis["tamanos"]], "o-", label="Todos los intentos")
            eje.set(ylabel=titulo, title="Mediana de consumo, incluye límites", yscale="log")
            eje.legend(fontsize=8)
        for eje in ejes:
            eje.set(xlabel="N", xticks=ns)
            eje.grid(alpha=.2)
        figura.savefig(destino/"exito_y_consumo.png", dpi=170)
        plt.close(figura)


def verificar_lotes(salida=RAIZ/"verificacion_fase4.json"):
    """Comprueba integridad y correspondencia de todos los lotes de la Fase 4."""
    carpetas = [RAIZ/"experimento1"] + [RAIZ/f"{prefijo}_{n}" for prefijo in ("escalabilidad", "cercanos") for n in range(3, 7)]
    comprobados = []
    for carpeta in carpetas:
        meta, lote, grupos = cargar(carpeta)
        for nombre, esperado in meta["fuentes_sha256"].items():
            # Los metadatos originales registran experimentos.py con ruta absoluta
            # de Windows. Verificar la copia actual, no otra carpeta de esa máquina.
            registrada = PureWindowsPath(nombre)
            fuente = Path(registrada.name if registrada.is_absolute() else registrada.as_posix())
            assert hashlib.sha256(fuente.read_bytes()).hexdigest() == esperado, f"Fuente cambiada: {fuente}"
        assert hashlib.sha256((carpeta/"instancias.json").read_bytes()).hexdigest() == meta["instancias_sha256"]
        esperadas = 1000 if carpeta.name == "experimento1" else 100
        assert len(lote["instancias"]) == esperadas
        assert len({tuple(s["estado"]) for s in lote["instancias"]}) == esperadas
        problema = Puzzle(lote["n"])
        assert all(problema.soluble(tuple(s["estado"])) for s in lote["instancias"])
        cantidad = sum(len(g) for g in grupos.values())
        assert cantidad == (16000 if carpeta.name == "experimento1" else 100)
        terminaciones = {}
        for clave, g in grupos.items():
            for r in g.values():
                terminaciones[r["estado"]] = terminaciones.get(r["estado"], 0)+1
                if clave[0] == "astar":
                    assert int(r["reabiertos"]) == 0, "Reapertura inesperada de A* con estas heurísticas consistentes"
                if meta["argumentos"]["experimento"] == 2 and r["estado"] == "resuelto":
                    assert r["tiempo_pared_ms"] <= 1000*meta["argumentos"]["segundos"], "Solución fuera del presupuesto temporal"
                if carpeta.name.startswith("cercanos"):
                    assert r["profundidad"] is None or r["profundidad"] <= 20
        comprobados.append({"carpeta": str(carpeta), "filas": cantidad, "terminaciones": terminaciones,
                            "csv_sha256": hashlib.sha256((carpeta/"resultados.csv").read_bytes()).hexdigest()})
    for nombre in ("analisis1", "analisis_escalabilidad", "analisis_cercanos"):
        a = json.loads((RAIZ/nombre/"analisis.json").read_text(encoding="utf-8"))
        assert a["sha256_codigo_analisis"] == hashlib.sha256(Path("analizar.py").read_bytes()).hexdigest()
        for carpeta, esperado in a["sha256_csv"].items():
            assert hashlib.sha256(Path(carpeta.replace("\\", "/"), "resultados.csv").read_bytes()).hexdigest() == esperado
    hallazgos = json.loads((RAIZ/"analisis1/hallazgos_derivados.json").read_text(encoding="utf-8"))
    assert hallazgos["Astar_distancias_verificadas_BFS"] == 8000
    registro = {"estado": "verificado", "busquedas": sum(c["filas"] for c in comprobados),
                "lotes": comprobados, "fuentes_experimentales_sin_cambios": True,
                "instancias_distintas_y_solubles_por_lote": True, "hashes_analisis_correctos": True,
                "profundidades_Astar_puzzle8_verificadas_BFS": hallazgos["Astar_distancias_verificadas_BFS"],
                "sha256_documentar_resultados": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    Path(salida).write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("modo", nargs="?", choices=("principal", "escalabilidad", "verificar"), default="principal")
    args = parser.parse_args()
    {"principal": principal, "escalabilidad": escalas, "verificar": verificar_lotes}[args.modo]()
