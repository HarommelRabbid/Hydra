import sys
from lexer import lex
from parser import Parser
from evaluator import Evaluator
from errors import HydraError

def run_hydra_code(code, evaluator=None):
    """Executes Hydra code and returns the current environment evaluator."""
    try:
        tokens, lines = lex(code)
        parser = Parser(tokens, lines)
        ast = parser.parse()
        
        # We reuse the evaluator for the REPL to keep variables in memory!
        if evaluator is None:
            evaluator = Evaluator(lines)
        else:
            evaluator.lines = lines 
            
        evaluator.evaluate(ast)
        return evaluator
        
    except HydraError as e:
        e.display()
    except Exception as e:
        print(f"Host Crash Prevented: {e}")
    
    return evaluator

def hydra_repl():
    """Starts the interactive Read-Eval-Print Loop."""
    print("========================================")
    print(" Hydra MVP v14.1 REPL ")
    print(" Type 'exit' to quit.")
    print("========================================")
    
    evaluator = Evaluator([])
    buffer = ""
    
    while True:
        try:
            prompt = "hydra> " if not buffer else "...  > "
            line = input(prompt)
            
            if line.strip() == "exit": 
                break
            if not line.strip() and not buffer: 
                continue
                
            buffer += line + "\n"
            
            # Simple heuristic to let the REPL process blocks naturally
            if buffer.count('[[') == buffer.count(']]'):
                if not buffer.strip().endswith(';') and not buffer.strip().endswith(']]'):
                    buffer = buffer.strip() + ';\n'
                    
                evaluator = run_hydra_code(buffer, evaluator)
                buffer = "" # Reset buffer after execution
                
        except (KeyboardInterrupt, EOFError):
            print("\nExiting Hydra...")
            break

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run a .hyd file! e.g., python hydra.py examples/math.hyd
        filepath = sys.argv[1]
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source_code = f.read()
                run_hydra_code(source_code)
        except FileNotFoundError:
            print(f"Error: Could not find file '{filepath}'.")
    else:
        hydra_repl()