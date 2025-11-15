#!/usr/bin/env python3
"""Convert generated mantras to template format.

Ported from ai-conditioner-web/legacy/python-implementation/utils/convert_lines.py
Enhanced with JSON support and better error handling.
"""
import os
import re
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class TemplateConverter:
    """Converts mantras with pronouns to template variables."""

    def __init__(self, verb_conjugations_path: Optional[str] = None):
        """Initialize converter.

        Args:
            verb_conjugations_path: Path to verb conjugations file (default: verb_conjugations.txt in script dir)
        """
        if verb_conjugations_path is None:
            verb_conjugations_path = Path(__file__).parent / 'verb_conjugations.txt'

        self.verbs_1ps, self.verbs_1pp, self.verbs_2ps, self.verbs_3ps = self._load_verb_conjugations(verb_conjugations_path)

    def _load_verb_conjugations(self, filepath) -> Tuple[Dict, Dict, Dict, Dict]:
        """Load verb conjugation mappings from file.

        File format:
          go|goes          (2 forms: base|third-person-singular)
          am|are|are|is    (4 forms: 1ps|1pp|2ps|3ps)

        Returns:
            Tuple of (1ps_dict, 1pp_dict, 2ps_dict, 3ps_dict)
        """
        verb_templates_1ps = {}
        verb_templates_1pp = {}
        verb_templates_2ps = {}
        verb_templates_3ps = {}

        with open(filepath, 'r', encoding='utf-8') as file:
            for line in file:
                conjugations = line.strip().split('|')
                if len(conjugations) == 2:  # format is "go|goes"
                    verb_templates_1ps[conjugations[0]] = line.strip()  # I go
                    verb_templates_1pp[conjugations[0]] = line.strip()  # we go
                    verb_templates_2ps[conjugations[0]] = line.strip()  # you go
                    verb_templates_3ps[conjugations[1]] = line.strip()  # she goes
                elif len(conjugations) == 4:  # format is "am|are|are|is"
                    verb_templates_1ps[conjugations[0]] = line.strip()  # I am
                    verb_templates_1pp[conjugations[1]] = line.strip()  # we are
                    verb_templates_2ps[conjugations[2]] = line.strip()  # you are
                    verb_templates_3ps[conjugations[3]] = line.strip()  # she is

        return verb_templates_1ps, verb_templates_1pp, verb_templates_2ps, verb_templates_3ps

    def convert_line(self, line: str, subject_name: str = "Slave", dominant_name: str = "Master") -> Tuple[str, List[str]]:
        """Convert a single line to template format.

        Args:
            line: Input text with pronouns (e.g., "I trust Master")
            subject_name: Named subject for 3rd person detection (default: "Slave")
            dominant_name: Named dominant for 3rd person detection (default: "Master")

        Returns:
            Tuple of (converted_line, warnings_list)
        """
        warnings = []

        # Check for ambiguous pronouns before conversion
        ambiguous_matches = re.findall(r'\b(you|her)\b', line, re.IGNORECASE)
        for match in ambiguous_matches:
            if match.lower() == 'you':
                warnings.append(f"'you' is ambiguous (subjective vs objective): {line.strip()}")
            if match.lower() == 'her':
                warnings.append(f"'her' is ambiguous (possessive vs objective): {line.strip()}")

        # Pronoun replacement patterns
        patterns = {
            re.compile(rf'\b{subject_name}\b', re.IGNORECASE): '{subject_name}',  # subject name (3rd person)
            re.compile(rf'\b{dominant_name}\b', re.IGNORECASE): '{dominant_name}',  # dominant name (3rd person)
            re.compile(r'\bi(\'|\')m\b', re.IGNORECASE): '{subject_subjective} am',  # no contractions
            re.compile(r'\bwe(\'|\')re\b', re.IGNORECASE): '{subject_subjective} am',  # convert 1pp→1ps
            re.compile(r'\bi\b', re.IGNORECASE): '{subject_subjective}',
            re.compile(r'\bwe\b', re.IGNORECASE): '{subject_subjective}',
            re.compile(r'\bmy|mine\b', re.IGNORECASE): '{subject_possessive}',
            re.compile(r'\bme\b', re.IGNORECASE): '{subject_objective}',
            re.compile(r'\bus\b', re.IGNORECASE): '{subject_objective}',
            re.compile(r'\byou\'re\b', re.IGNORECASE): '{dominant_subjective} are',
            re.compile(r'\bthey\'re\b', re.IGNORECASE): '{dominant_subjective} are',
            re.compile(r'\byou\b', re.IGNORECASE): '{dominant_subjective}',  # WARNING: ambiguous
            re.compile(r'\bshe\b', re.IGNORECASE): '{dominant_subjective}',
            re.compile(r'\bhe\b', re.IGNORECASE): '{dominant_subjective}',
            re.compile(r'\bhim\b', re.IGNORECASE): '{dominant_objective}',
            re.compile(r'\bthem\b', re.IGNORECASE): '{dominant_objective}',
            re.compile(r'\byour|yours\b', re.IGNORECASE): '{dominant_possessive}',
            re.compile(r'\bhis\b', re.IGNORECASE): '{dominant_possessive}',
            re.compile(r'\bher|hers\b', re.IGNORECASE): '{dominant_possessive}',  # WARNING: ambiguous
            re.compile(r'\btheir|theirs\b', re.IGNORECASE): '{dominant_possessive}',
            re.compile(r'\b(girl|boy)\b', re.IGNORECASE): '{subject_gender_noun}',
        }

        # Apply pronoun replacements
        for pattern, replacement in patterns.items():
            line = pattern.sub(replacement, line)

        # Verb conjugation wrapping
        # Pattern: {subject_name} <verb> → {subject_name} [verb_conjugations]
        matches = re.findall(r'\{subject_name\}\s+(\w+\b(?:\'\w+)?)', line, re.IGNORECASE)
        for match in matches:
            verb_original = match
            verb = verb_original.lower()
            if verb in self.verbs_3ps:
                pattern = r'(?<!\[)\b' + re.escape(verb_original) + r'\b(?!\])'
                replacement = "[" + self.verbs_3ps[verb] + "]"
                line = re.sub(pattern, replacement, line, flags=re.IGNORECASE)
            else:
                warnings.append(f"Verb '{verb}' not found in 3ps conjugations")

        # {dominant_name} <verb>
        matches = re.findall(r'\{dominant_name\}\s+(\w+\b(?:\'\w+)?)', line, re.IGNORECASE)
        for match in matches:
            verb_original = match
            verb = verb_original.lower()
            if verb in self.verbs_3ps:
                pattern = r'(?<!\[)\b' + re.escape(verb_original) + r'\b(?!\])'
                replacement = "[" + self.verbs_3ps[verb] + "]"
                line = re.sub(pattern, replacement, line, flags=re.IGNORECASE)
            else:
                warnings.append(f"Verb '{verb}' not found in 3ps conjugations")

        # {subject_subjective} <verb>
        matches = re.findall(r'\{subject(_subjective)?\}\s+(\w+\b(?:\'\w+)?)', line, re.IGNORECASE)
        for match in matches:
            verb_original = match[1]
            verb = verb_original.lower()
            if verb in self.verbs_1ps or verb in self.verbs_1pp:
                pattern = r'(?<!\[)\b' + re.escape(verb_original) + r'\b(?!\])'
                # Use 1ps by default (singular subject)
                replacement = "[" + self.verbs_1ps.get(verb, self.verbs_1pp.get(verb, verb)) + "]"
                line = re.sub(pattern, replacement, line, flags=re.IGNORECASE)
            else:
                warnings.append(f"Verb '{verb}' not found in 1ps or 1pp conjugations")

        # {dominant_subjective} <verb>
        matches = re.findall(r'\{dominant(_subjective)?\}\s+(\w+)\b', line, re.IGNORECASE)
        for match in matches:
            verb_original = match[1]
            verb = verb_original.lower()
            if verb in self.verbs_2ps or verb in self.verbs_3ps:
                pattern = r'(?<!\[)\b' + re.escape(verb_original) + r'\b(?!\])'
                # Use 2ps by default (you)
                replacement = "[" + self.verbs_2ps.get(verb, self.verbs_3ps.get(verb, verb)) + "]"
                line = re.sub(pattern, replacement, line, flags=re.IGNORECASE)

        # Warn about gender nouns
        gender_matches = re.findall(r'\b(boy|girl)\b', line, re.IGNORECASE)
        for match in gender_matches:
            warnings.append(f"Gender noun '{match}' found - may need {{subject_gender_noun}}")

        return line, warnings

    def convert_file(self, input_path: str, output_path: str, subject_name: str = "Slave", dominant_name: str = "Master") -> None:
        """Convert a text file line by line.

        Args:
            input_path: Input file path
            output_path: Output file path
            subject_name: Named subject
            dominant_name: Named dominant
        """
        with open(input_path, 'r', encoding='utf-8') as infile:
            lines = infile.readlines()

        with open(output_path, 'w', encoding='utf-8') as outfile:
            for line in lines:
                converted, warnings = self.convert_line(line, subject_name, dominant_name)
                outfile.write(converted)

                # Print warnings to stderr
                for warning in warnings:
                    print(f"[warn] {warning}", file=sys.stderr)

        print(f"[ok] File processed: {output_path}", file=sys.stderr)

    def convert_mantras(self, mantras: List[Dict], subject_name: str = "Slave", dominant_name: str = "Master") -> List[Dict]:
        """Convert list of mantra dicts with 'line' field.

        Args:
            mantras: List of dicts with 'line' key
            subject_name: Named subject
            dominant_name: Named dominant

        Returns:
            List of mantras with 'template' field added
        """
        results = []

        for mantra in mantras:
            if 'line' not in mantra:
                print(f"[warn] Mantra missing 'line' field: {mantra}", file=sys.stderr)
                continue

            converted, warnings = self.convert_line(mantra['line'], subject_name, dominant_name)

            result = mantra.copy()
            result['template'] = converted.strip()

            if warnings:
                result['conversion_warnings'] = warnings
                for warning in warnings:
                    print(f"[warn] {warning}", file=sys.stderr)

            results.append(result)

        return results


def main():
    """CLI interface for template converter."""
    parser = argparse.ArgumentParser(description="Convert mantras to template format")

    parser.add_argument('--input', type=str, help='Input file (text or JSON)')
    parser.add_argument('--output', type=str, help='Output file')
    parser.add_argument('--dominant', type=str, default='Master', help='Dominant name (default: Master)')
    parser.add_argument('--subject', type=str, default='Slave', help='Subject name (default: Slave)')
    parser.add_argument('--json', action='store_true', help='Input/output is JSON format with "line" field')
    parser.add_argument('--test', action='store_true', help='Run test conversions')

    args = parser.parse_args()

    converter = TemplateConverter()

    if args.test or not args.input:
        # Test conversions
        test_lines = [
            "I trust Master completely.",
            "I obey Master's commands.",
            "My will belongs to Master.",
            "Master guides me deeper.",
            "I feel safe when Master controls me.",
        ]

        print("[info] Running test conversions:", file=sys.stderr)
        for line in test_lines:
            converted, warnings = converter.convert_line(line)
            print(f"\n  Original:  {line}")
            print(f"  Template:  {converted.strip()}")
            if warnings:
                print(f"  Warnings:  {len(warnings)} warning(s)")

    if args.input:
        if args.json:
            # JSON mode
            with open(args.input, 'r', encoding='utf-8') as f:
                mantras = json.load(f)

            converted = converter.convert_mantras(mantras, args.subject, args.dominant)

            output_path = args.output or args.input.replace('.json', '_templated.json')
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(converted, f, indent=2, ensure_ascii=False)

            print(f"[ok] Converted {len(converted)} mantras to {output_path}", file=sys.stderr)

        else:
            # Text mode
            output_path = args.output or args.input.replace('.txt', '_templated.txt')
            converter.convert_file(args.input, output_path, args.subject, args.dominant)


if __name__ == '__main__':
    main()
