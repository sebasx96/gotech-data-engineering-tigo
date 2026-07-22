# Resumen de Implementación de la Capa Gold

## 1. Objetivo

La capa Gold transforma los datos validados de Silver en tablas analíticas orientadas al consumo de negocio.

Su persistencia principal se encuentra en PostgreSQL, dentro del esquema:

```text
gold
```

Las tablas están preparadas para ser consumidas mediante:

* Consultas SQL.
* Jupyter Notebook.
* Power BI.
* Herramientas como DBeaver o pgAdmin.
* Procesos analíticos en Python.

También se generan exportaciones Parquet como copias portables adicionales. PostgreSQL continúa siendo la persistencia oficial de la capa Gold.

---

## 2. Flujo implementado

```text
CSV Raw
   ↓
Bronze Parquet
   ↓
Silver Parquet
   ↓
Transformaciones Gold con Python y Pandas
   ↓
Validaciones del DataFrame
   ↓
Carga en PostgreSQL
   ↓
Validación posterior a la carga
   ↓
Exportación adicional a Parquet
```

La carga de cada tabla utiliza una estrategia de reemplazo completo.

Esto permite que la ejecución sea idempotente: volver a ejecutar el pipeline no genera registros duplicados.

---

## 3. Tablas Gold implementadas

| Tabla                         | Grano                              |   Filas |
| ----------------------------- | ---------------------------------- | ------: |
| `gold.academic_performance`   | Una fila por inscripción académica |  25.000 |
| `gold.invoice_financial`      | Una fila por factura               |  50.000 |
| `gold.product_sales`          | Una fila por línea de factura      | 150.000 |
| `gold.subscription_portfolio` | Una fila por suscripción           |  15.000 |
| `gold.crm_opportunity`        | Una fila por oportunidad comercial |   3.000 |
| `gold.crm_lead`               | Una fila por lead                  |   2.000 |
| `gold.student_360`            | Una fila por estudiante            |   5.000 |

Todas las tablas fueron validadas después de su carga en PostgreSQL.

---

## 4. `gold.academic_performance`

### Objetivo

Analizar el rendimiento académico por estudiante, curso, profesor, departamento y semestre.

### Fuentes principales

* `university.enrollments`
* `university.grades`
* `university.courses`
* `university.professors`
* `university.semesters`
* `billing.customers`

### Resultado

* 25.000 inscripciones.
* 25.000 `enrollment_id` únicos.
* 22.786 inscripciones con calificaciones.
* 22.645 inscripciones con pesos que no suman 1.
* Ningún estudiante sin relación con Billing.
* Ninguna nota normalizada fuera del rango 0–100.

### Nota normalizada

Debido a las inconsistencias encontradas en los pesos, la calificación se calcula mediante:

```text
SUM(score × weight) / SUM(weight)
```

La suma original se conserva mediante `weight_sum`, y la anomalía se identifica con `has_invalid_weight_sum`.

---

## 5. `gold.invoice_financial`

### Objetivo

Analizar facturación, pagos, saldos pendientes, sobrepagos y reconciliación financiera.

### Fuentes principales

* `billing.invoices`
* `billing.invoice_items`
* `billing.payments`
* `billing.customers`
* `university.students`

### Resultado

* 50.000 facturas.
* 50.000 `invoice_id` únicos.
* 25.071 facturas asociadas con estudiantes.
* 2.502 facturas sin líneas.
* 18.567 facturas sin pagos.
* 47.497 facturas con diferencias entre cabecera y líneas.
* 29.510 facturas con saldo pendiente.
* 20.482 facturas con sobrepago.
* 14.476 diferencias entre el estado registrado y el saldo calculado.

Estas diferencias se conservaron como indicadores analíticos y no fueron corregidas artificialmente.

### Tratamiento de monedas

Los valores monetarios nunca se consolidan mezclando monedas diferentes.

Todos los KPIs financieros deben agruparse o filtrarse mediante `currency`.

---

## 6. `gold.product_sales`

### Objetivo

Analizar cantidades, productos, categorías y ventas registradas en las líneas de factura.

### Resultado

* 150.000 líneas.
* 150.000 `invoice_item_id` únicos.
* 0 facturas faltantes.
* 0 clientes faltantes.
* 0 productos faltantes.
* 0 errores en `quantity × unit_price`.
* 75.076 líneas asociadas con estudiantes.
* 74.924 líneas asociadas con otros clientes.
* 8 monedas.
* 4 categorías de productos.

---

## 7. `gold.subscription_portfolio`

### Objetivo

Analizar el estado, duración y composición del portafolio de suscripciones.

### Resultado

* 15.000 suscripciones.
* 15.000 `subscription_id` únicos.
* 11.272 suscripciones activas.
* 1.486 suscripciones pausadas.
* 2.242 suscripciones canceladas.
* 7.573 suscripciones asociadas con estudiantes.
* 7.427 suscripciones de otros clientes.
* 783 fechas finales inválidas detectadas en Silver.
* 783 suscripciones sin fecha final válida.

Las fechas inválidas fueron anuladas en Silver y permanecen identificadas mediante una bandera de calidad.

---

## 8. `gold.crm_opportunity`

### Objetivo

Analizar el pipeline comercial, las etapas, actividades, contactos y resultados de las oportunidades.

### Fuentes principales

* `crm.opportunities`
* `crm.accounts`
* `crm.activities`
* `crm.opportunity_contacts`

### Resultado

* 3.000 oportunidades.
* 3.000 `opportunity_id` únicos.
* 2.221 oportunidades abiertas.
* 779 oportunidades cerradas.
* 476 oportunidades ganadas.
* 303 oportunidades perdidas.
* 105 oportunidades sin actividades.
* 414 oportunidades sin contactos.
* 1.029 fechas de cierre inválidas identificadas.
* Promedio de 3,34 actividades por oportunidad.
* Promedio de 2 contactos por oportunidad.

El campo `amount` no incluye moneda, por lo que no se compara directamente con los importes de Billing.

---

## 9. `gold.crm_lead`

### Objetivo

Analizar captación, calificación y conversión de leads.

### Resultado

* 2.000 leads.
* 2.000 `lead_id` únicos.
* 594 leads nuevos.
* 525 leads contactados.
* 395 leads calificados.
* 205 leads convertidos.
* 281 leads perdidos.
* 1.514 leads abiertos.
* 486 leads cerrados.
* 5 fuentes de captación.
* Puntaje promedio de 50,1.
* Tasa de conversión total de 10,25 %.

---

## 10. `gold.student_360`

### Objetivo

Crear una vista consolidada de cada estudiante combinando información académica, financiera y de suscripciones.

### Resultado

* 5.000 estudiantes.
* 5.000 `student_id` únicos.
* 0 estudiantes sin cliente relacionado.
* 25.000 inscripciones académicas agregadas.
* 25.071 facturas asociadas.
* 7.573 suscripciones asociadas.
* 38 estudiantes sin actividad académica.
* 33 estudiantes sin actividad de facturación.
* 1.099 estudiantes sin historial de suscripciones.
* 3.399 estudiantes con suscripción activa.
* 4.751 estudiantes con facturas pendientes.
* 1.947 estudiantes con facturas vencidas.

No se incorporaron totales monetarios consolidados en esta tabla porque los estudiantes pueden tener operaciones en diferentes monedas.

---

## 11. Integración entre dominios

La relación confiable entre Universidad y Billing es:

```text
university.students.student_id
=
billing.customers.external_ref
```

Los 5.000 estudiantes encontraron exactamente un cliente relacionado.

CRM se mantuvo como un dominio analítico separado porque no existe una clave compartida y suficientemente confiable con Universidad o Billing.

No se forzaron relaciones mediante correos electrónicos debido a:

* Posibles duplicados.
* Diferencias entre cuentas.
* Ausencia de una garantía de identidad.
* Riesgo de producir joins y conclusiones incorrectas.

CRM sí fue integrado internamente mediante sus cuentas, contactos, oportunidades y actividades.

---

## 12. Validaciones aplicadas

Cada tabla Gold valida:

* Cantidad de filas esperada.
* Clave principal no nula.
* Clave principal única.
* Conservación del grano.
* Relaciones completas.
* Cálculos numéricos.
* Indicadores booleanos.
* Ausencia de duplicados producidos por joins.
* Separación de importes por moneda.
* Conteos posteriores a la carga en PostgreSQL.

La tabla cargada se consulta nuevamente en PostgreSQL para confirmar el número total de filas y claves distintas.

---

## 13. Persistencia y respaldo

La persistencia principal es:

```text
PostgreSQL
└── base de datos: gotech_dw
    └── esquema: gold
```

Las exportaciones adicionales se encuentran en:

```text
data/gold/*.parquet
```

También se generan:

```text
backups/gold_structure.sql
backups/gold_data.dump
```

* `gold_structure.sql` contiene la definición legible de las tablas y restricciones.
* `gold_data.dump` contiene una copia restaurable y comprimida de la capa Gold.

---

## 14. Estado de la capa Gold

```text
Diseño analítico: completado
Transformaciones: completadas
Validaciones: completadas
Carga PostgreSQL: completada
Exportación Parquet: completada
Respaldo PostgreSQL: completado
```

El flujo completo `Bronze → Silver → Gold` está automatizado mediante Apache Airflow. El DAG se dispara manualmente y reconstruye las capas sin duplicar registros.
