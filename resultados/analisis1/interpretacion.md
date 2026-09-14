## 10. Fase 4: procedimiento y hallazgos del experimento principal

El 14 de septiembre de 2026 se ejecutaron **16000 búsquedas reales**: dos algoritmos y ocho configuraciones sobre las mismas 1000 permutaciones solubles distintas de Puzzle-8. Todas terminaron con solución. Las configuraciones de A* coincidieron en profundidad y sus **8000 respuestas se verificaron contra un oráculo BFS independiente**. Las profundidades óptimas de la muestra van de 8 a 30, con mediana 22 y media 21.855.

Los archivos originales están en [resultados/experimento1](resultados/experimento1), con instancias, mediciones, hashes y preparación. El análisis reproducible está en [analizar.py](analizar.py); las tablas y comprobaciones adicionales se generan con [documentar_resultados.py](documentar_resultados.py). La especificación previa de los experimentos se conserva en [protocolo_fase4.json](resultados/protocolo_fase4.json). Los resultados formales se incluyen en el proyecto; no se excluyen mediante `.gitignore`.

Se ejecutó un tratamiento a la vez, en un proceso nuevo por configuración. Se conservaron los límites de 300 segundos, 1024 MiB de RSS y dos millones de nodos simultáneos para el experimento principal. Ningún caso alcanzó esos límites. La máquina tiene un Intel Core i7-1165G7 de 11.ª generación, frecuencia nominal de 2.80 GHz, ocho procesadores lógicos, 16805126144 bytes de RAM, Windows 11 y Python 3.13.15 de 64 bits. El sistema no es un entorno de laboratorio con frecuencia, temperatura y actividad externa completamente controladas; hubo tareas breves de análisis y documentación durante parte de la ejecución. Se conservan CPU y tiempo de pared para hacer visible esa limitación.

### 10.1. Eficiencia de las heurísticas en A*

**Resultado.** H5 presenta una mediana de 85 expansiones; H4, 284.5; H3, 511; Manhattan, 895.5; y H1, 8461.5. H5 reduce aproximadamente un **90.5 %** la mediana respecto de Manhattan y un **99.0 %** respecto de H1. Son diferencias relativas entre medianas, no la mediana de porcentajes individuales. Su mediana de tiempo real es 0.76035 ms y su media de CPU es 1.140625 ms.

**Interpretación.** Las bases de patrones capturan restricciones conjuntas que Manhattan ignora. La reducción del trabajo de búsqueda compensa aquí el costo de consultar las tablas. Su preparación en A* requirió 49.759 ms para 30240 entradas; se registra fuera del tiempo de cada búsqueda. Amortizada entre 1000 casos representa aproximadamente 0.0498 ms adicionales por caso. No debe confundirse esta amortización con el costo de una única consulta que construya la tabla desde cero.

**Conclusión.** H5 fue seleccionada para el experimento de escalabilidad mediante el criterio definido: éxito y, a continuación, medianas de expansiones, CPU y memoria en nodos. Es la opción más favorable de esta implementación y muestra para reducir búsqueda, conservar optimalidad y obtener tiempos bajos; esto no prueba superioridad universal en otros tamaños o particiones.

![A*: expansiones y medias con IC](resultados/analisis1/astar_expandidos.png)

### 10.2. Más información heurística no implica menos tiempo

**Resultado.** H4 reduce la mediana de expansiones de 511 a 284.5 frente a H3, aproximadamente un 44.3 %. Sin embargo, la media de CPU aumenta de 16.296875 a 26.21875 ms, aproximadamente un 60.9 %, y la mediana de tiempo real pasa de 9.06585 a 15.3148 ms.

**Interpretación.** H4 calcula H3 y además consulta las abstracciones de esquinas. El ahorro de nodos no compensa su mayor costo de evaluación por nodo en este experimento. El precálculo ya se excluyó de los tiempos de búsqueda, por lo que no explica por sí solo el aumento observado.

**Conclusión.** La corrección de H4 es válida y aporta información, pero no desplaza a H3 como opción más rápida en esta comparación. Este resultado ilustra el equilibrio entre precisión y trabajo por nodo discutido en las diapositivas.

### 10.3. Codicioso: velocidad frente a calidad de solución

**Resultado.** Con H5, Codicioso tiene medianas de 36 expansiones, 0.33715 ms de tiempo real y 26 movimientos. A* con H5 tiene 85 expansiones, 0.76035 ms y 22 movimientos. Codicioso obtiene el óptimo en **352 de 1000 casos (35.2 %)**; el exceso pareado mediano respecto al óptimo es de cuatro movimientos y el exceso máximo es 34. H1 solo obtiene soluciones óptimas en 24 casos (2.4 %).

**Interpretación.** Ignorar el costo acumulado permite a Codicioso concentrarse en estados atractivos según h, pero puede aceptar rutas más largas. La menor cantidad de expansiones no significa por sí misma una solución mejor. Las diferencias de CPU submilisegundo no se pueden interpretar directamente desde medianas iguales a cero.

**Conclusión.** Codicioso con H5 resulta útil si se prioriza una respuesta rápida y se toleran movimientos adicionales. A* con H5 es preferible cuando se exige costo mínimo. Ambos tuvieron 100 % de éxito en estas 1000 instancias, por lo que la tasa de éxito no los diferencia aquí. Ese 100 % es por configuración y no convierte las 16000 búsquedas en 16000 instancias independientes.

![Codicioso: profundidad de las soluciones](resultados/analisis1/codicioso_profundidad.png)

### 10.4. Memoria: nodos almacenados y RAM no son la misma medida

**Resultado.** H5 tiene la menor mediana de memoria en nodos: 152 para A* y 67.5 para Codicioso. El menor RSS mediano, en cambio, corresponde a H3: 28.539 MiB en A* y 24.816 MiB en Codicioso. H5 registra respectivamente 29.566 y 28.984 MiB.

**Interpretación.** El conteo de frontera más visitados no incluye las PDB, las tablas geométricas, todos los padres ni el intérprete. El resultado es compatible con el costo adicional de las bases de patrones. No se puede atribuir cada byte de la diferencia exclusivamente a ellas: RSS también depende del asignador y del estado del proceso.

**Conclusión.** H5 gana en memoria de búsqueda expresada en nodos, pero no en RSS mediano. El informe y la presentación deben indicar siempre qué definición de memoria utilizan. RSS es un máximo muestreado, no una medición continua ni una cuota dura del sistema.

### 10.5. Pesos de H6 y dificultad

**Resultado.** En A*, las medianas de expansiones para pesos 0.25, 0.50 y 0.75 son 3814, 2177 y 1037.5. Todas conservan las mismas profundidades óptimas. Manhattan expande menos, con mediana 895.5. En Codicioso, las medianas de profundidad de esas variantes son 51, 50 y 52, y sus tasas de optimalidad solo 2.7 %, 3.0 % y 3.1 %.

**Interpretación.** Acercar la combinación convexa a Manhattan mejora aquí la búsqueda de A*, pero no supera a Manhattan. Codicioso no hereda una mejora monótona de calidad por aumentar el peso. Las pruebas post-hoc de profundidad no detectan diferencias significativas entre los tres pesos tras la corrección.

**Conclusión.** H6 no introduce un intercambio entre rapidez y optimalidad de A*: todas sus variantes mantienen optimalidad. En este experimento tampoco aporta una alternativa competitiva a H5.

**Resultado por dificultad.** Los estratos de profundidad óptima 0–15, 16–20, 21–25 y 26–31 contienen 46, 281, 541 y 132 casos. Para A*–H1 las medianas de expansiones son 191, 2409, 13298 y 41403; para A*–H5 son 16, 38, 117 y 313.

**Interpretación.** El trabajo crece con la profundidad y la diferencia entre heurísticas se amplía. Los estratos se calculan después de muestrear, no se usaron para seleccionar casos favorables. La profundidad y el tamaño del tablero son factores distintos.

**Conclusión.** H5 mantiene una reducción muy marcada del espacio explorado incluso en el estrato más difícil de la muestra.

![Expansiones por profundidad óptima](resultados/analisis1/dificultad.png)

### 10.6. Significación estadística y sus límites

**Resultado.** Friedman sobre expansiones arroja χ²=6977.1304 para A* y χ²=5457.9976 para Codicioso, con siete grados de libertad y 1000 bloques. Los p numéricos subdesbordan a cero; se reportan como **p<1e-300**, no como probabilidades exactamente nulas. Los 28 pares de heurísticas resultan significativos en cada algoritmo después de Wilcoxon–Bonferroni.

En A*, todas las profundidades coinciden. La fórmula con corrección de empates queda degenerada; el programa la trata explícitamente como ausencia de diferencias observadas, con estadístico convencional 0 y p=1. No se ejecuta un post-hoc innecesario para esa variable.

**Interpretación.** La evidencia respalda diferencias sistemáticas de expansiones dentro de la muestra pareada. La significación no demuestra que todos los efectos sean grandes ni que una heurística sea mejor en todas las instancias. Los tamaños de efecto se muestran mediante diferencias pareadas y comparaciones relativas; los intervalos del 95 % describen incertidumbre de medias, no de cada ejecución.

Hay excepciones por otras métricas. A*–H3 y A*–H6 con w=0.75 no presentan diferencias temporales significativas tras Bonferroni (p ajustado=1 en CPU y pared). Las profundidades de Codicioso–H3 y H4 tampoco difieren significativamente (p ajustado=1). Esto significa falta de evidencia para esas diferencias, no prueba de equivalencia.

**Conclusión.** Las conclusiones deben formularse por métrica. La prueba principal es expansiones; generados, RSS y tiempo de pared se incluyen además como análisis exploratorios. La corrección abarca los 28 pares de cada familia, no todas las métricas simultáneamente. Wilcoxon supone simetría de las diferencias bajo la hipótesis nula; no debe describirse sin más como una prueba universal de igualdad de medianas.

### 10.7. Resolución temporal y observación extrema

**Resultado.** 927 de las 1000 búsquedas A*–H5 y 977 de Codicioso–H5 registran cero en CPU, mientras que sus tiempos reales son positivos. Las mediciones de CPU muestran cuantización de aproximadamente 15.625 ms.

Una ejecución, instancia 728 de A*–H6 con w=0.50, registra **154201.303 ms de pared y 187.5 ms de CPU**. La media de pared de ese tratamiento es 219.777 ms. Como comprobación de sensibilidad, al omitir únicamente ese punto sería 65.642 ms, y la mediana cambiaría de 32.456 a 32.283 ms. La observación **se conserva en los CSV, tablas, intervalos y contrastes oficiales**; el cálculo sin ella solo diagnostica sensibilidad.

**Interpretación.** El cero en CPU no representa una búsqueda instantánea. La diferencia extrema entre CPU y pared es compatible con una demora de planificación, suspensión u otra interferencia externa; los datos no identifican cuál. La media resulta mucho más sensible a esa observación que la mediana.

**Conclusión.** No se debe clasificar el rendimiento submilisegundo por medianas de CPU iguales a cero ni atribuir esa demora extrema únicamente a H6. Se presentan ambas medidas, estadísticas robustas y limitaciones, sin corregir manualmente resultados.

![Tiempo real de A*: observación extrema visible](resultados/analisis1/astar_tiempo_pared_ms.png)

### 10.8. Tablas completas y trazabilidad

Las tablas siguientes proceden de las ejecuciones originales. Las medias e intervalos se calcularon sobre 1000 observaciones por combinación. Se usa desviación estándar muestral, percentiles lineales y bootstrap percentil del 95 % con 5000 remuestreos y semilla 20260913. Los intervalos de éxito emplean Wilson: para el 100 % observado en cada configuración, el IC95 es aproximadamente [99.62 %, 100 %]. Los boxplots muestran mediana, cuartiles, bigotes de 1.5 IQR y observaciones fuera de los bigotes; estas observaciones no se eliminaron. La escala `symlog` mantiene el cero y permite ver órdenes de magnitud; no debe interpretarse como una escala lineal. Profundidad y RSS se muestran en escala lineal.

Los CSV mantienen precisión completa. Las tablas Markdown redondean para lectura. Pueden regenerarse mediante:

```powershell
.venv\Scripts\python.exe analizar.py comparacion resultados/experimento1 --salida resultados/analisis1_repetido
.venv\Scripts\python.exe documentar_resultados.py
```

El segundo comando utiliza los resultados de `analisis1` y regenera solo sus tablas y comprobaciones auxiliares. No vuelve a ejecutar búsquedas ni modifica los CSV originales. Las descriptivas completas están en [descriptivas.csv](resultados/analisis1/descriptivas.csv), y los contrastes de las siete métricas y las diferencias entre algoritmos están en [analisis.json](resultados/analisis1/analisis.json).

Cada figura contiene un boxplot y barras de medias con IC95. Esta tabla permite consultar las catorce figuras:

| Métrica | A* | Codicioso |
|---|---|---|
| Profundidad | [Figura](resultados/analisis1/astar_profundidad.png) | [Figura](resultados/analisis1/codicioso_profundidad.png) |
| Expandidos | [Figura](resultados/analisis1/astar_expandidos.png) | [Figura](resultados/analisis1/codicioso_expandidos.png) |
| Generados | [Figura](resultados/analisis1/astar_generados.png) | [Figura](resultados/analisis1/codicioso_generados.png) |
| CPU | [Figura](resultados/analisis1/astar_tiempo_cpu_ms.png) | [Figura](resultados/analisis1/codicioso_tiempo_cpu_ms.png) |
| Tiempo de pared | [Figura](resultados/analisis1/astar_tiempo_pared_ms.png) | [Figura](resultados/analisis1/codicioso_tiempo_pared_ms.png) |
| Memoria en nodos | [Figura](resultados/analisis1/astar_memoria_max_nodos.png) | [Figura](resultados/analisis1/codicioso_memoria_max_nodos.png) |
| RSS muestreado | [Figura](resultados/analisis1/astar_rss_max_muestreado_mb.png) | [Figura](resultados/analisis1/codicioso_rss_max_muestreado_mb.png) |


