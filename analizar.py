"""Análisis de lotes formales terminados. No ejecuta búsquedas ni inventa casos."""
import argparse
from collections import defaultdict
import csv
import hashlib
from itertools import combinations
import json
import os
from pathlib import Path
import warnings
import numpy as np
import scipy
from scipy import stats
from scipy.optimize import curve_fit, OptimizeWarning
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent/".cache"/"matplotlib"))
import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt

METRICAS = ("profundidad", "expandidos", "generados", "tiempo_cpu_ms", "tiempo_pared_ms",
            "memoria_max_nodos", "rss_max_muestreado_mb")


def resumen(valores, semilla=20260913, remuestreos=5000):
    x = np.asarray(valores, dtype=float)
    if len(x) == 0:
        return {"n": 0}
    if not np.all(np.isfinite(x)):
        raise ValueError("Hay valores no finitos")
    r = {"n": len(x), "media": float(np.mean(x)), "mediana": float(np.median(x)),
         "desviacion": float(np.std(x, ddof=1)) if len(x) > 1 else None,
         "minimo": float(min(x)), "maximo": float(max(x)),
         "p25": float(np.percentile(x, 25)), "p75": float(np.percentile(x, 75)),
         "ic95_inferior": None, "ic95_superior": None}
    if len(x) > 1:
        if np.all(x == x[0]):
            inferior = superior = float(x[0])
        else:
            ic = stats.bootstrap((x,), np.mean, method="percentile", n_resamples=remuestreos,
                                 batch=128, confidence_level=.95, rng=np.random.default_rng(semilla))
            inferior, superior = map(float, ic.confidence_interval)
        r.update(ic95_inferior=inferior, ic95_superior=superior)
    return r


def resumen_exito(exitos):
    r = resumen(exitos)
    if len(exitos):
        ic = stats.binomtest(int(sum(exitos)), len(exitos)).proportion_ci(confidence_level=.95, method="wilson")
        r.update(ic95_inferior=float(ic.low), ic95_superior=float(ic.high))
    return r


def contrastar(matriz, nombres, alpha=.05):
    """Filas = bloques completos; columnas = tratamientos; todos los datos pareados."""
    x = np.asarray(matriz, dtype=float)
    if x.ndim != 2 or x.shape[1] != len(nombres) or not np.all(np.isfinite(x)):
        raise ValueError("Matriz de bloques inválida")
    b, k = x.shape
    salida = {"bloques": b, "tratamientos": nombres, "alpha": alpha, "posthoc": []}
    # Umbral prudente para la aproximación chi-cuadrado de Friedman.
    if b <= 10 or k <= 6:
        return {**salida, "estado": "muestra_insuficiente_para_aproximacion"}
    if np.all(x == x[:, :1]):
        return {**salida, "estado": "todos_los_tratamientos_empatados", "estadistico": 0., "p": 1.}
    f = stats.friedmanchisquare(*x.T)
    salida.update(estado="calculado", estadistico=float(f.statistic), p=float(f.pvalue),
                  rangos_medios=dict(zip(nombres, map(float, stats.rankdata(x, axis=1).mean(axis=0)))))
    if f.pvalue < alpha:
        pares = list(combinations(range(k), 2))
        for i, j in pares:
            d = x[:, i]-x[:, j]
            if np.all(d == 0):
                estadistico, p = 0., 1.
            else:
                w = stats.wilcoxon(d, zero_method="pratt", alternative="two-sided", method="auto")
                estadistico, p = float(w.statistic), float(w.pvalue)
            salida["posthoc"].append({"a": nombres[i], "b": nombres[j], "estadistico": estadistico,
                                      "p": p, "p_bonferroni": min(1., p*len(pares)),
                                      "significativo": bool(p*len(pares) < alpha),
                                      "mediana_diferencia_a_menos_b": float(np.median(d))})
    return salida


def ajustar_crecimiento(tamanos, valores):
    x, y = np.asarray(tamanos, dtype=float), np.asarray(valores, dtype=float)
    if len(x) != len(y) or not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError("Datos de ajuste inválidos")
    if len(set(x)) < 4 or np.any(y <= 0) or np.any(x <= 0) or np.ptp(y) == 0:
        return {"estado": "datos_insuficientes", "puntos": len(x)}
    modelos = {"exponencial": lambda n, a, b: a*b**n,
               "potencial": lambda n, a, c: a*n**c}
    salida = {"estado": "calculado", "puntos": len(x), "modelos": {}}
    for nombre, fun in modelos.items():
        z = x if nombre == "exponencial" else np.log(x)
        pendiente, intercepto = np.polyfit(z, np.log(y), 1)
        inicial = [np.exp(intercepto), np.exp(pendiente) if nombre == "exponencial" else pendiente]
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", OptimizeWarning)
                par, cov = curve_fit(fun, x, y, p0=inicial, maxfev=20000)
            pred = fun(x, *par)
            if not np.all(np.isfinite(pred)) or not np.all(np.isfinite(cov)):
                raise ValueError("Ajuste no finito")
            r2 = 1-float(np.sum((y-pred)**2)/np.sum((y-y.mean())**2))
            salida["modelos"][nombre] = {"parametros": list(map(float, par)), "r2": r2,
                                         "predicciones": list(map(float, pred))}
        except (RuntimeError, ValueError, OptimizeWarning, FloatingPointError) as error:
            salida["modelos"][nombre] = {"error": str(error)}
    return salida


def cargar(carpeta):
    carpeta = Path(carpeta)
    meta = json.loads((carpeta/"metadatos.json").read_text(encoding="utf-8"))
    if not meta["completo"] or meta["tipo"] != "experimento":
        raise ValueError("Solo se analizan lotes formales completos; se rechazan pruebas e incompletos")
    lote = json.loads((carpeta/"instancias.json").read_text(encoding="utf-8"))
    ids = {int(s["id"]) for s in lote["instancias"]}
    grupos = defaultdict(dict)
    with (carpeta/"resultados.csv").open(encoding="utf-8", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            peso = float(fila["peso"]) if fila["peso"] else None
            clave = (fila["algoritmo"], fila["heuristica"], peso)
            i = int(fila["instancia"])
            if i in grupos[clave] or i not in ids or int(fila["n"]) != lote["n"]:
                raise ValueError("Filas duplicadas o identificadores/tamaños incorrectos")
            for m in METRICAS:
                fila[m] = None if fila[m] == "" else float(fila[m])
                if fila[m] is None and m != "profundidad":
                    raise ValueError("Falta una métrica obligatoria")
                if fila[m] is not None and (fila[m] < 0 or not np.isfinite(fila[m])):
                    raise ValueError("Métrica negativa o no finita")
            if (fila["estado"] == "resuelto") != (fila["profundidad"] is not None):
                raise ValueError("Profundidad incompatible con el estado de terminación")
            grupos[clave][i] = fila
    esperadas = {(a, h, w) for a, h, w in meta["orden_configuraciones"]}
    if set(grupos) != esperadas or any(set(g) != ids for g in grupos.values()):
        raise ValueError("El CSV no contiene todos los tratamientos y bloques declarados")
    return meta, lote, grupos


def etiqueta(clave):
    return clave[1] + (f" w={clave[2]:g}" if clave[2] is not None else "")


def comparacion(carpeta, salida):
    meta, lote, grupos = cargar(carpeta)
    if meta["argumentos"]["experimento"] != 1 or lote["n"] != 3 or len(lote["instancias"]) != 1000:
        raise ValueError("La comparación requiere el experimento 1 completo")
    resultados = {"tipo": "analisis_experimento1", "fuente": str(carpeta), "contrastes": {},
                  "seleccion_astar": None, "comparacion_algoritmos": [], "notas": [
                      "Friedman/post-hoc usan únicamente bloques comunes resueltos por todas las heurísticas.",
                      "Wilcoxon contrasta simetría de diferencias alrededor de cero; no implica relevancia práctica.",
                      "RSS es muestreado; profundidad ausente no se imputa."]}
    descriptivas = []
    for clave in sorted(grupos, key=str):
        filas = list(grupos[clave].values())
        for ambito in ("todos_intentos", "resueltos"):
            muestra = filas if ambito == "todos_intentos" else [r for r in filas if r["estado"] == "resuelto"]
            for m in METRICAS:
                if m == "profundidad" and ambito == "todos_intentos":
                    continue
                datos = [r[m] for r in muestra if r[m] is not None]
                descriptivas.append({"algoritmo": clave[0], "heuristica": etiqueta(clave), "ambito": ambito,
                                     "metrica": m, **resumen(datos)})
        descriptivas.append({"algoritmo": clave[0], "heuristica": etiqueta(clave), "ambito": "todos_intentos",
                             "metrica": "exito", **resumen_exito([float(r["estado"] == "resuelto") for r in filas])})
    for algoritmo in ("astar", "codicioso"):
        claves = sorted([c for c in grupos if c[0] == algoritmo], key=str)
        comunes = sorted(set.intersection(*[{i for i, r in grupos[c].items() if r["estado"] == "resuelto"} for c in claves]))
        nombres = [etiqueta(c) for c in claves]
        resultados["contrastes"][algoritmo] = {}
        for m in METRICAS:
            matriz = np.array([[grupos[c][i][m] for c in claves] for i in comunes]).reshape(len(comunes), len(claves))
            resultados["contrastes"][algoritmo][m] = contrastar(matriz, nombres)
            if comunes:
                figura, ejes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
                ejes[0].boxplot(matriz, tick_labels=nombres)
                ejes[0].set_title("Distribución en bloques comunes resueltos")
                estadisticas = [resumen(matriz[:, i]) for i in range(len(claves))]
                medias = [r["media"] for r in estadisticas]
                ejes[1].bar(nombres, medias, color="#268d87")
                for i, r in enumerate(estadisticas):
                    if r["ic95_inferior"] is not None:
                        ejes[1].vlines(i, r["ic95_inferior"], r["ic95_superior"], color="black", linewidth=2)
                ejes[1].set_title("Media e intervalo bootstrap del 95 %")
                for eje in ejes:
                    eje.tick_params(axis="x", labelrotation=65)
                    eje.set_ylabel(m)
                    eje.grid(axis="y", alpha=.2)
                    if m not in ("profundidad", "rss_max_muestreado_mb"):
                        eje.set_yscale("symlog", linthresh=1)
                        eje.set_ylabel(m + " (escala symlog)")
                figura.suptitle(f"{algoritmo} · {m} · {len(comunes)} bloques")
                figura.savefig(salida/f"{algoritmo}_{m}.png", dpi=160)
                plt.close(figura)
        if algoritmo == "astar" and comunes:
            ranking = sorted(claves, key=lambda c: (
                -sum(r["estado"] == "resuelto" for r in grupos[c].values()),
                *[np.median([grupos[c][i][m] for i in comunes]) for m in
                  ("expandidos", "tiempo_cpu_ms", "memoria_max_nodos")]))
            resultados["seleccion_astar"] = {"algoritmo": "astar", "heuristica": ranking[0][1],
                                             "peso": ranking[0][2], "bloques_comunes": len(comunes),
                                             "criterio": "exito_desc, mediana_expandidos, mediana_cpu, mediana_memoria",
                                             "orden": [etiqueta(c) for c in ranking]}
    for c in [k for k in grupos if k[0] == "astar"]:
        otro = ("codicioso", c[1], c[2])
        ids = [i for i in grupos[c] if grupos[c][i]["estado"] == grupos[otro][i]["estado"] == "resuelto"]
        for m in METRICAS:
            a, b = [grupos[c][i][m] for i in ids], [grupos[otro][i][m] for i in ids]
            resultados["comparacion_algoritmos"].append({"heuristica": etiqueta(c), "metrica": m,
                "bloques": len(ids), "mediana_astar": float(np.median(a)) if ids else None,
                "mediana_codicioso": float(np.median(b)) if ids else None,
                "mediana_diferencia_codicioso_menos_astar": float(np.median(np.array(b)-a)) if ids else None})
    campos = ["algoritmo", "heuristica", "ambito", "metrica", "n", "media", "mediana", "desviacion",
              "minimo", "maximo", "p25", "p75", "ic95_inferior", "ic95_superior"]
    with (salida/"descriptivas.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(descriptivas)
    return resultados


def escalabilidad(carpetas, salida):
    datos, protocolo, heuristica = [], None, None
    for carpeta in carpetas:
        meta, lote, grupos = cargar(carpeta)
        if meta["argumentos"]["experimento"] != 2 or len(grupos) != 1:
            raise ValueError("Se requieren lotes del experimento 2")
        clave, filas = next(iter(grupos.items()))
        args = meta["argumentos"]
        actual = (lote["metodo"], lote["pasos_mezcla"], args["segundos"], args["memoria_mb"],
                  args["nodos"], args["max_estados_patron"], args["segundos_preparacion"])
        if protocolo is not None and (actual != protocolo or clave != heuristica):
            raise ValueError("No mezcle heurísticas, límites o métodos de generación distintos")
        protocolo, heuristica = actual, clave
        resueltos = [r for r in filas.values() if r["estado"] == "resuelto"]
        datos.append({"n": lote["n"], "intentos": len(filas), "resueltos": len(resueltos),
                      "tasa_exito": len(resueltos)/len(filas),
                      "metricas_resueltos": {m: resumen([r[m] for r in resueltos]) for m in METRICAS},
                      "consumo_intentos": {m: resumen([r[m] for r in filas.values()]) for m in METRICAS if m != "profundidad"},
                      "fuente": str(carpeta)})
    datos.sort(key=lambda x: x["n"])
    if len({d["n"] for d in datos}) != len(datos):
        raise ValueError("Hay tamaños repetidos")
    modelos = {}
    for m in ("expandidos", "tiempo_cpu_ms", "tiempo_pared_ms"):
        # No mezclar observaciones truncadas ni selección solo de casos fáciles.
        elegibles = [d for d in datos if d["resueltos"] == d["intentos"]]
        x = [d["n"] for d in elegibles]
        y = [d["metricas_resueltos"][m]["mediana"] for d in elegibles]
        modelos[m] = ajustar_crecimiento(x, y)
        figura, ejes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
        ejes[0].plot([d["n"] for d in datos], [100*d["tasa_exito"] for d in datos], "o-")
        ejes[0].axhline(50, color="gray", linestyle="--")
        ejes[0].set(xlabel="N", ylabel="Éxito (%)", ylim=(0, 105))
        ejes[1].plot(x, y, "o", label="Medianas: tamaños sin censura")
        for nombre, modelo in modelos[m].get("modelos", {}).items():
            if "predicciones" in modelo:
                ejes[1].plot(x, modelo["predicciones"], label=f"{nombre}, R²={modelo['r2']:.3f}")
        ejes[1].set(xlabel="N", ylabel=m)
        ejes[1].legend()
        figura.savefig(salida/f"escalabilidad_{m}.png", dpi=160)
        plt.close(figura)
    factibles = [d["n"] for d in datos if d["tasa_exito"] >= .5]
    with (salida/"escalabilidad.csv").open("w", encoding="utf-8", newline="") as f:
        campos = ["n", "intentos", "resueltos", "tasa_exito", "metrica", "ambito", "muestra",
                  "media", "mediana", "desviacion", "minimo", "maximo", "p25", "p75",
                  "ic95_inferior", "ic95_superior"]
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for d in datos:
            for ambito in ("metricas_resueltos", "consumo_intentos"):
                for m, resumen_m in d[ambito].items():
                    detalles = dict(resumen_m)
                    detalles["muestra"] = detalles.pop("n")
                    writer.writerow({"n": d["n"], "intentos": d["intentos"], "resueltos": d["resueltos"],
                                     "tasa_exito": d["tasa_exito"], "metrica": m, "ambito": ambito, **detalles})
    return {"tipo": "analisis_escalabilidad", "heuristica": heuristica, "protocolo": protocolo,
            "tamanos": datos, "N_max_observado": max(factibles) if factibles else None, "modelos": modelos,
            "nota": "Límite observado del protocolo. Ajustes solo con >=4 tamaños totalmente resueltos; no se imputan tiempos censurados."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("modo", choices=["comparacion", "escalabilidad"])
    parser.add_argument("carpetas", nargs="+")
    parser.add_argument("--salida", required=True)
    args = parser.parse_args()
    destino = Path(args.salida)
    try:
        if destino.exists():
            raise ValueError("La salida ya existe; use una carpeta nueva")
        for carpeta in args.carpetas:
            cargar(carpeta)  # Rechazo previo de datos incompletos o de validación.
        if args.modo == "comparacion" and len(args.carpetas) != 1:
            raise ValueError("Comparación admite un solo lote")
        destino.mkdir(parents=True)
        r = comparacion(args.carpetas[0], destino) if args.modo == "comparacion" else escalabilidad(args.carpetas, destino)
        r["versiones"] = {"numpy": np.__version__, "scipy": scipy.__version__, "matplotlib": matplotlib.__version__}
        r["sha256_codigo_analisis"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        r["sha256_csv"] = {c: hashlib.sha256(Path(c, "resultados.csv").read_bytes()).hexdigest() for c in args.carpetas}
        (destino/"analisis.json").write_text(json.dumps(r, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        print(f"Análisis guardado en {destino}")
    except (ValueError, KeyError, FileNotFoundError) as error:
        parser.exit(2, str(error)+"\n")


if __name__ == "__main__":
    main()
