"""Validación exhaustiva del Puzzle-8; no produce resultados experimentales."""
import argparse
from collections import deque
import json
from pathlib import Path
from puzzle.problema import Puzzle
from puzzle.heuristicas import Heuristicas


def validar(salida):
    p, hs = Puzzle(), Heuristicas(Puzzle())
    hs.preparar("H4")
    hs.preparar("H5")
    nombres = ["H1", "H2", "H3", "H4", "H5", "H6_0.25", "H6_0.5", "H6_0.75"]
    funciones = [hs.obtener(h) for h in nombres[:5]] + [hs.obtener("H6", w) for w in (.25, .5, .75)]
    distancia, cola = {p.meta: 0}, deque([p.meta])
    while cola:
        s = cola.popleft()
        for hijo in p.generar_hijos(s):
            if hijo not in distancia:
                distancia[hijo] = distancia[s]+1
                cola.append(hijo)
    print(f"Oráculo BFS: {len(distancia)} estados", flush=True)
    valores = {}
    mejoras = 0
    ejemplo = None
    for s, d in distancia.items():
        v = tuple(f(s) for f in funciones)
        assert all(0 <= h <= d for h in v), ("admisibilidad", s, d, v)
        assert v[3] >= v[2] >= v[1] >= v[0], ("dominancia", s)
        if v[3] > v[2]:
            mejoras += 1
            ejemplo = ejemplo or {"estado": s, "distancia_exacta": d, "H3": v[2], "H4": v[3]}
        valores[s] = v
    aristas = 0
    for s, v in valores.items():
        for hijo in p.generar_hijos(s):
            aristas += 1
            assert all(a <= 1+b for a, b in zip(v, valores[hijo])), ("consistencia", s, hijo, v, valores[hijo])
    assert len(distancia) == 181440
    assert max(distancia.values()) == 31
    assert mejoras > 0, "La corrección de esquinas debe aportar una mejora real"
    informe = {"tipo": "validacion_exhaustiva_no_experimento", "estados": len(distancia),
               "transiciones_dirigidas": aristas, "profundidad_maxima_oraculo": max(distancia.values()),
               "heuristicas": nombres, "admisibilidad": "verificada", "consistencia": "verificada",
               "dominancia_H4_H3_H2_H1": "verificada", "estados_H4_mayor_H3": mejoras,
               "ejemplo_mejora_esquinas": ejemplo}
    Path(salida).parent.mkdir(parents=True, exist_ok=True)
    Path(salida).write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(informe, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", default="verificacion/heuristicas.json")
    validar(parser.parse_args().salida)
