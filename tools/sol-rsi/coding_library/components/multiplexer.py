from lumina_compiler import LuminaAgent

class MultiplexerAgent(LuminaAgent):
    def configure(self):
        self.inputs = {
            "a": "Basin_A",
            "b": "Basin_B",
            "sel": "Basin_Sel"
        }
        self.outputs = {
            "out": "Basin_Out"
        }

    def flow(self):
        self.out = (self.a & ~self.sel) | (self.b & self.sel)