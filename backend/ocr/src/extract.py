import re
from typing import List, Dict, Optional



# ============================================================
#  FUNCIÓN PRINCIPAL — DETECTA TIPO DE DOCUMENTO Y EXTRAE
# ============================================================

def extract_albaran_data(
    text: str,
    ocr_data_list: Optional[List[Dict]] = None,
    doc_type: Optional[str] = None
) -> Dict:

    if doc_type is None:
        doc_type = _detect_doc_type(text)

    # -----------------------------
    # PACKING LIST INGLÉS
    # -----------------------------
    if doc_type == 'ingles':
        productos = extract_english_products(text)
        total_weight = extract_english_total(text)
        return {
            'doc_type': doc_type,
            'total_productos': len(productos),
            'productos': productos,
            'total_weight': total_weight
        }

    # -----------------------------
    # ALBARÁN ESPAÑOL COMERCIAL
    # -----------------------------
    if doc_type == 'español_comercial':
        productos = extract_spanish_commercial_products(text)
        return {
            'doc_type': doc_type,
            'total_productos': len(productos),
            'productos': productos
        }

    # -----------------------------
    # ALBARÁN PORTUGUÉS (LONJA)
    # -----------------------------
    if ocr_data_list:
        productos = []
        for ocr_data in ocr_data_list:
            productos.extend(extract_productos_from_ocr_data(ocr_data))
    else:
        productos = extract_productos(text)

    return {
        'doc_type': doc_type,
        'total_productos': len(productos),
        'productos': productos
    }


# ============================================================
#  DETECCIÓN DE TIPO DE DOCUMENTO
# ============================================================

def _detect_doc_type(text: str) -> str:
    text_up = text.upper()

    # PACKING LIST INGLÉS
    english_markers = [
        'PACKING LIST', 'DESCRIPTION OF GOODS',
        'WITHOUT GLAZE', 'WITH GLAZE', 'CTNS'
    ]
    if any(marker in text_up for marker in english_markers):
        return 'ingles'

    # ALBARÁN ESPAÑOL COMERCIAL
    six_digit_lines = re.findall(r'^\d{6}\s+[A-Z]', text_up, re.MULTILINE)
    if len(six_digit_lines) >= 2:
        return 'español_comercial'

    # DEFAULT → LONJA PORTUGUESA
    return 'portugues'


# ============================================================
#  EXTRACTOR ESPAÑOL COMERCIAL
# ============================================================

def extract_spanish_commercial_products(text: str) -> List[Dict]:
    lines = text.split('\n')
    products = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        prod_match = re.match(r'^(\d{6})\s+(.+)', line)
        if not prod_match:
            continue

        codigo = prod_match.group(1)
        rest = prod_match.group(2).strip()

        if 'DESCRIPCI' in rest.upper() or 'TOTAL' in rest.upper():
            continue

        iva_match = re.search(r'(\d+,\d{2})\s+(\d+,\d{2}|\d+)\s+\b(4|10|21)\b', rest)
        if iva_match:
            cantidad_str = iva_match.group(1)
            precio_raw = iva_match.group(2)

            if ',' in precio_raw:
                precio = float(precio_raw.replace(',', '.'))
            else:
                precio = int(precio_raw) / 100.0

            cantidad = float(cantidad_str.replace(',', '.'))
        else:
            price_numbers = re.findall(r'(?<![,\d])\d+,\d{2}(?!\d)', rest)
            if len(price_numbers) < 2:
                continue
            cantidad = float(price_numbers[0].replace(',', '.'))
            precio = float(price_numbers[1].replace(',', '.'))
            cantidad_str = price_numbers[0]

        first_pos = rest.find(cantidad_str)
        desc_raw = rest[:first_pos].strip()
        desc_raw = re.sub(r'\s+\d+\s*$', '', desc_raw).strip()
        descripcion = re.sub(r'\s+', ' ', desc_raw).strip()

        products.append({
            'lote': codigo,
            'cajas': 0,
            'especie': descripcion,
            'peso_kg': cantidad,
            'linea_original': line,
            'nombre': descripcion,
            'cantidad': cantidad,
            'precio': precio
        })

    return products


# ============================================================
#  EXTRACTOR PACKING LIST INGLÉS
# ============================================================

def extract_english_products(text: str) -> List[Dict]:
    text_up = text.upper()

    for token in [
        'IQF LIGHT SALTED PACIFIC COD',
        'IQF LIGHT SALTED SAITHE',
        'FROZEN GIGAS SQUID TUBE',
        'IQF GIGAS SQUID RING'
    ]:
        text_up = text_up.replace(' ' + token, '\n' + token)

    lines = [line.strip() for line in text_up.split('\n') if line.strip()]
    products = []
    i = 0

    while i < len(lines):
        line_up = lines[i].upper()

        if _is_english_product_start(line_up):
            block = [lines[i]]
            i += 1

            while i < len(lines):
                next_up = lines[i].upper()
                if _is_english_product_start(next_up) or next_up.startswith('TOTAL'):
                    break
                block.append(lines[i])
                i += 1

            product = _parse_english_product_block(block)
            if product:
                products.append(product)
            continue

        i += 1

    return products


def _is_english_product_start(line_up: str) -> bool:
    if 'PACKING:' in line_up or 'SIZE:' in line_up:
        return False
    tokens = ['PACIFIC COD', 'SAITHE', 'SQUID TUBE', 'SQUID RING']
    return any(t in line_up for t in tokens)


def _parse_english_product_block(block: List[str]) -> Optional[Dict]:
    title = block[0].strip()
    combined = ' '.join(block).upper()

    sci_match = re.search(r'\(([A-Z\s]{5,})\)', combined)
    scientific_name = sci_match.group(1).strip() if sci_match else _fallback_scientific_name(title)

    packing = ''
    packing_qty = ''
    for line in block:
        p_match = re.search(r'PACKING\s*:\s*(.+)$', line, re.IGNORECASE)
        if p_match:
            packing = p_match.group(1).strip()
            packing_qty = _extract_packing_qty(packing)
            break

    ctns_lines_with_glaze = []
    all_kgs_values = []
    ctns = 0

    for line in block:
        line_up = line.upper()
        has_ctns = 'CTNS' in line_up
        has_kgs = 'KGS' in line_up

        if has_ctns:
            ctns_match = re.search(r'(\d+)\s*CTNS', line_up)
            if ctns_match:
                ctns = max(ctns, int(ctns_match.group(1)))

        if has_ctns and has_kgs:
            kgs_tokens = re.findall(r'([A-Z0-9][A-Z0-9\.,]*)\s*KGS', line_up)
            kgs_values_line = []

            for token in kgs_tokens:
                parsed = _parse_ocr_float_token(token)
                if parsed is not None:
                    kgs_values_line.append(parsed)
                    all_kgs_values.append(parsed)

            if kgs_values_line:
                ctns_lines_with_glaze.append(kgs_values_line[-1])

    if ctns_lines_with_glaze:
        peso_with_glaze = ctns_lines_with_glaze[-1]
    elif all_kgs_values:
        peso_with_glaze = all_kgs_values[-1]
    else:
        peso_with_glaze = None

    return {
        'lote': '',
        'cajas': ctns,
        'especie': scientific_name,
        'scientific_name': scientific_name,
        'peso_kg': peso_with_glaze,
        'packing': packing,
        'packing_qty': packing_qty,
        'linea_original': title
    }


def _fallback_scientific_name(title: str) -> str:
    title_up = title.upper()
    if 'SQUID TUBE' in title_up:
        return 'GIGAS SQUID TUBE'
    if 'SQUID RING' in title_up:
        return 'GIGAS SQUID RING'
    return re.sub(r'\s+', ' ', title).strip()


def _extract_packing_qty(packing_text: str) -> str:
    normalized = packing_text.upper()
    normalized = re.sub(r'\bI\s*KG\b', '1KG', normalized)
    normalized = re.sub(r'\bIKG\b', '1KG', normalized)
    normalized = re.sub(r'\b1I1\s*KG\b', '11KG', normalized)

    match = re.search(r'(\d+\s*X\s*\d+\s*KG|\d+\s*KG)', normalized)
    return re.sub(r'\s+', ' ', match.group(1)).strip() if match else ''


def extract_english_total(text: str) -> Optional[float]:
    text_up = text.upper()
    lines = text_up.split('\n')

    for line in lines:
        if 'TOTAL' in line and ('WITH GLAZE' in line or 'WITHGLAZE' in line or 'W/GLAZE' in line):
            kgs_tokens = re.findall(r'([A-Z0-9][A-Z0-9\.,]*)\s*KGS', line)
            for token in kgs_tokens:
                parsed = _parse_ocr_float_token(token)
                if parsed is not None:
                    return parsed

    for line in lines:
        if 'TOTAL' in line and 'KGS' in line:
            kgs_tokens = re.findall(r'([A-Z0-9][A-Z0-9\.,]*)\s*KGS', line)
            parsed_values = [v for v in (_parse_ocr_float_token(t) for t in kgs_tokens) if v is not None]

            if len(parsed_values) >= 3:
                return parsed_values[-2]
            if parsed_values:
                return parsed_values[-1]

    return None


def _parse_ocr_float_token(token: str) -> Optional[float]:
    t = token.upper()
    replacements = {'O': '0', 'I': '1', 'L': '1', 'S': '5', 'B': '8', 'Z': '2'}
    normalized = ''.join(replacements.get(ch, ch) for ch in t)
    normalized = re.sub(r'[^0-9\.,]', '', normalized)

    if not normalized:
        return None

    if normalized.count('.') + normalized.count(',') > 1:
        last_sep = max(normalized.rfind('.'), normalized.rfind(','))
        integer = re.sub(r'[^0-9]', '', normalized[:last_sep])
        decimal = re.sub(r'[^0-9]', '', normalized[last_sep + 1:])
        normalized = f"{integer}.{decimal}" if decimal else integer
    else:
        normalized = normalized.replace(',', '.')

    try:
        return float(normalized)
    except:
        return None


# ============================================================
#  EXTRACTOR PORTUGUÉS (LONJA) — ORIGINAL COMPLETO
# ============================================================

def extract_productos_from_ocr_data(ocr_data: Dict) -> List[Dict]:
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
            'precio': float(precio) if precio else None,
            'linea_original': line_text.strip()
        }
        productos.append(producto)

    return productos


def extract_productos(text: str) -> List[Dict]:
    productos = []
    lines = text.split('\n')

    for line in lines:
        match = re.match(r'^\s*(\d{3,5})\s+(\d+)\s+([A-Z0-9][A-Z0-9\-\s/]+)', line, re.IGNORECASE)

        if match:
            lote = match.group(1)
            cajas = match.group(2)
            especie_raw = match.group(3).strip()
            especie = clean_especie_name(especie_raw, line)

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

            cajas_match = re.search(r'(\d+)\s*(?:Cxs|cajas|Cxa)', line, re.IGNORECASE)
            if cajas_match:
                cajas = cajas_match.group(1)

            producto = {
                'lote': lote,
                'cajas': int(cajas),
                'especie': especie,
                'peso_kg': float(peso) if peso else None,
                'precio': float(precio) if precio else None,
                'linea_original': line.strip()
            }

            productos.append(producto)

    return productos


# ============================================================
#  FUNCIONES AUXILIARES DE LONJA (ORIGINALES)
# ============================================================

def clean_especie_name(especie_raw: str, full_line: str) -> str:
    stop_words = [
        'Esp', 'Cientifica', 'Fao', 'Apres', 'Peso', 'Preco',
        'Val', 'IVA', 'Parapenaeus', 'Merluccius', 'Trachurus',
        'Lepidorhombus', 'Micromesistius', 'DPS', 'HKE', 'HOW',
        'LDB', 'WHB', 'Inte', 'HRE'
    ]

    words = especie_raw.split()
    clean_words = []

    for word in words:
        if any(stop in word for stop in stop_words):
            break
        clean_words.append(word)

    especie_clean = ' '.join(clean_words).strip()
    especie_clean = re.sub(r'[^\w\s\-/]+$', '', especie_clean)

    return especie_clean if especie_clean else especie_raw


def extract_totales(text: str) -> Dict:
    totales = {}

    quilos_match = re.search(r'Total\s+Quilos[.:\s]+(\d+[,\.]\d+)', text, re.IGNORECASE)
    if quilos_match:
        totales['total_kg'] = float(quilos_match.group(1).replace(',', '.'))

    cajas_match = re.search(r'Numero\s+Cxs[/Cbz/Dornas]*[.:\s]+(\d+)', text, re.IGNORECASE)
    if cajas_match:
        totales['total_cajas'] = int(cajas_match.group(1))

    return totales


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

