# Blueprint del proyecto

## Objetivo

Construir un pipeline de Ingeniería de Datos reproducible para integrar los dominios University, Billing y CRM, aplicar reglas explícitas de calidad y publicar contratos analíticos para Jupyter y Power BI.

## Arquitectura implementada

```text
CSV Raw
   ↓
Discovery y profiling
   ↓
Bronze Parquet
   ↓
Silver Parquet
   ↓
Gold PostgreSQL + Parquet
   ↓
Notebook Gold + Power BI
```

Apache Airflow orquesta manualmente las transformaciones Bronze → Silver → Gold dentro del ambiente Docker Compose.

## Componentes

- Ingesta y perfilado de 18 CSV.
- Capas Bronze, Silver y Gold.
- Validaciones bloqueantes y advertencias de calidad.
- Integración University–Billing mediante `external_ref`.
- Mart CRM independiente.
- Persistencia Gold en PostgreSQL.
- Exportaciones Gold en Parquet.
- Orquestación con Airflow.
- Documentación y análisis en Jupyter.
- Dashboard analítico en Power BI.

## Estado final

```text
Discovery y profiling: completados
Bronze: completado
Silver: completado y validado
Gold: completado y validado
PostgreSQL: completado
Parquet final: completado
Airflow: completado; ejecución manual
Notebooks: completados y ejecutados
Power BI: implementado
```

Las mejoras futuras se concentran en pruebas unitarias, CI/CD, programación periódica del DAG y operación sobre infraestructura administrada.
