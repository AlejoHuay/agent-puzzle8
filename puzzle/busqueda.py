"""Agente buscador: frontera priorizada, estados cerrados y métricas explícitas."""
from dataclasses import dataclass, field
from heapq import heappush, heappop
from itertools import count
from time import perf_counter, process_time
import psutil


@dataclass
class Limites:
    segundos: float = 300
    memoria_mb: float = 1024
    nodos: int = 2000000

    def __post_init__(self):
        if self.segundos <= 0 or self.memoria_mb <= 0 or self.nodos < 1:
            raise ValueError("Los límites deben ser positivos")


@dataclass
class Resultado:
    estado: str = "agotado"
    camino: list = field(default_factory=list)
    profundidad: int | None = None
    expandidos: int = 0
    generados: int = 0
    reabiertos: int = 0
    descartados: int = 0
    frontera_max: int = 0
    visitados_max: int = 0
    memoria_max_nodos: int = 0
    rss_max_muestreado_mb: float = 0
    tiempo_cpu_ms: float = 0
    tiempo_pared_ms: float = 0


@dataclass(slots=True)
class Nodo:
    estado: tuple
    g: int
    padre: object = None


class AgenteBuscador:
    def __init__(self, problema):
        self.problema = problema

    def resolver(self, inicio, tecnica, heuristica, limites=None, cancelar=None):
        if tecnica not in ("astar", "codicioso"):
            raise ValueError("Técnica desconocida")
        self.problema.validar(inicio)
        limites = limites or Limites()
        resultado = Resultado()
        reloj, cpu = perf_counter(), process_time()
        proceso = psutil.Process()

        def terminar(estado):
            resultado.estado = estado
            resultado.rss_max_muestreado_mb = max(resultado.rss_max_muestreado_mb,
                                                  proceso.memory_info().rss/2**20)
            resultado.tiempo_cpu_ms = (process_time()-cpu)*1000
            resultado.tiempo_pared_ms = (perf_counter()-reloj)*1000
            return resultado

        if not self.problema.soluble(inicio):
            return terminar("insoluble")
        frontera, cerrados, mejores = [], set(), {inicio: 0}
        serie = count()
        heappush(frontera, (heuristica(inicio), next(serie), Nodo(inicio, 0)))

        def memoria():
            resultado.frontera_max = max(resultado.frontera_max, len(frontera))
            resultado.visitados_max = max(resultado.visitados_max, len(cerrados))
            resultado.memoria_max_nodos = max(resultado.memoria_max_nodos, len(frontera)+len(cerrados))

        memoria()
        iteraciones = 0
        while frontera:
            if cancelar and cancelar():
                return terminar("cancelado")
            if perf_counter()-reloj >= limites.segundos:
                return terminar("limite_tiempo")
            if len(frontera)+len(cerrados) > limites.nodos:
                return terminar("limite_nodos")
            if iteraciones % 128 == 0:
                rss = proceso.memory_info().rss/2**20
                resultado.rss_max_muestreado_mb = max(resultado.rss_max_muestreado_mb, rss)
                if rss >= limites.memoria_mb:
                    return terminar("limite_memoria")
            iteraciones += 1
            _, _, nodo = heappop(frontera)
            s = nodo.estado
            if s in cerrados or nodo.g != mejores[s]:
                resultado.descartados += 1
                continue
            cerrados.add(s)
            memoria()
            if s == self.problema.meta:
                resultado.profundidad = nodo.g
                while nodo is not None:
                    resultado.camino.append(nodo.estado)
                    nodo = nodo.padre
                resultado.camino.reverse()
                return terminar("resuelto")
            resultado.expandidos += 1
            for hijo in self.problema.generar_hijos(s):
                resultado.generados += 1
                g = nodo.g+1
                if g >= mejores.get(hijo, float("inf")):
                    continue
                if hijo in cerrados:
                    cerrados.remove(hijo)
                    resultado.reabiertos += 1
                mejores[hijo] = g
                prioridad = heuristica(hijo) + (g if tecnica == "astar" else 0)
                heappush(frontera, (prioridad, next(serie), Nodo(hijo, g, nodo)))
                memoria()
        return terminar("agotado")
