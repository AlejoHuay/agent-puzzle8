"""Preparación y ejecución reproducible. No se ejecuta nada al importar."""
import argparse
import csv
from dataclasses import asdict
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import platform
import random
import sys
from time import perf_counter
import psutil
from puzzle.problema import Puzzle
from puzzle.heuristicas import Heuristicas
from puzzle.busqueda import AgenteBuscador, Limites, Resultado


def guardar_json(path, datos):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def configuraciones():
    return [(a, h, w) for a in ("astar", "codicioso") for h, w in
            [("H1", None), ("H2", None), ("H3", None), ("H4", None), ("H5", None),
             ("H6", .25), ("H6", .5), ("H6", .75)]]


def ejecutar_configuracion(lote, configuracion, opciones, destino, conexion):
    """Un proceso nuevo por tratamiento evita heredar las PDB del anterior."""
    try:
        p = Puzzle(lote["n"])
        algoritmo, nombre, peso = configuracion
        hs = Heuristicas(p, opciones["max_estados_patron"])
        proceso, t = psutil.Process(), perf_counter()
        datos = hs.preparar(nombre, lambda: perf_counter()-t > opciones["segundos_preparacion"] or
                           proceso.memory_info().rss/2**20 > opciones["memoria_mb"])
        conexion.send({"evento": "preparado", "algoritmo": algoritmo, "heuristica": nombre,
                       "peso": peso, **datos})
        h = hs.obtener(nombre, peso)
        limites = Limites(opciones["segundos"], opciones["memoria_mb"], opciones["nodos"])
        orden = list(lote["instancias"])
        random.Random(opciones["semilla_orden"]).shuffle(orden)
        campos = ["experimento", "instancia", "n", "algoritmo", "heuristica", "peso"] + [
            k for k in asdict(Resultado()) if k != "camino"]
        with Path(destino, "resultados.csv").open("a", newline="", encoding="utf-8") as archivo:
            tabla = csv.DictWriter(archivo, fieldnames=campos)
            for x in orden:
                r = AgenteBuscador(p).resolver(tuple(x["estado"]), algoritmo, h, limites)
                fila = asdict(r)
                fila.pop("camino")
                tabla.writerow({"experimento": opciones["experimento"], "instancia": x["id"],
                                "n": p.n, "algoritmo": algoritmo, "heuristica": nombre,
                                "peso": "" if peso is None else peso, **fila})
                archivo.flush()
        conexion.send({"evento": "completo"})
    except Exception as error:
        conexion.send({"evento": "error", "mensaje": f"{type(error).__name__}: {error}"})
    finally:
        conexion.close()


def preparar(args):
    path = Path(args.salida)
    if path.exists():
        raise ValueError("El archivo ya existe; use otro nombre para conservar las instancias")
    p = Puzzle(args.n)
    estados = p.instancias(args.cantidad, args.semilla, args.metodo, args.pasos)
    guardar_json(path, {"n": args.n, "semilla": args.semilla, "metodo": args.metodo,
                        "pasos_mezcla": args.pasos if args.metodo == "mezcla" else None,
                        "instancias": [{"id": i+1, "estado": s} for i, s in enumerate(estados)]})
    print(f"Preparadas {len(estados)} instancias en {path}")


def ejecutar(args):
    origen = Path(args.instancias)
    lote = json.loads(origen.read_text(encoding="utf-8"))
    p = Puzzle(lote["n"])
    ids = [x["id"] for x in lote["instancias"]]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("Identificadores vacíos o repetidos")
    for instancia in lote["instancias"]:
        if not p.soluble(tuple(instancia["estado"])):
            raise ValueError("Todas las instancias experimentales deben ser solubles")
    destino = Path(args.salida)
    if destino.exists():
        raise ValueError("La carpeta de salida ya existe: se evita mezclar o sobrescribir ejecuciones")
    configs = configuraciones() if args.experimento == 1 else [("astar", args.heuristica, args.peso)]
    if args.experimento == 1 and (p.n != 3 or len(ids) != 1000) and not args.validacion:
        raise ValueError("Experimento 1 requiere 1000 instancias de N=3; para pruebas use --validacion")
    if args.experimento == 2 and not args.heuristica:
        raise ValueError("Indique la heurística ganadora con --heuristica")
    if args.experimento == 2 and args.heuristica == "H6" and (args.peso is None or not 0 <= args.peso <= 1):
        raise ValueError("H6 requiere --peso entre 0 y 1")
    random.Random(args.semilla_orden).shuffle(configs)
    limites = Limites(args.segundos, args.memoria_mb, args.nodos)
    if args.segundos_preparacion <= 0 or args.max_estados_patron < 1:
        raise ValueError("Los presupuestos de preparación deben ser positivos")
    destino.mkdir(parents=True)
    fuentes = [Path(__file__)] + sorted(Path("puzzle").glob("*.py"))
    metadata = {"tipo": "validacion" if args.validacion else "experimento",
                "argumentos": {k: v for k, v in vars(args).items() if k != "func"}, "python": sys.version, "plataforma": platform.platform(),
                "cpu": platform.processor(), "cpu_logicos": psutil.cpu_count(),
                "ram_bytes": psutil.virtual_memory().total,
                "instancias_sha256": hashlib.sha256(origen.read_bytes()).hexdigest(),
                "fuentes_sha256": {str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in fuentes},
                "orden_configuraciones": configs, "preparacion": [], "completo": False}
    guardar_json(destino/"metadatos.json", metadata)
    guardar_json(destino/"instancias.json", lote)
    campos = ["experimento", "instancia", "n", "algoritmo", "heuristica", "peso"] + [
        k for k in asdict(Resultado()) if k != "camino"]
    with (destino/"resultados.csv").open("w", newline="", encoding="utf-8") as archivo:
        tabla = csv.DictWriter(archivo, fieldnames=campos)
        tabla.writeheader()
    for algoritmo, nombre, peso in configs:
        receptor, emisor = mp.Pipe(duplex=False)
        trabajador = mp.Process(target=ejecutar_configuracion,
                               args=(lote, (algoritmo, nombre, peso), metadata["argumentos"], str(destino), emisor))
        trabajador.start()
        emisor.close()
        completo = False
        try:
            while True:
                try:
                    disponible = receptor.poll(.2)
                except (EOFError, OSError):
                    break
                if disponible:
                    try:
                        mensaje = receptor.recv()
                    except EOFError:
                        break
                    if mensaje["evento"] == "preparado":
                        metadata["preparacion"].append(mensaje)
                        guardar_json(destino/"metadatos.json", metadata)
                    elif mensaje["evento"] == "completo":
                        completo = True
                        break
                    elif mensaje["evento"] == "error":
                        raise ValueError(mensaje["mensaje"])
                elif not trabajador.is_alive():
                    break
            trabajador.join()
            if not completo or trabajador.exitcode != 0:
                raise ValueError("Trabajador interrumpido: lote incompleto, conserve los datos parciales")
        finally:
            if trabajador.is_alive():
                trabajador.terminate()
                trabajador.join()
            trabajador.close()
            receptor.close()
        print(f"Completado {algoritmo} {nombre} {peso if peso is not None else ''}", flush=True)
    metadata["completo"] = True
    guardar_json(destino/"metadatos.json", metadata)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="comando", required=True)
    gen = sub.add_parser("preparar")
    gen.add_argument("--n", type=int, default=3)
    gen.add_argument("--cantidad", type=int, default=1000)
    gen.add_argument("--semilla", type=int, default=20260911)
    gen.add_argument("--metodo", choices=["permutacion", "mezcla"], default="permutacion")
    gen.add_argument("--pasos", type=int, default=30)
    gen.add_argument("--salida", required=True)
    gen.set_defaults(func=preparar)
    run = sub.add_parser("ejecutar")
    run.add_argument("--instancias", required=True)
    run.add_argument("--salida", required=True)
    run.add_argument("--experimento", type=int, choices=[1, 2], default=1)
    run.add_argument("--heuristica", choices=[f"H{i}" for i in range(1, 7)])
    run.add_argument("--peso", type=float)
    run.add_argument("--segundos", type=float, default=300)
    run.add_argument("--segundos-preparacion", type=float, default=300)
    run.add_argument("--memoria-mb", type=float, default=1024)
    run.add_argument("--nodos", type=int, default=2000000)
    run.add_argument("--max-estados-patron", type=int, default=350000)
    run.add_argument("--semilla-orden", type=int, default=20260912)
    run.add_argument("--validacion", action="store_true")
    run.set_defaults(func=ejecutar)
    args = parser.parse_args()
    try:
        args.func(args)
    except (ValueError, InterruptedError) as error:
        parser.exit(2, str(error)+"\n")


if __name__ == "__main__":
    mp.freeze_support()
    main()
