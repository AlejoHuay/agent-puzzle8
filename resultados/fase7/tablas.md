### Resumen de A* y Codicioso con la heurística seleccionada


| Métrica | Mediana A* | Mediana Codicioso | Media A* | Media Codicioso |
|---|---|---|---|---|
| profundidad | 22 | 26 | 21.86 | 27.36 |
| expandidos | 85 | 36 | 134.6 | 42.32 |
| generados | 237.5 | 101 | 375.5 | 118.4 |
| tiempo_cpu_ms | 0 | 0 | 1.141 | 0.3594 |
| tiempo_pared_ms | 0.7603 | 0.3372 | 1.193 | 0.3954 |
| memoria_max_nodos | 152 | 67.5 | 235.1 | 77.62 |
| rss_max_muestreado_mb | 29.57 | 28.98 | 29.45 | 28.99 |


### Comparación por instancia: Codicioso menos A*


| Métrica | Cod. menor | Igual | Cod. mayor | Diferencia mediana | p Bonferroni | Significativo |
|---|---|---|---|---|---|---|
| profundidad | 0 | 352 | 648 | 4 | 1.199e-194 | sí |
| expandidos | 852 | 44 | 104 | -46.5 | 7.025e-146 | sí |
| generados | 858 | 39 | 103 | -128.5 | 4.713e-148 | sí |
| tiempo_cpu_ms | 72 | 906 | 22 | 0 | 1.582e-06 | sí |
| tiempo_pared_ms | 858 | 0 | 142 | -0.3884 | 1.567e-124 | sí |
| memoria_max_nodos | 856 | 41 | 103 | -78 | 1.503e-147 | sí |
| rss_max_muestreado_mb | 999 | 0 | 1 | -0.543 | 1.308e-297 | sí |


### Descriptivas completas de las dos configuraciones


| Métrica | Algoritmo | Media | DE | Mín. | P25 | Mediana | P75 | Máx. | IC95 inf. | IC95 sup. |
|---|---|---|---|---|---|---|---|---|---|---|
| profundidad | astar | 21.86 | 3.449 | 8 | 20 | 22 | 24 | 30 | 21.64 | 22.07 |
| profundidad | codicioso | 27.36 | 7.848 | 8 | 22 | 26 | 32 | 58 | 26.87 | 27.85 |
| expandidos | astar | 134.6 | 150.5 | 8 | 40 | 85 | 175.2 | 1597 | 125.5 | 144.3 |
| expandidos | codicioso | 42.32 | 23.27 | 8 | 25 | 36 | 53 | 132 | 40.87 | 43.76 |
| generados | astar | 375.5 | 417.3 | 22 | 114.8 | 237.5 | 492 | 4465 | 350.3 | 402.7 |
| generados | codicioso | 118.4 | 62.9 | 22 | 71 | 101 | 149 | 365 | 114.5 | 122.3 |
| tiempo_cpu_ms | astar | 1.141 | 4.067 | 0 | 0 | 0 | 0 | 15.62 | 0.8906 | 1.406 |
| tiempo_cpu_ms | codicioso | 0.3594 | 2.343 | 0 | 0 | 0 | 0 | 15.62 | 0.2188 | 0.5156 |
| tiempo_pared_ms | astar | 1.193 | 1.316 | 0.0828 | 0.3837 | 0.7603 | 1.518 | 13.75 | 1.116 | 1.277 |
| tiempo_pared_ms | codicioso | 0.3954 | 0.2293 | 0.0997 | 0.2395 | 0.3372 | 0.4792 | 2.04 | 0.3813 | 0.4099 |
| memoria_max_nodos | astar | 235.1 | 254.1 | 16 | 75 | 152 | 306.2 | 2688 | 219.8 | 251.6 |
| memoria_max_nodos | codicioso | 77.62 | 38.68 | 16 | 48 | 67.5 | 98 | 225 | 75.22 | 80.01 |
| rss_max_muestreado_mb | astar | 29.45 | 0.2018 | 28.82 | 29.21 | 29.57 | 29.58 | 29.6 | 29.44 | 29.46 |
| rss_max_muestreado_mb | codicioso | 28.99 | 0.04394 | 28.71 | 28.95 | 28.98 | 29.02 | 29.06 | 28.98 | 28.99 |