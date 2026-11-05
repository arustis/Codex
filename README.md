# Tarjetas Dahua ASM100 y etiquetas TSC TE200

Aplicación de escritorio Python/Tkinter para Windows. Mantiene los códigos como
texto: `01025:65874` se divide en `01025` y `65874`, y la etiqueta contiene
únicamente `01025:65874`. Nunca se convierte un código a entero. La impresión
solo ocurre al pulsar **Imprimir**.

## Estado y alcance del lector

**La lectura de una unidad ASM100 real necesita verificar su interfaz/protocolo
en Windows. No se ha probado hardware físico en este entorno.** La aplicación
incluye diagnóstico, adaptadores y modo manual; no incluye un SDK propietario
Dahua ni afirma que el ASM100 sea un teclado.

Fuentes consultadas el 5 de noviembre de 2026:

- [Ficha oficial DHI-ASM100](https://materialfile.dahuasecurity.com/uploads/cpq/prm-os-srv-res/smart/datasheetzipfiles/DHI-ASM100_datasheet_20241101.pdf):
  USB 2.0, sin instalación de driver, Mifare, integración con SmartPSS-AC/DSS.
  No identifica clase USB, VID/PID, protocolo ni formato `Site:Card`.
- [Configuración ASM100 en DahuaWiki](https://dahuawiki.com/Access_Control/How_To_Setup_DHI_ASM100):
  SmartPSS activa el emisor desde el campo Card No. Esto demuestra integración
  con su software; no demuestra emulación de teclado ni una API pública.
- [Manual oficial TE200](https://fs.tscprinters.com/system/files/31-0650003-00_te200_user_manual_en_c.pdf):
  admite texto y comandos TSPL/TSPL2.
- [Manuales TSPL/TSPL2 de TSC](https://apac.tscprinters.com/en/downloads).

El formato de entrada admitido es texto ASCII `números:números`. No se deduce
Site Code a partir de un UID hexadecimal/decimal ni se presupone un formato
Wiegand. Si el equipo entrega un UID u otro formato, hace falta conocer su
regla de conversión; no existe una división universal correcta.

## Instalación en Windows

Instalar Python **3.10 o superior**, incluyendo Tcl/Tk y el lanzador `py`.
Desde PowerShell, en esta carpeta:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

No hace falta activar el entorno. Tkinter viene con el instalador de Python;
`pywin32` permite imprimir; `hidapi` enumera HID y permite leer HID genérico;
`pyserial` enumera y lee puertos COM. No instalar un paquete llamado `hid`
además de `hidapi`: pueden interferir entre sí.

## Detectar el lector antes de configurar la lectura

1. Con el lector desconectado, ejecutar y guardar visualmente el resultado:

   ```powershell
   .\.venv\Scripts\python.exe main.py --diagnose
   ```

2. Conectarlo y repetir. Comparar las interfaces nuevas. En Administrador de
   dispositivos, usar **Ver > Dispositivos por conexión** y consultar
   **Propiedades > Detalles > Id. de hardware** (`VID_xxxx&PID_yyyy`). Si no
   aparece en HID/COM, consultar también dispositivos USB y tarjetas inteligentes:
   la enumeración de la aplicación no cubre todas las clases USB.
3. En `config.py`, poner los IDs **reales**, por ejemplo `vendor_id=0x1234`,
   `product_id=0x5678` (estos valores son ilustrativos, no corresponden al ASM100).
   Si hay varios dispositivos iguales, configurar `serial_number`. Si hay varias
   interfaces HID, configurar `interface_number`. Reiniciar la aplicación.
4. Elegir el método según evidencia:

   | Resultado | Método |
   | --- | --- |
   | HID con `usage_page=1`, `usage=6`, y escribe el código en Bloc de notas | `keyboard` o `auto` |
   | Puerto COM coincidente | `serial`, puerto y baudrate confirmados |
   | HID genérico con protocolo de texto ASCII documentado | `hid_text`, tamaño y offset confirmados |
   | HID binario, USB propietario u otra clase | Obtener protocolo/SDK Dahua e implementar el puente `sdk` |

`auto` identifica por VID/PID y serie; elige teclado según uso HID o COM según
la enumeración. No abre cualquier teclado conectado ni interpreta automáticamente
HID binario. Con varias interfaces posibles pide configuración explícita.
Sin VID/PID avisa que el lector no está identificado; el modo manual sigue disponible.

### Si funciona como teclado HID

Probar primero en Bloc de notas con una tarjeta conocida. Confirmar que entrega
literalmente `01025:65874` y termina con **Enter** o **Tab**. Verificar también
la distribución del teclado de Windows: debe producir `:` correctamente.

En la aplicación, mantener la ventana activa y enfocar **Lectura / valor manual**.
La secuencia USB entra automáticamente en ese campo, se separa y actualiza la
vista previa sin tipeo humano. Enter/Tab finalizan la captura y seleccionan el
texto para que la siguiente tarjeta lo reemplace. **Limpiar**, **Imprimir** y
**Reconectar lector** devuelven el foco al campo de lectura.

La captura es local a la ventana, sin hooks globales: no recibe tarjetas mientras
otra aplicación tiene el foco. Los eventos de teclado normales de Tkinter no
identifican el dispositivo de origen; el teclado humano puede escribir en el
mismo campo. La presencia se revisa cada dos segundos; no equivale a verificar
que una tarjeta haya sido leída correctamente. Al reconectar, usar el botón
**Reconectar lector**.

### Serie o HID genérico

Los adaptadores de texto esperan tramas ASCII con terminador CR, LF o CRLF;
pueden recibir una trama en varios bloques. Rechazan bytes no ASCII, códigos
inválidos y tramas de más de `max_frame_length` bytes. Una trama demasiado larga
se descarta por completo hasta su terminador.

En serie se abre el COM seleccionado con 8N1 y `baudrate` configurable, lectura
con timeout de 200 ms. En HID se utiliza `hid_report_size`, se quitan
`hid_payload_offset` bytes iniciales de cada reporte y relleno NUL final. El
offset debe incluir report ID si lo hay. **Esto solo sirve si el protocolo real
es texto con ese encuadre.** No envía comandos de activación ni decodifica UID
binario. No usar Zadig ni cambiar drivers para probar este adaptador.

### Integración de un SDK propietario

Si la unidad requiere un SDK, solicitar a Dahua/distribuidor el SDK del emisor
USB ASM100, sus headers, DLL y ejemplo, compatibles con la arquitectura de
Python. El NetSDK para controladores de red no debe asumirse compatible con
este periférico USB.

Crear dentro del proyecto un módulo puente, configurar `mode="sdk"` y
`sdk_module="mi_puente_dahua"`. El contrato **definido por esta aplicación**, no
una API oficial de Dahua, es:

```python
# mi_puente_dahua.py (esquema, no implementación del SDK)
def open_reader(config):
    # Inicializar el SDK documentado; devolver un objeto con:
    # read_card(timeout_ms=200) -> str completa "01025:65874" o None
    # close() -> liberar el SDK/dispositivo
    ...
```

Las llamadas se realizan en un hilo de lectura. `read_card` debe respetar el
timeout y lanzar una excepción si pierde la conexión. El puente debe proporcionar
el texto exacto usando reglas de conversión confirmadas. La aplicación valida
ese texto antes de mostrarlo. No se distribuye un puente ficticio: completar
esta integración depende del SDK/protocolo y la prueba del equipo concreto.

## Seleccionar la TSC TE200

1. Instalar el driver oficial de TSC, conectar por USB y comprobar en Windows
   que la cola está disponible. Calibrar etiqueta/gap y configurar papel/ribbon
   con la utilidad de TSC según el material.
2. Listar los nombres exactos:

   ```powershell
   .\.venv\Scripts\python.exe main.py --list-printers
   ```

3. Elegir la cola en **Impresora Windows**. **Actualizar impresoras** vuelve a
   enumerarlas. Si hay una única cola con `TE200` en el nombre se preselecciona.
   Opcionalmente fijar el nombre exacto en `PRINTER_NAME` de `config.py`.

`printer.py` genera bytes ASCII TSPL y usa `OpenPrinter`, `StartDocPrinter` con
`RAW`, `StartPagePrinter`, `WritePrinter`, `EndPagePrinter`, `EndDocPrinter` y
`ClosePrinter`. Gestiona escrituras parciales y aborta el documento si falla.
No imprime mediante el renderizado GDI del driver.

Windows puede conservar una cola instalada aun con USB desconectado. Se rechazan
estados de error conocidos, pero el spooler puede aceptar y retener trabajos
sin detectar inmediatamente la desconexión. **«Windows aceptó el trabajo» no
confirma impresión física.** Ante un fallo, revisar la cola antes de reintentar
para evitar duplicados. La aplicación no reimprime automáticamente.

### Tamaño y TSPL

Editar `LABEL` en `config.py`: ancho, alto, gap en milímetros; X/Y en puntos;
fuente bitmap `1` a `8`; escala horizontal/vertical de `1` a `10`. Los valores
50×30 mm, gap 2 mm y X/Y 30 son iniciales ajustables. La TE200 tiene 203 dpi.
Comprobar que el texto quepa en el material, especialmente con códigos largos
o escalas grandes. La vista previa representa **el contenido textual**, no la
posición ni una simulación a escala.

Ejemplo generado por defecto:

```text
SIZE 50 mm,30 mm
GAP 2 mm,0 mm
DIRECTION 1
REFERENCE 0,0
CLS
TEXT 30,30,"3",0,1,1,"01025:65874"
PRINT 1,1
```

Se envía con CRLF y sin `END`: `PRINT 1,1` imprime una etiqueta; no estamos
declarando un programa BASIC que necesite `END`. El único texto dibujado es
`01025:65874`, sin títulos, códigos de barras ni prefijos.

## Probar lectura sin imprimir

Iniciar `main.py`, configurar el lector como se indicó y acercar una tarjeta.
Comprobar **Site Code = 01025**, **Card Code = 65874** y vista previa
**01025:65874**. No presionar **Imprimir**: leer nunca envía un trabajo.
Una lectura inválida borra la vista previa para evitar imprimir el valor anterior.

## Probar impresión con un valor manual, sin lector

```powershell
.\.venv\Scripts\python.exe main.py --manual
```

También se puede marcar **Modo de prueba manual (sin lector)** en la ventana.
Escribir o pegar `01025:65874` en **Lectura / valor manual**. Comprobar ambos
campos y la vista previa, seleccionar la TSC TE200 y pulsar **Imprimir**. No se
exige la presencia del lector. El botón **Limpiar** vacía la captura y los campos.

Para generar TSPL sin imprimir ni depender de Windows:

```powershell
.\.venv\Scripts\python.exe -c "from printer import build_tspl; print(build_tspl('01025:65874').decode('ascii'))"
```

Entradas como `01025:`, `:65874`, `1:2:3`, letras, espacios, dígitos Unicode o
saltos de línea en el valor manual son inválidas. Los terminadores de transporte
se eliminan únicamente en los adaptadores de lectura, antes de validar.

## Arquitectura y pruebas

- `main.py`: inicio y comandos de diagnóstico/listado.
- `gui.py`: widgets, modo manual, vista previa; eventos de E/S por cola al hilo Tk.
- `reader.py`: validación, inventario, selección y adaptadores independientes.
- `printer.py`: TSPL y spooler de Windows.
- `config.py`: parámetros inmutables del lector, etiqueta y cola.
- `tests/`: pruebas sin hardware del formato, detección y spooler simulado.

```powershell
.\.venv\Scripts\python.exe -m compileall -q main.py gui.py reader.py printer.py config.py tests
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas simuladas verifican los bytes y errores del spooler; no reemplazan
la prueba de la DLL, USB, GUI Windows ni de la salida física. Dependiendo del
entorno, las pruebas de GUI requieren una pantalla y Tcl/Tk instalados.

### Verificación realizada en este desarrollo

En Linux se verificó la sintaxis de todos los archivos Python, se ejecutaron 25
pruebas automatizadas exitosas y el diagnóstico real con `hidapi`/`pyserial`
instalados devolvió listas HID/COM vacías, sin errores. Se comprobó además la
generación exacta de TSPL con `01025:65874` y el mensaje al intentar listar colas
fuera de Windows. No fue posible abrir Tkinter por falta de pantalla gráfica;
quedan pendientes la GUI en Windows, el dispositivo ASM100 y la salida física
de la TE200.
