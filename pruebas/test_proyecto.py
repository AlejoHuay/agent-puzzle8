"""Pruebas de corrección, no experimentos comparativos de la práctica."""
from collections import deque
import os
import random
from time import perf_counter, sleep
import unittest
from puzzle.problema import Puzzle
from puzzle.heuristicas import Heuristicas
from puzzle.busqueda import AgenteBuscador, Limites


class ProblemaTest(unittest.TestCase):
    def test_validacion(self):
        for s in ((1, 2), (0,)*9, tuple(range(8))+(8.0,)):
            with self.assertRaises(ValueError):
                Puzzle().validar(s)
        with self.assertRaises(ValueError):
            Puzzle(1)

    def test_operadores(self):
        for n in (2, 3, 4, 5, 8):
            p = Puzzle(n)
            for s in [p.meta, p.mezclar(random.Random(n), 30)]:
                original = tuple(s)
                for h in p.generar_hijos(s):
                    self.assertTrue(p.soluble(h))
                    self.assertEqual(sum(a != b for a, b in zip(s, h)), 2)
                    self.assertIn(s, list(p.generar_hijos(h)))
                self.assertEqual(s, original)
            self.assertEqual(len(list(p.generar_hijos(p.meta))), 2)

    def test_paridad(self):
        for n in (3, 4, 5, 6):
            p = Puzzle(n)
            s = list(p.meta)
            s[0], s[1] = s[1], s[0]
            self.assertFalse(p.soluble(tuple(s)))
            self.assertTrue(p.soluble(p.meta))

    def test_reproducibilidad(self):
        p = Puzzle()
        a = p.instancias(15, 71)
        self.assertEqual(a, p.instancias(15, 71))
        self.assertEqual(len(set(a)), 15)
        self.assertTrue(all(p.soluble(s) for s in a))


class BusquedaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = Puzzle()
        cls.hs = Heuristicas(cls.p)
        cls.hs.preparar("H4")
        cls.hs.preparar("H5")

    def test_meta_y_un_paso(self):
        for algoritmo in ("astar", "codicioso"):
            agente = AgenteBuscador(self.p)
            r = agente.resolver(self.p.meta, algoritmo, self.hs.h3)
            self.assertEqual((r.estado, r.profundidad, r.expandidos, r.generados), ("resuelto", 0, 0, 0))
            self.assertEqual(r.memoria_max_nodos, 1)
            s = (1, 2, 3, 4, 5, 6, 7, 0, 8)
            r = agente.resolver(s, algoritmo, self.hs.h3)
            self.assertEqual((r.profundidad, r.expandidos, r.generados), (1, 1, 3))
            self.assertEqual(r.camino, [s, self.p.meta])

    def test_limites_y_cancelacion(self):
        s = (8, 6, 7, 2, 5, 4, 3, 0, 1)
        a = AgenteBuscador(self.p)
        for limites, esperado in [(Limites(1e-12, 1024), "limite_tiempo"),
                                   (Limites(30, .0001), "limite_memoria"),
                                   (Limites(30, 1024, 1), "limite_nodos")]:
            r = a.resolver(s, "astar", self.hs.h1, limites)
            self.assertEqual(r.estado, esperado)
            self.assertIsNone(r.profundidad)
            self.assertFalse(r.camino)
        self.assertEqual(a.resolver(s, "astar", self.hs.h1, cancelar=lambda: True).estado, "cancelado")

    def test_insoluble(self):
        r = AgenteBuscador(self.p).resolver((2, 1, 3, 4, 5, 6, 7, 8, 0), "astar", self.hs.h2)
        self.assertEqual(r.estado, "insoluble")
        self.assertEqual(r.expandidos, 0)

    def test_heuristicas_y_caminos_con_oraculo(self):
        # BFS independiente, solo como oráculo de pruebas hasta profundidad 8.
        dist, cola = {self.p.meta: 0}, deque([self.p.meta])
        while cola:
            s = cola.popleft()
            if dist[s] == 8:
                continue
            for h in self.p.generar_hijos(s):
                if h not in dist:
                    dist[h] = dist[s]+1
                    cola.append(h)
        casos = list(dist)[::max(1, len(dist)//12)]
        for nombre, peso in [(f"H{i}", None) for i in range(1, 6)] + [("H6", w) for w in (.25, .5, .75)]:
            f = self.hs.obtener(nombre, peso)
            self.assertEqual(f(self.p.meta), 0)
            for s in casos:
                for algoritmo in ("astar", "codicioso"):
                    r = AgenteBuscador(self.p).resolver(s, algoritmo, f)
                    self.assertEqual(r.estado, "resuelto")
                    self.assertEqual(r.camino[0], s)
                    self.assertEqual(r.camino[-1], self.p.meta)
                    self.assertEqual(len(r.camino)-1, r.profundidad)
                    for a, b in zip(r.camino, r.camino[1:]):
                        self.assertIn(b, list(self.p.generar_hijos(a)))
                    if algoritmo == "astar":
                        self.assertEqual(r.profundidad, dist[s])
                        self.assertEqual(r.reabiertos, 0)

    def test_caso_profundidad_31(self):
        r = AgenteBuscador(self.p).resolver((8, 6, 7, 2, 5, 4, 3, 0, 1), "astar", self.hs.h5)
        self.assertEqual(r.estado, "resuelto")
        self.assertEqual(r.profundidad, 31)

    def test_h3_corrige_conflictos_compartidos(self):
        s = (3, 1, 2, 0, 5, 6, 4, 7, 8)
        h = (0, 1, 2, 3, 5, 6, 4, 7, 8)
        self.assertEqual(self.hs.h3(s), 9)
        self.assertLessEqual(self.hs.h3(s), 1+self.hs.h3(h))

    def test_pdb_presupuesto_y_cancelacion(self):
        hs = Heuristicas(Puzzle(4), 5000)
        info = hs.preparar("H5")
        self.assertTrue(all(len(hs.tablas[g]) <= 5000 for g in hs.grupos["H5"]))
        self.assertEqual(hs.h5(hs.p.meta), 0)
        with self.assertRaises(InterruptedError):
            Heuristicas(Puzzle(4)).preparar("H5", lambda: True)
        with self.assertRaises(ValueError):
            self.hs.obtener("H6", 2)

    def test_generalizacion(self):
        for n in (4, 5):
            p, hs = Puzzle(n), Heuristicas(Puzzle(n))
            s = next(p.generar_hijos(p.meta))
            for nombre in ("H1", "H2", "H3", "H4", "H5", "H6"):
                hs.preparar(nombre)
                heuristica = hs.obtener(nombre, .5)
                r = AgenteBuscador(p).resolver(s, "astar", heuristica)
                self.assertEqual(r.profundidad, 1)
                for pasos in (5, 12, 25):
                    estado = p.mezclar(random.Random(pasos), pasos)
                    self.assertLessEqual(heuristica(estado), pasos)
                    for hijo in p.generar_hijos(estado):
                        self.assertLessEqual(abs(heuristica(estado)-heuristica(hijo)), 1)


class JuegoTest(unittest.TestCase):
    def test_controles_y_render(self):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        import pygame
        from juego import Juego
        juego = Juego()
        try:
            inicial = juego.estado
            juego.mover(juego.p.vecinos[juego.estado.index(0)][0])
            self.assertNotEqual(juego.estado, inicial)
            juego.accion("deshacer")
            self.assertEqual(juego.estado, inicial)
            juego.accion("mas")
            self.assertEqual(juego.p.n, 4)
            juego.accion("algoritmo")
            self.assertEqual(juego.algoritmo, "codicioso")
            juego.accion("heuristica")
            self.assertEqual(juego.heuristica, "H4")
            juego.dibujar()
            juego.animacion = [juego.p.meta]
            juego.actualizar()
            self.assertEqual(juego.estado, juego.p.meta)
        finally:
            juego.cancelar()
            pygame.quit()

    def test_asistente_en_proceso_y_cancelacion(self):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        import pygame
        from juego import Juego
        juego = Juego()
        try:
            juego.estado = (1, 2, 3, 4, 5, 6, 7, 0, 8)
            juego.accion("resolver")
            limite = perf_counter()+15
            while (juego.proceso or juego.animacion) and perf_counter() < limite:
                juego.actualizar()
                sleep(.01)
            self.assertIsNone(juego.proceso)
            self.assertEqual(juego.estado, juego.p.meta)
            juego.accion("mezclar")
            juego.accion("resolver")
            juego.accion("cancelar")
            self.assertIsNone(juego.proceso)
            self.assertFalse(juego.animacion)
        finally:
            juego.cancelar()
            pygame.quit()


if __name__ == "__main__":
    unittest.main()
