# Datenmodell

## Tabelle documents

- id
- filename
- archive_path
- document_type
- extracted_data
- created_at
- verified
- document_text
- notes

## Tabelle financial_products  
  
- id  
- product_type (Rentenversicherung, Bausparvertrag, etc.)  
- provider  
- contract_start  
- contract_number  
- monthly_contribution  
- status

## Tabelle tax_entries

- id
- document_id
- category
- tax_year
- deductible_amount

## Tabelle learning_rules

- id
- pattern
- category
- confidence

## Dokumentenschema

json:

```json
{
	"document_type": "",
	"issuer": "",
	"document_date": "",
	"amount": null,
	"tax_relevant": false,
	"tags": []
}
```

Fachspezifische Felder wie `issuer`, `document_date`, `amount`,
`invoice_number`, `policy_number` oder `tax_year` werden aktuell in
`documents.extracted_data` als JSON gespeichert.



### Relevante Entscheidungen  
  
- [[001_sqlite]]
