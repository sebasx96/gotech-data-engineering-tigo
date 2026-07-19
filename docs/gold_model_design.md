# Diseño del Modelo Analítico Gold

## 1. Objetivo

La capa Gold transforma los datos validados de Silver en tablas analíticas orientadas al negocio, preparadas para ser almacenadas en PostgreSQL y consumidas desde Jupyter y Power BI.

El modelo está diseñado para soportar:

* Análisis del rendimiento académico.
* Monitoreo de facturación y pagos.
* Análisis de ventas por producto.
* Análisis del portafolio de suscripciones.
* Análisis del pipeline comercial de CRM.
* Análisis integrado entre estudiantes y clientes.

La implementación prioriza:

* Claridad en el grano de cada tabla.
* Trazabilidad hacia los datos de origen.
* Facilidad de consulta.
* Utilidad para el negocio.
* Simplicidad técnica.
* Integración con Power BI.

No se busca crear un modelo excesivamente complejo, sino una solución sólida, reproducible y fácil de explicar durante la presentación.

---

## 2. Integración entre dominios

La relación principal entre los dominios Universidad y Billing es:

```text
university.students.student_id
=
billing.customers.external_ref
```

Los 5.000 estudiantes disponibles en el dominio Universidad tienen correspondencia con un registro de cliente en Billing.

De los 10.000 clientes existentes en Billing:

* 5.000 están asociados con estudiantes.
* 5.000 no tienen un registro académico relacionado.

Esta relación permite combinar información académica, financiera y de suscripciones.

Ejemplos de análisis posibles:

* Rendimiento académico por estado de suscripción.
* Estudiantes con o sin suscripción activa.
* Estado de facturación de los estudiantes.
* Rendimiento académico por categoría de producto.
* Estudiantes con facturas vencidas.
* Relación observada entre comportamiento académico y financiero.

No se afirmará causalidad entre estas variables. Solo se presentarán asociaciones observadas en los datos.

### Integración con CRM

CRM se mantendrá como un dominio analítico separado.

No existe un identificador compartido y confiable que permita relacionar directamente CRM con Universidad o Billing.

Aunque podrían existir coincidencias aisladas por correo electrónico, estas relaciones no son suficientemente robustas para construir joins confiables.

Por este motivo:

* No se crearán relaciones artificiales.
* No se asumirán equivalencias basadas únicamente en correos similares.
* CRM tendrá sus propias tablas Gold y KPIs comerciales.

Esta decisión protege la integridad del modelo y evita generar conclusiones incorrectas.

---

## 3. Tablas de la capa Gold

## 3.1 `gold.student_360`

### Grano de la tabla

Una fila por estudiante asociado con un cliente de Billing.

### Objetivo

Construir una vista consolidada del estudiante que combine información académica, financiera y de suscripciones.

### Fuentes

* `university.students`
* `billing.customers`
* Agregados de `university.enrollments`
* Agregados de `university.grades`
* Agregados de `billing.invoices`
* Agregados de `billing.subscriptions`

### Campos principales

* `student_id`
* `customer_id`
* `student_first_name`
* `student_last_name`
* `student_email`
* `customer_email`
* `student_country`
* `customer_country`
* `customer_segment`
* `student_enrolled_at`
* `courses_enrolled`
* `courses_completed`
* `courses_failed`
* `courses_dropped`
* `average_normalized_grade`
* `invoice_count`
* `active_subscription_count`
* `has_active_subscription`

### Consideración monetaria

No se incluirá un único total financiero consolidado por estudiante sin separar por moneda.

Un cliente puede tener facturas en distintas monedas, por lo que sumar todos los valores produciría un resultado incorrecto.

Los análisis monetarios se realizarán siempre agrupados o filtrados por `currency`.

---

## 3.2 `gold.academic_performance`

### Grano de la tabla

Una fila por inscripción académica.

### Objetivo

Analizar el rendimiento de cada estudiante por curso, profesor, departamento y semestre.

### Fuentes

* `university.enrollments`
* `university.grades`
* `university.courses`
* `university.professors`
* `university.semesters`
* `university.students`
* `billing.customers`

### Campos principales

* `enrollment_id`
* `student_id`
* `customer_id`
* `course_id`
* `course_code`
* `course_name`
* `department`
* `credits`
* `professor_id`
* `professor_name`
* `semester_id`
* `semester_code`
* `semester_year`
* `semester_half`
* `enrolled_at`
* `enrollment_status`
* `assessment_count`
* `weight_sum`
* `normalized_grade`
* `has_grades`
* `has_invalid_weight_sum`

### Cálculo de la nota normalizada

Debido a que los pesos de las evaluaciones no siempre suman 1, se utilizará la siguiente fórmula:

```text
SUM(score * weight) / SUM(weight)
```

Este cálculo permite obtener una nota ponderada normalizada sin modificar arbitrariamente los pesos originales.

La suma original de los pesos se conservará en el campo:

```text
weight_sum
```

También se incluirá la bandera:

```text
has_invalid_weight_sum
```

Esta bandera permitirá identificar las inscripciones cuyos pesos no sumaban 1 en los datos fuente.

La anomalía permanecerá visible y será documentada como un problema de calidad no bloqueante.

---

## 3.3 `gold.invoice_financial`

### Grano de la tabla

Una fila por factura.

### Objetivo

Analizar facturación, pagos, saldos pendientes, sobrepagos y problemas de reconciliación.

### Fuentes

* `billing.invoices`
* `billing.payments`
* `billing.invoice_items`
* `billing.customers`
* `university.students`

### Campos principales

* `invoice_id`
* `customer_id`
* `student_id`
* `issued_at`
* `due_at`
* `invoice_status`
* `currency`
* `invoice_total`
* `invoice_item_count`
* `invoice_item_total`
* `payment_count`
* `paid_amount`
* `balance_amount`
* `outstanding_amount`
* `overpayment_amount`
* `has_invoice_items`
* `has_payments`
* `invoice_items_match_header`

### Reglas de cálculo

```text
balance_amount = invoice_total - paid_amount
```

```text
outstanding_amount = MAX(balance_amount, 0)
```

```text
overpayment_amount = MAX(-balance_amount, 0)
```

### Decisión de calidad

Los siguientes valores se conservarán por separado:

* Total registrado en la cabecera de factura.
* Total calculado a partir de las líneas.
* Total pagado.
* Saldo pendiente.
* Sobrepago.

Esto es necesario porque se detectaron diferencias importantes entre facturas, líneas de factura y pagos.

No se corregirán artificialmente esos valores.

En su lugar, el modelo expondrá indicadores explícitos de reconciliación.

---

## 3.4 `gold.product_sales`

### Grano de la tabla

Una fila por línea de factura.

### Objetivo

Analizar productos, categorías, cantidades vendidas e ingresos registrados en las líneas de factura.

### Fuentes

* `billing.invoice_items`
* `billing.invoices`
* `billing.products`
* `billing.customers`
* `university.students`

### Campos principales

* `invoice_item_id`
* `invoice_id`
* `customer_id`
* `student_id`
* `product_id`
* `sku`
* `product_name`
* `product_category`
* `issued_at`
* `invoice_status`
* `currency`
* `quantity`
* `unit_price`
* `line_total`

### Consideración monetaria

Todos los análisis monetarios deben:

* Agruparse por moneda.
* Filtrarse por moneda.
* Evitar sumar monedas distintas.

No se realizará conversión de monedas porque el proyecto no incluye una fuente histórica de tipos de cambio.

---

## 3.5 `gold.subscription_portfolio`

### Grano de la tabla

Una fila por suscripción.

### Objetivo

Analizar el estado, duración y distribución del portafolio de suscripciones.

### Fuentes

* `billing.subscriptions`
* `billing.products`
* `billing.customers`
* `university.students`

### Campos principales

* `subscription_id`
* `customer_id`
* `student_id`
* `product_id`
* `product_name`
* `product_category`
* `subscription_status`
* `start_date`
* `end_date`
* `duration_days`
* `is_active`
* `is_student_customer`
* `invalid_end_date_flag`

### Tratamiento de fechas inválidas

Cuando el dato fuente contenía una fecha de finalización anterior a la fecha de inicio:

* La fila fue conservada.
* La fecha inválida fue convertida en nula dentro de Silver.
* Se añadió una bandera de calidad.
* La anomalía permanece visible en Gold.

La duración de la suscripción solo se calculará cuando las fechas disponibles sean válidas.

---

## 3.6 `gold.crm_opportunity`

### Grano de la tabla

Una fila por oportunidad comercial.

### Objetivo

Analizar el pipeline comercial, las etapas de venta, las oportunidades ganadas y las actividades asociadas.

### Fuentes

* `crm.opportunities`
* `crm.accounts`
* `crm.activities`
* `crm.opportunity_contacts`

### Campos principales

* `opportunity_id`
* `opportunity_name`
* `account_id`
* `account_name`
* `industry`
* `account_country`
* `stage`
* `amount`
* `created_at`
* `close_date`
* `activity_count`
* `contact_count`
* `is_open`
* `is_closed`
* `is_won`
* `invalid_close_date_flag`

### Consideración monetaria

El campo `amount` de las oportunidades no contiene información de moneda.

Por esta razón:

* Se presentará como importe registrado en el sistema fuente.
* No se comparará directamente con los importes de Billing.
* No se combinará con facturación en un mismo KPI financiero.
* Esta limitación será explicada en la presentación.

---

## 3.7 `gold.crm_lead`

### Grano de la tabla

Una fila por lead.

### Objetivo

Analizar la captación, calificación y conversión de leads.

### Fuente

* `crm.leads`

### Campos principales

* `lead_id`
* `lead_source`
* `lead_status`
* `lead_score`
* `created_at`
* `is_converted`
* `is_qualified`
* `is_lost`

Esta tabla permitirá medir el rendimiento de las distintas fuentes de captación y el avance de los leads dentro del proceso comercial.

---

## 4. KPIs principales

## 4.1 KPIs académicos

* Cantidad total de inscripciones.
* Cantidad de estudiantes activos.
* Tasa de finalización.
* Tasa de reprobación.
* Tasa de abandono.
* Nota normalizada promedio.
* Nota promedio por curso.
* Nota promedio por departamento.
* Nota promedio por semestre.
* Rendimiento académico por profesor.
* Cantidad de inscripciones sin calificaciones.
* Cantidad de inscripciones con pesos inconsistentes.

### Fórmulas principales

```text
completion_rate =
completed_enrollments / total_enrollments
```

```text
failure_rate =
failed_enrollments / total_enrollments
```

```text
dropout_rate =
dropped_enrollments / total_enrollments
```

---

## 4.2 KPIs de facturación

* Cantidad de facturas por estado.
* Total facturado por moneda.
* Total pagado por moneda.
* Total pendiente por moneda.
* Total sobrepagado por moneda.
* Tasa de facturas vencidas.
* Cantidad de facturas sin líneas.
* Cantidad de facturas sin pagos.
* Cantidad de facturas con diferencias entre cabecera y líneas.
* Ventas por producto.
* Ventas por categoría de producto.

### Fórmula de tasa de facturas vencidas

```text
overdue_invoice_rate =
overdue_invoices / total_invoices
```

---

## 4.3 KPIs de suscripciones

* Cantidad total de suscripciones.
* Cantidad de suscripciones activas.
* Cantidad de suscripciones pausadas.
* Cantidad de suscripciones canceladas.
* Tasa de suscripciones activas.
* Suscripciones por categoría de producto.
* Duración promedio de las suscripciones.
* Cantidad de clientes estudiantes con suscripción activa.
* Cantidad de estudiantes sin suscripción activa.
* Cantidad de suscripciones con fechas inválidas.

### Fórmula de tasa activa

```text
active_subscription_rate =
active_subscriptions / total_subscriptions
```

---

## 4.4 KPIs de CRM

* Cantidad total de oportunidades.
* Oportunidades por etapa.
* Cantidad de oportunidades ganadas.
* Cantidad de oportunidades perdidas.
* Tasa de oportunidades ganadas.
* Pipeline abierto por etapa.
* Importe promedio por oportunidad.
* Cantidad promedio de actividades por oportunidad.
* Cantidad promedio de contactos por oportunidad.
* Cantidad total de leads.
* Tasa de conversión de leads.
* Leads por fuente.
* Conversiones por fuente.
* Puntaje promedio de leads.

### Tasa de oportunidades ganadas

```text
win_rate =
won_opportunities
/
(won_opportunities + lost_opportunities)
```

Las oportunidades abiertas no se incluirán en el denominador de esta tasa.

### Tasa de conversión de leads

```text
lead_conversion_rate =
converted_leads / total_leads
```

---

## 4.5 KPIs integrados Universidad–Billing

* Cantidad de estudiantes relacionados con clientes.
* Porcentaje de estudiantes con suscripción activa.
* Nota promedio por estado de suscripción.
* Rendimiento académico por categoría de producto.
* Estudiantes sin suscripción activa.
* Facturas vencidas por perfil académico.
* Estado de facturación por resultado académico.
* Cantidad de cursos completados por segmento de cliente.
* Comparación de rendimiento entre estudiantes con y sin suscripción activa.

Estos análisis serán presentados como relaciones observadas.

No se afirmará que una variable cause directamente el comportamiento de otra.

---

## 5. Tratamiento de monedas

Billing contiene múltiples monedas:

* USD
* CLP
* EUR
* MXN
* COP
* ARS
* PEN
* BRL

No se sumarán importes de distintas monedas en un único valor consolidado.

Todos los KPIs monetarios de Billing deberán:

* Agruparse por `currency`.
* Filtrarse por `currency`.
* Mostrar claramente la moneda utilizada.

La conversión monetaria queda fuera del alcance actual debido a que no se proporcionó una fuente confiable de tipos de cambio históricos.

Una mejora futura podría incorporar una tabla externa de tipos de cambio y convertir los importes hacia una moneda común.

---

## 6. Decisiones técnicas principales

### Silver en Parquet

La capa Silver permanece en Parquet porque este formato ofrece:

* Compresión eficiente.
* Tipos de datos definidos.
* Lectura columnar.
* Mejor rendimiento que CSV.
* Facilidad de procesamiento con Pandas.
* Portabilidad entre herramientas.

### Gold en PostgreSQL

La capa Gold será persistida en PostgreSQL porque permite:

* Consultas SQL.
* Creación de esquemas y tablas relacionales.
* Integración directa con Power BI.
* Control de restricciones.
* Automatización de cargas.
* Reutilización de tablas analíticas.
* Acceso centralizado a los resultados.

### Conservación de identificadores de origen

Inicialmente se conservarán los identificadores de origen como claves principales de las tablas Gold.

Ejemplos:

* `student_id`
* `customer_id`
* `invoice_id`
* `enrollment_id`
* `opportunity_id`

Esta decisión mejora la trazabilidad y reduce complejidad innecesaria para el alcance actual.

El uso de claves sustitutas podría implementarse como mejora futura.

### Idempotencia

Las transformaciones Gold deberán ser idempotentes.

Esto significa que ejecutar nuevamente el pipeline no debe generar registros duplicados.

La carga podrá implementarse mediante:

* Reemplazo completo de tablas analíticas.
* `TRUNCATE` seguido de carga.
* `DROP TABLE` y recreación controlada.
* Estrategias `UPSERT`, si se requieren posteriormente.

Para el volumen actual, se priorizará una carga completa y reproducible.

### Visibilidad de problemas de calidad

Los problemas de calidad no serán ocultados.

Se conservarán indicadores explícitos como:

* `has_invalid_weight_sum`
* `invalid_end_date_flag`
* `invalid_close_date_flag`
* `invoice_items_match_header`
* `has_invoice_items`
* `has_payments`

Esto permite que las anomalías sean visibles en consultas, notebooks, dashboards y presentaciones.

---

## 7. Estrategia de implementación

La implementación seguirá este orden:

1. Configurar PostgreSQL mediante Docker Compose.
2. Crear el esquema `gold`.
3. Desarrollar las transformaciones Gold con Python y Pandas.
4. Leer los archivos Silver en formato Parquet.
5. Construir las tablas analíticas.
6. Validar el grano y la unicidad de cada tabla.
7. Cargar las tablas en PostgreSQL.
8. Validar conteos e integridad.
9. Exportar las tablas Gold a Parquet cuando corresponda.
10. Consumir Gold desde Jupyter.
11. Conectar Power BI con PostgreSQL.
12. Automatizar el flujo mediante Airflow.

---

## 8. Validaciones previstas para Gold

Cada tabla deberá validar:

* Cantidad de filas esperada.
* Unicidad de su clave principal.
* Ausencia de claves principales nulas.
* Conservación del grano definido.
* Relaciones válidas entre identificadores.
* Tipos de datos correctos.
* Cálculos numéricos consistentes.
* Ausencia de duplicados generados por joins.
* Separación correcta de importes por moneda.
* Ejecución idempotente.

Ejemplos:

```text
gold.student_360:
una fila por student_id
```

```text
gold.academic_performance:
una fila por enrollment_id
```

```text
gold.invoice_financial:
una fila por invoice_id
```

```text
gold.product_sales:
una fila por invoice_item_id
```

```text
gold.subscription_portfolio:
una fila por subscription_id
```

```text
gold.crm_opportunity:
una fila por opportunity_id
```

```text
gold.crm_lead:
una fila por lead_id
```

---

## 9. Mejoras futuras

Como mejoras futuras se consideran:

* Incorporar claves sustitutas.
* Implementar dimensiones lentamente cambiantes.
* Añadir cargas incrementales.
* Incorporar una tabla de tipos de cambio.
* Añadir pruebas automatizadas.
* Implementar monitoreo y alertas.
* Añadir un catálogo de datos.
* Incorporar almacenamiento de objetos como MinIO.
* Añadir herramientas de calidad como Great Expectations.
* Implementar procesamiento distribuido si el volumen aumenta.
* Construir un modelo dimensional más extenso.
* Añadir control de linaje de datos.
* Implementar una estrategia formal de historización.
