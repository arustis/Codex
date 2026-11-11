# Tarjetas y Etiquetas

Aplicación de escritorio Python/Tkinter para Windows para leer tarjetas e imprimir
etiquetas. Admite lectores que escriben como teclado en **Lectura / valor manual**
e impresoras de etiquetas compatibles con TSPL instaladas en Windows. No depende
de una marca de lector; la conversión de UID debe coincidir con la configuración
del equipo. El lector probado es un Dahua ASM100; la impresión prevista utiliza
una TSC TE200.
**La aplicación ya no busca el USB, no pide VID/PID ni necesita detectar el lector
para funcionar.** También permite escribir o pegar un código sin lector conectado.

## Instalar en Windows desde el escritorio

La compilación de GitHub genera **TarjetasYEtiquetas-Setup-1.1.0.exe** para
Windows 10/11 de 64 bits. No se necesita instalar Python en la computadora de uso.

1. Abrir la ejecución exitosa **Instalador Windows** en la pestaña **Actions**
   del repositorio y descargar el artefacto **Tarjetas-y-Etiquetas-Windows-x64**.
   Es necesario iniciar sesión en GitHub para descargar los artefactos.
2. Extraer el ZIP y abrir `TarjetasYEtiquetas-Setup-1.1.0.exe`.
3. Aceptar la solicitud de administrador para instalar en
   `C:\Program Files\Tarjetas y Etiquetas` (si Windows está en C).
4. Dejar seleccionada **Crear un acceso directo en el escritorio** y finalizar.
5. Abrir **Tarjetas y Etiquetas** desde el escritorio con doble clic. No aparece
   una consola y no se necesitan Python, PowerShell ni archivos del proyecto.

El instalador incluye el ejecutable y sus dependencias. No mover únicamente
el `.exe` fuera de su carpeta instalada. Para quitarlo, usar **Configuración >
Aplicaciones > Tarjetas y Etiquetas > Desinstalar**. La aplicación se ejecuta
como usuario normal; solo el instalador requiere permisos de administrador.
El driver de la impresora se instala por separado cuando se pase a impresión.

El instalador aún no tiene firma digital: Windows puede indicar editor
desconocido. Usar el artefacto de la ejecución correspondiente al commit del PR.

## Ejecutar desde el código fuente (desarrollo)

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

### Hexadecimal del UID

Debajo de la lectura se muestra **Hexadecimal (UID)**, un campo de solo lectura
que se actualiza automáticamente. Usa los cuatro bytes en el mismo orden de
la conversión Site/Card, concatenados, en mayúsculas y sin espacios ni `0x`.
Por ejemplo, `2518946491` muestra **`BB122496`** y `1` muestra **`01000000`**.
Se conservan los ocho dígitos, incluidos los ceros.

Si se ingresa directamente `Site:Card`, no se dispone del UID original y el
campo hexadecimal queda vacío. También se vacía al limpiar o recibir un dato
inválido. El hexadecimal es informativo: la etiqueta sigue conteniendo solo
el texto de la vista previa, como `47890:09366`.

## Probar sin impresora

Abrir la aplicación y escanear o pegar `2518946491`. Debe mostrar
**47890**, **09366** y **47890:09366**. Probar también `01025:65874`.
El estado de impresora se muestra por separado y no tapa el resultado de lectura.
No hace falta conectar la TE200 ni pulsar Imprimir para esta prueba.

`main.py --manual` sigue disponible para desactivar adaptadores avanzados,
aunque en el modo teclado predeterminado no se requiere seleccionar un modo
manual especial para escribir o pegar.

## Seleccionar una impresora de etiquetas e imprimir

1. Instalar el driver oficial de una impresora compatible con TSPL en Windows
   y conectar la impresora (por ejemplo, una TSC TE200 por USB).
2. Configurar/calibrar papel, gap y ribbon con la utilidad del fabricante según el material.
3. Pulsar **Actualizar impresoras** y seleccionar su cola de Windows. Si hay
   una única cola con `TE200` en su nombre, se preselecciona. Opcionalmente fijar
   su nombre exacto en `PRINTER_NAME` de `config.py`.
4. Leer una llave o pegar un valor manual. Revisar la vista previa y pulsar
   **Imprimir**: la etiqueta contiene únicamente el texto de la vista previa.

El nombre de la cola puede ser cualquiera. El envío RAW requiere que la
impresora entienda TSPL; instalar un driver no agrega ese lenguaje a modelos
que no lo admiten.

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

### Configurar etiqueta y corregir texto cortado / saltos

En el ejecutable, pulsar **Configurar etiqueta**. No hace falta editar Python
ni reinstalar para cambiar las medidas. Indicar:

La versión 1.1.0 parte del rollo confirmado por el usuario: **25 mm de ancho ×
12 mm de alto, separación de 3 mm, TE200 a 203 dpi**. Usa fuente 2, escala 1×1
y posición X=34, Y=38 puntos para centrar el código habitual de 11 caracteres.
Esos valores se pueden ajustar si cambia el rollo.

- **Ancho** del adhesivo de izquierda a derecha, en mm (sin el soporte).
- **Alto** del adhesivo en el sentido de avance del rollo, sin la separación.
- **Separación / GAP** entre dos adhesivos, en mm.
- **Resolución** real del equipo: la TE200 usa **203 dpi**, equivalentes a
  8 puntos por mm. Los equipos de 300 dpi usan 12 puntos por mm.
- **Posición X/Y** en puntos desde el origen del texto; fuente y escalas.
- **Orientación**: `0` normal (predeterminada), `1` invertida.

Los ajustes se guardan por usuario en
`%LOCALAPPDATA%\TarjetasYEtiquetas\label.json`, fuera de Program Files. Se
conservan al cerrar y al actualizar el programa; no requieren administrador.
Se admiten coma o punto decimal en las medidas. Un archivo inválido se informa
y se reemplaza solo al guardar nuevos valores válidos desde el diálogo.

Antes de imprimir, la aplicación estima el tamaño del texto con las fuentes
bitmap TSPL2. Si queda fuera del ancho o alto configurados, cancela el envío
y pide reducir fuente/escala o ajustar posición/medidas. No recorta ni omite
el Site Code para hacerlo caber. La vista previa principal sigue mostrando
el contenido textual, no un plano a escala.

Cada trabajo envía las medidas elegidas, orientación sin espejo, origen 0,0,
SHIFT 0,0 y OFFSET 0, para evitar heredar desplazamientos del trabajo anterior.
Se envía una sola etiqueta mediante `PRINT 1,1`, con CRLF y sin `END` porque
no se está declarando un programa BASIC. El driver no corrige las dimensiones
del TSPL RAW: las medidas de este diálogo deben coincidir con el rollo.

Si aparecen etiquetas en blanco entre impresiones:

1. Medir el adhesivo y el espacio por separado y corregir los ajustes.
2. En la utilidad de TSC, seleccionar el sensor **GAP** y calibrarlo para ese
   rollo. La calibración puede avanzar varias etiquetas; no se ejecuta
   automáticamente en cada impresión.
3. Pulsar **FEED** en la impresora: debe avanzar una etiqueta y detenerse en
   la separación. Si también salta etiquetas, revisar calibración, guías y sensor.
4. Probar una sola impresión y ajustar X/Y si hace falta. No aumentar el alto
   para corregir una posición desplazada.

La validación de software no puede detectar un rollo de otras medidas ni una
calibración incorrecta; la comprobación física sigue siendo necesaria.

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

## Generar el instalador (desarrollo)

PyInstaller debe compilar en Windows x64; no se genera un ejecutable Windows
con PyInstaller desde Linux. El workflow `.github/workflows/windows-installer.yml`
se ejecuta en cada PR hacia `main`, al actualizar `main` y manualmente desde
Actions una vez que el workflow está en la rama predeterminada. Publica el
instalador como artefacto durante 90 días; descargarlo y conservarlo antes de
su vencimiento. No crea una release ni cambia `main` automáticamente.

Para compilar localmente en Windows, instalar Inno Setup 6 y ejecutar desde
la raíz del repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\scripts\build_windows.ps1 -PythonExe .\.venv\Scripts\python.exe
```

El resultado queda en `dist/installer/`. La carpeta de distribución está en
`dist/TarjetasYEtiquetas/`. `APP_VERSION` en `config.py` determina la versión.
Los valores predeterminados de Python se integran en el bundle; editar
`config.py` requiere recompilar. Los ajustes de etiqueta se editan y guardan
desde la GUI sin recompilar.

El workflow comprueba sintaxis y pruebas en Windows, compila con PyInstaller,
genera el instalador con Inno Setup, lo instala en una carpeta temporal y
comprueba el acceso directo. Luego ejecuta el binario instalado con una opción
interna de autoprueba para verificar Tkinter, extensiones y conversión del UID
sin enviar trabajos a la impresora. Esto no sustituye la prueba física de la TE200.
