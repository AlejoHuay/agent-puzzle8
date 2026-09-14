"""Juego Pygame con asistente cancelable; las búsquedas no bloquean la ventana."""
import argparse
from dataclasses import asdict
import multiprocessing as mp
import os
from pathlib import Path
import queue
import random
from time import perf_counter
import pygame
import psutil
from puzzle.problema import Puzzle
from puzzle.heuristicas import Heuristicas
from puzzle.busqueda import AgenteBuscador, Limites


def asistir(n, estado, algoritmo, nombre, salida, detener):
    try:
        p, inicio = Puzzle(n), perf_counter()
        hs = Heuristicas(p)
        proceso = psutil.Process()
        hs.preparar(nombre, lambda: detener.is_set() or perf_counter()-inicio > 15 or
                    proceso.memory_info().rss/2**20 > 512)
        r = AgenteBuscador(p).resolver(estado, algoritmo, hs.obtener(nombre, .5),
                                       Limites(15, 512, 300000), detener.is_set)
        salida.put(asdict(r))
    except Exception as error:
        salida.put({"estado": "error", "mensaje": str(error), "camino": []})


class Juego:
    FONDO = (13, 22, 38)
    PANEL = (23, 37, 57)
    TEXTO = (233, 241, 249)
    VERDE = (71, 218, 179)

    def __init__(self, n=3, semilla=20260911):
        pygame.init()
        self.pantalla = pygame.display.set_mode((1060, 740))
        pygame.display.set_caption("Ruta Cero | Laboratorio de puzzles")
        self.fuente = pygame.font.Font(None, 27)
        self.pequena = pygame.font.Font(None, 22)
        self.titulo = pygame.font.Font(None, 52)
        self.numero = pygame.font.Font(None, 48)
        self.rng = random.Random(semilla)
        self.proceso = None
        self.cola = None
        self.detener = None
        self.algoritmo, self.heuristica = "astar", "H3"
        self.botones = []
        self.nuevo(n)

    def cancelar(self):
        if self.proceso:
            self.detener.set()
            self.proceso.join(.2)
            if self.proceso.is_alive():
                self.proceso.terminate()
                self.proceso.join()
            self.proceso.close()
            self.proceso = None
            self.cola.close()
            self.cola = None
        self.animacion = []

    def nuevo(self, n=None):
        self.cancelar()
        self.p = Puzzle(n or self.p.n)
        self.estado = self.p.mezclar(self.rng, 20 + self.p.n*2)
        self.original = self.estado
        self.historial = []
        self.movimientos = 0
        self.inicio = perf_counter()
        self.mensaje = "Ordena las fichas. El espacio vacío abre el camino."
        self.detalle = ""
        self.resuelto_en = None
        self.siguiente = 0

    def mover(self, destino):
        if self.proceso or self.animacion:
            return
        if destino in self.p.vecinos[self.estado.index(0)]:
            aux = list(self.estado)
            cero = aux.index(0)
            aux[cero], aux[destino] = aux[destino], aux[cero]
            self.historial.append(self.estado)
            self.estado = tuple(aux)
            self.movimientos += 1
            self.comprobar()

    def comprobar(self):
        if self.estado == self.p.meta:
            self.mensaje = "¡Ruta completada! Todas las fichas están en su lugar."
            self.resuelto_en = perf_counter()
        else:
            self.resuelto_en = None
            if self.mensaje.startswith("¡Ruta completada"):
                self.mensaje = "Puedes seguir moviendo las fichas o pedir ayuda."

    def accion(self, clave):
        if clave == "mezclar":
            self.nuevo()
        elif clave == "cancelar":
            self.cancelar()
            self.mensaje = "Asistente detenido. Puedes continuar jugando."
        elif clave == "deshacer" and not self.proceso and not self.animacion and self.historial:
            self.estado = self.historial.pop()
            self.movimientos = max(0, self.movimientos-1)
            self.comprobar()
        elif clave == "resolver" and not self.proceso and not self.animacion:
            self.cola, self.detener = mp.Queue(), mp.Event()
            self.proceso = mp.Process(target=asistir, args=(self.p.n, self.estado,
                                  self.algoritmo, self.heuristica, self.cola, self.detener))
            self.proceso.start()
            self.mensaje = "El asistente está buscando una ruta…"
            self.detalle = "Puedes cancelar o iniciar un tablero nuevo."
        elif clave == "algoritmo" and not self.proceso and not self.animacion:
            self.algoritmo = "codicioso" if self.algoritmo == "astar" else "astar"
        elif clave == "heuristica" and not self.proceso and not self.animacion:
            self.heuristica = f"H{int(self.heuristica[1]) % 6 + 1}"
        elif clave == "menos":
            self.nuevo(max(3, self.p.n-1))
        elif clave == "mas":
            self.nuevo(min(8, self.p.n+1))

    def actualizar(self):
        if self.proceso:
            try:
                r = self.cola.get_nowait()
            except queue.Empty:
                if not self.proceso.is_alive() and self.proceso.exitcode not in (None, 0):
                    self.cancelar()
                    self.mensaje = "El asistente se interrumpió. Puedes volver a intentar."
            else:
                self.cancelar()
                self.mensaje = {"resuelto": "Ruta encontrada. Reproduciendo movimientos…",
                                "limite_tiempo": "Se alcanzó el límite de tiempo del asistente.",
                                "limite_memoria": "Se alcanzó el límite de memoria del asistente.",
                                "limite_nodos": "Se alcanzó el límite de nodos del asistente."}.get(
                                    r["estado"], r.get("mensaje", r["estado"]))
                if r["estado"] == "resuelto":
                    self.animacion = [tuple(s) for s in r["camino"][1:]]
                    self.detalle = f"{r['profundidad']} pasos · {r['expandidos']} expansiones · {r['tiempo_pared_ms']:.1f} ms"
                    if not self.animacion:
                        self.comprobar()
        if self.animacion and perf_counter() >= self.siguiente:
            self.historial.append(self.estado)
            self.estado = self.animacion.pop(0)
            self.movimientos += 1
            self.siguiente = perf_counter()+.22
            self.comprobar()

    def texto(self, texto, pos, color=None, fuente=None):
        self.pantalla.blit((fuente or self.fuente).render(texto, True, color or self.TEXTO), pos)

    def dibujar(self):
        self.pantalla.fill(self.FONDO)
        self.texto("RUTA CERO", (42, 30), self.VERDE, self.titulo)
        self.texto("Un movimiento cambia el siguiente.", (44, 80), (155, 178, 201))
        self.botones = []
        n, lado = self.p.n, 510/self.p.n
        pygame.draw.rect(self.pantalla, self.PANEL, (36, 123, 528, 528), border_radius=20)
        for i, valor in enumerate(self.estado):
            r, c = divmod(i, n)
            rect = pygame.Rect(45+c*lado+4, 132+r*lado+4, lado-8, lado-8)
            if valor:
                correcto = valor == i+1
                pygame.draw.rect(self.pantalla, (39, 107, 103) if correcto else (44, 68, 96), rect, border_radius=10)
                numero = self.numero.render(str(valor), True, self.TEXTO)
                self.pantalla.blit(numero, numero.get_rect(center=rect.center))
            else:
                pygame.draw.rect(self.pantalla, (18, 29, 46), rect, border_radius=10)
            self.botones.append((rect, i))
        pygame.draw.rect(self.pantalla, self.PANEL, (594, 123, 426, 528), border_radius=20)
        self.texto("TU TABLERO", (622, 146), self.VERDE)
        tiempo = (self.resuelto_en or perf_counter())-self.inicio
        self.texto(f"{n} × {n}   /   {n*n-1} fichas", (622, 181))
        self.texto(f"{self.movimientos} movimientos    {int(tiempo)//60:02}:{int(tiempo)%60:02}", (622, 214))
        for x, y, ancho, clave, etiqueta in [
            (622, 254, 175, "menos", "− Tamaño"), (807, 254, 185, "mas", "+ Tamaño"),
            (622, 305, 370, "algoritmo", "Algoritmo: " + ("A*" if self.algoritmo == "astar" else "Codicioso")),
            (622, 356, 370, "heuristica", self.heuristica + " · " + {
                "H1": "Fichas fuera de lugar", "H2": "Manhattan", "H3": "Conflictos lineales",
                "H4": "Esquinas", "H5": "Patrones", "H6": "Mezcla (w = 0.5)"}[self.heuristica]),
            (622, 416, 370, "resolver", "Resolver con asistente"),
            (622, 467, 175, "mezclar", "Nuevo tablero"), (807, 467, 185, "deshacer", "Deshacer"),
            (622, 518, 370, "cancelar", "Detener asistente")]:
            rect = pygame.Rect(x, y, ancho, 40)
            pygame.draw.rect(self.pantalla, (35, 122, 105) if clave == "resolver" else (39, 57, 78), rect, border_radius=9)
            self.texto(etiqueta, (x+14, y+9))
            self.botones.append((rect, clave))
        self.texto("Clic en una ficha o flechas para mover el hueco.", (622, 581), fuente=self.pequena)
        self.texto("R: nuevo · Espacio: asistente · Esc: detener", (622, 610), fuente=self.pequena)
        self.texto(self.mensaje[:100], (44, 673), self.VERDE, self.pequena)
        self.texto(self.detalle[:100], (44, 702), fuente=self.pequena)
        pygame.display.flip()

    def ejecutar(self, cuadros=None, captura=None):
        reloj, activo, total = pygame.time.Clock(), True, 0
        try:
            while activo:
                for evento in pygame.event.get():
                    if evento.type == pygame.QUIT:
                        activo = False
                    elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                        for rect, clave in self.botones:
                            if rect.collidepoint(evento.pos):
                                self.mover(clave) if isinstance(clave, int) else self.accion(clave)
                                break
                    elif evento.type == pygame.KEYDOWN:
                        claves = {pygame.K_r: "mezclar", pygame.K_SPACE: "resolver", pygame.K_ESCAPE: "cancelar"}
                        if evento.key in claves:
                            self.accion(claves[evento.key])
                        else:
                            delta = {pygame.K_UP: -self.p.n, pygame.K_DOWN: self.p.n,
                                     pygame.K_LEFT: -1, pygame.K_RIGHT: 1}.get(evento.key)
                            if delta is not None:
                                self.mover(self.estado.index(0)+delta)
                self.actualizar()
                self.dibujar()
                reloj.tick(60)
                total += 1
                if cuadros and total >= cuadros:
                    activo = False
            if captura:
                Path(captura).parent.mkdir(parents=True, exist_ok=True)
                pygame.image.save(self.pantalla, captura)
        finally:
            self.cancelar()
            pygame.quit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, choices=range(3, 9), default=3)
    parser.add_argument("--semilla", type=int, default=20260911)
    parser.add_argument("--prueba-grafica", action="store_true")
    parser.add_argument("--captura")
    args = parser.parse_args()
    if args.prueba_grafica:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    Juego(args.n, args.semilla).ejecutar(5 if args.prueba_grafica else None, args.captura)


if __name__ == "__main__":
    mp.freeze_support()
    main()
