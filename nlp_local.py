"""
nlp_local.py - Enhanced local natural language to Boolean logic parser
Handles complex expressions with multiple conditions
"""

import re
import itertools
from typing import Dict, List, Set, Tuple

class LocalNLParser:
    """
    Convert natural language to Boolean logic
    """
    
    def __init__(self):
        # Biological terms mapping
        self.variable_keywords = {
            'iptg': 'IPTG',
            'atc': 'aTc',
            'aTc': 'aTc',
            'arabinose': 'Arabinose',
            'ara': 'Arabinose',
        }
        
        # Words to ignore
        self.ignore_words = {
            'a', 'an', 'the', 'and', 'or', 'not', 'but', 'for', 'with', 'without',
            'when', 'then', 'than', 'that', 'this', 'these', 'those', 'is', 'are',
            'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'shall', 'should', 'may', 'might', 'must', 'can', 'could',
            'turn', 'turns', 'turned', 'turning', 'on', 'off', 'activate', 'activates',
            'circuit', 'gate', 'input', 'output', 'present', 'absent', 'both', 'either',
            'neither', 'nor', 'all', 'any', 'some', 'none', 'works', 'working', 'work',
            'want', 'need', 'like', 'make', 'create', 'build', 'design', 'give', 'get',
            'put', 'set', 'see', 'show', 'display', 'high', 'low', 'true', 'false',
            'yes', 'no', '1', '0', 'conditions', 'following', 'below', 'above', 'using'
        }
    
    def parse(self, text: str) -> Dict:
        """
        Parse natural language to Boolean expression
        """
        text = text.lower()
        
        # Step 1: Extract all variables
        variables = self._extract_variables(text)
        
        # Step 2: Parse into terms (split by OR)
        terms = self._split_into_terms(text)
        
        # Step 3: Parse each term into literals
        expression_parts = []
        for term in terms:
            term_expr = self._parse_term(term, variables)
            if term_expr:
                expression_parts.append(term_expr)
        
        # Step 4: Combine with OR
        if expression_parts:
            expression = '+'.join(expression_parts)
        else:
            expression = '.'.join(variables)

        expression = expression.replace(' ', '')
        
        # Step 5: Generate truth table
        truth_table = self._generate_truth_table(expression, variables)
        
        return {
            'expression': expression,
            'variables': list(set(variables)),  # Remove duplicates
            'truth_table': truth_table,
            'original_text': text
        }
    
    def _extract_variables(self, text: str) -> List[str]:
        """Extract all biological variables from text"""
        found = []
        
        for keyword, var in self.variable_keywords.items():
            if keyword in text:
                if var not in found:
                    found.append(var)
        
        return found
    
    def _split_into_terms(self, text: str) -> List[str]:
        """Split the text into OR-separated terms"""
        # Look for OR indicators
        or_indicators = [' or ', ' either ', ' alternatively ', ' otherwise ']
        
        # Try to split by bullet points first
        if '- ' in text or '* ' in text:
            # Split by bullet points
            lines = text.split('\n')
            terms = []
            for line in lines:
                if line.strip().startswith('-') or line.strip().startswith('*'):
                    # Remove bullet and clean
                    term = re.sub(r'^[-*\s]+', '', line.strip())
                    if term:
                        terms.append(term)
            if terms:
                return terms
        
        # Try to split by OR indicators
        for indicator in or_indicators:
            if indicator in text:
                return [t.strip() for t in text.split(indicator) if t.strip()]
        
        # Default: return whole text as one term
        return [text]
    
    def _parse_term(self, term: str, all_vars: List[str]) -> str:
        """Parse a single term (AND conditions) into literals"""
        collective_expr = self._parse_collective_term(term, all_vars)
        if collective_expr:
            return collective_expr
        
        # Split by AND indicators
        and_indicators = [' and ', ' & ', ' both ', ' together ']
        
        parts = [term]
        for indicator in and_indicators:
            new_parts = []
            for part in parts:
                if indicator in part:
                    new_parts.extend([p.strip() for p in part.split(indicator) if p.strip()])
                else:
                    new_parts.append(part)
            parts = new_parts
        
        # If no AND split found, just use the term
        if len(parts) == 1 and (' and ' not in term) and (' & ' not in term):
            parts = [term]
        
        # Parse each part into a literal
        literals = []
        seen_vars = set()
        
        for part in parts:
            lit = self._parse_literal(part, all_vars)
            if lit:
                var_name = lit.replace("'", "")
                if var_name not in seen_vars:
                    literals.append(lit)
                    seen_vars.add(var_name)
        
        if literals:
            return '.'.join(literals)
        return ''

    def _parse_collective_term(self, term: str, all_vars: List[str]) -> str:
        """Parse grouped statements like 'IPTG, aTc, Arabinose are all absent'."""
        term_lower = term.lower()
        ordered_vars = [var for var in all_vars if var.lower() in term_lower]

        if len(ordered_vars) < 2:
            return ''

        absent_patterns = [
            'all absent', 'are all absent', 'all off',
            'all low', 'all false', 'none present', 'none are present'
        ]
        present_patterns = [
            'all present', 'are all present', 'all on',
            'all high', 'all true'
        ]

        if any(pattern in term_lower for pattern in absent_patterns):
            return '.'.join(f"{var}'" for var in ordered_vars)

        if any(pattern in term_lower for pattern in present_patterns):
            return '.'.join(ordered_vars)

        return ''
    
    def _parse_literal(self, part: str, all_vars: List[str]) -> str:
        """Parse a single literal (variable with possible NOT)"""
        part = part.lower()
        
        # Check for NOT indicators
        not_indicators = ['not ', 'absent', 'without ', 'missing', 'no ', 'none', 'false']
        is_not = any(ind in part for ind in not_indicators)
        
        # Find which variable this is
        for var in all_vars:
            var_lower = var.lower()
            if var_lower in part:
                if is_not:
                    return f"{var}'"
                else:
                    return var
                
        result = result.replace(' ', '')
        return ''
    
    def _generate_truth_table(self, expression: str, variables: List[str]) -> List[Dict]:
        """Generate truth table from Boolean expression"""
        if not variables or not expression:
            return []
        
        # Remove duplicates
        variables = list(set(variables))
        
        # Create short variable names for evaluation
        var_map = {}
        short_vars = []
        for i, var in enumerate(variables):
            short = chr(65 + i)  # A, B, C, ...
            var_map[short] = var
            short_vars.append(short)
        
        # Convert expression to use short variables
        short_expr = expression
        for i, var in enumerate(variables):
            short = chr(65 + i)
            # Handle NOT (variable with prime)
            if f"{var}'" in short_expr:
                short_expr = short_expr.replace(f"{var}'", f"(not {short})")
            # Handle plain variable
            elif var in short_expr:
                # Use word boundaries to avoid partial matches
                short_expr = re.sub(rf'\b{re.escape(var)}\b', short, short_expr)
        
        # Replace operators
        short_expr = short_expr.replace('.', ' and ').replace('+', ' or ')
        
        # Generate all combinations
        truth_table = []
        for combo in itertools.product([0, 1], repeat=len(short_vars)):
            row = {}
            # Map values to short variables
            for i, val in enumerate(combo):
                row[short_vars[i]] = val
            
            # Create evaluation context
            context = {}
            for i, val in enumerate(combo):
                context[short_vars[i]] = bool(val)
            
            # Evaluate expression
            try:
                result = int(eval(short_expr, {"__builtins__": {}}, context))
            except:
                result = 0
            
            # Map back to original variable names
            display_row = {}
            for i, val in enumerate(combo):
                display_row[variables[i]] = val
            display_row['output'] = result
            
            truth_table.append(display_row)
        
        return truth_table
    
    def interactive(self):
        """Run interactive mode"""
        print("\n" + "="*60)
        print("🧬 GeneTech Natural Language Parser")
        print("="*60)
        print("Describe your circuit in plain English:")
        print("Examples:")
        print("  • Simple: 'IPTG and aTc'")
        print("  • With NOT: 'IPTG but not aTc'")
        print("  • Complex:")
        print("    a circuit that turns on when:")
        print("    - IPTG is absent AND aTc is absent")
        print("    - OR IPTG is present AND aTc is present")
        print("="*60)
        
        while True:
            print("\n📝 Enter your request (or 'quit' to exit):")
            text = input("> ").strip()
            
            if text.lower() in ['quit', 'exit', 'q']:
                break
            
            if not text:
                continue
            
            result = self.parse(text)
            
            print("\n" + "="*60)
            print("📊 RESULTS")
            print("="*60)
            print(f"\n✅ Expression: {result['expression']}")
            print(f"\n📋 Variables: {', '.join(result['variables'])}")
            
            # Show truth table
            if result['truth_table']:
                print("\n📋 Truth Table:")
                headers = list(result['truth_table'][0].keys())
                print("   " + " | ".join(headers))
                print("   " + "-" * (5 * len(headers) + 2))
                for row in result['truth_table'][:8]:  # Show first 8 rows
                    values = [str(row[h]) for h in headers]
                    print("   " + " | ".join(values))


# Test
if __name__ == "__main__":
    parser = LocalNLParser()
    
    # Test your complex expression
    complex_text = """a circuit that turns on when:
- IPTG is absent AND aTc is absent AND Arabinose is absent, OR
- IPTG is present AND aTc is absent AND Arabinose is absent, OR
- IPTG is present AND aTc is absent AND Arabinose is present, OR
- IPTG is present AND aTc is present AND Arabinose is present"""
    
    print("\n" + "="*70)
    print("🧪 TESTING COMPLEX EXPRESSION")
    print("="*70)
    print(f"\n📝 Input:\n{complex_text}")
    
    result = parser.parse(complex_text)
    
    print(f"\n✅ Output: {result['expression']}")
    print(f"📋 Variables: {result['variables']}")
    
    # Show truth table for verification
    if result['truth_table']:
        print("\n📋 Truth Table (first 8 rows):")
        headers = list(result['truth_table'][0].keys())
        print("   " + " | ".join(headers))
        print("   " + "-" * (5 * len(headers) + 2))
        for i, row in enumerate(result['truth_table'][:8]):
            values = [str(row[h]) for h in headers]
            print("   " + " | ".join(values))
