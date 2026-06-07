import sys
from pathlib import Path
sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))
sys.path.insert(0, str(sol_root / "tools" / "sol-rsi"))

from lumina_compiler import LuminaCompiler, LuminaAgent, LuminaASTVisitor, LuminaLogosCompiler

class TestComposedFullAdder(LuminaAgent):
    def configure(self):
        self.inputs = {"x": "Basin_A", "y": "Basin_B", "cin": "Basin_Cin"}
        self.outputs = {"sum": "Basin_SUM", "cout": "Basin_Cout"}
        
        # Instantiate two half adders
        self.ha1 = self.use_component("half_adder", inputs={"x": "x", "y": "y"}, outputs={"sum": "s1", "cout": "c1"})
        self.ha2 = self.use_component("half_adder", inputs={"x": "s1", "y": "cin"}, outputs={"sum": "sum", "cout": "c2"})

    def flow(self):
        self.ha1.run()
        self.ha2.run()
        self.cout = self.c1 | self.c2

agent = TestComposedFullAdder()
# Extract flow source
import inspect, textwrap
flow_src = textwrap.dedent(inspect.getsource(TestComposedFullAdder.flow))
if not flow_src.strip().startswith("def "):
    indented = "\n".join("    " + line for line in flow_src.splitlines())
    flow_src = f"def flow(self):\n{indented}"
    
parsed_ast = ast = __import__("ast").parse(flow_src)
visitor = LuminaASTVisitor(agent)
func_def = parsed_ast.body[0]
for stmt in func_def.body:
    visitor.visit(stmt)

print("Visitor Statements:")
for i, stmt in enumerate(visitor.statements):
    print(f"  {i}: {stmt}")

compiler = LuminaLogosCompiler()
compiler.register_map = {'A': None, 'B': None, 'C': None, 'D': None}
compiler.var_sources = agent.inputs.copy()
compiler.var_destinations = agent.outputs.copy()

# Precompute inputs
compiler.stmt_inputs = []
for stmt in visitor.statements:
    inputs_set = set()
    op_type = stmt[0]
    if op_type == "OP":
        inputs_set.add(stmt[3])
        inputs_set.add(stmt[4])
    elif op_type == "COND_ASSIGN":
        inputs_set.add(stmt[2])
        inputs_set.add(stmt[3])
        inputs_set.add(stmt[4])
    elif op_type == "STORE":
        inputs_set.add(stmt[1])
    elif op_type == "JUMP_IF_ACTIVE":
        inputs_set.add(stmt[1])
    compiler.stmt_inputs.append(inputs_set)

compiler._compute_liveness(visitor.statements)

print("\nLiveness Analysis:")
for i, stmt in enumerate(visitor.statements):
    print(f"  {i}: stmt={stmt} | live_out={compiler.live_out[i]}")

# Compile using compile_agent directly
print("\nCompiling via compile_agent...")
try:
    program = LuminaCompiler.compile_agent(TestComposedFullAdder)
    print("Compilation Succeeded! Generated Instructions:")
    for inst in program:
        print(f"  {inst}")
except Exception as e:
    import traceback
    traceback.print_exc()
