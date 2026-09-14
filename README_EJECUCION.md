# Instalación y ejecución de Puzzle-N

Esta guía contiene únicamente instrucciones de uso. El informe está en [README.md](README.md) y el análisis ampliado en [README_COMPLEMENTARIO.md](README_COMPLEMENTARIO.md).

Los comandos principales son para **PowerShell en Windows** y se ejecutan desde la raíz del proyecto, donde están `juego.py` y `requirements.txt`. No hace falta activar el entorno virtual. Para jugar bastan los apartados 1 y 2; los demás programas son independientes del juego.

## 1. Preparar el entorno e instalar dependencias

Abra la carpeta del proyecto en VS Code y una terminal PowerShell. Si la terminal está en otra carpeta, entre en la raíz; en la ubicación de este proyecto:

```powershell
Set-Location -LiteralPath 'C:\Users\elgua\Downloads\INTELIGENCIA-ARTIFICAL'
```

Si copió el proyecto a otra ubicación, cambie esa ruta. Utilice Python **3.13 de 64 bits**, versión del entorno de referencia para las dependencias fijadas. Compruebe el intérprete:

```powershell
python --version
python -c "import struct; print(struct.calcsize('P') * 8)"
```

El segundo comando debe mostrar `64`. Si `python` no existe o apunta a otra versión y tiene instalado el lanzador de Windows, compruebe `py -3.13 --version` y utilice `py -3.13` en lugar de `python` para crear el entorno.

En una instalación nueva:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip check
```

Si ya existe el entorno funcional de este proyecto, no necesita crearlo otra vez: ejecute los dos comandos de `pip` si quiere comprobar o completar sus dependencias. El archivo [requirements.txt](requirements.txt) fija Pygame, psutil, NumPy, SciPy y Matplotlib. No copie `.venv` desde otra máquina; créelo en la máquina de destino.

En Linux/macOS, desde la raíz, el equivalente es:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
.venv/bin/python juego.py
```

En los comandos individuales posteriores sustituya `.venv\Scripts\python.exe` por `.venv/bin/python`. El bucle de escalabilidad mostrado más abajo utiliza sintaxis PowerShell. El entorno comprobado del proyecto es Windows; el juego requiere una sesión gráfica.

## 2. Abrir y utilizar el juego

```powershell
.venv\Scripts\python.exe juego.py
```

Para comenzar en 4×4 y fijar la semilla:

```powershell
.venv\Scripts\python.exe juego.py --n 4 --semilla 20260911
```

`--n` acepta tamaños de 3 a 8. El tamaño predeterminado es 3. También puede cambiar tamaño, algoritmo y heurística desde los botones de la ventana.

| Control | Acción |
|---|---|
| Clic en una ficha adyacente al hueco | Moverla al hueco. |
| Flechas | Mover el hueco en la dirección indicada. |
| R / «Nuevo tablero» | Generar otro tablero. |
| Espacio / «Resolver con asistente» | Solicitar y reproducir una solución. |
| Esc / «Detener asistente» | Cancelar el asistente. |
| «Deshacer» | Deshacer un movimiento. |
| «Algoritmo» / botón de heurística | Cambiar la configuración del asistente. |
| Cerrar la ventana | Terminar el juego y su proceso auxiliar. |

Para utilizar H5, selecciónela con el botón de heurística. La variante H6 de la interfaz usa peso 0.5; otros pesos se prueban por consola. El asistente tiene límites de 15 segundos para preparación y 15 segundos para búsqueda, 512 MiB de RSS y 300000 nodos simultáneos. Que se detenga por un límite no significa que el tablero sea insoluble. La ventana informa el estado de la operación.

## 3. Resolver un tablero desde la consola

Escriba las fichas por filas, separadas por comas, utilizando `0` para el hueco. Deben aparecer todos los números de `0` a `N²−1` exactamente una vez.

```powershell
.venv\Scripts\python.exe resolver.py "1,2,3,4,5,6,7,0,8" --algoritmo astar --heuristica H5
.venv\Scripts\python.exe resolver.py "1,2,3,4,5,6,7,0,8" --algoritmo codicioso --heuristica H5
.venv\Scripts\python.exe resolver.py "1,2,3,4,5,6,7,0,8" --heuristica H6 --peso 0.25
.venv\Scripts\python.exe resolver.py "1,2,3,4,5,6,7,8,9,10,11,12,13,14,0,15" --n 4 --heuristica H5 --segundos 5 --memoria-mb 512
```

Se imprime JSON con el camino, profundidad, nodos, tiempos, memoria, preparación y condición de terminación. El primer ejemplo necesita un movimiento. La consola usa A*, H3, N=3, 30 segundos y 512 MiB por defecto. `--segundos` limita por separado la preparación y la búsqueda; no es un límite conjunto de ambas. `--peso` solo afecta a H6. El motor admite N≥2.

## 4. Consultar o regenerar los análisis existentes

Para leer los resultados no hace falta ejecutar nada: abra el README y los archivos de `resultados/`. Para regenerar la síntesis de A* y Codicioso con la heurística seleccionada:

```powershell
.venv\Scripts\python.exe comparar_algoritmos.py
```

Este programa usa rutas fijas: `resultados/experimento1` y la selección y descriptivas de `resultados/analisis1`. Regenera tablas, JSON, CSV y figura en `resultados/fase7`. **No ejecuta búsquedas** ni admite parámetros de línea de comandos, incluido `--help`.

Para recalcular el análisis completo de las mediciones originales en una carpeta nueva:

```powershell
.venv\Scripts\python.exe analizar.py comparacion resultados/experimento1 --salida resultados/analisis1_local
.venv\Scripts\python.exe analizar.py escalabilidad resultados/escalabilidad_3 resultados/escalabilidad_4 resultados/escalabilidad_5 resultados/escalabilidad_6 --salida resultados/escala_local
.venv\Scripts\python.exe analizar.py escalabilidad resultados/cercanos_3 resultados/cercanos_4 resultados/cercanos_5 resultados/cercanos_6 --salida resultados/cercanos_local
```

`analizar.py` crea descriptivas CSV, análisis JSON y figuras PNG. La carpeta de salida debe ser nueva. Rechaza lotes incompletos y lotes de validación. No mezcle los estudios de permutaciones y mezcla corta en una misma llamada.

Para regenerar las tablas auxiliares de los análisis originales:

```powershell
.venv\Scripts\python.exe documentar_resultados.py principal
.venv\Scripts\python.exe documentar_resultados.py escalabilidad
```

Estas dos órdenes usan las carpetas originales `analisis1`, `analisis_escalabilidad` y `analisis_cercanos`; no usan automáticamente las salidas con sufijo `_local`. Regeneran sus archivos auxiliares, no modifican los README. `principal` también comprueba las profundidades con BFS. Sin argumento se ejecuta `principal`.

## 5. Ejecutar experimentos nuevos, opcional

Los resultados originales ya están incluidos. Estos comandos son para repetir mediciones, no son necesarios para instalar o jugar. Use nombres de salida nuevos; los ejemplos usan el prefijo `manual_`. Si ya existen, cambie el nombre de forma consistente en las órdenes dependientes.

### Prueba pequeña del circuito experimental

```powershell
.venv\Scripts\python.exe experimentos.py preparar --n 3 --cantidad 2 --metodo mezcla --pasos 4 --semilla 20260911 --salida resultados/manual_prueba.json
.venv\Scripts\python.exe experimentos.py ejecutar --instancias resultados/manual_prueba.json --salida resultados/manual_prueba --validacion --segundos 5
```

Son 32 búsquedas: dos instancias por 16 configuraciones. El lote queda identificado como validación y no sirve como entrada del análisis formal.

### Campaña completa de Puzzle-8

```powershell
.venv\Scripts\python.exe experimentos.py preparar --n 3 --cantidad 1000 --metodo permutacion --semilla 20260911 --salida resultados/manual_instancias_3.json
.venv\Scripts\python.exe experimentos.py ejecutar --instancias resultados/manual_instancias_3.json --salida resultados/manual_experimento1 --experimento 1 --segundos 300 --memoria-mb 1024 --nodos 2000000
.venv\Scripts\python.exe analizar.py comparacion resultados/manual_experimento1 --salida resultados/manual_analisis1
```

La campaña ejecuta **16000 búsquedas secuenciales**: A* y Codicioso con H1–H5 y H6 con pesos 0.25, 0.50 y 0.75. Puede tardar bastante; los 300 segundos son por búsqueda. Ejecute el análisis solo después de que termine correctamente el lote. La selección obtenida se guarda en `resultados/manual_analisis1/analisis.json`; `comparar_algoritmos.py` sigue leyendo las rutas originales descritas en el apartado 4.

### Aplicar H5 a otros tamaños

Para repetir el protocolo uniforme de escalabilidad con la H5 ya seleccionada en los resultados incluidos:

```powershell
foreach ($n in 3..6) {
    .venv\Scripts\python.exe experimentos.py preparar --n $n --cantidad 100 --metodo permutacion --semilla (20260911+$n) --salida "resultados/manual_escala_instancias_$n.json"
    if ($LASTEXITCODE -ne 0) { throw "No se prepararon las instancias N=$n" }
    .venv\Scripts\python.exe experimentos.py ejecutar --instancias "resultados/manual_escala_instancias_$n.json" --salida "resultados/manual_escala_$n" --experimento 2 --heuristica H5 --segundos 5 --memoria-mb 1024 --nodos 2000000
    if ($LASTEXITCODE -ne 0) { throw "El lote N=$n no termino correctamente" }
}
.venv\Scripts\python.exe analizar.py escalabilidad resultados/manual_escala_3 resultados/manual_escala_4 resultados/manual_escala_5 resultados/manual_escala_6 --salida resultados/manual_analisis_escala
```

`--experimento 2` ejecuta únicamente A*. No existe una opción de este ejecutor para una campaña de Codicioso en tableros grandes. Para una instancia individual use `resolver.py --n ... --algoritmo codicioso`.

Para crear casos de mezcla corta en un estudio separado, `preparar` admite `--metodo mezcla --pasos 20`. El protocolo complementario original usa 100 casos por tamaño y semilla `20261911+N`; sus comandos completos e interpretación están en [README_COMPLEMENTARIO.md](README_COMPLEMENTARIO.md). No mezcle esas instancias con las permutaciones en un mismo análisis.

### Archivos generados y límites

Cada ejecución experimental genera `instancias.json`, `resultados.csv` y `metadatos.json` en su carpeta. Las filas se guardan progresivamente. `completo=true` se establece al finalizar todos los tratamientos, aunque algunas búsquedas hayan terminado por límite de recursos.

El ejecutor no reanuda lotes parciales ni sobrescribe carpetas existentes. Una interrupción de la terminal puede dejar `completo=false`; conserve ese lote identificado y utilice otra salida para repetirlo.

La preparación de patrones tiene un límite independiente de 300 segundos por defecto, ajustable con `--segundos-preparacion`. `--max-estados-patron` vale 350000 y `--semilla-orden`, 20260912. Tiempo, RSS y nodos son límites cooperativos. Los estados `limite_tiempo`, `limite_memoria` y `limite_nodos` son desenlaces de la búsqueda, no errores de instalación.

## 6. Pruebas y comprobación de archivos

Suite funcional y estadística:

```powershell
.venv\Scripts\python.exe -m unittest discover -s pruebas -v
```

Validación exhaustiva de las heurísticas de Puzzle-8, con salida separada de la evidencia incluida:

```powershell
.venv\Scripts\python.exe validar_heuristicas.py --salida verificacion/heuristicas_local.json
```

Esta validación recorre todos los estados solubles de Puzzle-8 y puede tardar más que las pruebas unitarias. Comprueba propiedades, no genera las estadísticas del informe.

Prueba gráfica de cinco cuadros, sin ventana interactiva:

```powershell
.venv\Scripts\python.exe juego.py --prueba-grafica --captura verificacion/juego_local.png
```

Verificación de integridad de los lotes originales, guardando un registro nuevo:

```powershell
.venv\Scripts\python.exe -c "from documentar_resultados import verificar_lotes; verificar_lotes('verificacion/integridad_local.json')"
```

También existe `documentar_resultados.py verificar`, pero su salida predeterminada regenera `resultados/verificacion_fase4.json`. El verificador está destinado a los lotes originales del proyecto: una modificación posterior de una fuente experimental puede producir una discrepancia de hashes legítima y no debe ocultarse alterando los registros históricos.

## 7. Ayuda y problemas de ejecución

Para consultar todas las opciones disponibles:

```powershell
.venv\Scripts\python.exe juego.py --help
.venv\Scripts\python.exe resolver.py --help
.venv\Scripts\python.exe experimentos.py preparar --help
.venv\Scripts\python.exe experimentos.py ejecutar --help
.venv\Scripts\python.exe analizar.py --help
.venv\Scripts\python.exe validar_heuristicas.py --help
.venv\Scripts\python.exe documentar_resultados.py --help
```

| Situación | Qué comprobar |
|---|---|
| No se encuentra `python` | Instalar o seleccionar Python 3.13 de 64 bits; probar `py -3.13` si está disponible el lanzador. |
| No se encuentra `.venv\Scripts\python.exe` | Estar en la raíz y haber creado el entorno con `python -m venv .venv`. |
| `ModuleNotFoundError` | Instalar `requirements.txt` con el mismo ejecutable `.venv\Scripts\python.exe` utilizado para lanzar el programa. |
| La política de PowerShell impide activar el entorno | No se requiere activación: use directamente los comandos de esta guía. |
| La carpeta o archivo de salida ya existe | Usar un nombre nuevo; el programa protege los resultados existentes. |
| La ventana no aparece | Lanzar `juego.py` sin `--prueba-grafica`, desde una sesión con pantalla. |
| El asistente o los procesos fallan dentro de un entorno aislado | Ejecutar desde una terminal local normal. El asistente y el ejecutor experimental necesitan crear procesos y canales de comunicación. |
| Acentos o símbolos no se muestran bien en la consola | Añadir `-X utf8` inmediatamente después del ejecutable Python. |

Los programas de análisis no necesitan abrir la ventana del juego. El material docente de `material/` se conserva como referencia y no se ejecuta como punto de entrada de este proyecto.
