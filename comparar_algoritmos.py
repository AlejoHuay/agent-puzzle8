"""Fase 7: comparación pareada de algoritmos con la heurística ya seleccionada.

Reutiliza las mediciones de Puzzle-8; no ejecuta búsquedas ni cambia su selección.
"""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy import stats
from analizar import cargar, resumen, resumen_exito, METRICAS, plt
from documentar_resultados import tabla


def signos(diferencias, familia=7):
    """Binomial bilateral sobre diferencias no nulas; los empates se informan."""
    d = np.asarray(diferencias)
    menores, iguales, mayores = (int(np.sum(d < 0)), int(np.sum(d == 0)), int(np.sum(d > 0)))
    n = menores + mayores
    p = float(stats.binomtest(menores, n, .5, alternative="two-sided").pvalue) if n else 1.
    return {"codicioso_menor": menores, "empates": iguales, "codicioso_mayor": mayores,
            "no_empatados": n, "p": p, "p_bonferroni": min(1., familia*p),
            "significativo": bool(familia*p < .05)}


def main():
    fuente = Path("resultados/experimento1")
    salida = Path("resultados/fase7")
    _, lote, grupos = cargar(fuente)
    previo = json.loads(Path("resultados/analisis1/analisis.json").read_text(encoding="utf-8"))
    seleccion = previo["seleccion_astar"]
    h, w = seleccion["heuristica"], seleccion["peso"]
    a, c = grupos[("astar", h, w)], grupos[("codicioso", h, w)]
    ids = sorted(a)
    assert lote["n"] == 3 and len(ids) == 1000 and set(ids) == set(c)
    assert all(a[i]["estado"] == c[i]["estado"] == "resuelto" for i in ids)
    # Reutilizar también los IC originales: un bootstrap finito con igual
    # semilla cambia ligeramente si se reordena antes la misma muestra.
    with Path("resultados/analisis1/descriptivas.csv").open(encoding="utf-8", newline="") as archivo:
        anteriores = {(r["algoritmo"], r["metrica"]): r for r in csv.DictReader(archivo)
                      if r["heuristica"] == h and r["ambito"] == "resueltos"}
    def descriptiva(algoritmo, metrica):
        r = anteriores[algoritmo, metrica]
        return {"n": int(r["n"]), **{k: float(r[k]) for k in
                ("media", "mediana", "desviacion", "minimo", "maximo", "p25", "p75", "ic95_inferior", "ic95_superior")}}
    salida.mkdir(parents=True, exist_ok=True)
    datos, descriptivas, comparaciones = {}, [], []
    resumen_tabla, pares_tabla, completas = [], [], []
    for m in METRICAS:
        x, y = np.array([a[i][m] for i in ids]), np.array([c[i][m] for i in ids])
        ra, rc, rd = descriptiva("astar", m), descriptiva("codicioso", m), resumen(y-x)
        prueba = signos(y-x, len(METRICAS))
        datos[m] = {"astar": ra, "codicioso": rc, "diferencia_codicioso_menos_astar": rd, "signos": prueba}
        resumen_tabla.append([m, ra["mediana"], rc["mediana"], ra["media"], rc["media"]])
        pares_tabla.append([m, prueba["codicioso_menor"], prueba["empates"], prueba["codicioso_mayor"],
                            rd["mediana"], prueba["p_bonferroni"], "sí" if prueba["significativo"] else "no"])
        for algoritmo, r in (("astar", ra), ("codicioso", rc)):
            descriptivas.append({"algoritmo": algoritmo, "metrica": m, **r})
            completas.append([m, algoritmo, *[r[k] for k in ("media", "desviacion", "minimo", "p25", "mediana", "p75", "maximo", "ic95_inferior", "ic95_superior")]])
        comparaciones.append({"metrica": m, **prueba, **{f"diferencia_{k}": v for k, v in rd.items()}})
    pa, pc = np.array([a[i]["profundidad"] for i in ids]), np.array([c[i]["profundidad"] for i in ids])
    assert np.all(pc >= pa) and np.all(pa > 0)
    calidad = {"exito_astar": resumen_exito([1]*len(ids)), "exito_codicioso": resumen_exito([1]*len(ids)),
               "optimalidad_codicioso": resumen_exito((pc == pa).astype(int)),
               "optimas_codicioso": int(np.sum(pc == pa)), "exceso_movimientos": resumen(pc-pa),
               "exceso_relativo_porcentaje": resumen(100*(pc/pa-1))}
    for nombre, filas in (("descriptivas.csv", descriptivas), ("comparaciones.csv", comparaciones)):
        with (salida/nombre).open("w", encoding="utf-8", newline="") as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=list(filas[0]))
            escritor.writeheader()
            escritor.writerows(filas)
    registro = {"fase": 7, "instancias": len(ids), "heuristica": h, "peso": w, "metricas": datos,
                "calidad": calidad, "seleccion_previa": seleccion,
                "nota": "Análisis exploratorio posterior sobre la muestra usada para seleccionar H; signos bilaterales, siete comparaciones Bonferroni. Sin nuevas búsquedas.",
                "versiones": previo["versiones"],
                "sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                           (fuente/"resultados.csv", fuente/"instancias.json", Path(__file__), Path("analizar.py"), Path("documentar_resultados.py"), Path("resultados/analisis1/analisis.json"), Path("resultados/analisis1/descriptivas.csv"))}}
    (salida/"analisis.json").write_text(json.dumps(registro, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    texto = ["### Resumen de A* y Codicioso con la heurística seleccionada\n",
             tabla(["Métrica", "Mediana A*", "Mediana Codicioso", "Media A*", "Media Codicioso"], resumen_tabla),
             "\n### Comparación por instancia: Codicioso menos A*\n",
             tabla(["Métrica", "Cod. menor", "Igual", "Cod. mayor", "Diferencia mediana", "p Bonferroni", "Significativo"], pares_tabla),
             "\n### Descriptivas completas de las dos configuraciones\n",
             tabla(["Métrica", "Algoritmo", "Media", "DE", "Mín.", "P25", "Mediana", "P75", "Máx.", "IC95 inf.", "IC95 sup."], completas)]
    (salida/"tablas.md").write_text("\n\n".join(texto), encoding="utf-8")
    figura, ejes = plt.subplots(1, 4, figsize=(14, 4), layout="constrained")
    for eje, m, titulo in zip(ejes, ("profundidad", "expandidos", "tiempo_pared_ms", "memoria_max_nodos"),
                              ("Movimientos", "Nodos expandidos", "Pared (ms)", "Memoria (nodos)")):
        eje.boxplot([[a[i][m] for i in ids], [c[i][m] for i in ids]], tick_labels=["A*", "Codicioso"])
        eje.set_title(titulo)
        eje.grid(axis="y", alpha=.2)
        if m != "profundidad":
            eje.set_yscale("log")
            eje.set_ylabel("Escala logarítmica")
    figura.suptitle(f"Puzzle-8 · {h} · {len(ids)} instancias compartidas")
    figura.savefig(salida/"comparacion_h5.png", dpi=160)
    plt.close(figura)
    print(json.dumps({"calidad": calidad, "comparaciones": pares_tabla}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
