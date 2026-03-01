import re
import os

def resolve_taxonomy_mismatches(file_path='hypnosis_taxonomy.md'):
    if not os.path.exists(file_path):
        return

    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    technique_def_pattern = re.compile(r'^(?:#+|\*|-)\s*(?:[A-Za-z\s*_-]+)?\b([A-Z]{3,5}-\d{2})\b')
    defined_techniques = set()
    for line in lines:
        match = technique_def_pattern.search(line)
        if match:
            defined_techniques.add(match.group(1))

    matrix_start_idx = -1
    matrix_end_idx = len(lines)
    matrix_header_pattern = re.compile(r'(?i)Phase-Technique Compatibility Matrix')
    
    for i, line in enumerate(lines):
        if matrix_header_pattern.search(line):
            matrix_start_idx = i
            break

    if matrix_start_idx == -1:
        return

    for i in range(matrix_start_idx + 1, len(lines)):
        if lines[i].startswith('##') and not lines[i].startswith('###'):
            matrix_end_idx = i
            break

    matrix_lines = lines[matrix_start_idx:matrix_end_idx]
    
    tech_ref_pattern = re.compile(r'\b([A-Z]{3,5}-\d{2})\b')
    referenced_techniques = set()
    table_start = -1
    table_end = -1
    
    for i, line in enumerate(matrix_lines):
        if '|' in line:
            if table_start == -1:
                table_start = i
            table_end = i + 1
            referenced_techniques.update(tech_ref_pattern.findall(line))

    orphans = defined_techniques - referenced_techniques

    if not orphans:
        return

    category_mapping = {
        'PLEA-02': 'Suggestion / Conditioning',
        'PLEA-03': 'Suggestion / Deepening',
        'PLEA-04': 'Induction / Arousal',
        'PLEA-05': 'Trance Maintenance',
    }
    
    orphan_groups = {}
    invalid_orphans = set()
    
    for orphan in orphans:
        if orphan in category_mapping:
            orphan_groups.setdefault(category_mapping[orphan], []).append(orphan)
        else:
            invalid_orphans.add(orphan)

    new_matrix_lines = matrix_lines[:]
    
    if table_start != -1 and orphan_groups:
        for cat, techs in orphan_groups.items():
            placed = False
            for i in range(table_start, table_end):
                row = new_matrix_lines[i]
                parts = row.split('|')
                if len(parts) > 2 and '---' not in row:
                    phase_col = parts[1].strip().lower()
                    if cat.split(' / ')[0].lower() in phase_col:
                        parts[2] = parts[2].rstrip() + f", {', '.join(techs)} "
                        new_matrix_lines[i] = '|'.join(parts) + '\n'
                        placed = True
                        break
            if not placed:
                new_row = f"| {cat} | {', '.join(techs)} |\n"
                new_matrix_lines.insert(table_end, new_row)
                table_end += 1

    lines = lines[:matrix_start_idx] + new_matrix_lines + lines[matrix_end_idx:]

    if invalid_orphans:
        filtered_lines = []
        skip_mode = False
        for line in lines:
            match = technique_def_pattern.search(line)
            if match and match.group(1) in invalid_orphans:
                skip_mode = True
                continue
            
            if skip_mode:
                if line.startswith('#') or (line.startswith('-') and not line.startswith('  ')):
                    skip_mode = False
                else:
                    continue
            
            if not skip_mode:
                filtered_lines.append(line)
        lines = filtered_lines

    with open(file_path, 'w', encoding='utf-8') as file:
        file.writelines(lines)

if __name__ == "__main__":
    resolve_taxonomy_mismatches()