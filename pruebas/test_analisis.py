"""Casos artificiales de prueba: nunca se incorporan a los resultados del puzzle."""
import unittest
import numpy as np
from analizar import resumen, resumen_exito, contrastar, ajustar_crecimiento, cargar


class AnalisisTest(unittest.TestCase):
    def test_descriptivas_y_constantes(self):
        r = resumen([1, 2, 3, 4], remuestreos=100)
        self.assertEqual(r["media"], 2.5)
        self.assertEqual(r["mediana"], 2.5)
        self.assertAlmostEqual(r["desviacion"], np.sqrt(5/3))
        self.assertEqual(resumen([]), {"n": 0})
        self.assertIsNone(resumen([2])["ic95_inferior"])
        r = resumen([2]*20)
        self.assertEqual((r["ic95_inferior"], r["ic95_superior"]), (2, 2))
        self.assertEqual(resumen([1, 2, 3], remuestreos=100), resumen([1, 2, 3], remuestreos=100))
        self.assertGreater(resumen_exito([0]*20)["ic95_superior"], 0)
        self.assertLess(resumen_exito([1]*20)["ic95_inferior"], 1)

    def test_friedman_empates_y_posthoc(self):
        nombres = [str(i) for i in range(8)]
        empatadas = np.repeat(np.arange(20)[:, None], 8, axis=1)
        self.assertEqual(contrastar(empatadas, nombres)["p"], 1)
        ordenadas = empatadas + np.arange(8)[None, :]
        r = contrastar(ordenadas, nombres)
        self.assertLess(r["p"], .05)
        self.assertEqual(len(r["posthoc"]), 28)
        for par in r["posthoc"]:
            self.assertEqual(par["p_bonferroni"], min(1, par["p"]*28))
        self.assertEqual(contrastar(ordenadas[:2], nombres)["estado"], "muestra_insuficiente_para_aproximacion")

    def test_modelos_y_datos_insuficientes(self):
        self.assertEqual(ajustar_crecimiento([3, 4], [10, 20])["estado"], "datos_insuficientes")
        x = np.array([3, 4, 5, 6, 7])
        r = ajustar_crecimiento(x, 2*3.**x)
        self.assertAlmostEqual(r["modelos"]["exponencial"]["r2"], 1)
        self.assertAlmostEqual(r["modelos"]["exponencial"]["parametros"][1], 3)

    def test_no_mezclar_validacion_con_experimentos(self):
        with self.assertRaises(ValueError):
            cargar("verificacion/integracion")


if __name__ == "__main__":
    unittest.main()
