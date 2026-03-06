import re
from errors import HydraError

TOKEN_TYPES = [
    ('MULTILINE_COMMENT', r'/\*[\s\S]*?\*/'),
    ('COMMENT',       r'//.*'),
    ('FLOAT_LITERAL', r'\d+\.\d+'),
    ('INT_LITERAL',   r'\d+'),
    ('FSTR_LITERAL',  r'\$"(?:\\.|[^"\\])*"'), 
    ('STR_LITERAL',   r'"(?:\\.|[^"\\])*"'),
    ('TRUE',          r'\btrue\b'),
    ('FALSE',         r'\bfalse\b'),
    ('NULL',          r'\bnull\b'),
    ('KEYWORD',       r'\b(int|float|str|bool|void|auto|if|elseif|else|while|for|foreach|function|array|return|switch|case|def|break|continue|lib|class|const|local|global|try|catch)\b'),
    
    ('OP_IN',         r'∈|\bin\b'),
    ('OP_NOTIN',      r'∉|\bnotin\b'),
    ('OP_SUBSET',     r'⊂|\bsubset\b'),
    ('OP_SUPERSET',   r'⊃|\bsuperset\b'),
    ('OP_UNION',      r'∪|\bunion\b'),
    ('OP_INTERSECT',  r'∩|\bintersect\b'),
    
    ('ID',            r'[a-zA-Z_π∞][a-zA-Z0-9_π∞]*'),
    ('DOUBLE_COLON',  r'::'),
    ('LBLOCK',        r'\[\['),
    ('RBLOCK',        r'\]\]'),
    ('LPAREN',        r'\('),
    ('RPAREN',        r'\)'),
    ('LBRACE',        r'\{'),
    ('RBRACE',        r'\}'),
    ('LBRACKET',      r'\['),
    ('RBRACKET',      r'\]'),
    ('COLON',         r':'),
    ('SEMI',          r';'),
    ('COMMA',         r','),
    ('DOT',           r'\.'),
    ('OP_QUESTION',   r'\?'), 
    
    ('OP_AND_LOGIC',  r'&&'),
    ('OP_OR_LOGIC',   r'\|\|'),
    ('OP_INC',        r'\+\+'),
    ('OP_DEC',        r'--'),
    ('OP_LSHIFT_EQ',  r'<<='),
    ('OP_RSHIFT_EQ',  r'>>='),
    ('OP_PLUS_EQ',    r'\+='),
    ('OP_MINUS_EQ',   r'-='),
    ('OP_MUL_EQ',     r'\*='),
    ('OP_DIV_EQ',     r'/='),
    ('OP_MOD_EQ',     r'%='),
    ('OP_AND_EQ',     r'&='),
    ('OP_OR_EQ',      r'\|='),
    ('OP_XOR_EQ',     r'\^='),
    ('OP_LSHIFT',     r'<<'),
    ('OP_RSHIFT',     r'>>'),
    ('OP_EQ',         r'=='),
    ('OP_NEQ',        r'!=|≠'),
    ('OP_LTE',        r'<='),
    ('OP_GTE',        r'>='),
    ('OP_APPROX',     r'≈|~='),
    
    ('OP_NOT_LOGIC',  r'!'),
    ('OP_LT',         r'<'),
    ('OP_GT',         r'>'),
    ('ASSIGN',        r'='),
    ('OP_PLUS',       r'\+'),
    ('OP_MINUS',      r'-'),
    ('OP_POW',        r'\*\*'),
    ('POST_POW2',     r'²'),
    ('POST_POW3',     r'³'),
    ('OP_MUL',        r'\*|×'),
    ('OP_DIV',        r'/|÷'),
    ('OP_MOD',        r'%'),
    ('OP_AND',        r'&'),
    ('OP_OR',         r'\|'),
    ('OP_XOR',        r'\^'),
    ('OP_NOT',        r'~'),
    ('OP_LEN',        r'#'), 
    ('WHITESPACE',    r'\s+'),
]

class Token:
    def __init__(self, type_, value, line, col):
        self.type, self.value, self.line, self.col = type_, value, line, col
        self.length = len(value)
    def __repr__(self): return f"Token({self.type}, {repr(self.value)})"

def lex(code):
    lines = code.split('\n')
    tokens, line_num, col_num, pos = [], 1, 1, 0
    
    while pos < len(code):
        match = None
        for token_type, regex in TOKEN_TYPES:
            regex_match = re.match(regex, code[pos:])
            if regex_match:
                value = regex_match.group(0)
                if token_type not in ['WHITESPACE', 'COMMENT', 'MULTILINE_COMMENT']:
                    tokens.append(Token(token_type, value, line_num, col_num))
                newlines = value.count('\n')
                if newlines > 0:
                    line_num += newlines
                    col_num = len(value) - value.rfind('\n')
                else: col_num += len(value)
                pos += len(value); match = True; break
        if not match:
            err_line = lines[line_num - 1] if line_num <= len(lines) else ""
            raise HydraError(f"Unrecognized character '{code[pos]}'", line_num, col_num, err_line)
    return tokens, lines