### 📄 **Conversor de Extrato Novadax para Koinly**  

Este script converte extratos da corretora **Novadax** (no formato CSV) para um arquivo **CSV** no padrão **Koinly**, facilitando a importação e análise das transações de compra, venda, taxas e saques.

---

## 🚀 **Como Usar**  

### **1. Instale as dependências**  
- Certifique-se de ter o **Python 3** instalado em seu sistema.  
- O script utiliza apenas bibliotecas da **biblioteca padrão do Python** (como `csv`, `re`, `datetime`, `unicodedata`), então **nenhuma instalação adicional** via `pip` é necessária.

Se quiser verificar se o Python 3 está instalado, use:
```bash
python --version
```
ou 
```bash
python3 --version
```

---

### **2. Estrutura de Arquivos**  
📁 Projeto/  
├── 📄 `converter_novadax_koinly.py` *(Script de conversão)*  
├── 📄 `novadax.csv` *(Arquivo CSV original da Novadax)*  
└── 📄 `novadax_koinly_custom.csv` *(Arquivo CSV gerado para o Koinly)*  

---

### **3. Código do Script**  
Salve o código abaixo em um arquivo chamado `converter_novadax_koinly.py`:

```python
import csv
from datetime import datetime
import re
import unicodedata

def normalize_str(s: str) -> str:
    """
    Remove acentos e caracteres especiais, retornando texto em ascii basico,
    tudo em minúsculo, p/ facilitar comparação.
    """
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()

def convert_date(novadax_date: str) -> str:
    """
    Converte data/hora do formato 'DD/MM/YYYY HH:MM:SS' para 'YYYY-MM-DD HH:MM UTC'.
    Se falhar, retorna 'Invalid Date'.
    """
    try:
        dt = datetime.strptime(novadax_date, "%d/%m/%Y %H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return "Invalid Date"

def extract_numeric_value(text: str) -> str:
    """
    Extrai o primeiro número (podendo ter sinal + ou -), remove separadores de milhar,
    converte vírgula em ponto decimal, sem arredondar.
    Se não encontrar nenhum número, retorna string vazia.
    """
    # Remove o trecho '(≈R$...)' que confunde a extração
    temp = re.sub(r'\(≈R\\$[^)]*\)', '', text)

    # Localiza todos os números (c/ ou s/ sinal)
    matches = re.findall(r'[+-]?\s*\d[\d.,]*', temp)
    if not matches:
        return ""  # Nenhum número encontrado

    # Por padrão, pega o PRIMEIRO número
    raw_val = matches[0]

    # Remove espaços internos: '- 1,234' -> '-1,234'
    raw_val = re.sub(r'\s+', '', raw_val)

    # Troca vírgula decimal por ponto
    raw_val = raw_val.replace(',', '.')

    # Se houver mais de um ponto, pode ser separador de milhar
    parts = raw_val.split('.')
    if len(parts) > 2:
        # Último item = parte decimal, o resto = milhar
        decimal_part = parts[-1]
        thousand_parts = parts[:-1]
        raw_val = ''.join(thousand_parts) + '.' + decimal_part

    return raw_val

def process_novadax_row(row):
    """
    Converte uma linha do CSV da Novadax em uma linha do CSV no padrão Koinly,
    mantendo campos vazios quando não há dados.
    """
    if len(row) < 5:
        return ["Invalid Row"] * 12

    data_str, tipo_str, moeda, valor_str, status = row[:5]

    # Converte data
    date = convert_date(data_str)

    # Normaliza o texto de tipo p/ facilitar comparação (remove acentos, lowercase)
    tipo_normalizado = normalize_str(tipo_str)

    # Extrai valor numérico principal
    valor = extract_numeric_value(valor_str)

    # Inicializa campos do Koinly
    sent_amount = ""
    sent_currency = ""
    received_amount = ""
    received_currency = ""
    fee_amount = ""
    fee_currency = ""
    label = ""
    description = tipo_str  # Texto original na descrição

    # Verifica qual tipo de operação
    if "taxa de transacao" in tipo_normalizado:
        fee_amount = valor
        fee_currency = moeda
    elif "taxa de saque de criptomoedas" in tipo_normalizado:
        fee_amount = valor
        fee_currency = moeda
    elif "deposito em reais" in tipo_normalizado:
        # Dinheiro que entra
        received_amount = valor
        received_currency = moeda
    elif "redeemed bonus" in tipo_normalizado:
        # Bônus que entra
        received_amount = valor
        received_currency = moeda
        label = "reward"
    elif "compra" in tipo_normalizado:
        # Compra => se moeda for BRL, é 'Sent'. Se não, é cripto 'Received'
        if moeda.upper() == "BRL":
            sent_amount = valor
            sent_currency = "BRL"
        else:
            received_amount = valor
            received_currency = moeda
    elif "venda" in tipo_normalizado:
        # Venda => se moeda for BRL, é 'Received'. Se não, é cripto 'Sent'
        if moeda.upper() == "BRL":
            received_amount = valor
            received_currency = "BRL"
        else:
            sent_amount = valor
            sent_currency = moeda
    elif "saque de criptomoedas" in tipo_normalizado:
        # Saque => cripto sai
        sent_amount = valor
        sent_currency = moeda

    # Retorna a linha no formato do Koinly
    return [
        date,
        sent_amount,
        sent_currency,
        received_amount,
        received_currency,
        fee_amount,
        fee_currency,
        "",  # Net Worth Amount
        "",  # Net Worth Currency
        label,
        description,
        "",  # TxHash
    ]

def convert_novadax_to_koinly(input_file, output_file):
    """
    Lê o CSV da Novadax (input_file) e gera um CSV no formato Koinly (output_file).
    """
    with open(input_file, mode='r', encoding='utf-8') as infile, \
         open(output_file, mode='w', encoding='utf-8', newline='') as outfile:

        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        # Cabeçalho Koinly
        writer.writerow([
            "Date", "Sent Amount", "Sent Currency",
            "Received Amount", "Received Currency",
            "Fee Amount", "Fee Currency",
            "Net Worth Amount", "Net Worth Currency",
            "Label", "Description", "TxHash"
        ])

        # Pula a linha de cabeçalho do CSV da Novadax
        next(reader, None)

        for row in reader:
            koinly_row = process_novadax_row(row)
            writer.writerow(koinly_row)

if __name__ == "__main__":
    input_file = "novadax.csv"
    output_file = "novadax_koinly_custom.csv"
    convert_novadax_to_koinly(input_file, output_file)
    print(f"Arquivo convertido salvo em: {output_file}")
```

---

### **4. Como Executar**  

No terminal ou prompt de comando, vá até a pasta onde o script está salvo e execute:

```bash
python converter_novadax_koinly.py
```

Por padrão, ele vai ler o arquivo chamado **`novadax.csv`** e gerar outro chamado **`novadax_koinly_custom.csv`**.

---

### **5. Resultado**  

- O arquivo CSV resultante (ex: `novadax_koinly_custom.csv`) terá as **12 colunas** exigidas pelo Koinly:  
  1. `Date`  
  2. `Sent Amount`  
  3. `Sent Currency`  
  4. `Received Amount`  
  5. `Received Currency`  
  6. `Fee Amount`  
  7. `Fee Currency`  
  8. `Net Worth Amount`  
  9. `Net Worth Currency`  
  10. `Label`  
  11. `Description`  
  12. `TxHash`  

- Cada linha corresponderá a **uma linha** do CSV original da Novadax.  
- O campo `Date` será convertido para o formato **`YYYY-MM-DD HH:MM UTC`**.  
- Os valores numéricos serão extraídos automaticamente (excluindo texto como `R$` ou `≈R$...`).  
- A coluna **`Label`** será preenchida com `reward` se for um `Redeemed Bonus` e vazia nos outros casos, exceto quando for detectada `taxa` ou `depósito em reais`.

---

### 🛠️ **Personalização**  

- Para alterar o **arquivo de entrada**, mude a variável `input_file` no final do script (ex: `"novadax_2024.csv"`).  
- Para definir o **nome do arquivo de saída**, ajuste `output_file` (ex: `"koinly_pronto.csv"`).  
- Caso surja algum novo tipo de transação da Novadax, ajuste a função `process_novadax_row` para mapear corretamente.

---

💡 **Dica:**  
- Confirme se o **CSV original** da Novadax possui ao menos 5 colunas na ordem:  
  1. DataHora  
  2. Tipo  
  3. Moeda  
  4. Valor  
  5. Status  
- Se o script encontrar menos de 5 colunas em uma linha, ele marca como **Invalid Row**.  
- Se desejar preencher o `TxHash` ou `Net Worth Amount`, você pode editar o script para adequar às suas necessidades.

---

📌 **Licença**  
Este script é de uso livre. Personalize e adapte conforme suas necessidades! 😎
