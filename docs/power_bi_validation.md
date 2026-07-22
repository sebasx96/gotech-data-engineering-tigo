# Auditoría de Power BI

## Alcance

Esta auditoría documenta la estructura confirmada del archivo
`powerbi/gotech_bootcamp_dashboard.pbix`. El PBIX no fue modificado durante el
cierre del proyecto. Las pruebas que requieren abrir Power BI Desktop se
registran como pendientes y no se presentan como ejecutadas.

## Resultado de la inspección estructural

| Elemento | Resultado |
|---|---:|
| Páginas | 5 |
| Visuales | 68 |
| Tablas del modelo, incluida la tabla de medidas | 8 |
| Segmentador de moneda | Confirmado en la página 03 |

### Páginas y visuales

| Página | Visuales | Alcance principal |
|---|---:|---|
| 01 Resumen Ejecutivo | 12 | KPIs y visión integral |
| 02 Rendimiento Académico | 12 | Inscripciones, notas y aprobación |
| 03 Facturación y Productos | 15 | Facturación, cobranzas, productos y moneda |
| 04 Suscripciones y Student 360 | 14 | Portafolio, estado y vista del estudiante |
| 05 CRM | 15 | Leads, oportunidades y pipeline comercial |
| **Total** | **68** | |

La página **03 Facturación y Productos** contiene un segmentador basado en
`Fact Invoice[currency]`. El modelo mantiene CRM en una página separada, de
acuerdo con la falta de una clave confiable para relacionarlo con estudiantes.

### Tablas identificadas en el modelo

1. `Dim Student`
2. `Fact Academic`
3. `Fact Invoice`
4. `Fact Product Sales`
5. `Fact Subscription`
6. `Fact Opportunity`
7. `Fact Lead`
8. `Kpi Measures`

## Contrato de métricas financieras

Las definiciones recomendadas para la próxima edición manual del PBIX se
encuentran en
[power_bi_dashboard_blueprint.md](power_bi_dashboard_blueprint.md). Deben
interpretarse así:

| Métrica | Definición | Conteo esperado |
|---|---|---:|
| Facturas sin líneas | `has_invoice_items = FALSE` | 2.502 |
| Diferencias cabecera–detalle estrictas | Tiene líneas y `invoice_items_match_header = FALSE` | 47.497 |
| Alerta combinada de ítems | Sin líneas o con diferencia | 49.999 |
| Facturas con saldo material | `is_outstanding = TRUE`, tolerancia 0,01 | 29.510 |
| Saldo positivo bruto | `outstanding_amount > 0`, sin tolerancia | 29.515 |

Los indicadores estrictos y combinados no deben sumarse entre sí. El indicador
oficial de facturas pendientes es el que aplica la tolerancia de 0,01.

## Validaciones manuales pendientes

Las siguientes pruebas requieren Power BI Desktop y quedan pendientes:

- Abrir el PBIX y ejecutar una actualización completa sin errores.
- Confirmar que las siete tablas analíticas y `Kpi Measures` estén disponibles.
- Revisar que las relaciones esperadas estén activas, con cardinalidad y
  dirección de filtro correctas.
- Confirmar que las tablas CRM permanezcan sin relaciones artificiales con
  estudiantes.
- Validar que el segmentador de moneda sea de selección única y filtre todos
  los KPIs y gráficos monetarios de la página 03.
- Comparar tarjetas y totales contra PostgreSQL y el notebook Gold.
- Probar selección cruzada, limpieza de filtros y navegación en las cinco
  páginas.
- Revisar que no existan visuales en blanco, mensajes de error, textos cortados
  ni formatos numéricos inconsistentes.
- Aplicar manualmente las medidas DAX recomendadas y volver a comprobar los
  conteos antes de guardar una nueva versión.

## Estado

| Validación | Estado |
|---|---|
| Estructura del archivo | Confirmada |
| Conteo de páginas, visuales y tablas | Confirmado |
| Presencia del segmentador de moneda | Confirmada estructuralmente |
| Interacciones y filtros en Power BI Desktop | Pendiente |
| Actualización de medidas DAX dentro del PBIX | No ejecutada |
| Modificación del PBIX durante este cierre | No realizada |
