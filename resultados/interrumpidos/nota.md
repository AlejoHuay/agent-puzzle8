# Lote interrumpido durante la Fase 4

Al retomar la sesión después del agotamiento de tokens informado por el usuario, el lote uniforme N=6 tenía 67 registros y `completo=false`. No quedaba ningún proceso Python activo. Los 67 registros terminaron por límite de tiempo; no se infirió el resultado de los 33 intentos pendientes.

Se conserva aquí la carpeta parcial sin cambiar sus CSV ni metadatos. Se repite el lote completo con las mismas instancias, código, orden y presupuestos, en un proceso nuevo, porque el ejecutor no implementa reanudación. El resultado formal se guarda en `resultados/escalabilidad_6`.

Este lote parcial queda excluido de las estadísticas, modelos y denominadores formales. La repetición obedece a una interrupción técnica, no a la selección de resultados favorables. Las 67 búsquedas adicionales deben distinguirse de las 16800 búsquedas previstas en los lotes formales.
