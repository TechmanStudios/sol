from lumina_compiler import LuminaAgent


class SRLatchAgent(LuminaAgent):
    def configure(self):
        self.inputs = {"s": "Basin_S", "r": "Basin_R"}
        self.outputs = {"q": "Basin_Q", "qbar": "Basin_Qbar"}

    def flow(self):
        not_both = ~(self.s & self.r)
        next_q = (self.s | (self.q & ~self.r)) & not_both
        next_qbar = (~next_q) & not_both
        self.q = next_q
        self.qbar = next_qbar