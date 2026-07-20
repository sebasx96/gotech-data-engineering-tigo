# Implementación de Apache Airflow

## 1. Objetivo

Apache Airflow se utiliza para orquestar y automatizar el pipeline completo de Ingeniería de Datos.

El flujo implementado ejecuta las capas en el siguiente orden:

```text
CSV Raw
   ↓
Bronze Parquet
   ↓
Silver Parquet
   ↓
Gold PostgreSQL
```

Airflow garantiza que una etapa solo comience cuando la etapa anterior haya terminado correctamente.

---

## 2. Arquitectura en Docker

El ambiente reproducible se levanta mediante Docker Compose y contiene tres servicios separados:

```text
Docker Compose
├── PostgreSQL
│   └── Persistencia de la capa Gold
├── Airflow
│   └── Orquestación Bronze → Silver → Gold
└── Jupyter
    └── Profiling, análisis, KPIs e insights
```

Los servicios se comunican mediante la red interna creada por Docker Compose.

Dentro de los contenedores, PostgreSQL se encuentra disponible mediante:

```text
Host: postgres
Port: 5432
Database: gotech_dw
```

Desde la computadora local se encuentra disponible mediante:

```text
Host: localhost
Port: 5432
```

---

## 3. Servicios

### PostgreSQL

Responsabilidades:

- Persistir las siete tablas analíticas Gold.
- Permitir consultas SQL.
- Servir como fuente para Power BI.
- Mantener los resultados entre reinicios mediante un volumen Docker.

Puerto local:

```text
5432
```

### Airflow

Responsabilidades:

- Ejecutar las transformaciones en el orden correcto.
- Registrar el estado de cada tarea.
- Facilitar la revisión de logs.
- Permitir reintentos.
- Demostrar automatización e idempotencia.

Interfaz:

```text
http://localhost:8080
```

### Jupyter

Responsabilidades:

- Documentación técnica ejecutable.
- Profiling y exploración.
- Cálculo de KPIs.
- Visualizaciones.
- Generación de insights.

Interfaz:

```text
http://localhost:8888/lab
```

---

## 4. DAG implementado

El DAG se encuentra en:

```text
dags/gotech_pipeline.py
```

Identificador:

```text
gotech_bronze_silver_gold
```

El DAG contiene tres tareas:

```text
build_bronze
      ↓
build_and_validate_silver
      ↓
build_and_validate_gold
```

### `build_bronze`

Ejecuta:

```bash
python -m src.ingestion.bronze
```

Responsabilidades:

- Leer los CSV originales.
- Persistir las 18 tablas en Parquet.
- Mantener la estructura por dominio.
- Preparar los datos para Silver.

### `build_and_validate_silver`

Ejecuta:

```bash
python -m src.transformation.silver
```

Responsabilidades:

- Convertir tipos de datos.
- Aplicar reglas de limpieza.
- Tratar fechas cronológicamente inválidas.
- Validar claves primarias.
- Validar claves foráneas.
- Validar rangos y categorías.
- Reconciliar conteos Bronze–Silver.
- Reportar advertencias no bloqueantes.

### `build_and_validate_gold`

Ejecuta:

```bash
python -m src.transformation.gold
```

Responsabilidades:

- Construir las siete tablas analíticas.
- Validar el grano de cada tabla.
- Cargar los resultados en PostgreSQL.
- Crear claves primarias.
- Validar conteos después de la carga.
- Generar exportaciones Parquet adicionales.

---

## 5. Configuración de ejecución

El DAG utiliza:

```text
schedule=None
catchup=False
max_active_runs=1
```

### Justificación

- `schedule=None`: durante el bootcamp el pipeline se ejecuta manualmente para facilitar la demostración.
- `catchup=False`: evita crear ejecuciones históricas innecesarias.
- `max_active_runs=1`: evita que dos ejecuciones completas modifiquen simultáneamente las mismas tablas.

Como mejora futura, el DAG podría programarse diariamente o según la frecuencia de llegada de los archivos fuente.

---

## 6. Manejo de errores y reintentos

Las tareas tienen:

- Un reintento automático.
- Una espera de dos minutos antes del reintento.
- Un tiempo máximo de ejecución.
- Dependencias explícitas.

Si Bronze falla:

```text
Silver no se ejecuta.
Gold no se ejecuta.
```

Si Silver falla:

```text
Gold no se ejecuta.
```

Esto evita publicar datos Gold basados en capas incompletas o inválidas.

---

## 7. Idempotencia

El pipeline fue ejecutado nuevamente desde Airflow y las tres tareas terminaron exitosamente.

La ejecución es idempotente porque:

- Bronze reemplaza los archivos Parquet de salida.
- Silver vuelve a generar sus archivos sin duplicar filas.
- Gold reemplaza las tablas analíticas en PostgreSQL.
- Las claves primarias y los conteos se validan después de cada carga.

Resultado:

```text
build_bronze                  SUCCESS
build_and_validate_silver     SUCCESS
build_and_validate_gold       SUCCESS
```

---

## 8. Validaciones operativas

Airflow detectó correctamente el DAG:

```text
gotech_bronze_silver_gold
```

La comprobación de errores de importación retornó:

```text
No data found
```

En este comando, el resultado significa que no existían errores de importación.

Los tres servicios fueron levantados correctamente:

```text
gotech-postgres   healthy
gotech-jupyter    healthy
gotech-airflow    running
```

Jupyter también logró conectarse a PostgreSQL mediante la red interna de Docker.

---

## 9. Comandos principales

Levantar el ambiente:

```bash
docker compose up -d --build
```

Revisar servicios:

```bash
docker compose ps
```

Ver logs de Airflow:

```bash
docker compose logs airflow --tail 100
```

Listar DAGs:

```bash
docker compose exec airflow airflow dags list --local
```

Revisar errores de importación:

```bash
docker compose exec airflow airflow dags list-import-errors --local
```

Ejecutar el DAG:

```bash
docker compose exec airflow airflow dags trigger gotech_bronze_silver_gold
```

Detener los servicios sin eliminar los volúmenes:

```bash
docker compose down
```

---

## 10. Decisiones técnicas

### Airflow y Jupyter separados

Airflow y Jupyter se ejecutan en contenedores independientes porque cumplen responsabilidades diferentes:

- Airflow automatiza procesos.
- Jupyter soporta exploración y análisis interactivo.

Esto evita mezclar dependencias y responsabilidades.

### Código compartido

Los contenedores montan el código de `src/`, lo que permite reutilizar las mismas transformaciones probadas localmente.

### PostgreSQL compartido

Airflow, Jupyter y las herramientas analíticas consumen la misma instancia de PostgreSQL.

### Desarrollo frente a producción

El modo actual es adecuado para desarrollo, evaluación y demostración.

En producción podrían utilizarse:

- Componentes de Airflow distribuidos.
- Una base PostgreSQL administrada.
- Gestión centralizada de secretos.
- Almacenamiento de objetos.
- Monitoreo y alertas.
- CI/CD.
- Infraestructura de contenedores administrada.

---

## 11. Estado final

```text
PostgreSQL en Docker: completado
Jupyter en Docker: completado
Airflow en Docker: completado
DAG detectado: completado
Errores de importación: 0
Ejecución Bronze: exitosa
Ejecución Silver: exitosa
Ejecución Gold: exitosa
Pipeline completo automatizado: completado
```

El siguiente paso es analizar las tablas Gold, calcular KPIs, construir visualizaciones y preparar el dashboard de Power BI.
