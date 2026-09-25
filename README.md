# Intérprete Tree-Walk de Lox (Entrega Parcial)

Trabajo Práctico para la materia **Lenguajes y Compiladores (75.14 / 95.57) — FIUBA**.

Este repositorio contiene la implementación incremental de un intérprete *Tree-Walk* para el lenguaje de programación **Lox**, siguiendo y adaptando los conceptos de diseño de compiladores e intérpretes (basado en *Crafting Interpreters*, Robert Nystrom) con arquitectura modular en Python 3.12 y empaquetado con `uv`.

---

## 🏛️ Arquitectura del Sistema

El pipeline de ejecución se divide en cuatro fases principales desacopladas:

```mermaid
graph LR
    Source[Código Fuente .lox] --> Scanner[Scanner / Lexer]
    Scanner --> Tokens[Tokens]
    Tokens --> Parser[Parser Descenso Recursivo]
    Parser --> AST[AST Nodos Expr / Stmt]
    AST --> Resolver[Resolver Análisis Semántico]
    Resolver --> Scopes[Resolución de Scopes y Distancias]
    Scopes --> Interpreter[Interpreter Tree-Walk]
    Interpreter --> Runtime[Entorno / Consola / Errores]
```

1. **Análisis Léxico (`lox.syntax.scanner`)**:
   - Transforma el flujo de texto en una secuencia de objetos `Token`.
   - Soporta operadores aritméticos (`+`, `-`, `*`, `/`, `%`), de comparación (`==`, `!=`, `<`, `<=`, `>`, `>=`), lógicos (`!`, `and`, `or`), literales numéricos, cadenas con secuencias de escape y palabras reservadas.
   - Rastreo de número de línea y columna para diagnósticos precisos.

2. **Árbol de Sintaxis Abstracta y Análisis Sintáctico (`lox.syntax.ast` y `lox.syntax.parser`)**:
   - Nodos fuertemente tipados organizados en jerarquías de `Expr` y `Stmt`.
   - Parser por descenso recursivo que modela precedencias y asociatividad estándar.
   - Desazucarado sintáctico del bucle `for` hacia sentencias `while` contenidas en bloques léxicos.
   - Recuperación ante errores sintácticos mediante *Panic Mode Recovery* sincronizando en delimitadores de sentencias.

3. **Análisis Semántico y Resolución de Ámbitos (`lox.semantics.resolver`)**:
   - Pase previo a la ejecución que visita el AST calculando la distancia léxica estática (`depth`) de variables locales y vinculaciones a funciones.
   - Soluciona de raíz el *Closure Bug* garantizando que las funciones capturen exactamente el ámbito léxico donde fueron definidas.
   - Validación temprana de errores semánticos:
     - Detección de lectura de variables locales en su propio inicializador (`var a = a;`).
     - Detección de declaraciones duplicadas dentro de un mismo bloque local.
     - Detección de sentencias `return` en el nivel superior fuera de cualquier función.

4. **Ejecución en Tiempo de Ejecución (`lox.runtime`)**:
   - `Interpreter`: Implementa los patrones Visitor de `ExprVisitor` y `StmtVisitor`.
   - `Environment`: Tabla de símbolos jerárquica con enlace al entorno envolvente (`enclosing`) y soporte de acceso directo por distancia (`get_at` / `assign_at`).
   - Semántica estricta de *truthiness* de Lox: únicamente `nil` y `false` son falsos; `0` y `""` son verdaderos.
   - Control de flujo por excepciones para desenrollar la pila en llamadas y sentencias `return` (`LoxReturnException`).
   - Invocables de usuario (`LoxFunction`) y funciones nativas del sistema (`ClockFunction` para `clock()`).

---

## 🚀 Requisitos e Instalación

Se requiere Python 3.12 o superior y [`uv`](https://docs.astral.sh/uv/) como gestor de entorno:

```sh
# Clonar el repositorio
git clone <url-del-repo>
cd LyC-TP

# Instalar dependencias del proyecto (incluye pytest)
uv sync
```

---

## 💻 Uso de la Interfaz CLI (`pylox`)

El punto de entrada principal es `pylox` (o `python3 -m lox.cli`):

### 1. Modo Archivo (Script)
Ejecuta un programa completo desde un archivo `.lox`:
```sh
uv run pylox script.lox
```

### 2. Modo Interactivo (REPL)
Inicia una consola interactiva línea a línea que evalúa tanto sentencias como expresiones individuales:
```sh
uv run pylox
```

### 3. Modos de Diagnóstico e Inspección
- **Modo Scanner (Tokens):**
  ```sh
  uv run pylox --scanner script.lox
  ```
- **Modo Parser (Árbol Sintáctico AST en formato S-Expressions):**
  ```sh
  uv run pylox --ast script.lox
  ```

---

## 🧪 Validación y Tests

### Tests Unitarios Propios
El proyecto cuenta con una amplia suite de pruebas unitarias cubriendo casos límite, precedencias, errores léxicos, sintácticos, semánticos y de runtime:

```sh
uv run pytest
```
> Resultado actual: **88 tests pasando**.

### Suite de Pruebas Oficial de la Cátedra (`real-tests`)
Para ejecutar la suite de compatibilidad provista por los docentes:

```sh
python3 ../Practica/plox/real-tests/script.py "uv run pylox"
```
Comprende la verificación de:
- `0-simple.lox` (Aritmética, cadenas, lógica booleana)
- `1-flow.lox` (Bifurcaciones `if/else`, bucles `while`, bucles `for`)
- `2-functions.lox` (Ámbitos, recursión de Fibonacci, funciones de orden superior, closures y *Closure Bug*)
- `3-minsky.lox` (Simulación completa de una Minsky Machine con registro y salto condicional)
- `4-fizzbuzz.lox` (Bucles, módulo `%` y acumuladores de texto)

> Salida esperada: **`| Todo OK |`**.

---

## 📊 Benchmarks de Rendimiento

Se incluye una suite de pruebas de rendimiento automatizada en `benches/`:

```sh
uv run python benches/benchmark.py 3
```

### Resultados Obtenidos (Promedios)

| Benchmark | Descripción | Promedio (s) | Mínimo (s) | Máximo (s) |
| :--- | :--- | :---: | :---: | :---: |
| **`fibonacci.lox`** | Cálculo recursivo de `fib(25)` con desenrollado intensivo de stack | **0.5844 s** | 0.5388 s | 0.6170 s |
| **`loop.lox`** | Bucle de 50.000 iteraciones con mutación de variables y módulo | **0.1536 s** | 0.1510 s | 0.1559 s |
| **`minsky.lox`** | Simulación de máquina de Minsky (1.500 evaluaciones completas) | **3.7478 s** | 3.7393 s | 3.7540 s |

### Conclusiones de Rendimiento
- La resolución estática de variables (`Resolver`) reduce significativamente el costo de búsqueda en cadenas de entornos en tiempo de ejecución al permitir saltos indexados directos (`get_at`).
- El modelo *Tree-Walk* ofrece claridad conceptual y semántica exacta para la entrega parcial, sentando la base de validaciones semánticas requeridas para la futura compilación a bytecode y máquina virtual de la Entrega Final.
