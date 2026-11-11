# Tarjetas Dahua ASM100 y etiquetas TSC TE200

Aplicación de escritorio Python/Tkinter para Windows. El lector utilizado se
comporta como teclado: al escanear escribe en **Lectura / valor manual**.
**La aplicación ya no busca el USB, no pide VID/PID ni necesita detectar el lector
para funcionar.** También permite escribir o pegar un código sin lector conectado.

## Instalar y ejecutar

Descargar el repositorio completo desde **Code > Download ZIP** y extraerlo.
Abrir PowerShell en la carpeta que contiene `main.py`, `config.py` y
`requirements.txt`. No ejecutar los tests como archivos sueltos desde Downloads.

Instalar Python **3.10 o superior** con Tcl/Tk. Ejecutar:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Tkinter viene con Python para Windows. `pywin32` envía etiquetas a la cola de
Windows. `hidapi` y `pyserial` se utilizan solo para diagnóstico o adaptadores
avanzados; la entrada normal por teclado no los importa ni enumera dispositivos.
No instalar otro paquete llamado `hid` junto con `hidapi`.

## Leer y convertir una llave

Mantener la ventana activa y el campo **Lectura / valor manual** enfocado.
Escanear la llave: Site Code, Card Code y vista previa se actualizan sin pulsar
Imprimir y sin requerir una impresora. La lectura nunca imprime automáticamente.

Se admiten dos tipos de entrada:

| Entrada | Site Code | Card Code | Vista previa / etiqueta |
| --- | --- | --- | --- |
| `2518946491` | `47890` | `09366` | `47890:09366` |
| `2519062667` | `35800` | `09622` | `35800:09622` |
| `01025:65874` | `01025` | `65874` | `01025:65874` |

La regla del UID decimal se confirmó con la llave del usuario:

1. `2518946491` en hexadecimal es `962412BB`.
2. Recuperar sus cuatro bytes en orden little endian produce `BB 12 24 96`.
3. Interpretar cada par en big endian: `BB12` = `47890`, `2496` = `9366`.
4. Completar cada campo a cinco dígitos: **`47890:09366`**.

El UID de entrada admite de 1 a 10 dígitos ASCII y valores entre `0` y
`4294967295`. Esta conversión corresponde a esta configuración del lector;
no es una regla universal para cualquier UID o formato Wiegand.

Una entrada que ya contiene `Site:Card` se valida como dos grupos de números
ASCII con exactamente un `:` y **conserva literalmente todos sus ceros**.
No se convierte ese texto a entero ni se cambia su longitud. La conversión
numérica solo se aplica a un UID decimal sin `:`. Se rechazan letras, espacios,
hexadecimal escrito directamente y valores fuera de rango. Una lectura inválida
vacía los campos y la vista previa para no imprimir la lectura anterior.

Enter o Tab finalizan la captura y seleccionan el contenido para reemplazarlo
con la siguiente llave. Si el lector no envía terminador, usar **Limpiar** o
**Preparar lectura** antes de otro escaneo. El primer botón vacía el campo;
el segundo lo enfoca y selecciona sin borrar el dato.

La captura es local a la ventana: no recibe lecturas mientras otra aplicación
tiene el foco. El estado **Entrada por teclado habilitada** indica que la
captura está preparada, no que se haya comprobado una conexión USB física.

## Probar sin impresora

Abrir la aplicación y escanear o pegar `2518946491`. Debe mostrar
**47890**, **09366** y **47890:09366**. Probar también `01025:65874`.
El estado de impresora se muestra por separado y no tapa el resultado de lectura.
No hace falta conectar la TE200 ni pulsar Imprimir para esta prueba.

`main.py --manual` sigue disponible para desactivar adaptadores avanzados,
aunque en el modo teclado predeterminado no se requiere seleccionar un modo
manual especial para escribir o pegar.

## Seleccionar la TSC TE200 e imprimir

1. Instalar su driver oficial en Windows y conectar la impresora por USB.
2. Configurar/calibrar papel, gap y ribbon con la utilidad de TSC según el material.
3. Pulsar **Actualizar impresoras** y seleccionar la cola **TSC TE200**. Si hay
   una única cola con `TE200` en su nombre, se preselecciona. Opcionalmente fijar
   su nombre exacto en `PRINTER_NAME` de `config.py`.
4. Leer una llave o pegar un valor manual. Revisar la vista previa y pulsar
   **Imprimir**: la etiqueta contiene únicamente el texto de la vista previa.

Para listar las colas sin abrir la interfaz:

```powershell
.\.venv\Scripts\python.exe main.py --list-printers
```

La impresión genera bytes TSPL ASCII y los envía con `pywin32` usando
`OpenPrinter`, `StartDocPrinter` con tipo `RAW`, `StartPagePrinter`,
`WritePrinter`, `EndPagePrinter`, `EndDocPrinter` y `ClosePrinter`.
Gestiona escrituras parciales y aborta el documento si falla.

**Windows aceptó el trabajo** confirma el envío a la cola, no la salida física.
Windows puede mantener una cola disponible con USB desconectado. Se rechazan
estados de error conocidos; revisar la cola y la impresora antes de reintentar
para evitar duplicados. No hay reintentos automáticos.

### Etiqueta configurable

En `config.py`, editar `LABEL`: ancho, alto y gap en mm; X/Y en puntos;
fuente bitmap TSPL de `1` a `8`; escalas horizontal/vertical entre `1` y `10`.
Los valores iniciales son 50×30 mm, gap 2 mm, posición 30/30. La TE200 es de
203 dpi. Verificar que el texto quepa en el material, especialmente con códigos
largos o escalas grandes. La vista previa representa contenido, no una imagen
a escala de la etiqueta.

Ejemplo de comandos para la llave confirmada:

```text
SIZE 50 mm,30 mm
GAP 2 mm,0 mm
DIRECTION 1
REFERENCE 0,0
CLS
TEXT 30,30,"3",0,1,1,"47890:09366"
PRINT 1,1
```

Se envían con CRLF, sin `END` porque no se declara un programa BASIC.

## Adaptadores avanzados y diagnóstico opcional

El modo normal es `READER.mode="keyboard"`. No necesita configuración USB.
Para otras unidades/protocolos se conservan adaptadores separados en `reader.py`:

- `auto`: enumera HID/COM por VID/PID y exige una interfaz no ambigua.
- `serial`: puerto COM, velocidad configurable, 8N1, timeout de 200 ms.
- `hid_text`: reportes ASCII documentados, tamaño/offset configurables, sin
  comandos propietarios de activación. No interpreta HID binario.
- `sdk`: módulo puente propio para un SDK documentado por el fabricante.
- `manual`: no inicia adaptadores; se sigue pudiendo escribir o pegar.

Solo para esos casos, ejecutar `main.py --diagnose` y comparar el inventario
con/sin dispositivo. Obtener IDs reales en Administrador de dispositivos;
configurar `vendor_id`, `product_id` y, de ser necesario, `serial_number`,
`interface_number` o `port`. No usar valores de ejemplo ni cambiar drivers
con Zadig. Serie/HID texto esperan tramas ASCII terminadas en CR, LF o CRLF,
con límite `max_frame_length`; HID elimina el offset inicial y NUL final.

Para un SDK, configurar `sdk_module` con un módulo del proyecto que exponga
`open_reader(config)`. Debe devolver un objeto con
`read_card(timeout_ms=200)` (texto decimal, Site:Card o `None`) y `close()`.
Las llamadas ocurren en un hilo. Respetar el timeout y lanzar una excepción
ante desconexión. No se incluye SDK propietario ni se presupone que el NetSDK
para controladores de red sirva para el emisor USB.

## Arquitectura y pruebas

- `main.py`: inicio y opciones de diagnóstico/listado.
- `gui.py`: Tkinter, captura por teclado, vista previa y eventos de E/S por cola.
- `reader.py`: conversión del UID, validación y adaptadores separados.
- `printer.py`: generación TSPL y cola RAW de Windows.
- `config.py`: parámetros del lector, etiqueta y cola.
- `tests/`: validación, conversión, lectura, lógica GUI y spooler simulado.

Ejecutar desde la carpeta principal del proyecto:

```powershell
.\.venv\Scripts\python.exe -m compileall -q main.py gui.py reader.py printer.py config.py tests
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas de lógica GUI usan variables Tcl reales sin necesitar pantalla.
Las pruebas simuladas no sustituyen la lectura física, la GUI en Windows ni
la impresión en la TE200. La prueba física de impresión está pendiente.

Fuentes de los dispositivos:
[ficha oficial ASM100](https://materialfile.dahuasecurity.com/uploads/cpq/prm-os-srv-res/smart/datasheetzipfiles/DHI-ASM100_datasheet_20241101.pdf),
[configuración DahuaWiki](https://dahuawiki.com/Access_Control/How_To_Setup_DHI_ASM100),
[manual oficial TE200](https://fs.tscprinters.com/system/files/31-0650003-00_te200_user_manual_en_c.pdf),
[manuales TSPL](https://apac.tscprinters.com/en/downloads).
La ficha USB del ASM100 no especifica su protocolo; la entrada por teclado y
la conversión descritas aquí se basan en la prueba y el ejemplo del usuario.
