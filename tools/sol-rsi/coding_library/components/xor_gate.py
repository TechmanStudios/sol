from lumina_compiler import LuminaAgent

class XorGateAgent(LuminaAgent):
    def configure(self):
        self.inputs = {"x": "Basin_A", "y": "Basin_B"}
        self.outputs = {"z": "Basin_SUM"}

    def flow(self):
        self.z = self.x ^ self.y