from lumina_compiler import LuminaAgent

class HalfAdderAgent(LuminaAgent):
    def configure(self):
        self.inputs = {"x": "Basin_A", "y": "Basin_B"}
        self.outputs = {"sum": "Basin_SUM", "cout": "Basin_Cout"}

    def flow(self):
        self.sum = self.x ^ self.y
        self.cout = self.x & self.y