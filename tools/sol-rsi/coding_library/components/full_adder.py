from lumina_compiler import LuminaAgent

class FullAdderAgent(LuminaAgent):
    def configure(self):
        self.inputs = {"x": "Basin_A", "y": "Basin_B", "cin": "Basin_Cin"}
        self.outputs = {"sum": "Basin_SUM", "cout": "Basin_Cout"}

    def flow(self):
        self.sum = self.x ^ self.y ^ self.cin
        self.cout = (self.x & self.y) | (self.x & self.cin) | (self.y & self.cin)