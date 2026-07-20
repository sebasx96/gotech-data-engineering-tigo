# Lista de evidencias para la presentación

Crea una carpeta local:

```text
evidence/
```

Guarda allí capturas con nombres claros.

## 1. Docker

Archivo sugerido:

```text
01_docker_services.png
```

Debe mostrar:

```bash
docker compose ps
```

Servicios visibles:

- gotech-postgres
- gotech-airflow
- gotech-jupyter

---

## 2. Airflow

Archivo sugerido:

```text
02_airflow_dag_success.png
```

Captura la vista Grid o Graph con:

- `build_bronze`
- `build_and_validate_silver`
- `build_and_validate_gold`

Las tres tareas deben aparecer en verde.

---

## 3. Jupyter

Archivo sugerido:

```text
03_jupyter_gold_analysis.png
```

Captura:

- Una visualización relevante.
- La última validación.
- El mensaje `Notebook Gold ejecutado correctamente.`

---

## 4. PostgreSQL Gold

Archivo sugerido:

```text
04_postgresql_gold_tables.png
```

Ejecuta una consulta que muestre las tablas y conteos.

Ejemplo:

```sql
SELECT 'academic_performance' AS table_name, COUNT(*) AS row_count
FROM gold.academic_performance
UNION ALL
SELECT 'invoice_financial', COUNT(*)
FROM gold.invoice_financial
UNION ALL
SELECT 'product_sales', COUNT(*)
FROM gold.product_sales
UNION ALL
SELECT 'subscription_portfolio', COUNT(*)
FROM gold.subscription_portfolio
UNION ALL
SELECT 'crm_opportunity', COUNT(*)
FROM gold.crm_opportunity
UNION ALL
SELECT 'crm_lead', COUNT(*)
FROM gold.crm_lead
UNION ALL
SELECT 'student_360', COUNT(*)
FROM gold.student_360;
```

Conteos esperados:

| Tabla | Filas |
|---|---:|
| academic_performance | 25.000 |
| invoice_financial | 50.000 |
| product_sales | 150.000 |
| subscription_portfolio | 15.000 |
| crm_opportunity | 3.000 |
| crm_lead | 2.000 |
| student_360 | 5.000 |

---

## 5. Calidad de datos

Archivo sugerido:

```text
05_data_quality_findings.png
```

Captura la tabla del notebook que muestra:

- Pesos académicos inconsistentes.
- Facturas sin líneas.
- Facturas sin pagos.
- Diferencias cabecera-líneas.
- Fechas inválidas de suscripción.
- Fechas inválidas de oportunidades.

---

## 6. Modelo de Power BI

Archivo sugerido:

```text
06_power_bi_model.png
```

Debe mostrar:

```text
Dim Student
Fact Academic
Fact Invoice
Fact Product Sales
Fact Subscription
Fact Opportunity
Fact Lead
```

Verifica que CRM permanezca separado.

---

## 7. Dashboard

Capturas sugeridas:

```text
07_dashboard_executive.png
08_dashboard_academic.png
09_dashboard_billing.png
10_dashboard_student360.png
11_dashboard_crm.png
```

---

## 8. GitHub

Archivo sugerido:

```text
12_github_repository.png
```

Debe mostrar:

- README.
- `src/`
- `dags/`
- `notebooks/`
- `docs/`
- `docker/`
- `docker-compose.yml`

No muestres:

- `.env`
- contraseñas
- tokens
- credenciales
