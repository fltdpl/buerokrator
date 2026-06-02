# Datenmodell

## Tabelle documents

- id
- filename
- original_filename
- document_type
- issuer
- document_date
- amount
- tax_relevant
- archive_path
- created_at

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

### Relevante Entscheidungen  
  
- [[001_sqlite]]