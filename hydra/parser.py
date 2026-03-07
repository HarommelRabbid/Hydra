# parser_engine.py
from errors import HydraError
from lexer import lex

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
            if val in ['const', 'local', 'global', 'auto', 'int', 'str', 'float', 'bool', 'void', 'any']: return self.parse_decl()
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
                        while self.current().type == 'COMMA': 
                            self.consume('COMMA')
                            if self.current().type == 'RPAREN': break
                            args.append(self.parse_expr())
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
        p_type = 'any'
        # Check for root type (e.g., int, str)
        if self.current() and self.current().type == 'KEYWORD' and self.current().value in ['auto', 'int', 'str', 'float', 'bool', 'void', 'any']:
            p_type = self.consume('KEYWORD').value
            
        # Check if it is marked as an array!
        if self.current() and self.current().type == 'KEYWORD' and self.current().value == 'array':
            self.consume('KEYWORD')
            if self.current() and self.current().type == 'DOUBLE_COLON':
                self.consume('DOUBLE_COLON')
            p_type = f"{p_type}_array"
            
        p_name = self.consume('ID').value
        default_expr = None
        if self.current() and self.current().type == 'ASSIGN': 
            self.consume('ASSIGN')
            default_expr = self.parse_expr() 
        return {'type': p_type, 'name': p_name, 'default': default_expr}

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
                    while self.current().type == 'COMMA': 
                        self.consume('COMMA')
                        if self.current().type == 'RPAREN': break
                        params.append(self.parse_param())
                self.consume('RPAREN'); body = self.parse_block()
                return {'type': 'MethodDef', 'class_name': class_name, 'return_type': var_type, 'name': name, 'params': params, 'body': body, 'modifiers': modifiers}

        if self.current() and self.current().type == 'KEYWORD':
            if self.current().value == 'function':
                self.consume('KEYWORD'); self.consume('DOUBLE_COLON')
                name = self.consume('ID').value; self.consume('LPAREN')
                params = []
                if self.current().type != 'RPAREN':
                    params.append(self.parse_param())
                    while self.current().type == 'COMMA': 
                        self.consume('COMMA')
                        if self.current().type == 'RPAREN': break
                        params.append(self.parse_param())
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
                        while self.current().type == 'COMMA': 
                            self.consume('COMMA')
                            if self.current().type == 'RPAREN': break
                            params.append(self.parse_param())
                    self.consume('RPAREN'); body = self.parse_block()
                    # Upgraded to allow Strict Typed Array Return Values!
                    return {'type': 'FuncDecl', 'return_type': f"{var_type}_array", 'name': name, 'params': params, 'body': body, 'modifiers': modifiers}
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
                            while self.current().type == 'COMMA': 
                                self.consume('COMMA')
                                if self.current().type == 'RBRACE': break 
                                elements.append(self.parse_expr())
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
                while self.current().type == 'COMMA': 
                    self.consume('COMMA')
                    if self.current().type == 'RPAREN': break
                    args.append(self.parse_expr())
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
        self.consume('KEYWORD') 
        try_body = self.parse_block()
        
        self.consume('KEYWORD') 
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
            self.consume('KEYWORD')
            if self.current() and self.current().type == 'COLON': self.consume('COLON')
            else_body = self.parse_block()
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
                    
        if self.current() and self.current().type in ['OP_NOT', 'OP_LEN', 'OP_NOT_LOGIC', 'OP_MINUS', 'OP_PLUS']:
            op = self.consume().value
            return {'type': 'UnaryOp', 'op': op, 'expr': self.parse_unary()}
        return self.parse_primary()

    def parse_primary(self):
        tok = self.consume()
        if tok.type == 'INT_LITERAL': expr = {'type': 'Literal', 'value': int(tok.value), '_length': tok.length}
        elif tok.type == 'FLOAT_LITERAL': expr = {'type': 'Literal', 'value': float(tok.value), '_length': tok.length}
        
        elif tok.type == 'STR_LITERAL': 
            parsed_str = bytes(tok.value[1:-1], "utf-8").decode("unicode_escape")
            expr = {'type': 'Literal', 'value': parsed_str, '_length': tok.length} 
            
        elif tok.type == 'TRUE': expr = {'type': 'Literal', 'value': True, '_length': tok.length}
        elif tok.type == 'FALSE': expr = {'type': 'Literal', 'value': False, '_length': tok.length}
        elif tok.type == 'NULL': expr = {'type': 'Literal', 'value': None, '_length': tok.length}
        elif tok.type == 'ID': expr = {'type': 'Identifier', 'name': tok.value, '_length': tok.length}
        
        elif tok.type == 'FSTR_LITERAL':
            raw_str = tok.value[2:-1] 
            parts = []
            i = 0
            curr_text = ""
            while i < len(raw_str):
                if raw_str[i] == '\\' and i + 1 < len(raw_str):
                    if raw_str[i+1] in ['{', '}']:
                        curr_text += raw_str[i+1]; i += 2; continue
                    else:
                        curr_text += raw_str[i:i+2]; i += 2; continue
                        
                if raw_str[i] == '{':
                    if curr_text:
                        parsed_txt = bytes(curr_text, "utf-8").decode("unicode_escape")
                        parts.append({'type': 'Literal', 'value': parsed_txt, '_length': 0})
                        curr_text = ""
                    i += 1
                    brace_count = 1
                    expr_str = ""
                    in_str = False 
                    while i < len(raw_str) and brace_count > 0:
                        if raw_str[i] == '"' and raw_str[i-1] != '\\': in_str = not in_str
                        if not in_str:
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
                            if temp_parser.current() is not None:
                                self.error(f"Syntax error inside f-string at: {temp_parser.current().value}", tok)
                            parts.append(expr_ast)
                    i += 1; continue
                    
                curr_text += raw_str[i]; i += 1
                
            if curr_text: 
                parsed_txt = bytes(curr_text, "utf-8").decode("unicode_escape")
                parts.append({'type': 'Literal', 'value': parsed_txt, '_length': 0})
            expr = {'type': 'FString', 'parts': parts, '_length': tok.length}
        
        elif tok.type == 'LBRACE':
            elements = []
            if self.current().type != 'RBRACE':
                elements.append(self.parse_expr())
                while self.current().type == 'COMMA': 
                    self.consume('COMMA')
                    if self.current().type == 'RBRACE': break 
                    elements.append(self.parse_expr())
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
                    while self.current().type == 'COMMA': 
                        self.consume('COMMA')
                        if self.current().type == 'RPAREN': break 
                        args.append(self.parse_expr())
                self.consume('RPAREN'); expr = {'type': 'CallExpr', 'target': expr, 'args': args}
            elif self.current().type == 'LBRACKET':
                self.consume('LBRACKET'); idx = self.parse_expr(); self.consume('RBRACKET')
                expr = {'type': 'ArrayAccess', 'target': expr, 'index': idx}
            elif self.current().type == 'DOT':
                self.consume('DOT'); prop = self.consume() 
                if prop.type not in ['ID', 'KEYWORD']: self.error("Expected property name")
                expr = {'type': 'DotAccess', 'target': expr, 'prop': prop.value}
            else: break
        return expr