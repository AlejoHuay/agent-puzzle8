"""Representación inmutable y operadores del material, generalizados a N x N."""
import random


class Puzzle:
    def __init__(self, n=3):
        if type(n) is not int or n < 2:
            raise ValueError("N debe ser un entero mayor o igual a 2")
        self.n = n
        self.meta = tuple(range(1, n*n)) + (0,)
        self.vecinos = []
        for p in range(n*n):
            r, c = divmod(p, n)
            # Orden del AgenteRK8: arriba, abajo, izquierda, derecha.
            self.vecinos.append(tuple(q for valido, q in (
                (r > 0, p-n), (r < n-1, p+n),
                (c > 0, p-1), (c < n-1, p+1)) if valido))

    def validar(self, estado):
        if len(estado) != self.n**2 or any(type(v) is not int for v in estado):
            raise ValueError("El estado debe contener N² enteros")
        if set(estado) != set(self.meta):
            raise ValueError("Se requiere cada ficha de 0 a N²-1 exactamente una vez")

    def soluble(self, estado):
        self.validar(estado)
        fichas = [v for v in estado if v]
        inv = sum(a > b for i, a in enumerate(fichas) for b in fichas[i+1:])
        if self.n % 2:
            return inv % 2 == 0
        fila_desde_abajo = self.n - estado.index(0)//self.n
        return (inv + fila_desde_abajo) % 2 == 1

    def generar_hijos(self, estado):
        cero = estado.index(0)
        for q in self.vecinos[cero]:
            hijo = list(estado)
            hijo[cero], hijo[q] = hijo[q], hijo[cero]
            yield tuple(hijo)

    def mezclar(self, rng, pasos=30):
        if pasos < 0:
            raise ValueError("Los pasos no pueden ser negativos")
        estado, anterior = self.meta, None
        for _ in range(pasos):
            candidatos = [s for s in self.generar_hijos(estado) if s != anterior]
            anterior, estado = estado, rng.choice(candidatos)
        return estado

    def instancias(self, cantidad, semilla, metodo="permutacion", pasos=30):
        if cantidad < 1 or metodo not in ("permutacion", "mezcla"):
            raise ValueError("Cantidad o método inválido")
        rng, vistos, salida = random.Random(semilla), set(), []
        intentos = 0
        while len(salida) < cantidad:
            intentos += 1
            if intentos > max(10000, cantidad*1000):
                raise ValueError("No se obtuvieron suficientes estados distintos; revise el protocolo")
            if metodo == "mezcla":
                estado = self.mezclar(rng, pasos)
            else:
                lista = list(self.meta)
                rng.shuffle(lista)
                estado = tuple(lista)
                if not self.soluble(estado):
                    continue
            if estado not in vistos:
                vistos.add(estado)
                salida.append(estado)
        return salida
