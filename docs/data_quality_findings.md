# Hallazgos de Calidad de Datos

## 1. Propósito

Este documento registra los hallazgos de calidad detectados durante la construcción y validación de las capas Bronze y Silver. El objetivo es mantener trazabilidad sobre los problemas presentes en las fuentes, el tratamiento aplicado y las decisiones que afectarán al modelo Gold.

## 2. Resumen de validación de Silver

El pipeline Silver procesa correctamente las 18 tablas de los dominios Billing, CRM y University.

Las siguientes validaciones bloqueantes finalizaron correctamente:

- Conversión de fechas originales.
- Reconciliación de filas entre Bronze y Silver.
- Integridad de claves primarias.
- Integridad referencial de claves foráneas.
- Reglas cronológicas.
- Rangos numéricos.
- Valores categóricos permitidos.
- Cálculo de `invoice_items.line_total` mediante `quantity * unit_price`.

No se perdieron ni se añadieron filas accidentalmente durante la transformación de Bronze a Silver.

## 3. Inconsistencias cronológicas

### 3.1. Suscripciones de Billing

Se detectaron **783 suscripciones** cuyo `end_date` era anterior a `start_date`.

Tratamiento aplicado en Silver:

- Se preservó el registro completo.
- El `end_date` inconsistente se convirtió en nulo.
- Se añadió la bandera `end_date_quality_valid`.

Justificación: eliminar el registro habría provocado pérdida de información válida de cliente, producto y estado. Mantener la fila y marcar el atributo defectuoso conserva trazabilidad sin presentar la fecha como confiable.

### 3.2. Oportunidades de CRM

Se detectaron **1.029 oportunidades** cuyo `close_date` era anterior a `created_at`.

Tratamiento aplicado en Silver:

- Se preservó el registro completo.
- El `close_date` inconsistente se convirtió en nulo.
- Se añadió la bandera `close_date_quality_valid`.

Justificación: el resto de los atributos de la oportunidad siguen siendo útiles para analizar el embudo comercial. La fecha inválida no debe utilizarse para métricas de duración.

## 4. Pesos de calificaciones

Se encontraron **22.786 inscripciones** con al menos una calificación. De ellas, **22.645** tienen pesos cuya suma difiere de 1 utilizando una tolerancia de 0,01.

El total de pesos observado por inscripción varía entre **0,10 y 3,31**.

Clasificación: advertencia no bloqueante del dato fuente.

Decisión:

- No modificar arbitrariamente los pesos en Silver.
- Preservar los valores recibidos.
- Documentar el hallazgo.
- Para calcular una nota ponderada comparable en Gold, evaluar la normalización:

```sql
SUM(score * weight) / NULLIF(SUM(weight), 0)
```

Esta regla deberá quedar identificada como una decisión de negocio y no como una corrección silenciosa de la fuente.

## 5. Colisiones de correo en contactos CRM

Se detectaron **4 registros**, correspondientes a **2 direcciones de correo repetidas**, en `crm.contacts`.

Los registros poseen identificadores, cuentas u otros atributos diferentes, por lo que no se consideran duplicados completos y no se eliminaron automáticamente.

Decisión:

- Conservar los registros.
- Tratar el correo como atributo descriptivo, no como clave primaria.
- Registrar la colisión de clave natural como advertencia.

## 6. Reconciliación financiera

### 6.1. Facturas frente a líneas de factura

- **2.502 facturas** no tienen líneas asociadas.
- **47.497 facturas con líneas** presentan una diferencia superior a 0,01 entre `invoices.total` y la suma de `invoice_items.line_total`.
- Solo **1 factura con líneas** reconcilia dentro de la tolerancia de 0,01.
- El indicador combinado `invoice_items_match_header = False` afecta a **49.999 facturas** porque incluye tanto las 2.502 facturas sin líneas como las 47.497 facturas con diferencia.

Decisión analítica:

- Utilizar `invoices.total` como fuente para KPIs de facturación de cabecera.
- Utilizar `invoice_items.line_total` para análisis de productos y composición de ventas.
- No reemplazar un importe por otro ni mezclarlos sin indicar la fuente de la métrica.
- Mostrar por separado las facturas sin líneas y las facturas con líneas que no reconcilian, evitando doble conteo.
- Utilizar el indicador de 49.999 únicamente cuando se describa explícitamente como alerta combinada.

### 6.2. Facturas frente a pagos

- **18.567 facturas** no tienen pagos asociados.
- **8 facturas** quedan balanceadas dentro de una tolerancia de 0,01.
- **29.510 facturas** presentan saldo pendiente material superior a 0,01.
- **20.482 facturas** presentan pagos superiores al total de cabecera por más de 0,01.
- Sin aplicar la tolerancia, **29.515 facturas** tienen un saldo positivo; cinco de ellas tienen exactamente 0,01 y no se consideran materiales. Esta cifra no se utiliza como KPI oficial.

Decisión analítica:

- Calcular facturación y pagos como métricas separadas.
- Utilizar `is_outstanding = True` como contrato oficial para respetar la tolerancia monetaria de 0,01.
- Usar el balance únicamente con una advertencia sobre la falta de reconciliación del origen.
- No inferir automáticamente que un sobrepago sea un error o un crédito sin una regla de negocio explícita.

## 7. Relación entre dominios

Se confirmó una relación confiable entre Billing y University:

```text
billing.customers.external_ref = university.students.student_id
```

Resultados:

- `billing.customers` contiene 10.000 clientes.
- 5.000 clientes tienen `external_ref` nulo.
- Los otros 5.000 valores de `external_ref` corresponden a los 5.000 estudiantes.
- Todos los estudiantes tienen correspondencia en Billing.

Esta relación permitirá integrar desempeño académico, inscripciones, suscripciones, facturas y pagos en Gold.

CRM no dispone de una clave compartida suficientemente confiable con Billing o University. Por ello se modelará como un mart comercial separado, evitando uniones basadas únicamente en coincidencias débiles de nombre o correo.

## 8. Criterio de severidad

### Validación bloqueante

Una regla bloqueante detecta un problema que impide confiar en la ejecución técnica del pipeline, por ejemplo:

- pérdida de filas;
- claves primarias inválidas;
- claves foráneas huérfanas;
- imposibilidad de interpretar fechas configuradas;
- valores fuera de rangos técnicos obligatorios.

Una validación bloqueante fallida debe detener la ejecución.

### Advertencia no bloqueante

Una advertencia identifica una anomalía del sistema fuente que debe documentarse y tratarse explícitamente, pero no demuestra un fallo técnico del pipeline.

## 9. Estado

La capa Silver se considera completada porque:

- las 18 tablas se generan de forma reproducible;
- todas las validaciones bloqueantes pasan;
- las anomalías de fuente permanecen visibles;
- las decisiones de tratamiento están documentadas;
- el pipeline puede avanzar hacia el diseño de Gold.
