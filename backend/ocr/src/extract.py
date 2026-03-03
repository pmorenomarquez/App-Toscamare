import re
from typing import List, Dict, Optional


def extract_albaran_data(text: str, ocr_data_list: Optional[List[Dict]] = None) -> Dict:
    """
    Extrae productos y cantidades de un albarán de lonja
    
    Args:
        text: Texto extraído por OCR
    
    Returns:
        Dict con productos y sus cantidades
    """
    if ocr_data_list:
        productos = []
        for ocr_data in ocr_data_list:
            productos.extend(extract_productos_from_ocr_data(ocr_data))
    else:
        productos = extract_productos(text)
    
    return {
        'total_productos': len(productos),
        'productos': productos
    }


def extract_productos_from_ocr_data(ocr_data: Dict) -> List[Dict]:
    """
    Extrae productos usando datos OCR con coordenadas para elegir el peso correcto.

    Args:
        ocr_data: Dict con salida de pytesseract.image_to_data

    Returns:
        Lista de diccionarios con informacion de productos
    """
    productos = []
    lines = _build_lines_from_ocr_data(ocr_data)
    peso_x_header = _find_column_x(lines, [r'^peso$'])
    precio_x = _find_column_x(lines, [r'^preco$', r'^precio$'])
    val_x = _find_rightmost_column_x(lines, [r'^val\.?$', r'^valor$', r'^val\.pesc\.?$', r'^valpesc\.?$'])
    peso_x_infer, peso_tol = _infer_weight_column(lines)
    peso_x = peso_x_header if peso_x_header is not None else peso_x_infer

    for line in lines:
        line_text = line['text']
        match = re.match(r'^\s*(\d{3,5})\s+(\d+)\s+([A-Z0-9][A-Z0-9\-\s/]+)', line_text, re.IGNORECASE)
        if not match:
            continue

        lote = match.group(1)
        cajas = match.group(2)
        especie_raw = match.group(3).strip()
        especie = clean_especie_name(especie_raw, line_text)

        peso = _select_weight_from_line(
            line['words'],
            peso_x=peso_x,
            peso_tol=peso_tol,
            val_x=val_x
        )
        if peso is None:
            peso = _select_weight_from_text(line_text)

        precio = _select_decimal_from_line(line['words'], precio_x, peso_tol)
        val = _select_decimal_from_line(line['words'], val_x, peso_tol)
        if precio is None or val is None:
            precio, val = _select_price_and_value_from_text(line_text)

        peso = _reconcile_weight(peso, precio, val)

        producto = {
            'lote': lote,
            'cajas': int(cajas),
            'especie': especie,
            'peso_kg': float(peso) if peso else None,
            'precio': float(precio) if precio else None, #########################################
            'linea_original': line_text.strip()
        }
        productos.append(producto)

    return productos


def _build_lines_from_ocr_data(ocr_data: Dict) -> List[Dict]:
    lines = {}
    count = len(ocr_data.get('text', []))

    for i in range(count):
        word = (ocr_data['text'][i] or '').strip()
        if not word:
            continue

        try:
            conf = float(ocr_data['conf'][i])
        except Exception:
            conf = -1

        if conf < 30:
            continue

        key = (
            ocr_data.get('block_num', [0])[i],
            ocr_data.get('par_num', [0])[i],
            ocr_data.get('line_num', [0])[i]
        )
        left = ocr_data['left'][i]
        width = ocr_data['width'][i]
        x_center = left + (width / 2.0)

        lines.setdefault(key, []).append({
            'text': word,
            'x': x_center,
            'left': left
        })

    line_entries = []
    for _, words in lines.items():
        words_sorted = sorted(words, key=lambda w: w['left'])
        line_text = ' '.join(w['text'] for w in words_sorted)
        line_entries.append({'text': line_text, 'words': words_sorted})

    return line_entries


def _find_column_x(lines: List[Dict], patterns: List[str]) -> Optional[float]:
    xs = []
    for line in lines:
        for word in line['words']:
            for pattern in patterns:
                if re.match(pattern, word['text'], re.IGNORECASE):
                    xs.append(word['x'])
                    break

    if not xs:
        return None

    xs.sort()
    mid = len(xs) // 2
    return xs[mid]


def _find_rightmost_column_x(lines: List[Dict], patterns: List[str]) -> Optional[float]:
    xs = []
    for line in lines:
        for word in line['words']:
            for pattern in patterns:
                if re.match(pattern, word['text'], re.IGNORECASE):
                    xs.append(word['x'])
                    break

    if not xs:
        return None

    return max(xs)


def _select_weight_from_line(
    words: List[Dict],
    peso_x: Optional[float],
    peso_tol: Optional[float],
    val_x: Optional[float]
) -> Optional[str]:
    candidates = []
    for word in words:
        if re.match(r'^\d+[,\.]\d+$', word['text']):
            is_one_decimal = bool(re.match(r'^\d+[,\.]\d$', word['text']))
            candidates.append({
                'text': word['text'],
                'x': word['x'],
                'one_decimal': is_one_decimal
            })

    if not candidates:
        return None

    if peso_x is not None:
        candidates.sort(key=lambda c: (0 if c['one_decimal'] else 1, abs(c['x'] - peso_x)))
        best = candidates[0]

        if peso_tol is not None and abs(best['x'] - peso_x) > peso_tol:
            return None

        if val_x is not None:
            if abs(best['x'] - peso_x) >= abs(best['x'] - val_x):
                return None

        return best['text'].replace(',', '.')

    return _select_weight_from_text(' '.join(c['text'] for c in candidates))


def _select_decimal_from_line(
    words: List[Dict],
    target_x: Optional[float],
    tol: Optional[float]
) -> Optional[str]:
    if target_x is None:
        return None

    candidates = []
    for word in words:
        if re.match(r'^\d+[,\.]\d+$', word['text']):
            candidates.append({'text': word['text'], 'x': word['x']})

    if not candidates:
        return None

    candidates.sort(key=lambda c: abs(c['x'] - target_x))
    best = candidates[0]

    if tol is not None and abs(best['x'] - target_x) > tol:
        return None

    return best['text'].replace(',', '.')


def _infer_weight_column(lines: List[Dict]) -> (Optional[float], Optional[float]):
    xs = []
    for line in lines:
        for word in line['words']:
            if re.match(r'^\d+[,\.]\d$', word['text']):
                xs.append(word['x'])

    if not xs:
        return None, None

    min_x = min(xs)
    max_x = max(xs)
    bucket_size = max(30.0, (max_x - min_x) / 20.0)

    buckets = {}
    for x in xs:
        bucket = int(round((x - min_x) / bucket_size))
        buckets.setdefault(bucket, []).append(x)

    best_bucket = max(buckets.items(), key=lambda item: len(item[1]))[1]
    center = _median(best_bucket)
    deviations = [abs(x - center) for x in best_bucket]
    dev = _median(deviations) if deviations else bucket_size
    tol = max(dev * 3.0, bucket_size * 2.0)

    return center, tol


def _median(values: List[float]) -> float:
    values_sorted = sorted(values)
    mid = len(values_sorted) // 2
    if len(values_sorted) % 2 == 0:
        return (values_sorted[mid - 1] + values_sorted[mid]) / 2.0
    return values_sorted[mid]


def _select_weight_from_text(line: str) -> Optional[str]:
    peso_matches = re.findall(r'(\d+[,\.]\d+)', line)
    if not peso_matches:
        return None

    peso_one_decimal = [p for p in peso_matches if re.match(r'^\d+[,\.]\d$', p)]
    if peso_one_decimal:
        return peso_one_decimal[0].replace(',', '.')

    return peso_matches[-1].replace(',', '.')


def _select_price_and_value_from_text(line: str) -> (Optional[str], Optional[str]):
    matches = re.findall(r'(\d+[,\.]\d+)', line)
    if len(matches) < 2:
        return None, None

    precio = matches[1]
    val = matches[2] if len(matches) > 2 else None
    return precio.replace(',', '.'), val.replace(',', '.') if val else None


def _reconcile_weight(
    peso: Optional[str],
    precio: Optional[str],
    val: Optional[str]
) -> Optional[str]:
    if precio is None or val is None:
        return peso

    try:
        precio_f = float(precio)
        val_f = float(val)
    except ValueError:
        return peso

    if precio_f <= 0 or val_f <= 0:
        return peso

    if peso is None:
        calc = round(val_f / precio_f, 1)
        return f"{calc:.1f}"

    try:
        peso_f = float(peso)
    except ValueError:
        return peso

    expected = peso_f * precio_f
    tolerance = max(0.8, val_f * 0.05)
    if abs(expected - val_f) > tolerance:
        calc = round(val_f / precio_f, 1)
        return f"{calc:.1f}"

    return peso


def extract_productos(text: str) -> List[Dict]:
    """
    Extrae la lista de productos con sus cantidades del texto OCR
    
    Busca patrones como:
    - Lote Cxs Especie ... Peso
    - 1092 1 CARAPAU T1/A ... 7,4
    - 249 1 GAMBA-BRANC-MIU ... 9,9
    
    Args:
        text: Texto del OCR
    
    Returns:
        Lista de diccionarios con información de productos
    """
    productos = []
    
    # Dividir el texto en líneas
    lines = text.split('\n')
    
    for i, line in enumerate(lines):
        # Buscar líneas que parezcan productos
        # Patrón: número (lote) + número (cajas) + nombre especie + ... + peso
        
        # Patrón flexible para capturar diferentes formatos
        # Ejemplo: "1092 1 CARAPAU T1/A ... 7,4"
        # Ejemplo: "249 1 GAMBA-BRANC-MIU Parapenaeus longiros DPS Inte 9,9"
        
        # Buscar líneas que empiecen con número de lote (3-4 dígitos)
        match = re.match(r'^\s*(\d{3,5})\s+(\d+)\s+([A-Z0-9][A-Z0-9\-\s/]+)', line, re.IGNORECASE)
        
        if match:
            lote = match.group(1)
            cajas = match.group(2)
            especie_raw = match.group(3).strip()
            
            # Limpiar el nombre de la especie
            # Tomar solo hasta encontrar palabras que no sean parte del nombre
            especie = clean_especie_name(especie_raw, line)
            
            # Buscar peso en la misma línea (números con coma o punto decimal)
            # Preferir formatos de kg con un decimal (p. ej. 7,4) sobre valores monetarios (11,47)
            peso_matches = re.findall(r'(\d+[,\.]\d+)', line)
            peso = None
            if peso_matches:
                peso_one_decimal = [p for p in peso_matches if re.match(r'^\d+[,\.]\d$', p)]
                if peso_one_decimal:
                    peso = peso_one_decimal[0].replace(',', '.')
                else:
                    peso = peso_matches[-1].replace(',', '.')

            precio, val = _select_price_and_value_from_text(line)
            peso = _reconcile_weight(peso, precio, val)
            
            # Buscar cantidad de cajas adicionales si hay "Cxs" o similar
            cajas_match = re.search(r'(\d+)\s*(?:Cxs|cajas|Cxa)', line, re.IGNORECASE)
            if cajas_match:
                cajas = cajas_match.group(1)
            
            producto = {
                'lote': lote,
                'cajas': int(cajas),
                'especie': especie,
                'peso_kg': float(peso) if peso else None,
                'precio': float(precio) if precio else None, #########################################
                'linea_original': line.strip()
            }
            
            productos.append(producto)
    
    return productos


def clean_especie_name(especie_raw: str, full_line: str) -> str:
    """
    Limpia el nombre de la especie eliminando información extra
    
    Args:
        especie_raw: Nombre crudo de la especie
        full_line: Línea completa para contexto
    
    Returns:
        Nombre limpio de la especie
    """
    # Patrones comunes que indican fin del nombre de especie
    stop_words = [
        'Esp', 'Cientifica', 'Fao', 'Apres', 'Peso', 'Preco',
        'Val', 'IVA', 'Parapenaeus', 'Merluccius', 'Trachurus',
        'Lepidorhombus', 'Micromesistius', 'DPS', 'HKE', 'HOW',
        'LDB', 'WHB', 'Inte', 'HRE'
    ]
    
    words = especie_raw.split()
    clean_words = []
    
    for word in words:
        # Parar si encontramos una palabra que indica datos científicos
        if any(stop in word for stop in stop_words):
            break
        clean_words.append(word)
    
    especie_clean = ' '.join(clean_words).strip()
    
    # Remover caracteres finales no deseados
    especie_clean = re.sub(r'[^\w\s\-/]+$', '', especie_clean)
    
    return especie_clean if especie_clean else especie_raw


def extract_totales(text: str) -> Dict:
    """
    Extrae información de totales del albarán (opcional, por si lo necesitas después)
    
    Args:
        text: Texto del OCR
    
    Returns:
        Dict con totales
    """
    totales = {}
    
    # Buscar total de quilos
    quilos_match = re.search(r'Total\s+Quilos[.:\s]+(\d+[,\.]\d+)', text, re.IGNORECASE)
    if quilos_match:
        totales['total_kg'] = float(quilos_match.group(1).replace(',', '.'))
    
    # Buscar número total de cajas
    cajas_match = re.search(r'Numero\s+Cxs[/Cbz/Dornas]*[.:\s]+(\d+)', text, re.IGNORECASE)
    if cajas_match:
        totales['total_cajas'] = int(cajas_match.group(1))
    
    return totales
