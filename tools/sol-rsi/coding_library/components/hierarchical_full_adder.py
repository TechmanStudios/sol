from lumina_compiler import LuminaAgent


class HierarchicalFullAdderAgent(LuminaAgent):
    """
    Hierarchical Full-Adder composed of two distinct HalfAdder sub-component
    instances (ha1, ha2) plus a wave-OR carry combiner.
    """

    def configure(self):
        self.inputs = {"x": "Basin_A", "y": "Basin_B", "cin": "Basin_Cin"}
        self.outputs = {"sum": "Basin_SUM", "cout": "Basin_Cout"}
        self.ha1 = self.use_component(
            "half_adder",
            inputs={"x": "x", "y": "y"},
            outputs={"sum": "s1", "cout": "c1"},
            instance_name="ha1",
        )
        self.ha2 = self.use_component(
            "half_adder",
            inputs={"x": "s1", "y": "cin"},
            outputs={"sum": "sum", "cout": "c2"},
            instance_name="ha2",
        )

    def flow(self):
        self.ha1.run()
        self.ha2.run()
        self.cout = self.c1 | self.c2
