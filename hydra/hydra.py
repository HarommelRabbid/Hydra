# Hydra v14 by Harommel

import re
import sys
import math

# ==========================================
# 0. ERROR HANDLER (Enhanced Carets & Padding Fix)
# ==========================================
class HydraError(Exception):
    def __init__(self, msg, line, col, line_text, length=1):
        self.msg, self.line, self.col = msg, line, col
        self.line_text, self.length = line_text, length

    def display(self):
        prefix = f"{self.line} | "
        prefix1 = (" " * len(str(self.line))) + " | "
        padding = " " * (self.col - 1)
        carets = "^" * max(1, self.length)
        sys.stderr.write(f"\nHydra has encountered an error: {self.msg}\n")
        sys.stderr.write(f"--> Line {self.line}, Column {self.col}\n")
        sys.stderr.write(f"{prefix}{self.line_text}\n")
        sys.stderr.write(f"{prefix1}{padding}{carets}\n")

# ==========================================
# 1. LEXER 
# ==========================================
TOKEN_TYPES = [
    ('MULTILINE_COMMENT', r'/\*[\s\S]*?\*/'),
    ('COMMENT',       r'//.*'),
    ('FLOAT_LITERAL', r'\d+\.\d+'),
    ('INT_LITERAL',   r'\d+'),
    ('FSTR_LITERAL',  r'\$"(?:\\.|[^"\\])*"'), # Interpolated Strings
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
    ('OP_QUESTION',   r'\?'), # Ternary Operator
    
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

# ==========================================
# 2. PARSER
# ==========================================
class Parser:
    def __init__(self, tokens, lines):
        self.tokens, self.lines, self.pos = tokens, lines, 0

    def current(self): return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def error(self, msg, token=None):
        line = token.line if token else (self.tokens[self.pos].line if self.pos < len(self.tokens) else len(self.lines))
        col = token.col if token else (self.tokens[self.pos].col if self.pos < len(self.tokens) else len(self.lines[-1]) if self.lines else 1)
        length = token.length if token else 1
        line_text = self.lines[line - 1] if 0 < line <= len(self.lines) else ""
        raise HydraError(f"Parser Error: {msg}", line, col, line_text, length)

    def consume(self, expected_type=None):
        token = self.current()
        if expected_type and (not token or token.type != expected_type):
            err = token.type if token else "EOF"
            self.error(f"Expected {expected_type}, but got {err}", token)
        self.pos += 1; return token

    def parse(self):
        statements = []
        while self.current() is not None: statements.append(self.parse_statement())
        return {'type': 'Program', 'body': statements}

    def parse_statement(self):
        token = self.current()
        if not token: return None
        line, col, length = token.line, token.col, token.length
        node = self._parse_stmt_inner()
        if isinstance(node, dict) and '_line' not in node: 
            node['_line'], node['_col'], node['_length'] = line, col, length
        return node

    def _parse_stmt_inner(self):
        token = self.current()
        if token.type == 'KEYWORD':
            val = token.value
            if val in ['const', 'local', 'global', 'auto', 'int', 'str', 'float', 'bool', 'void']: return self.parse_decl()
            elif val == 'if': return self.parse_if()
            elif val == 'while': return self.parse_while()
            elif val == 'for': return self.parse_for()
            elif val == 'foreach': return self.parse_foreach()
            elif val == 'switch': return self.parse_switch()
            elif val == 'try': return self.parse_try_catch()
            elif val == 'lib': return self.parse_lib()
            elif val == 'class': return self.parse_class()
            elif val == 'return':
                self.consume('KEYWORD')
                if self.current() and self.current().type == 'SEMI':
                    self.consume('SEMI'); return {'type': 'Return', 'value': None}
                expr = self.parse_expr(); self.consume('SEMI')
                return {'type': 'Return', 'value': expr}
            elif val == 'break': self.consume('KEYWORD'); self.consume('SEMI'); return {'type': 'Break'}
            elif val == 'continue': self.consume('KEYWORD'); self.consume('SEMI'); return {'type': 'Continue'}
                
        elif token.type == 'ID':
            next_tok = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            
            if next_tok and next_tok.type == 'ID':
                var_type = self.consume('ID').value; var_name = self.consume('ID').value
                args = []
                if self.current().type == 'LPAREN':
                    self.consume('LPAREN')
                    if self.current().type != 'RPAREN':
                        args.append(self.parse_expr())
                        while self.current().type == 'COMMA': self.consume('COMMA'); args.append(self.parse_expr())
                    self.consume('RPAREN')
                if self.current().type == 'SEMI':
                    self.consume('SEMI'); return {'type': 'VarDecl', 'var_type': var_type, 'name': var_name, 'value': None, 'args': args, 'modifiers': []}
                self.consume('ASSIGN'); val = self.parse_expr(); self.consume('SEMI')
                return {'type': 'VarDecl', 'var_type': var_type, 'name': var_name, 'value': val, 'args': args, 'modifiers': []}
                
            expr = self.parse_primary()
            if self.current() and self.current().type in ['OP_INC', 'OP_DEC']:
                op = self.consume().value; self.consume('SEMI')
                return {'type': 'UpdateObj', 'target': expr, 'operator': op}
            elif self.current() and self.current().type in [
                'ASSIGN', 'OP_PLUS_EQ', 'OP_MINUS_EQ', 'OP_MUL_EQ', 'OP_DIV_EQ', 
                'OP_MOD_EQ', 'OP_LSHIFT_EQ', 'OP_RSHIFT_EQ', 'OP_AND_EQ', 'OP_OR_EQ', 'OP_XOR_EQ'
            ]:
                op = self.consume().value; val = self.parse_expr(); self.consume('SEMI')
                return {'type': 'AssignObj', 'target': expr, 'value': val, 'operator': op}
                
            self.consume('SEMI'); return {'type': 'ExprStmt', 'expr': expr}
        self.error(f"Unexpected statement starting with {token.value}", token)

    def parse_param(self):
        p_type = self.consume('KEYWORD').value if self.current().type == 'KEYWORD' and self.current().value in ['auto', 'int', 'str', 'float', 'bool', 'void'] else 'any'
        p_name = self.consume('ID').value
        if self.current().type == 'ASSIGN': self.consume('ASSIGN'); self.parse_expr()
        return {'type': p_type, 'name': p_name}

    def parse_decl(self):
        modifiers = []
        while self.current() and self.current().type == 'KEYWORD' and self.current().value in ['const', 'local', 'global']:
            modifiers.append(self.consume('KEYWORD').value)
            
        var_type = self.consume('KEYWORD').value
        
        if self.current() and self.current().type == 'ID':
            next_tok = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            if next_tok and next_tok.type == 'DOUBLE_COLON':
                class_name = self.consume('ID').value; self.consume('DOUBLE_COLON')
                keyword_tok = self.consume('KEYWORD')
                if keyword_tok.value != 'function': self.error("Expected 'function'")
                self.consume('DOUBLE_COLON'); name = self.consume('ID').value; self.consume('LPAREN')
                params = []
                if self.current().type != 'RPAREN':
                    params.append(self.parse_param())
                    while self.current().type == 'COMMA': self.consume('COMMA'); params.append(self.parse_param())
                self.consume('RPAREN'); body = self.parse_block()
                return {'type': 'MethodDef', 'class_name': class_name, 'return_type': var_type, 'name': name, 'params': params, 'body': body, 'modifiers': modifiers}

        if self.current() and self.current().type == 'KEYWORD':
            if self.current().value == 'function':
                self.consume('KEYWORD'); self.consume('DOUBLE_COLON')
                name = self.consume('ID').value; self.consume('LPAREN')
                params = []
                if self.current().type != 'RPAREN':
                    params.append(self.parse_param())
                    while self.current().type == 'COMMA': self.consume('COMMA'); params.append(self.parse_param())
                self.consume('RPAREN'); body = self.parse_block()
                return {'type': 'FuncDecl', 'return_type': var_type, 'name': name, 'params': params, 'body': body, 'modifiers': modifiers}
            
            elif self.current().value == 'array':
                next_tok = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
                third_tok = self.tokens[self.pos + 2] if self.pos + 2 < len(self.tokens) else None
                if next_tok and next_tok.type == 'DOUBLE_COLON' and third_tok and third_tok.type == 'KEYWORD' and third_tok.value == 'function':
                    self.consume('KEYWORD'); self.consume('DOUBLE_COLON'); self.consume('KEYWORD'); self.consume('DOUBLE_COLON')
                    name = self.consume('ID').value; self.consume('LPAREN')
                    params = []
                    if self.current().type != 'RPAREN':
                        params.append(self.parse_param())
                        while self.current().type == 'COMMA': self.consume('COMMA'); params.append(self.parse_param())
                    self.consume('RPAREN'); body = self.parse_block()
                    return {'type': 'FuncDecl', 'return_type': 'array', 'name': name, 'params': params, 'body': body, 'modifiers': modifiers}
                else:
                    self.consume('KEYWORD'); self.consume('DOUBLE_COLON')
                    name = self.consume('ID').value
                    if self.current().type == 'SEMI':
                        self.consume('SEMI'); return {'type': 'ArrayDecl', 'var_type': var_type, 'name': name, 'value': None, 'modifiers': modifiers}
                    self.consume('ASSIGN')
                    if self.current().type == 'LBRACE':
                        self.consume('LBRACE'); elements = []
                        if self.current().type != 'RBRACE':
                            elements.append(self.parse_expr())
                            while self.current().type == 'COMMA': self.consume('COMMA'); elements.append(self.parse_expr())
                        self.consume('RBRACE'); self.consume('SEMI')
                        return {'type': 'ArrayDecl', 'var_type': var_type, 'name': name, 'elements': elements, 'modifiers': modifiers}
                    else:
                        expr = self.parse_expr(); self.consume('SEMI')
                        return {'type': 'ArrayDecl', 'var_type': var_type, 'name': name, 'value': expr, 'modifiers': modifiers}
        
        name = self.consume('ID').value; args = []
        if self.current().type == 'LPAREN':
            self.consume('LPAREN')
            if self.current().type != 'RPAREN':
                args.append(self.parse_expr())
                while self.current().type == 'COMMA': self.consume('COMMA'); args.append(self.parse_expr())
            self.consume('RPAREN')
        if self.current().type == 'SEMI':
            self.consume('SEMI'); return {'type': 'VarDecl', 'var_type': var_type, 'name': name, 'value': None, 'args': args, 'modifiers': modifiers}
        self.consume('ASSIGN'); expr = self.parse_expr(); self.consume('SEMI')
        return {'type': 'VarDecl', 'var_type': var_type, 'name': name, 'value': expr, 'args': args, 'modifiers': modifiers}

    def parse_block(self):
        self.consume('LBLOCK'); stmts = []
        while self.current() and self.current().type != 'RBLOCK': stmts.append(self.parse_statement())
        self.consume('RBLOCK'); return stmts

    def parse_try_catch(self):
        self.consume('KEYWORD') # try
        try_body = self.parse_block()
        
        self.consume('KEYWORD') # catch
        catch_var = None
        if self.current() and self.current().type == 'COLON':
            self.consume('COLON')
            if self.current() and self.current().type == 'ID':
                catch_var = self.consume('ID').value
                
        catch_body = self.parse_block()
        return {'type': 'TryCatch', 'try_body': try_body, 'catch_body': catch_body, 'catch_var': catch_var}

    def parse_if(self):
        self.consume('KEYWORD'); self.consume('COLON'); self.consume('LPAREN')
        cond = self.parse_expr(); self.consume('RPAREN'); body = self.parse_block()
        elseifs = []
        while self.current() and self.current().type == 'KEYWORD' and self.current().value == 'elseif':
            self.consume('KEYWORD'); self.consume('COLON'); self.consume('LPAREN')
            e_cond = self.parse_expr(); self.consume('RPAREN'); e_body = self.parse_block()
            elseifs.append({'condition': e_cond, 'body': e_body})
        else_body = None
        if self.current() and self.current().type == 'KEYWORD' and self.current().value == 'else':
            self.consume('KEYWORD'); else_body = self.parse_block()
        return {'type': 'If', 'condition': cond, 'body': body, 'elseifs': elseifs, 'else_body': else_body}

    def parse_lib(self):
        self.consume('KEYWORD'); self.consume('DOUBLE_COLON'); name = self.consume('ID').value; body = self.parse_block()
        return {'type': 'LibDecl', 'name': name, 'body': body}
        
    def parse_class(self):
        self.consume('KEYWORD'); self.consume('DOUBLE_COLON'); name = self.consume('ID').value; body = self.parse_block()
        return {'type': 'ClassDecl', 'name': name, 'body': body}

    def parse_while(self):
        self.consume('KEYWORD'); self.consume('COLON'); self.consume('LPAREN')
        c = self.parse_expr(); self.consume('RPAREN'); b = self.parse_block()
        return {'type': 'While', 'condition': c, 'body': b}

    def parse_for(self):
        self.consume('KEYWORD'); self.consume('COLON'); self.consume('LPAREN')
        decl = self.parse_decl() if self.current().value in ['const','local','global','auto','int','str','float','bool'] else self.parse_statement()
        cond = self.parse_expr(); self.consume('SEMI')
        expr = self.parse_primary()
        if self.current() and self.current().type in ['OP_INC', 'OP_DEC']:
            step = {'type': 'UpdateObj', 'target': expr, 'operator': self.consume().value}
        else:
            op_tok = self.consume(); val = self.parse_expr()
            step = {'type': 'AssignObj', 'target': expr, 'value': val, 'operator': op_tok.value}
        self.consume('RPAREN'); body = self.parse_block()
        return {'type': 'For', 'decl': decl, 'cond': cond, 'step': step, 'body': body}

    def parse_foreach(self):
        self.consume('KEYWORD'); self.consume('COLON'); item = self.consume('ID').value; self.consume('COLON'); arr = self.consume('ID').value
        return {'type': 'Foreach', 'item': item, 'array': arr, 'body': self.parse_block()}

    def parse_switch(self):
        self.consume('KEYWORD'); self.consume('COLON'); self.consume('LPAREN'); v = self.parse_expr(); self.consume('RPAREN'); self.consume('LBLOCK')
        cases = []; default = None
        while self.current() and self.current().type != 'RBLOCK':
            tok = self.consume('KEYWORD')
            if tok.value == 'case':
                self.consume('DOUBLE_COLON'); c_val = self.parse_expr(); self.consume('COLON'); self.consume('LBRACKET'); body = []
                while self.current().type != 'RBRACKET': body.append(self.parse_statement())
                self.consume('RBRACKET'); cases.append({'value': c_val, 'body': body})
            elif tok.value == 'def':
                self.consume('COLON'); self.consume('LBRACKET'); body = []
                while self.current().type != 'RBRACKET': body.append(self.parse_statement())
                self.consume('RBRACKET'); default = body
        self.consume('RBLOCK')
        return {'type': 'Switch', 'variable': v, 'cases': cases, 'default': default}

    def parse_expr(self): 
        return self.parse_ternary()
        
    def parse_ternary(self):
        node = self.parse_logical_or()
        if self.current() and self.current().type == 'OP_QUESTION':
            self.consume('OP_QUESTION')
            true_expr = self.parse_expr()
            self.consume('COLON')
            false_expr = self.parse_expr()
            return {'type': 'TernaryOp', 'condition': node, 'true_expr': true_expr, 'false_expr': false_expr}
        return node
    
    def parse_logical_or(self):
        left = self.parse_logical_and()
        while self.current() and self.current().type == 'OP_OR_LOGIC':
            op = self.consume().value; left = {'type': 'BinOp', 'left': left, 'op': op, 'right': self.parse_logical_and()}
        return left
        
    def parse_logical_and(self):
        left = self.parse_bitwise_or()
        while self.current() and self.current().type == 'OP_AND_LOGIC':
            op = self.consume().value; left = {'type': 'BinOp', 'left': left, 'op': op, 'right': self.parse_bitwise_or()}
        return left
        
    def parse_bitwise_or(self):
        left = self.parse_bitwise_xor()
        while self.current() and self.current().type == 'OP_OR':
            op = self.consume().value; left = {'type': 'BinOp', 'left': left, 'op': op, 'right': self.parse_bitwise_xor()}
        return left
        
    def parse_bitwise_xor(self):
        left = self.parse_bitwise_and()
        while self.current() and self.current().type == 'OP_XOR':
            op = self.consume().value; left = {'type': 'BinOp', 'left': left, 'op': op, 'right': self.parse_bitwise_and()}
        return left
        
    def parse_bitwise_and(self):
        left = self.parse_comp()
        while self.current() and self.current().type == 'OP_AND':
            op = self.consume().value; left = {'type': 'BinOp', 'left': left, 'op': op, 'right': self.parse_comp()}
        return left

    def parse_comp(self):
        left = self.parse_shift()
        while self.current() and self.current().type in ['OP_EQ', 'OP_NEQ', 'OP_LT', 'OP_GT', 'OP_LTE', 'OP_GTE', 'OP_IN', 'OP_NOTIN', 'OP_SUBSET', 'OP_SUPERSET', 'OP_APPROX']:
            op = self.consume().value; left = {'type': 'BinOp', 'left': left, 'op': op, 'right': self.parse_shift()}
        return left
        
    def parse_shift(self):
        left = self.parse_term()
        while self.current() and self.current().type in ['OP_LSHIFT', 'OP_RSHIFT']:
            op = self.consume().value; left = {'type': 'BinOp', 'left': left, 'op': op, 'right': self.parse_term()}
        return left

    def parse_term(self):
        left = self.parse_factor()
        while self.current() and self.current().type in ['OP_PLUS', 'OP_MINUS', 'OP_UNION']:
            op = self.consume().value; left = {'type': 'BinOp', 'left': left, 'op': op, 'right': self.parse_factor()}
        return left
        
    def parse_factor(self):
        left = self.parse_power()
        while self.current() and self.current().type in ['OP_MUL', 'OP_DIV', 'OP_MOD', 'OP_INTERSECT']:
            op = self.consume().value; left = {'type': 'BinOp', 'left': left, 'op': op, 'right': self.parse_power()}
        return left
        
    def parse_power(self):
        left = self.parse_unary()
        while self.current() and self.current().type == 'OP_POW':
            op = self.consume().value; left = {'type': 'BinOp', 'left': left, 'op': op, 'right': self.parse_unary()}
        return left

    def parse_unary(self):
        if self.current() and self.current().type == 'LPAREN':
            next_tok = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            if next_tok and next_tok.type == 'KEYWORD' and next_tok.value in ['int', 'str', 'float', 'bool']:
                third_tok = self.tokens[self.pos + 2] if self.pos + 2 < len(self.tokens) else None
                if third_tok and third_tok.type == 'RPAREN':
                    self.consume('LPAREN'); cast_type = self.consume('KEYWORD').value; self.consume('RPAREN')
                    return {'type': 'Cast', 'cast_type': cast_type, 'expr': self.parse_unary()}
                    
        if self.current() and self.current().type in ['OP_NOT', 'OP_LEN', 'OP_NOT_LOGIC']:
            op = self.consume().value
            return {'type': 'UnaryOp', 'op': op, 'expr': self.parse_unary()}
        return self.parse_primary()

    def parse_primary(self):
        tok = self.consume()
        if tok.type == 'INT_LITERAL': expr = {'type': 'Literal', 'value': int(tok.value), '_length': tok.length}
        elif tok.type == 'FLOAT_LITERAL': expr = {'type': 'Literal', 'value': float(tok.value), '_length': tok.length}
        elif tok.type == 'STR_LITERAL': expr = {'type': 'Literal', 'value': tok.value[1:-1], '_length': tok.length} 
        elif tok.type == 'TRUE': expr = {'type': 'Literal', 'value': True, '_length': tok.length}
        elif tok.type == 'FALSE': expr = {'type': 'Literal', 'value': False, '_length': tok.length}
        elif tok.type == 'NULL': expr = {'type': 'Literal', 'value': None, '_length': tok.length}
        elif tok.type == 'ID': expr = {'type': 'Identifier', 'name': tok.value, '_length': tok.length}
        
        # --- INTERPOLATED STRING PARSING ---
        elif tok.type == 'FSTR_LITERAL':
            raw_str = tok.value[2:-1] 
            parts = []
            i = 0
            curr_text = ""
            while i < len(raw_str):
                # Handle escaping (ignoring escaped curlies)
                if raw_str[i] == '\\' and i + 1 < len(raw_str):
                    if raw_str[i+1] in ['{', '}']:
                        curr_text += raw_str[i+1]
                        i += 2
                        continue
                    else:
                        curr_text += raw_str[i:i+2]
                        i += 2
                        continue
                        
                # Dynamic Expression Block
                if raw_str[i] == '{':
                    if curr_text:
                        parts.append({'type': 'Literal', 'value': curr_text, '_length': 0})
                        curr_text = ""
                    i += 1
                    brace_count = 1
                    expr_str = ""
                    while i < len(raw_str) and brace_count > 0:
                        if raw_str[i] == '{': brace_count += 1
                        elif raw_str[i] == '}': brace_count -= 1
                        if brace_count > 0:
                            expr_str += raw_str[i]
                            i += 1
                            
                    if expr_str.strip():
                        temp_tokens, temp_lines = lex(expr_str)
                        if temp_tokens:
                            temp_parser = Parser(temp_tokens, temp_lines)
                            expr_ast = temp_parser.parse_expr()
                            parts.append(expr_ast)
                    i += 1
                    continue
                    
                curr_text += raw_str[i]
                i += 1
                
            if curr_text: parts.append({'type': 'Literal', 'value': curr_text, '_length': 0})
            expr = {'type': 'FString', 'parts': parts, '_length': tok.length}
        
        elif tok.type == 'LBRACE':
            elements = []
            if self.current().type != 'RBRACE':
                elements.append(self.parse_expr())
                while self.current().type == 'COMMA': self.consume('COMMA'); elements.append(self.parse_expr())
            self.consume('RBRACE')
            expr = {'type': 'ArrayLiteral', 'elements': elements}
            
        elif tok.type == 'LPAREN': expr = self.parse_expr(); self.consume('RPAREN')
        else: self.error(f"Unexpected token in expression: {tok.value}", tok)

        while self.current():
            if self.current().type == 'POST_POW2':
                self.consume('POST_POW2')
                expr = {'type': 'BinOp', 'left': expr, 'op': '**', 'right': {'type': 'Literal', 'value': 2}}
            elif self.current().type == 'POST_POW3':
                self.consume('POST_POW3')
                expr = {'type': 'BinOp', 'left': expr, 'op': '**', 'right': {'type': 'Literal', 'value': 3}}
            elif self.current().type == 'LPAREN':
                self.consume('LPAREN'); args = []
                if self.current().type != 'RPAREN':
                    args.append(self.parse_expr())
                    while self.current().type == 'COMMA': self.consume('COMMA'); args.append(self.parse_expr())
                self.consume('RPAREN'); expr = {'type': 'CallExpr', 'target': expr, 'args': args}
            elif self.current().type == 'LBRACKET':
                self.consume('LBRACKET'); idx = self.parse_expr(); self.consume('RBRACKET')
                expr = {'type': 'ArrayAccess', 'target': expr, 'index': idx}
            elif self.current().type == 'DOT':
                self.consume('DOT'); prop = self.consume('ID').value
                expr = {'type': 'DotAccess', 'target': expr, 'prop': prop}
            else: break
        return expr

# ==========================================
# 3. EVALUATOR 
# ==========================================
class ReturnException(Exception):
    def __init__(self, value): self.value = value
class BreakException(Exception): pass
class ContinueException(Exception): pass

class Environment:
    def __init__(self, parent=None):
        self.vars, self.meta, self.parent = {}, {}, parent
        
    def check_type(self, val, expected_type):
        if val is None: return True 
        if expected_type == 'int': return isinstance(val, int) and not isinstance(val, bool)
        if expected_type == 'float': return isinstance(val, (int, float)) and not isinstance(val, bool)
        if expected_type == 'str': return isinstance(val, str)
        if expected_type == 'bool': return isinstance(val, bool)
        if expected_type == 'array': return isinstance(val, list)
        return True 
        
    def set(self, name, value, var_type='any', modifiers=None):
        self.vars[name] = value
        self.meta[name] = {'type': var_type, 'modifiers': modifiers or []}
        
    def update(self, name, value):
        if name in self.vars:
            meta = self.meta[name]
            if 'const' in meta['modifiers']: raise TypeError(f"Cannot reassign constant variable '{name}'")
            if not self.check_type(value, meta['type']):
                val_type = type(value).__name__.replace('str', 'string')
                raise TypeError(f"Type Mismatch: Cannot assign '{val_type}' to '{meta['type']}' variable '{name}'")
            self.vars[name] = value
        elif self.parent: self.parent.update(name, value)
        else: raise NameError(f"Variable '{name}' not defined.")
        
    def get(self, name):
        if name in self.vars: return self.vars[name]
        if self.parent: return self.parent.get(name)
        raise NameError(f"Variable '{name}' not defined.")

class Evaluator:
    def __init__(self, lines):
        self.env, self.lines = Environment(), lines
        self.current_line, self.current_col = 1, 1
        
        self.env.set('π', math.pi, 'float', ['global', 'const'])
        self.env.set('pi', math.pi, 'float', ['global', 'const'])
        self.env.set('∞', float('inf'), 'float', ['global', 'const'])
        self.env.set('infinity', float('inf'), 'float', ['global', 'const'])
        
        def native_write(*args):
            sys.stdout.write(" ".join("null" if a is None else str(a) for a in args) + "\n")
            return None

        def native_read(*args):
            sys.stdout.write(" ".join("null" if a is None else str(a) for a in args))
            return sys.stdin.readline()
            
        def native_typeof(val):
            if val is None: return "null"
            if isinstance(val, bool): return "bool"
            if isinstance(val, int): return "int"
            if isinstance(val, float): return "float"
            if isinstance(val, str): return "str"
            if isinstance(val, list): return "array"
            if hasattr(val, '__class__'): return val.__class__.__name__
            return "unknown"

        self.register_native_func("write", native_write)
        self.register_native_func("read", native_read)
        self.register_native_func("typeof", native_typeof)
        
    def register_native_func(self, name, func): self.env.set(name, func, 'function', ['global', 'const'])
    def register_native_var(self, name, val, val_type='any'): self.env.set(name, val, val_type, ['global'])
    def register_native_obj(self, name, py_obj): self.env.set(name, py_obj, 'any', ['global'])
    def register_native_lib(self, name, py_lib): self.env.set(name, py_lib, 'any', ['global', 'const'])
    def register_native_class(self, name, py_class): self.env.set(name, {'type': 'NativeClass', 'class': py_class}, 'any', ['global', 'const'])

    def evaluate(self, node):
        if type(node) is list:
            for stmt in node: self.evaluate(stmt)
            return

        if isinstance(node, dict) and '_line' in node:
            self.current_line, self.current_col = node['_line'], node['_col']
            
        try:
            t = node['type']
            if t == 'Program':
                for stmt in node['body']: self.evaluate(stmt)
                    
            elif t == 'VarDecl':
                val = None
                try:
                    type_obj = self.env.get(node['var_type']) if 'var_type' in node else None
                    if isinstance(type_obj, dict):
                        if type_obj.get('type') == 'Class':
                            args = [self.evaluate(a) for a in node.get('args', [])]
                            val = Environment(parent=self.env); old_env = self.env; self.env = val 
                            for stmt in type_obj['body']: self.evaluate(stmt)
                            constructor = val.vars.get(node['var_type']) or val.vars.get('init')
                            if constructor and isinstance(constructor, dict) and constructor.get('type') == 'Function':
                                call_env = Environment(parent=constructor['closure'])
                                for i, param in enumerate(constructor['params']):
                                    if i < len(args): call_env.set(param['name'], args[i])
                                self.env = call_env
                                try:
                                    for stmt in constructor['body']: self.evaluate(stmt)
                                except ReturnException: pass
                            self.env = old_env
                            
                        elif type_obj.get('type') == 'NativeClass':
                            args = [self.evaluate(a) for a in node.get('args', [])]
                            val = type_obj['class'](*args)
                except NameError: pass
                
                if node.get('value') is not None: val = self.evaluate(node['value'])
                
                # --- AUTO INFERENCE ---
                actual_type = node['var_type']
                if actual_type == 'auto':
                    if val is not None:
                        if isinstance(val, bool): actual_type = 'bool'
                        elif isinstance(val, int): actual_type = 'int'
                        elif isinstance(val, float): actual_type = 'float'
                        elif isinstance(val, str): actual_type = 'str'
                        elif isinstance(val, list): actual_type = 'array'
                        else: actual_type = 'any'
                    else: actual_type = 'any'
                
                target_env = self.env
                if 'global' in node.get('modifiers', []):
                    while target_env.parent: target_env = target_env.parent
                
                if not target_env.check_type(val, actual_type):
                    val_type = "null" if val is None else type(val).__name__.replace('str', 'string')
                    raise TypeError(f"Type Mismatch: Cannot assign '{val_type}' to '{actual_type}' variable '{node['name']}'")
                target_env.set(node['name'], val, actual_type, node.get('modifiers', []))
            
            elif t == 'ArrayDecl':
                if 'elements' in node: val = [self.evaluate(e) for e in node['elements']]
                else: val = self.evaluate(node['value']) if node.get('value') is not None else None
                    
                target_env = self.env
                if 'global' in node.get('modifiers', []):
                    while target_env.parent: target_env = target_env.parent
                if not target_env.check_type(val, 'array'):
                    val_type = "null" if val is None else type(val).__name__.replace('str', 'string').replace('list', 'array')
                    raise TypeError(f"Type Mismatch: Cannot assign '{val_type}' to 'array' variable '{node['name']}'")
                target_env.set(node['name'], val, 'array', node.get('modifiers', []))

            elif t == 'UpdateObj':
                target = node['target']; delta = 1 if node['operator'] == '++' else -1
                if target['type'] == 'Identifier':
                    self.env.update(target['name'], self.env.get(target['name']) + delta)
                elif target['type'] == 'DotAccess':
                    obj = self.evaluate(target['target'])
                    if isinstance(obj, Environment): obj.vars[target['prop']] += delta
                    elif hasattr(obj, target['prop']): setattr(obj, target['prop'], getattr(obj, target['prop']) + delta)
                    elif isinstance(obj, dict): obj[target['prop']] += delta
                elif target['type'] == 'ArrayAccess':
                    arr = self.evaluate(target['target']); idx = self.evaluate(target['index'])
                    if isinstance(arr, list) and idx >= len(arr): arr.extend([None] * (idx - len(arr) + 1))
                    arr[idx] += delta
                
            elif t == 'AssignObj':
                target = node['target']; val = self.evaluate(node['value']); op = node['operator']
                
                def apply_op(current, v, o):
                    if o == '=': return v
                    if o == '+=': return str(current)+str(v) if isinstance(current,str) or isinstance(v,str) else current+v
                    if o == '-=': return current - v
                    if o == '*=': return current * v
                    if o == '/=': return current / v
                    if o == '%=': return current % v
                    if o == '<<=': return current << v
                    if o == '>>=': return current >> v
                    if o == '&=': return current & v
                    if o == '|=': return current | v
                    if o == '^=': return current ^ v
                    return v

                if target['type'] == 'Identifier':
                    if op == '=': self.env.update(target['name'], val)
                    else: self.env.update(target['name'], apply_op(self.env.get(target['name']), val, op))
                elif target['type'] == 'DotAccess':
                    obj = self.evaluate(target['target'])
                    if isinstance(obj, Environment): 
                        if op == '=': obj.vars[target['prop']] = val
                        else: obj.vars[target['prop']] = apply_op(obj.vars[target['prop']], val, op)
                    elif hasattr(obj, target['prop']):
                        if op == '=': setattr(obj, target['prop'], val)
                        else: setattr(obj, target['prop'], apply_op(getattr(obj, target['prop']), val, op))
                    elif isinstance(obj, dict):
                        if op == '=': obj[target['prop']] = val
                        else: obj[target['prop']] = apply_op(obj[target['prop']], val, op)
                elif target['type'] == 'ArrayAccess':
                    arr = self.evaluate(target['target']); idx = self.evaluate(target['index'])
                    if isinstance(arr, list) and idx >= len(arr): arr.extend([None] * (idx - len(arr) + 1))
                    if op == '=': arr[idx] = val
                    else: arr[idx] = apply_op(arr[idx], val, op)
                    
            elif t == 'ExprStmt': self.evaluate(node['expr'])
            elif t == 'FuncDecl': self.env.set(node['name'], {'type': 'Function', 'params': node['params'], 'body': node['body'], 'closure': self.env}, 'function', node.get('modifiers', []))
            
            elif t == 'MethodDef':
                class_def = self.env.get(node['class_name'])
                if not isinstance(class_def, dict) or class_def.get('type') != 'Class':
                    raise TypeError(f"Cannot attach method to non-class '{node['class_name']}'")
                func_node = {'type': 'FuncDecl', 'return_type': node['return_type'], 'name': node['name'], 'params': node['params'], 'body': node['body'], 'modifiers': node['modifiers']}
                class_def['body'].append(func_node)
                
            elif t == 'LibDecl':
                lib_env = Environment(parent=self.env); old_env = self.env; self.env = lib_env
                for stmt in node['body']: self.evaluate(stmt)
                self.env = old_env; self.env.set(node['name'], lib_env)
            elif t == 'ClassDecl': self.env.set(node['name'], {'type': 'Class', 'body': node['body']})
                
            elif t == 'CallExpr':
                func = self.evaluate(node['target'])
                args = [self.evaluate(arg) for arg in node['args']]
                
                if callable(func): return func(*args)
                    
                call_env = Environment(parent=func['closure'])
                for i, param in enumerate(func['params']):
                    if i < len(args): call_env.set(param['name'], args[i])
                old_env, result = self.env, None; self.env = call_env
                try:
                    for stmt in func['body']: self.evaluate(stmt)
                except ReturnException as r: result = r.value
                finally: self.env = old_env
                return result
                
            elif t == 'DotAccess':
                obj = self.evaluate(node['target'])
                if isinstance(obj, Environment) and node['prop'] in obj.vars: return obj.vars[node['prop']]
                if hasattr(obj, node['prop']): return getattr(obj, node['prop'])
                if isinstance(obj, dict) and node['prop'] in obj: return obj[node['prop']]
                raise NameError(f"Property '{node['prop']}' not found.")
                
            elif t == 'ArrayAccess':
                arr = self.evaluate(node['target']); return arr[self.evaluate(node['index'])]
            elif t == 'ArrayLiteral': return [self.evaluate(e) for e in node['elements']]
            
            # --- TRY / CATCH SCOPING ---
            elif t == 'TryCatch':
                old_env = self.env
                try_env = Environment(parent=old_env)
                self.env = try_env
                try:
                    for stmt in node['try_body']: self.evaluate(stmt)
                except HydraError as e:
                    self.env = old_env 
                    catch_env = Environment(parent=self.env)
                    if node['catch_var']:
                        catch_env.set(node['catch_var'], e.msg, 'str')
                    self.env = catch_env
                    for stmt in node['catch_body']: self.evaluate(stmt)
                finally:
                    self.env = old_env
                    
            elif t == 'Cast':
                val = self.evaluate(node['expr'])
                if val is None: return None
                try:
                    if node['cast_type'] == 'int': return int(float(val)) if isinstance(val, (int, float)) else int(val)
                    if node['cast_type'] == 'float': return float(val)
                    if node['cast_type'] == 'str': return str(val)
                    if node['cast_type'] == 'bool': return bool(val)
                except ValueError:
                    raise TypeError(f"Cannot explicitly cast '{val}' to {node['cast_type']}")

            elif t == 'If':
                if self.evaluate(node['condition']):
                    for stmt in node['body']: self.evaluate(stmt)
                else:
                    handled = False
                    for elif_node in node['elseifs']:
                        if self.evaluate(elif_node['condition']):
                            for stmt in elif_node['body']: self.evaluate(stmt)
                            handled = True; break
                    if not handled and node['else_body']:
                        for stmt in node['else_body']: self.evaluate(stmt)

            elif t == 'While':
                while self.evaluate(node['condition']):
                    try:
                        for stmt in node['body']: self.evaluate(stmt)
                    except BreakException: break
                    except ContinueException: continue
                    
            elif t == 'For':
                old_env = self.env; self.env = Environment(parent=old_env) 
                if node['decl']: self.evaluate(node['decl'])
                while self.evaluate(node['cond']):
                    try:
                        for stmt in node['body']: self.evaluate(stmt)
                    except BreakException: break
                    except ContinueException: pass
                    self.evaluate(node['step'])
                self.env = old_env
                
            elif t == 'Foreach':
                arr = self.env.get(node['array']); old_env = self.env
                for item in arr:
                    self.env = Environment(parent=old_env); self.env.set(node['item'], item)
                    try:
                        for stmt in node['body']: self.evaluate(stmt)
                    except BreakException: break
                    except ContinueException: continue
                self.env = old_env
                
            elif t == 'Switch':
                switch_val = self.evaluate(node['variable']); matched = False
                for case in node['cases']:
                    if switch_val == self.evaluate(case['value']):
                        matched = True
                        for stmt in case['body']: self.evaluate(stmt)
                        break 
                if not matched and node['default'] is not None:
                    for stmt in node['default']: self.evaluate(stmt)

            elif t == 'Return': 
                return_val = self.evaluate(node['value']) if node.get('value') is not None else None
                raise ReturnException(return_val)
                
            elif t == 'Break': raise BreakException()
            elif t == 'Continue': raise ContinueException()

            elif t == 'UnaryOp':
                expr = self.evaluate(node['expr'])
                if node['op'] == '!': return not expr
                if node['op'] == '~': return ~expr
                if node['op'] == '#':
                    if isinstance(expr, (str, list)): return len(expr)
                    raise TypeError("Length operator '#' can only be applied to arrays or strings")

            elif t == 'TernaryOp':
                cond = self.evaluate(node['condition'])
                return self.evaluate(node['true_expr']) if cond else self.evaluate(node['false_expr'])

            # --- DYNAMIC F-STRING EVALUATION ---
            elif t == 'FString':
                res = ""
                for p in node['parts']:
                    val = self.evaluate(p)
                    res += "null" if val is None else str(val)
                return res

            elif t == 'BinOp':
                op = node['op']
                l = self.evaluate(node['left'])
                
                if op == '&&': return bool(l and self.evaluate(node['right']))
                if op == '||': return bool(l or self.evaluate(node['right']))
                
                r = self.evaluate(node['right'])
                
                if op == '+': 
                    l_str = "null" if l is None else str(l)
                    r_str = "null" if r is None else str(r)
                    return l_str + r_str if isinstance(l,str) or isinstance(r,str) else l+r
                    
                if op == '-': return l - r
                if op in ['*', '×']: return l * r
                if op in ['/', '÷']: return l / r
                if op == '%': return l % r
                if op == '**': return l ** r
                if op == '<<': return l << r
                if op == '>>': return l >> r
                if op == '&': return l & r
                if op == '|': return l | r
                if op == '^': return l ^ r
                if op == '<=': return l <= r
                if op == '>=': return l >= r
                if op in ['!=', '≠']: return l != r
                if op == '==': return l == r
                if op == '<': return l < r
                if op == '>': return l > r
                if op in ['≈', '~=']: return abs(l - r) <= 1e-9
                
                if op in ['∈', 'in']: return l in r
                if op in ['∉', 'notin']: return l not in r
                if op in ['⊂', 'subset']: return set(l).issubset(set(r))
                if op in ['⊃', 'superset']: return set(l).issuperset(set(r))
                if op in ['∪', 'union']:
                    res = list(l)
                    for x in r:
                        if x not in res: res.append(x)
                    return res
                if op in ['∩', 'intersect']: return [x for x in l if x in r]
                
            elif t == 'Literal': return node['value']
            elif t == 'Identifier': return self.env.get(node['name'])
            
        except (ReturnException, BreakException, ContinueException, HydraError):
            raise
        except Exception as e:
            line_text = self.lines[self.current_line - 1] if self.lines else ""
            length = node.get('_length', 1) 
            raise HydraError(str(e), self.current_line, self.current_col, line_text, length)

# ==========================================
# 4. RUNNER (Showcasing v14 Features)
# ==========================================
if __name__ == "__main__":
    
    hydra_source_code = """
    int x = 3;
    int y = -x;
    """
    
    try:
        tokens, lines = lex(hydra_source_code)
        parser = Parser(tokens, lines)
        ast = parser.parse()
        
        interpreter = Evaluator(lines)
        
        interpreter.evaluate(ast)
        
    except HydraError as e:
        e.display()
    except Exception as e:
        import traceback
        traceback.print_exc()