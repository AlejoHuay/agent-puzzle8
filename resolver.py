"""Solucionador por consola, independiente del juego y los experimentos."""
import argparse
from dataclasses import asdict
import json
from time import perf_counter
import psutil
from puzzle.busqueda import AgenteBuscador, Limites
from puzzle.heuristicas import Heuristicas
from puzzle.problema import Puzzle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("estado", help='Fichas por filas separadas por comas: "1,2,3,4,5,6,7,0,8"')
    parser.add_argument("--n", type=int, default=3)
    parser.add_argument("--algoritmo", choices=["astar", "codicioso"], default="astar")
    parser.add_argument("--heuristica", choices=[f"H{i}" for i in range(1, 7)], default="H3")
    parser.add_argument("--peso", type=float, default=.5)
    parser.add_argument("--segundos", type=float, default=30)
    parser.add_argument("--memoria-mb", type=float, default=512)
    args = parser.parse_args()
    try:
        p = Puzzle(args.n)
        s = tuple(int(v) for v in args.estado.split(","))
        p.validar(s)
        hs, t = Heuristicas(p), perf_counter()
        proc = psutil.Process()
        preparacion = hs.preparar(args.heuristica, lambda: perf_counter()-t > args.segundos or
                                 proc.memory_info().rss/2**20 > args.memoria_mb)
        r = AgenteBuscador(p).resolver(s, args.algoritmo, hs.obtener(args.heuristica, args.peso),
                                      Limites(args.segundos, args.memoria_mb))
        print(json.dumps({"preparacion": preparacion, **asdict(r)}, ensure_ascii=False, indent=2))
    except (ValueError, InterruptedError) as error:
        parser.exit(2, str(error)+"\n")


if __name__ == "__main__":
    main()
