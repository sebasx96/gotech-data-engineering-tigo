# Diseño del Dashboard Power BI

## 1. Objetivo

Construir un dashboard ejecutivo y técnico basado en las siete tablas del esquema `gold` de PostgreSQL.

El dashboard debe permitir:

- Analizar rendimiento académico.
- Revisar facturación y saldos.
- Explorar ventas por producto.
- Analizar suscripciones.
- Evaluar leads y oportunidades CRM.
- Mostrar alertas de calidad.
- Presentar una visión integrada del estudiante.

---

## 2. Tablas que se importarán

| Tabla PostgreSQL | Nombre recomendado en Power BI |
|---|---|
| `gold.academic_performance` | `Fact Academic` |
| `gold.invoice_financial` | `Fact Invoice` |
| `gold.product_sales` | `Fact Product Sales` |
| `gold.subscription_portfolio` | `Fact Subscription` |
| `gold.crm_opportunity` | `Fact Opportunity` |
| `gold.crm_lead` | `Fact Lead` |
| `gold.student_360` | `Dim Student` |

---

## 3. Relaciones

### Relación académica

```text
Dim Student[student_id] 1 ───── * Fact Academic[student_id]
```

### Relación de facturación

```text
Dim Student[student_id] 1 ───── * Fact Invoice[student_id]
```

### Relación de líneas de producto

```text
Fact Invoice[invoice_id] 1 ───── * Fact Product Sales[invoice_id]
```

### Relación de suscripciones

```text
Dim Student[student_id] 1 ───── * Fact Subscription[student_id]
```

### CRM

`Fact Opportunity` y `Fact Lead` permanecen sin relación con Universidad y Billing porque no existe una clave confiable compartida.

Todas las relaciones deben utilizar:

```text
Cardinalidad: Uno a varios
Dirección de filtro: Única
Estado: Activa
```

---

## 4. Tabla de medidas

Después de cargar las tablas, crear una tabla vacía llamada:

```text
Measures
```

Todas las medidas DAX deben almacenarse en esta tabla.

---

# 5. Medidas DAX

## 5.1 Resumen general

### Total Students

```DAX
Total Students =
DISTINCTCOUNT('Dim Student'[student_id])
```

### Total Enrollments

```DAX
Total Enrollments =
COUNTROWS('Fact Academic')
```

### Total Invoices

```DAX
Total Invoices =
COUNTROWS('Fact Invoice')
```

### Total Subscriptions

```DAX
Total Subscriptions =
COUNTROWS('Fact Subscription')
```

### Total Leads

```DAX
Total Leads =
COUNTROWS('Fact Lead')
```

### Total Opportunities

```DAX
Total Opportunities =
COUNTROWS('Fact Opportunity')
```

---

## 5.2 Rendimiento académico

### Completed Enrollments

```DAX
Completed Enrollments =
CALCULATE(
    [Total Enrollments],
    'Fact Academic'[enrollment_status] = "completed"
)
```

### Failed Enrollments

```DAX
Failed Enrollments =
CALCULATE(
    [Total Enrollments],
    'Fact Academic'[enrollment_status] = "failed"
)
```

### Dropped Enrollments

```DAX
Dropped Enrollments =
CALCULATE(
    [Total Enrollments],
    'Fact Academic'[enrollment_status] = "dropped"
)
```

### Completion Rate

```DAX
Completion Rate =
DIVIDE(
    [Completed Enrollments],
    [Total Enrollments],
    0
)
```

### Failure Rate

```DAX
Failure Rate =
DIVIDE(
    [Failed Enrollments],
    [Total Enrollments],
    0
)
```

### Dropout Rate

```DAX
Dropout Rate =
DIVIDE(
    [Dropped Enrollments],
    [Total Enrollments],
    0
)
```

### Average Normalized Grade

```DAX
Average Normalized Grade =
CALCULATE(
    AVERAGE('Fact Academic'[normalized_grade]),
    'Fact Academic'[has_grades] = TRUE()
)
```

### Invalid Grade Weights

```DAX
Invalid Grade Weights =
CALCULATE(
    COUNTROWS('Fact Academic'),
    'Fact Academic'[has_invalid_weight_sum] = TRUE()
)
```

### Invalid Grade Weight Rate

```DAX
Invalid Grade Weight Rate =
DIVIDE(
    [Invalid Grade Weights],
    [Total Enrollments],
    0
)
```

---

## 5.3 Facturación

> Los importes deben visualizarse con un filtro de moneda. No se deben sumar monedas distintas en una misma tarjeta.

### Invoiced Amount

```DAX
Invoiced Amount =
SUM('Fact Invoice'[invoice_total])
```

### Paid Amount

```DAX
Paid Amount =
SUM('Fact Invoice'[paid_amount])
```

### Outstanding Amount

```DAX
Outstanding Amount =
SUM('Fact Invoice'[outstanding_amount])
```

### Overpayment Amount

```DAX
Overpayment Amount =
SUM('Fact Invoice'[overpayment_amount])
```

### Outstanding Invoices

```DAX
Outstanding Invoices =
CALCULATE(
    COUNTROWS('Fact Invoice'),
    'Fact Invoice'[outstanding_amount] > 0
)
```

### Overdue Invoices

```DAX
Overdue Invoices =
CALCULATE(
    COUNTROWS('Fact Invoice'),
    'Fact Invoice'[invoice_status] = "overdue"
)
```

### Overdue Invoice Rate

```DAX
Overdue Invoice Rate =
DIVIDE(
    [Overdue Invoices],
    [Total Invoices],
    0
)
```

### Invoices Without Items

```DAX
Invoices Without Items =
CALCULATE(
    COUNTROWS('Fact Invoice'),
    'Fact Invoice'[has_invoice_items] = FALSE()
)
```

### Invoices Without Payments

```DAX
Invoices Without Payments =
CALCULATE(
    COUNTROWS('Fact Invoice'),
    'Fact Invoice'[has_payments] = FALSE()
)
```

### Header Line Mismatches

```DAX
Header Line Mismatches =
CALCULATE(
    COUNTROWS('Fact Invoice'),
    'Fact Invoice'[invoice_items_match_header] = FALSE()
)
```

### Collection Rate

```DAX
Collection Rate =
DIVIDE(
    [Paid Amount],
    [Invoiced Amount],
    0
)
```

---

## 5.4 Ventas por producto

### Units Sold

```DAX
Units Sold =
SUM('Fact Product Sales'[quantity])
```

### Product Sales Amount

```DAX
Product Sales Amount =
SUM('Fact Product Sales'[line_total])
```

### Product Invoice Count

```DAX
Product Invoice Count =
DISTINCTCOUNT('Fact Product Sales'[invoice_id])
```

### Average Line Value

```DAX
Average Line Value =
AVERAGE('Fact Product Sales'[line_total])
```

---

## 5.5 Suscripciones

### Active Subscriptions

```DAX
Active Subscriptions =
CALCULATE(
    [Total Subscriptions],
    'Fact Subscription'[is_active] = TRUE()
)
```

### Paused Subscriptions

```DAX
Paused Subscriptions =
CALCULATE(
    [Total Subscriptions],
    'Fact Subscription'[subscription_status] = "paused"
)
```

### Cancelled Subscriptions

```DAX
Cancelled Subscriptions =
CALCULATE(
    [Total Subscriptions],
    'Fact Subscription'[subscription_status] = "cancelled"
)
```

### Active Subscription Rate

```DAX
Active Subscription Rate =
DIVIDE(
    [Active Subscriptions],
    [Total Subscriptions],
    0
)
```

### Student Subscriptions

```DAX
Student Subscriptions =
CALCULATE(
    [Total Subscriptions],
    'Fact Subscription'[is_student_customer] = TRUE()
)
```

### Invalid Subscription Dates

```DAX
Invalid Subscription Dates =
CALCULATE(
    COUNTROWS('Fact Subscription'),
    'Fact Subscription'[invalid_end_date_flag] = TRUE()
)
```

### Average Subscription Duration

```DAX
Average Subscription Duration =
AVERAGE('Fact Subscription'[duration_days])
```

---

## 5.6 CRM: oportunidades

### Open Opportunities

```DAX
Open Opportunities =
CALCULATE(
    [Total Opportunities],
    'Fact Opportunity'[is_open] = TRUE()
)
```

### Closed Opportunities

```DAX
Closed Opportunities =
CALCULATE(
    [Total Opportunities],
    'Fact Opportunity'[is_closed] = TRUE()
)
```

### Won Opportunities

```DAX
Won Opportunities =
CALCULATE(
    [Total Opportunities],
    'Fact Opportunity'[is_won] = TRUE()
)
```

### Lost Opportunities

```DAX
Lost Opportunities =
CALCULATE(
    [Total Opportunities],
    'Fact Opportunity'[is_lost] = TRUE()
)
```

### Closed Win Rate

```DAX
Closed Win Rate =
DIVIDE(
    [Won Opportunities],
    [Closed Opportunities],
    0
)
```

### Average Activities per Opportunity

```DAX
Average Activities per Opportunity =
AVERAGE('Fact Opportunity'[activity_count])
```

### Opportunities Without Activities

```DAX
Opportunities Without Activities =
CALCULATE(
    [Total Opportunities],
    'Fact Opportunity'[has_activities] = FALSE()
)
```

### Opportunities Without Contacts

```DAX
Opportunities Without Contacts =
CALCULATE(
    [Total Opportunities],
    'Fact Opportunity'[has_contacts] = FALSE()
)
```

### Invalid Opportunity Dates

```DAX
Invalid Opportunity Dates =
CALCULATE(
    [Total Opportunities],
    'Fact Opportunity'[invalid_close_date_flag] = TRUE()
)
```

---

## 5.7 CRM: leads

### Converted Leads

```DAX
Converted Leads =
CALCULATE(
    [Total Leads],
    'Fact Lead'[is_converted] = TRUE()
)
```

### Qualified Leads

```DAX
Qualified Leads =
CALCULATE(
    [Total Leads],
    'Fact Lead'[is_qualified] = TRUE()
)
```

### Lost Leads

```DAX
Lost Leads =
CALCULATE(
    [Total Leads],
    'Fact Lead'[is_lost] = TRUE()
)
```

### Lead Conversion Rate

```DAX
Lead Conversion Rate =
DIVIDE(
    [Converted Leads],
    [Total Leads],
    0
)
```

### Average Lead Score

```DAX
Average Lead Score =
AVERAGE('Fact Lead'[lead_score])
```

---

## 5.8 Student 360

### Students With Academic Activity

```DAX
Students With Academic Activity =
CALCULATE(
    [Total Students],
    'Dim Student'[has_academic_activity] = TRUE()
)
```

### Students With Billing Activity

```DAX
Students With Billing Activity =
CALCULATE(
    [Total Students],
    'Dim Student'[has_billing_activity] = TRUE()
)
```

### Students With Subscription History

```DAX
Students With Subscription History =
CALCULATE(
    [Total Students],
    'Dim Student'[has_subscription_history] = TRUE()
)
```

### Students With Active Subscription

```DAX
Students With Active Subscription =
CALCULATE(
    [Total Students],
    'Dim Student'[has_active_subscription] = TRUE()
)
```

### Students With Outstanding Invoices

```DAX
Students With Outstanding Invoices =
CALCULATE(
    [Total Students],
    'Dim Student'[has_outstanding_invoices] = TRUE()
)
```

### Students With Overdue Invoices

```DAX
Students With Overdue Invoices =
CALCULATE(
    [Total Students],
    'Dim Student'[has_overdue_invoices] = TRUE()
)
```

### Student Active Subscription Rate

```DAX
Student Active Subscription Rate =
DIVIDE(
    [Students With Active Subscription],
    [Total Students],
    0
)
```

### Average Student Grade

```DAX
Average Student Grade =
AVERAGE('Dim Student'[average_normalized_grade])
```

### Average Completed Courses

```DAX
Average Completed Courses =
AVERAGE('Dim Student'[courses_completed])
```

---

# 6. Páginas del dashboard

## Página 1 — Resumen Ejecutivo

### Tarjetas

- Total Students
- Total Enrollments
- Completion Rate
- Overdue Invoices
- Active Subscriptions
- Lead Conversion Rate

### Gráficos

- Inscripciones por estado.
- Facturas por estado.
- Suscripciones por estado.
- Leads por estado.
- Alertas de calidad.

### Segmentadores

- Moneda.
- Semestre.
- Departamento.
- Estado académico.

---

## Página 2 — Rendimiento Académico

### Tarjetas

- Total Enrollments
- Completion Rate
- Failure Rate
- Dropout Rate
- Average Normalized Grade
- Invalid Grade Weights

### Gráficos

- Barras: inscripciones por estado.
- Barras: nota promedio por departamento.
- Matriz: departamento, curso, inscripciones y nota.
- Barras: estudiantes con y sin suscripción activa.
- Tabla: cursos con mayor abandono.

---

## Página 3 — Facturación y Productos

### Tarjetas

- Total Invoices
- Invoiced Amount
- Paid Amount
- Outstanding Amount
- Collection Rate
- Overdue Invoices

### Gráficos

- Facturas por estado.
- Importe facturado por moneda.
- Saldos pendientes por moneda.
- Top productos por ventas.
- Ventas por categoría.
- Alertas de reconciliación.

### Segmentador obligatorio

```text
currency
```

Las tarjetas monetarias deben depender de una sola moneda seleccionada.

---

## Página 4 — Suscripciones y Student 360

### Tarjetas

- Active Subscriptions
- Active Subscription Rate
- Students With Active Subscription
- Students With Outstanding Invoices
- Students With Overdue Invoices
- Average Student Grade

### Gráficos

- Suscripciones por estado.
- Suscripciones por categoría.
- Nota promedio con y sin suscripción activa.
- Cursos completados por estado de suscripción.
- Estudiantes con facturas vencidas.
- Tabla de segmentos de estudiantes.

---

## Página 5 — CRM

### Tarjetas

- Total Leads
- Lead Conversion Rate
- Average Lead Score
- Total Opportunities
- Closed Win Rate
- Average Activities per Opportunity

### Gráficos

- Funnel de leads.
- Conversión por fuente.
- Oportunidades por etapa.
- Oportunidades con y sin actividades.
- Oportunidades con y sin contactos.
- Alertas de fechas inválidas.

---

# 7. Reglas visuales

- Utilizar un máximo de seis tarjetas por página.
- Mantener el mismo encabezado en las cinco páginas.
- Utilizar títulos claros y orientados a negocio.
- Evitar gráficos 3D.
- Mantener filtros visibles.
- No mezclar monedas.
- Mostrar porcentajes con uno o dos decimales.
- Mostrar importes con separadores de miles.
- Incluir una nota sobre calidad de datos.
- Mantener CRM visualmente separado cuando corresponda.

---

# 8. Narrativa para la presentación

El dashboard debe contar esta historia:

1. El pipeline consolida tres dominios.
2. Bronze conserva los datos originales.
3. Silver limpia y valida.
4. Gold crea contratos analíticos.
5. Airflow automatiza el flujo.
6. PostgreSQL sirve los datos.
7. Power BI presenta KPIs e insights.
8. Los problemas de calidad no se ocultan; se exponen y cuantifican.
9. Las monedas se mantienen separadas.
10. CRM no se fuerza dentro de Student 360 sin una clave confiable.

---

# 9. Validación final

Antes de presentar:

- Revisar que las siete tablas carguen.
- Confirmar las cuatro relaciones.
- Confirmar que no existan relaciones bidireccionales.
- Confirmar que CRM permanezca separado.
- Validar todas las tarjetas contra PostgreSQL o Jupyter.
- Probar cada segmentador.
- Revisar que una moneda esté seleccionada en páginas monetarias.
- Eliminar visuales con errores o campos vacíos.
- Guardar el archivo `.pbix`.
