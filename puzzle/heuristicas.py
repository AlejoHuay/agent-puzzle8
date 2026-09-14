"""Heurísticas consistentes; PDB aditivas mediante búsqueda 0-1 inversa."""
from bisect import bisect_left
from collections import deque
from math import perm
from time import perf_counter


def eliminaciones(secuencia):
    """Mínimas eliminaciones para ordenar: longitud menos LIS estricta."""
    colas = []
    for v in secuencia:
        i = bisect_left(colas, v)
        if i == len(colas):
            colas.append(v)
        else:
            colas[i] = v
    return len(secuencia) - len(colas)


class Heuristicas:
    def __init__(self, problema, max_estados_patron=350000):
        self.p = problema
        self.max_estados_patron = max_estados_patron
        self.tablas = {}
        self.grupos = {}
        m, n = len(problema.meta), problema.n
        self.distancias = [[0 if v == 0 else abs(i//n-(v-1)//n)+abs(i%n-(v-1)%n)
                            for i in range(m)] for v in range(m)]

    def h1(self, s):
        return sum(v != 0 and v != i+1 for i, v in enumerate(s))

    def h2(self, s):
        return sum(self.distancias[v][i] for i, v in enumerate(s))

    def h3(self, s):
        n = self.p.n
        c = 0
        for r in range(n):
            fila = [s[r*n+j] for j in range(n)]
            c += eliminaciones([(v-1)%n for v in fila if v and (v-1)//n == r])
        for col in range(n):
            columna = [s[r*n+col] for r in range(n)]
            c += eliminaciones([(v-1)//n for v in columna if v and (v-1)%n == col])
        return self.h2(s) + 2*c

    def _limitar_grupo(self, grupo):
        grupo = tuple(grupo)
        while grupo and perm(self.p.n**2, len(grupo)+1) > self.max_estados_patron:
            grupo = grupo[:-1]
        if not grupo:
            raise ValueError("Presupuesto de PDB insuficiente incluso para una ficha")
        return grupo

    def _construir(self, grupo, cancelar):
        if grupo in self.tablas:
            return
        inicio = (len(self.p.meta)-1,) + tuple(v-1 for v in grupo)
        dist, cola = {inicio: 0}, deque([(inicio, 0)])
        pasos = 0
        while cola:
            s, costo = cola.popleft()
            if costo != dist[s]:
                continue
            pasos += 1
            if pasos % 1024 == 0 and cancelar and cancelar():
                raise InterruptedError("Preparación de PDB interrumpida por límite o cancelación")
            for q in self.p.vecinos[s[0]]:
                aux = list(s)
                aux[0] = q
                if q in s[1:]:
                    j = s.index(q, 1)
                    aux[j] = s[0]
                    incremento = 1
                else:
                    incremento = 0
                hijo = tuple(aux)
                nuevo = costo + incremento
                if nuevo < dist.get(hijo, float("inf")):
                    dist[hijo] = nuevo
                    if incremento:
                        cola.append((hijo, nuevo))
                    else:
                        cola.appendleft((hijo, nuevo))
        self.tablas[grupo] = dist

    def preparar(self, nombre, cancelar=None):
        inicio = perf_counter()
        if nombre == "H5" and nombre not in self.grupos:
            fichas = list(range(1, self.p.n**2))
            grupos = []
            while fichas:
                g = self._limitar_grupo(fichas[:4])
                grupos.append(g)
                fichas = fichas[len(g):]
            self.grupos[nombre] = grupos
        if nombre == "H4" and nombre not in self.grupos:
            n = self.p.n
            esquinas = (0, n-1, n*(n-1))  # La última esquina tiene como meta el hueco.
            self.grupos[nombre] = [self._limitar_grupo(
                [i+1] + [q+1 for q in self.p.vecinos[i] if q+1 < n*n]) for i in esquinas]
        for grupo in self.grupos.get(nombre, []):
            self._construir(grupo, cancelar)
        return {"segundos": perf_counter()-inicio,
                "grupos": self.grupos.get(nombre, []),
                "entradas": sum(len(self.tablas[g]) for g in self.grupos.get(nombre, []))}

    @staticmethod
    def posiciones(s):
        pos = [0]*len(s)
        for i, v in enumerate(s):
            pos[v] = i
        return pos

    def h4(self, s):
        pos = self.posiciones(s)
        manhattan = self.h2(s)
        cotas = [self.h3(s)]
        for g in self.grupos["H4"]:
            d = self.tablas[g][(pos[0],) + tuple(pos[v] for v in g)]
            resto = manhattan - sum(self.distancias[v][pos[v]] for v in g)
            cotas.append(d + resto)
        return max(cotas)

    def h5(self, s):
        pos = self.posiciones(s)
        return sum(self.tablas[g][(pos[0],) + tuple(pos[v] for v in g)] for g in self.grupos["H5"])

    def obtener(self, nombre, peso=None):
        if nombre == "H6":
            if peso is None or not 0 <= peso <= 1:
                raise ValueError("H6 requiere un peso entre cero y uno")
            return lambda s: peso*self.h2(s)+(1-peso)*self.h1(s)
        if nombre not in ("H1", "H2", "H3", "H4", "H5"):
            raise ValueError("Heurística desconocida")
        if nombre in ("H4", "H5") and any(g not in self.tablas for g in self.grupos.get(nombre, [()])):
            raise ValueError("Primero prepare las bases de patrones")
        return getattr(self, nombre.lower())
