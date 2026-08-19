# Hogar de los Alpes — Modelos Context Mapper (CML)

Esta carpeta contiene los modelos de arquitectura de la solución **Hogar de los Alpes** escritos en el
DSL de [Context Mapper](https://contextmapper.org/):

- `Context_AsIs.cml` — Context Map del estado actual (monolito, `AS_IS`).
- `Context_ToBe.cml` — Context Map del estado objetivo (arquitectura no monolítica, `TO_BE`).

Los archivos generados (diagramas Graphviz `.gv`, imágenes, etc.) se ubican en la carpeta `src-gen/`.

- `Context_AsIs.png` — Imágen del Context Map del estado actual en formato PNG.
- `Context_ToBe.png` — Imágen del Context Map del estado objetivo en formato PNG.
---

## 1. Requisitos previos

| Requisito | Descripción |
|-----------|-------------|
| **Java (JDK) 17+** | Context Mapper se ejecuta sobre la JVM. Verifica con `java -version`. |
| **Visual Studio Code** | Editor donde se instala la extensión. |
| **Graphviz** (opcional) | Necesario para renderizar los diagramas `.gv` como imágenes. |

### Instalar Java

Descarga e instala un JDK 17 o superior (por ejemplo [Temurin / Eclipse Adoptium](https://adoptium.net/)).

Verifica la instalación:

```powershell
java -version
```

Debe mostrar una versión `17` o superior. Si el comando no se reconoce, asegúrate de que la
variable de entorno `JAVA_HOME` esté configurada y que `%JAVA_HOME%\bin` esté en el `PATH`.

### Instalar Graphviz (opcional, para ver diagramas)

```powershell
winget install Graphviz.Graphviz
```

Reinicia la terminal (o VS Code) para que el comando `dot` quede disponible en el `PATH`.

---

## 2. Instalar la extensión de Context Mapper

### Opción A — Desde la interfaz de VS Code

1. Abre **VS Code**.
2. Ve a la vista de **Extensiones** (`Ctrl` + `Shift` + `X`).
3. Busca **`Context Mapper`** (publicador *Context Mapper*).
4. Presiona **Install**.

### Opción B — Desde la paleta de comandos

1. Abre la paleta de comandos (`Ctrl` + `Shift` + `P`).
2. Ejecuta: `Extensions: Install Extensions`.
3. Busca **`Context Mapper`** e instálala.

### Opción C — Desde la terminal

```powershell
code --install-extension contextmapper.context-mapper-vscode-extension
```

Tras instalar, **recarga VS Code** si se solicita. La extensión activa el resaltado de sintaxis,
la validación y los comandos de generación para los archivos `.cml`.

---

## 3. Abrir y validar los modelos

1. Abre esta carpeta en VS Code (`File > Open Folder...` y selecciona la raíz del proyecto).
2. Abre `Context_AsIs.cml` o `Context_ToBe.cml`.
3. La extensión valida el archivo automáticamente:
   - Si hay errores de sintaxis, aparecen subrayados en el editor y listados en la
     pestaña **Problems** (`Ctrl` + `Shift` + `M`).
   - Si no hay errores, el modelo está listo para generar diagramas.

---

## 4. Generar diagramas a partir de los `.cml`

Context Mapper puede transformar los modelos en diagramas Graphviz (`.gv`) e imágenes PNG.

1. Abre el archivo que quieras procesar, por ejemplo `Context_ToBe.cml`.
2. Haz clic derecho sobre el editor **o** abre la paleta de comandos (`Ctrl` + `Shift` + `P`).
3. Ejecuta el comando de generación, por ejemplo:
   - **`Context Mapper: Generate Graphical Context Map`**
4. El resultado se guarda en la carpeta **`src-gen/`** (por ejemplo `Context_ToBe_ContextMap.png`).

> La extensión también ofrece otros generadores (PlantUML, Service Cutter, etc.) accesibles
> desde el mismo menú contextual / paleta de comandos.


## Referencias

- Sitio oficial: <https://contextmapper.org/>
- Documentación del DSL: <https://contextmapper.org/docs/language-reference/>
- Extensión en el Marketplace: <https://marketplace.visualstudio.com/items?itemName=contextmapper.context-mapper-vscode-extension>
