# Datos de entrada

El pipeline espera 18 archivos CSV bajo `data/raw`.

```text
data/raw/
├── university/
│   ├── semesters.csv
│   ├── professors.csv
│   ├── students.csv
│   ├── courses.csv
│   ├── enrollments.csv
│   └── grades.csv
├── billing/
│   ├── customers.csv
│   ├── products.csv
│   ├── subscriptions.csv
│   ├── invoices.csv
│   ├── invoice_items.csv
│   └── payments.csv
└── crm/
    ├── accounts.csv
    ├── contacts.csv
    ├── leads.csv
    ├── opportunities.csv
    ├── opportunity_contacts.csv
    └── activities.csv
```

Las carpetas `data/bronze`, `data/silver` y `data/gold` son salidas derivadas y se reconstruyen al ejecutar el pipeline.

El ZIP de entrega incluye los datos Raw para permitir la reproducción. En el repositorio público pueden excluirse si las condiciones de distribución del dataset así lo requieren.
