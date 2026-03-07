# evaluator.py
import sys
import math
from errors import HydraError

class ReturnException(Exception):
    def __init__(self, value, node=None): 
        self.value = value
        self.node = node

class BreakException(Exception): 
    def __init__(self, node=None): self.node = node

class ContinueException(Exception): 
    def __init__(self, node=None): self.node = node

class Environment:
    def __init__(self, parent=None):
        self.vars, self.meta, self.parent = {}, {}, parent
        
    def get_meta(self, name):
        if name in self.meta: return self.meta[name]
        if self.parent: return self.parent.get_meta(name)
        return None
        
    def check_type(self, val, expected_type):
        if val is None: return True 
        if expected_type == 'int': return isinstance(val, int) and not isinstance(val, bool)
        if expected_type == 'float': return isinstance(val, (int, float)) and not isinstance(val, bool)
        if expected_type == 'str': return isinstance(val, str)
        if expected_type == 'bool': return isinstance(val, bool)
        if expected_type == 'array': return isinstance(val, list)
        
        if expected_type.endswith('_array'):
            if not isinstance(val, list): return False
            inner_type = expected_type.replace('_array', '')
            if inner_type in ['any', 'auto']: return True
            for item in val:
                if not self.check_type(item, inner_type): return False
            return True
            
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
            sys.stdout.write(" ".join(self.to_hydra_str(a) for a in args) + "\n")
            return None
            
        def native_read():
            return sys.stdin.readline().strip()
            
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
        
    def to_hydra_str(self, val):
        if val is None: return "null"
        if isinstance(val, bool): return "true" if val else "false"
        return str(val)

    def register_native_func(self, name, func): self.env.set(name, func, 'function', ['global', 'const'])

    def evaluate(self, node):
        if type(node) is list:
            for stmt in node: self.evaluate(stmt)
            return

        if isinstance(node, dict) and '_line' in node:
            self.current_line, self.current_col = node['_line'], node['_col']
            
        try:
            t = node['type']
            if t == 'Program':
                try:
                    for stmt in node['body']: self.evaluate(stmt)
                except ReturnException as r: 
                    if r.node: node = r.node; self.current_line = node.get('_line', self.current_line); self.current_col = node.get('_col', self.current_col)
                    raise SyntaxError("Cannot 'return' outside a function.")
                except BreakException as b: 
                    if b.node: node = b.node; self.current_line = node.get('_line', self.current_line); self.current_col = node.get('_col', self.current_col)
                    raise SyntaxError("Cannot 'break' outside a loop.")
                except ContinueException as c: 
                    if c.node: node = c.node; self.current_line = node.get('_line', self.current_line); self.current_col = node.get('_col', self.current_col)
                    raise SyntaxError("Cannot 'continue' outside a loop.")
                    
            elif t == 'VarDecl':
                actual_type_base = node['var_type']
                
                # Loop through all comma-separated variable declarations!
                for decl in node['declarations']:
                    decl_name = decl['name']
                    decl_val = None
                    
                    if decl_name in self.env.vars:
                        raise NameError(f"Variable '{decl_name}' is already defined in this scope.")
                        
                    try:
                        type_obj = self.env.get(actual_type_base) if actual_type_base != 'auto' else None
                        if isinstance(type_obj, dict) and type_obj.get('type') == 'Class':
                            args = [self.evaluate(a) for a in decl.get('args', [])]
                            decl_val = Environment(parent=self.env); old_env = self.env; self.env = decl_val 
                            for stmt in type_obj['body']: self.evaluate(stmt)
                            constructor = decl_val.vars.get(actual_type_base) or decl_val.vars.get('init')
                            if constructor and isinstance(constructor, dict) and constructor.get('type') == 'Function':
                                call_env = Environment(parent=constructor['closure'])
                                for i, param in enumerate(constructor['params']):
                                    if i < len(args): call_env.set(param['name'], args[i])
                                self.env = call_env
                                try:
                                    for stmt in constructor['body']: self.evaluate(stmt)
                                except ReturnException: pass
                            self.env = old_env
                    except NameError: pass
                    
                    if decl.get('value') is not None: 
                        decl_val = self.evaluate(decl['value'])
                        if isinstance(decl_val, list): decl_val = decl_val.copy() 
                    
                    actual_type = actual_type_base
                    if actual_type == 'auto':
                        if decl_val is not None:
                            if isinstance(decl_val, bool): actual_type = 'bool'
                            elif isinstance(decl_val, int): actual_type = 'int'
                            elif isinstance(decl_val, float): actual_type = 'float'
                            elif isinstance(decl_val, str): actual_type = 'str'
                            elif isinstance(decl_val, list): actual_type = 'array'
                            else: actual_type = 'any'
                        else: actual_type = 'any'
                    
                    target_env = self.env
                    if 'global' in node.get('modifiers', []):
                        while target_env.parent: target_env = target_env.parent
                    
                    if not target_env.check_type(decl_val, actual_type):
                        val_type = "null" if decl_val is None else type(decl_val).__name__.replace('str', 'string')
                        raise TypeError(f"Type Mismatch: Cannot assign '{val_type}' to '{actual_type}' variable '{decl_name}'")
                    target_env.set(decl_name, decl_val, actual_type, node.get('modifiers', []))
            
            elif t == 'ArrayDecl':
                if 'elements' in node: val = [self.evaluate(e) for e in node['elements']]
                else: 
                    val = self.evaluate(node['value']) if node.get('value') is not None else None
                    if isinstance(val, list): val = val.copy()
                    
                target_env = self.env
                if 'global' in node.get('modifiers', []):
                    while target_env.parent: target_env = target_env.parent
                    
                actual_type = node.get('var_type', 'any')
                if actual_type not in ['auto', 'any']:
                    if val is not None:
                        for i, item in enumerate(val):
                            if not target_env.check_type(item, actual_type):
                                item_type = "null" if item is None else type(item).__name__.replace('str', 'string')
                                raise TypeError(f"Type Mismatch: Cannot assign '{item_type}' to '{actual_type} array' at index {i}.")
                                
                saved_type = f"{actual_type}_array" if actual_type not in ['auto', 'any'] else 'array'
                
                if not target_env.check_type(val, saved_type):
                    val_type = "null" if val is None else type(val).__name__.replace('str', 'string').replace('list', 'array')
                    raise TypeError(f"Type Mismatch: Cannot assign '{val_type}' to '{actual_type} array' variable '{node['name']}'")
                    
                target_env.set(node['name'], val, saved_type, node.get('modifiers', []))

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
                    if isinstance(arr, str): raise TypeError("Strings are immutable in Hydra.")
                    if isinstance(arr, list) and idx >= len(arr): arr.extend([None] * (idx - len(arr) + 1))
                    arr[idx] += delta
                
            elif t == 'AssignObj':
                target = node['target']; val = self.evaluate(node['value']); op = node['operator']
                def apply_op(current, v, o):
                    if o == '=': return v
                    if o == '+=': 
                        if isinstance(current, str) or isinstance(v, str): return self.to_hydra_str(current) + self.to_hydra_str(v)
                        return current + v
                    if o == '-=': return current - v
                    if o == '*=': return current * v
                    if o == '/=': return current / v
                    if o == '%=': return current % v
                    return v

                if target['type'] == 'Identifier':
                    if op == '=': self.env.update(target['name'], val)
                    else: self.env.update(target['name'], apply_op(self.env.get(target['name']), val, op))
                elif target['type'] == 'DotAccess':
                    obj = self.evaluate(target['target'])
                    if isinstance(obj, Environment): 
                        if op == '=': obj.vars[target['prop']] = val
                        else: obj.vars[target['prop']] = apply_op(obj.vars[target['prop']], val, op)
                elif target['type'] == 'ArrayAccess':
                    arr = self.evaluate(target['target']); idx = self.evaluate(target['index'])
                    if isinstance(arr, str): raise TypeError("Strings are immutable in Hydra.")
                    if isinstance(arr, list) and idx >= len(arr): arr.extend([None] * (idx - len(arr) + 1))
                    
                    val_to_assign = val if op == '=' else apply_op(arr[idx], val, op)
                    if target['target']['type'] == 'Identifier':
                        meta = self.env.get_meta(target['target']['name'])
                        if meta and meta['type'].endswith('_array'):
                            inner_type = meta['type'].replace('_array', '')
                            if inner_type not in ['any', 'auto']:
                                if not self.env.check_type(val_to_assign, inner_type):
                                    v_type = "null" if val_to_assign is None else type(val_to_assign).__name__.replace('str', 'string')
                                    raise TypeError(f"Type Mismatch: Cannot assign '{v_type}' into '{inner_type} array'.")
                    arr[idx] = val_to_assign
                    
            elif t == 'ExprStmt': self.evaluate(node['expr'])
            
            elif t == 'FuncDecl': self.env.set(node['name'], {'type': 'Function', 'return_type': node.get('return_type', 'any'), 'params': node['params'], 'body': node['body'], 'closure': self.env}, 'function', node.get('modifiers', []))
            
            elif t == 'MethodDef':
                class_def = self.env.get(node['class_name'])
                class_def['body'].append({'type': 'FuncDecl', 'return_type': node['return_type'], 'name': node['name'], 'params': node['params'], 'body': node['body'], 'modifiers': node['modifiers']})
                
            elif t == 'ClassDecl': self.env.set(node['name'], {'type': 'Class', 'body': node['body']})
                
            elif t == 'CallExpr':
                if node['target']['type'] == 'Identifier':
                    func_name = node['target']['name']
                    try:
                        func = self.env.get(func_name)
                    except NameError:
                        if '_line' in node['target']: self.current_line, self.current_col = node['target']['_line'], node['target']['_col']
                        elif '_line' in node: self.current_line, self.current_col = node['_line'], node['_col']
                        line_text = self.lines[self.current_line - 1] if self.lines and self.current_line <= len(self.lines) else ""
                        idx = line_text.find(func_name, max(0, self.current_col - 1))
                        if idx == -1: idx = line_text.find(func_name)
                        if idx != -1: self.current_col = idx + 1
                        node = {'_length': len(func_name)}
                        raise NameError(f"Function '{func_name}' not defined.")
                else:
                    func = self.evaluate(node['target'])
                
                args = [self.evaluate(arg) for arg in node['args']]
                if callable(func): return func(*args)
                if not isinstance(func, dict) or 'params' not in func: raise TypeError(f"Target is not callable.")
                if len(args) > len(func['params']): raise TypeError(f"Too many arguments passed! Expected {len(func['params'])}, got {len(args)}.")
                    
                call_env = Environment(parent=func['closure'])
                for i, param in enumerate(func['params']):
                    if i < len(args): call_env.set(param['name'], args[i])
                    elif param.get('default') is not None: call_env.set(param['name'], self.evaluate(param['default']))
                    else: raise TypeError(f"Missing required argument '{param['name']}'.")
                
                old_env, result = self.env, None; self.env = call_env
                return_node = None
                try:
                    for stmt in func['body']: self.evaluate(stmt)
                except ReturnException as r: 
                    result = r.value; return_node = r.node
                finally: self.env = old_env
                
                ret_type = func.get('return_type', 'any')
                if ret_type != 'any' and ret_type != 'auto':
                    if ret_type == 'void' and result is not None:
                        v_type = type(result).__name__.replace('str', 'string')
                        if return_node:
                            val_node = return_node.get('value', return_node) or return_node
                            self.current_line = val_node.get('_line', self.current_line); self.current_col = val_node.get('_col', self.current_col)
                            node = val_node
                        raise TypeError(f"Type Mismatch: 'void' function cannot return a value of type '{v_type}'.")
                    elif ret_type != 'void' and not old_env.check_type(result, ret_type):
                        v_type = "null" if result is None else type(result).__name__.replace('str', 'string')
                        if return_node:
                            val_node = return_node.get('value', return_node) or return_node
                            self.current_line = val_node.get('_line', self.current_line); self.current_col = val_node.get('_col', self.current_col)
                            line_text = self.lines[self.current_line - 1] if self.lines and self.current_line <= len(self.lines) else ""
                            if val_node.get('type') == 'Literal' and isinstance(val_node.get('value'), str):
                                s_val = f'"{val_node["value"]}"'
                                idx = line_text.find(s_val)
                                if idx != -1: self.current_col = idx + 1; node = {'_length': len(s_val)}
                            elif val_node.get('type') == 'Identifier':
                                idx = line_text.find(val_node['name'])
                                if idx != -1: self.current_col = idx + 1; node = {'_length': len(val_node['name'])}
                            else: node = val_node
                        raise TypeError(f"Type Mismatch: Function expected to return '{ret_type}', but returned '{v_type}'.")
                return result
                
            elif t == 'DotAccess':
                obj = self.evaluate(node['target'])
                if isinstance(obj, Environment) and node['prop'] in obj.vars: return obj.vars[node['prop']]
                raise NameError(f"Property '{node['prop']}' not found.")
                
            elif t == 'ArrayAccess':
                arr = self.evaluate(node['target'])
                idx = self.evaluate(node['index'])
                if isinstance(arr, (list, str)): return arr[idx] if 0 <= idx < len(arr) else None
                raise TypeError("Cannot index non-array or non-string.")
                
            elif t == 'ArrayLiteral': return [self.evaluate(e) for e in node['elements']]
            
            elif t == 'TryCatch':
                old_env = self.env
                try_env = Environment(parent=old_env)
                self.env = try_env
                try:
                    for stmt in node['try_body']: self.evaluate(stmt)
                except Exception as e:
                    error_msg = str(e) if not isinstance(e, HydraError) else e.msg
                    self.env = old_env 
                    catch_env = Environment(parent=self.env)
                    if node['catch_var']: catch_env.set(node['catch_var'], error_msg, 'str')
                    self.env = catch_env
                    try:
                        for stmt in node['catch_body']: self.evaluate(stmt)
                    finally: self.env = old_env
                finally:
                    if self.env is try_env: self.env = old_env
                    
            elif t == 'Cast':
                val = self.evaluate(node['expr'])
                if val is None: return None
                try:
                    if node['cast_type'] == 'int': return int(float(val)) if isinstance(val, (int, float)) else int(val)
                    if node['cast_type'] == 'float': return float(val)
                    if node['cast_type'] == 'str': return str(val)
                    if node['cast_type'] == 'bool': return bool(val)
                except ValueError: raise TypeError(f"Cannot explicitly cast '{val}' to {node['cast_type']}")

            elif t == 'If':
                if self.evaluate(node['condition']):
                    old_env = self.env; self.env = Environment(parent=old_env)
                    try:
                        for stmt in node['body']: self.evaluate(stmt)
                    finally: self.env = old_env
                else:
                    handled = False
                    for elif_node in node['elseifs']:
                        if self.evaluate(elif_node['condition']):
                            old_env = self.env; self.env = Environment(parent=old_env)
                            try:
                                for stmt in elif_node['body']: self.evaluate(stmt)
                            finally: self.env = old_env
                            handled = True; break
                    if not handled and node['else_body']:
                        old_env = self.env; self.env = Environment(parent=old_env)
                        try:
                            for stmt in node['else_body']: self.evaluate(stmt)
                        finally: self.env = old_env

            elif t == 'While':
                while self.evaluate(node['condition']):
                    old_env = self.env; self.env = Environment(parent=old_env) 
                    try:
                        for stmt in node['body']: self.evaluate(stmt)
                    except BreakException: self.env = old_env; break
                    except ContinueException: self.env = old_env; continue
                    finally: self.env = old_env
                    
            elif t == 'For':
                loop_env = Environment(parent=self.env); old_env = self.env; self.env = loop_env 
                try:
                    if node['decl']: self.evaluate(node['decl'])
                    while self.evaluate(node['cond']):
                        iter_env = Environment(parent=self.env); self.env = iter_env
                        try:
                            for stmt in node['body']: self.evaluate(stmt)
                        except BreakException: self.env = loop_env; break
                        except ContinueException: pass 
                        finally: self.env = loop_env
                        self.evaluate(node['step'])
                finally: self.env = old_env
                
            elif t == 'Foreach':
                arr = self.env.get(node['array']); old_env = self.env
                for item in arr:
                    self.env = Environment(parent=old_env); self.env.set(node['item'], item)
                    try:
                        for stmt in node['body']: self.evaluate(stmt)
                    except BreakException: self.env = old_env; break
                    except ContinueException: self.env = old_env; continue
                    finally: self.env = old_env
                
            elif t == 'Switch':
                switch_val = self.evaluate(node['variable']); matched = False
                for case in node['cases']:
                    if switch_val == self.evaluate(case['value']):
                        matched = True
                        old_env = self.env; self.env = Environment(parent=old_env)
                        try:
                            for stmt in case['body']: self.evaluate(stmt)
                        finally: self.env = old_env
                        break 
                if not matched and node['default'] is not None:
                    old_env = self.env; self.env = Environment(parent=old_env)
                    try:
                        for stmt in node['default']: self.evaluate(stmt)
                    finally: self.env = old_env

            elif t == 'Return': 
                return_val = self.evaluate(node['value']) if node.get('value') is not None else None
                raise ReturnException(return_val, node)
                
            elif t == 'Break': raise BreakException(node)
            elif t == 'Continue': raise ContinueException(node)

            elif t == 'UnaryOp':
                expr = self.evaluate(node['expr'])
                if node['op'] == '!': return not expr
                if node['op'] == '~': return ~expr
                if node['op'] == '-': return -expr
                if node['op'] == '+': return +expr
                if node['op'] == '#': return len(expr)

            elif t == 'TernaryOp':
                cond = self.evaluate(node['condition'])
                return self.evaluate(node['true_expr']) if cond else self.evaluate(node['false_expr'])

            elif t == 'FString':
                res = ""
                for p in node['parts']: res += self.to_hydra_str(self.evaluate(p))
                return res

            elif t == 'BinOp':
                op = node['op']; l = self.evaluate(node['left'])
                if op == '&&': return bool(l and self.evaluate(node['right']))
                if op == '||': return bool(l or self.evaluate(node['right']))
                
                r = self.evaluate(node['right'])
                try:
                    if op == '+': 
                        if isinstance(l, str) or isinstance(r, str): return self.to_hydra_str(l) + self.to_hydra_str(r)
                        return l + r
                    if op == '-': return l - r
                    if op in ['*', '×']: return l * r
                    if op in ['/', '÷']: return l / r
                    if op == '%': return l % r
                    if op == '**': return l ** r
                    if op == '==': return l == r
                    if op in ['!=', '≠']: return l != r
                    if op == '<': return l < r
                    if op == '>': return l > r
                except ZeroDivisionError: raise HydraError("Division by zero") 
                    
            elif t == 'Literal': return node['value']
            elif t == 'Identifier': return self.env.get(node['name'])
            
        except (ReturnException, BreakException, ContinueException, HydraError): raise
        except Exception as e:
            line_text = self.lines[self.current_line - 1] if self.lines else ""
            length = node.get('_length', 1) 
            raise HydraError(str(e), self.current_line, self.current_col, line_text, length)