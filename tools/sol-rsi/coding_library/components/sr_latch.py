from lumina_compiler import LuminaAgent

class SRLatchAgent(LuminaAgent):
    def configure(self):
        self.inputs = {"s": "Basin_S", "r": "Basin_R"}
        self.outputs = {"q": "Basin_Q", "qbar": "Basin_Qbar"}

    def flow(self):
        self.q = ~(self.r | self.qbar)
        self.qbar = ~(self.s | self.q)