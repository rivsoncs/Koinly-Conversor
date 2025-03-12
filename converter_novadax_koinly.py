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
