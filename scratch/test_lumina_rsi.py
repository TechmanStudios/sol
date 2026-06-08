#!/usr/bin/env python3
# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Lumina Compiler & VM Runtime Verification Suite
=================================================
Runs unit tests to validate AST visitor parsing, loop compilation,
nudge/settle/assertion VM execution, and full compilation correctness.
"""

import sys
import unittest
from pathlib import Path

# Add project root and scratch paths to python path
sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))
sys.path.insert(0, str(sol_root / "tools" / "sol-rsi"))

from lumina_compiler import LuminaCompiler, LuminaAgent
from agentic_inventor import run_trial, TASKS

class TestLuminaCompiler(unittest.TestCase):
    def test_basic_assignments(self):
        """Test compiling basic XOR and standard assignments in Lumina."""
        inputs = {"x": "Basin_A", "y": "Basin_B"}
        outputs = {"z": "Basin_SUM"}
        flow_src = "self.z = self.x ^ self.y"
        
        instructions = LuminaCompiler.compile_flow_src(inputs, outputs, flow_src)
        self.assertTrue(len(instructions) > 0)
        
        ops = [inst.op for inst in instructions]
        self.assertIn("LOAD", ops)
        self.assertIn("XOR", ops)
        self.assertIn("STORE", ops)
        self.assertIn("CLEAR", ops)

    def test_while_loop_compilation(self):
        """Test compiling a while loop in Lumina."""
        inputs = {"x": "Basin_A", "y": "Basin_B"}
        outputs = {"z": "Basin_SUM"}
        flow_src = """
        self.z = self.x
        while self.z:
            self.z = self.y
        """
        
        instructions = LuminaCompiler.compile_flow_src(inputs, outputs, flow_src)
        ops = [inst.op for inst in instructions]
        
        self.assertIn("LABEL", ops)
        self.assertIn("JUMP", ops)
        self.assertIn("JUMP_IF_ACTIVE", ops)
        self.assertIn("NOT", ops)

    def test_analog_helpers_compilation(self):
        """Test compiling custom analog helper methods in Lumina."""
        inputs = {"x": "Basin_A"}
        outputs = {"z": "Basin_SUM"}
        flow_src = """
        self.nudge("Basin_SUM", 10.0)
        self.settle(15)
        self.assert_mass("A", 12.0)
        self.z = self.x
        """
        
        instructions = LuminaCompiler.compile_flow_src(inputs, outputs, flow_src)
        ops = [inst.op for inst in instructions]
        
        self.assertIn("NUDGE", ops)
        self.assertIn("SETTLE", ops)
        self.assertIn("ASSERT_MASS", ops)

    def test_vm_execution_with_analog_ops(self):
        """Test execution of custom instructions on the monkey-patched VM sequencer."""
        class TestNudgeAgent(LuminaAgent):
            def configure(self):
                self.inputs = {"x": "Basin_A"}
                self.outputs = {"z": "Basin_SUM"}
            def flow(self):
                self.nudge("Basin_SUM", 20.0)
                self.settle(10)
                self.assert_mass("A", 0.0) # will always pass since mass >= 0
                self.z = self.x
                
        program = LuminaCompiler.compile_agent(TestNudgeAgent)
        
        # Test XOR gate task with this program
        history, success, msg = run_trial("xor_gate", (1, 0), program)
        self.assertTrue(success, f"Trial failed with: {msg}")
        self.assertTrue(len(history) > 0)
        
        # Verify Basin_SUM mass was boosted by NUDGE
        final_sum_mass = history[-1]["rho_basin_c"] # Basin_SUM is the 3rd basin
        self.assertTrue(final_sum_mass > 20.0, f"Expected boosted mass, got {final_sum_mass}")

    def test_multiplexer_compilation(self):
        """Test compiling and executing a 2-to-1 Multiplexer."""
        class TestMuxAgent(LuminaAgent):
            def configure(self):
                self.inputs = {"a": "Basin_A", "b": "Basin_B", "sel": "Basin_Sel"}
                self.outputs = {"out": "Basin_Out"}
            def flow(self):
                self.out = self.b if self.sel else self.a
                
        program = LuminaCompiler.compile_agent(TestMuxAgent)
        self.assertTrue(len(program) > 0)
        
        # Test case: sel=0 -> out=a
        history, success, msg = run_trial("multiplexer", (1, 0, 0), program) # a=1, b=0, sel=0
        self.assertTrue(success, f"Mux trial failed: {msg}")
        
        # Test case: sel=1 -> out=b
        history, success, msg = run_trial("multiplexer", (0, 1, 1), program) # a=0, b=1, sel=1
        self.assertTrue(success, f"Mux trial failed: {msg}")

    def test_sr_latch_compilation(self):
        """Test compiling and executing a stateful SR Latch."""
        class TestSrLatchAgent(LuminaAgent):
            def configure(self):
                self.inputs = {"s": "Basin_S", "r": "Basin_R"}
                self.outputs = {"q": "Basin_Q", "qbar": "Basin_Qbar"}
            def flow(self):
                # Q = S | (Q & ~R)
                self.q = self.s | (self.q & ~self.r)
                self.qbar = ~self.q
                
        program = LuminaCompiler.compile_agent(TestSrLatchAgent)
        self.assertTrue(len(program) > 0)
        
        # Run sequential trial verifying Set, Hold, Reset, Hold sequence
        history, success, msg = run_trial("sr_latch", None, program)
        self.assertTrue(success, f"SR Latch sequential trial failed: {msg}")

    def test_hierarchical_composition_compilation(self):
        """Test compiling a composite agent using sub-components from the coding library."""
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
                
        program = LuminaCompiler.compile_agent(TestComposedFullAdder)
        self.assertTrue(len(program) > 0)
        
        ops = [inst.op for inst in program]
        # It should contain loaded variables and logic gates (XOR, AND_MS, OR_MS)
        self.assertIn("LOAD", ops)
        self.assertIn("XOR", ops)
        self.assertIn("AND_MS", ops)
        self.assertIn("OR_MS", ops)
        self.assertIn("STORE", ops)

class TestLLMIntegration(unittest.TestCase):
    def test_gemini_routing_and_client_resolution(self):
        """Test that client.py resolves Google Gemini provider correctly and maps config details."""
        import os
        from unittest.mock import patch, MagicMock
        from client import SolLLM
        import config

        # Temporarily mock MODELS and PROVIDERS in config to have a test configuration
        test_models = {
            "test_gemini": {
                "id": "gemini-3.5-flash",
                "name": "Gemini 3.5 Flash",
                "role": "primary",
                "provider": "google",
                "context_window": 1048576,
                "cost_per_1k_input": 0.000075,
                "cost_per_1k_output": 0.0003,
                "is_reasoning": False
            }
        }
        test_providers = {
            "google": {
                "name": "Google (Gemini)",
                "endpoint": "https://generativelanguage.googleapis.com",
                "env_var": "GOOGLE_API_KEY",
                "sdk": "openai"
            }
        }

        # Mock the environment to have GOOGLE_API_KEY set
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "fake_gemini_key_1234"}):
            with patch("config.MODELS", test_models), patch("config.PROVIDERS", test_providers), patch("client.MODELS", test_models):
                # Instantiate client
                llm = SolLLM(verbose=False)
                
                # Mock openai.OpenAI client
                with patch("openai.OpenAI") as mock_openai_cls:
                    mock_client = MagicMock()
                    mock_openai_cls.return_value = mock_client
                    
                    # Mock completion response
                    mock_response = MagicMock()
                    mock_response.choices = [MagicMock()]
                    mock_response.choices[0].message.content = "```python\n# mock code\n```"
                    mock_response.usage.prompt_tokens = 100
                    mock_response.usage.completion_tokens = 50
                    mock_client.chat.completions.create.return_value = mock_response

                    # Trigger a completion using the test gemini slot
                    res = llm._call_model(
                        messages=[{"role": "user", "content": "hi"}],
                        model_key="test_gemini",
                        max_tokens=1000,
                        temperature=0.4
                    )
                    
                    # Assert client was created with corrected endpoint and api key
                    mock_openai_cls.assert_called_once_with(
                        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
                        api_key="fake_gemini_key_1234"
                    )
                    self.assertTrue(res.success)
                    self.assertEqual(res.content, "```python\n# mock code\n```")

    def test_rate_limiting_circuit_breaker(self):
        """Test that client.py blocks calls when per-minute or per-day rate limits are exceeded."""
        from unittest.mock import patch
        from client import SolLLM

        llm = SolLLM(verbose=False)
        llm.budget = {
            "max_calls_per_cycle": 20,
            "max_cost_per_cycle_usd": 2.0,
            "max_cost_per_day_usd": 10.0,
            "max_calls_per_minute": 5,
            "max_calls_per_day": 10
        }

        # 1. Test when under limits
        with patch("client.load_recent_calls_count", return_value=2), \
             patch("client.load_daily_calls_count", return_value=4), \
             patch("client.load_daily_cost", return_value=0.5):
            ok, reason = llm._check_budget()
            self.assertTrue(ok)

        # 2. Test when per-minute calls exceed limit
        with patch("client.load_recent_calls_count", return_value=6), \
             patch("client.load_daily_calls_count", return_value=4), \
             patch("client.load_daily_cost", return_value=0.5):
            ok, reason = llm._check_budget()
            self.assertFalse(ok)
            self.assertIn("rate limit: too many calls in the last minute", reason)

        # 3. Test when per-day calls exceed limit
        with patch("client.load_recent_calls_count", return_value=2), \
             patch("client.load_daily_calls_count", return_value=12), \
             patch("client.load_daily_cost", return_value=0.5):
            ok, reason = llm._check_budget()
            self.assertFalse(ok)
            self.assertIn("rate limit: too many calls today", reason)

class TestCodingLibrary(unittest.TestCase):
    def test_library_manager_sync_and_load(self):
        """Test that LuminaLibraryAgent can sync from ledger, register, and serve components and docs."""
        import tempfile
        import shutil
        import json
        from pathlib import Path
        from coding_library.library_agent import LuminaLibraryAgent

        # Create a temp directory for the library
        temp_dir = Path(tempfile.mkdtemp())
        try:
            # Create a mock ledger file
            mock_ledger = temp_dir / "mock_ledger.jsonl"
            mock_entry = {
                "task": "mock_xor",
                "success": True,
                "history": [
                    {"cycle": 1, "status": "COMPILE_FAIL", "error": "some error", "code": ""},
                    {"cycle": 2, "status": "SUCCESS", "code": "class MockXor(LuminaAgent):\n    pass"}
                ]
            }
            with open(mock_ledger, "w", encoding="utf-8") as f:
                f.write(json.dumps(mock_entry) + "\n")

            # Create documentation directory structure inside temp
            doc_dir = temp_dir / "documentation"
            doc_dir.mkdir(parents=True, exist_ok=True)
            with open(doc_dir / "substrate_reference.md", "w", encoding="utf-8") as f:
                f.write("# Substrate Info")

            # Initialize library manager
            manager = LuminaLibraryAgent(library_dir=temp_dir)
            
            # Sync
            synced = manager.sync_from_ledger(ledger_path=mock_ledger)
            self.assertEqual(synced, ["mock_xor"])

            # Verify saved file
            saved_file = temp_dir / "components" / "mock_xor.py"
            self.assertTrue(saved_file.exists())
            with open(saved_file, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("MockXor", content)

            # Test list and load
            self.assertIn("mock_xor", manager.list_components())
            loaded_code = manager.load_component("mock_xor")
            self.assertIn("MockXor", loaded_code)

            # Test documentation retrieval
            doc_text = manager.get_documentation("substrate_reference")
            self.assertEqual(doc_text, "# Substrate Info")

        finally:
            shutil.rmtree(temp_dir)

    def test_expert_team_routing_and_queries(self):
        """Test that the expert team can route queries and respond using mocked client responses."""
        from unittest.mock import patch, MagicMock
        from coding_library.experts import LuminaExpertTeam
        
        team = LuminaExpertTeam()
        
        # 1. Test Substrate Expert routing and response
        with patch.object(team.experts["substrate"].llm, "_call_model") as mock_call:
            mock_res = MagicMock()
            mock_res.success = True
            mock_res.content = "Mass preservation requires rho >= 14.0."
            mock_call.return_value = mock_res
            
            ans = team.ask_expert("substrate", "Describe mass preservation limit.")
            self.assertEqual(ans, "Mass preservation requires rho >= 14.0.")
            mock_call.assert_called_once()
            
            # Verify system prompt content
            messages = mock_call.call_args[1]["messages"]
            self.assertIn("SOL Substrate Physics Expert", messages[0]["content"])
            
        # 2. Test Compiler Expert routing and response
        with patch.object(team.experts["compiler"].llm, "_call_model") as mock_call:
            mock_res = MagicMock()
            mock_res.success = True
            mock_res.content = "self.nudge maps to NUDGE instruction."
            mock_call.return_value = mock_res
            
            ans = team.ask_expert("compiler", "Explain self.nudge.")
            self.assertEqual(ans, "self.nudge maps to NUDGE instruction.")
            mock_call.assert_called_once()
            
            # Verify system prompt content
            messages = mock_call.call_args[1]["messages"]
            self.assertIn("Lumina Compiler and Instruction", messages[0]["content"])

        # 3. Test Synthesis Expert routing and response
        with patch.object(team.experts["synthesis"].llm, "_call_model") as mock_call:
            mock_res = MagicMock()
            mock_res.success = True
            mock_res.content = "XOR gate is verified in registry."
            mock_call.return_value = mock_res
            
            ans = team.ask_expert("synthesis", "What is verified?")
            self.assertEqual(ans, "XOR gate is verified in registry.")
            mock_call.assert_called_once()
            
            # Verify system prompt content
            messages = mock_call.call_args[1]["messages"]
            self.assertIn("Logic Synthesis Expert", messages[0]["content"])

    def test_exciton_moa_expert_routing_and_queries(self):
        """Test that the Exciton-MOA expert team can route queries and make library queries."""
        from unittest.mock import patch, MagicMock
        from coding_library.exciton_moa_experts import ExcitonMoaExpertTeam
        
        team = ExcitonMoaExpertTeam()
        
        # 1. Test Giants Expert routing
        with patch.object(team.experts["giants"].llm, "_call_model") as mock_call:
            mock_res = MagicMock()
            mock_res.success = True
            mock_res.content = "Statistician regulates pressure curve."
            mock_call.return_value = mock_res
            
            ans = team.ask_expert("giants", "What does Statistician do?")
            self.assertEqual(ans, "Statistician regulates pressure curve.")
            mock_call.assert_called_once()
            self.assertIn("Exciton-MOA Giants Expert", mock_call.call_args[1]["messages"][0]["content"])

        # 2. Test Manifold Expert routing
        with patch.object(team.experts["manifold"].llm, "_call_model") as mock_call:
            mock_res = MagicMock()
            mock_res.success = True
            mock_res.content = "Blank Manifold is a topological vacuum."
            mock_call.return_value = mock_res
            
            ans = team.ask_expert("manifold", "What is the Blank Manifold?")
            self.assertEqual(ans, "Blank Manifold is a topological vacuum.")
            mock_call.assert_called_once()
            self.assertIn("Exciton-MOA Manifold Expert", mock_call.call_args[1]["messages"][0]["content"])

        # 3. Test Cross-team query to Library
        with patch.object(team.lib_agent, "load_component", return_value="class MockGate: pass"):
            code = team.experts["giants"].query_library("xor_gate")
            self.assertEqual(code, "class MockGate: pass")

        with patch.object(team.lib_agent, "ask_expert", return_value="Mocked response on nudge."):
            ans = team.experts["manifold"].ask_lumina_expert("compiler", "nudge rules")
            self.assertEqual(ans, "Mocked response on nudge.")

    def test_level_architecture_expert_routing_and_queries(self):
        """Test that the Level Architecture expert team can route queries and make library queries."""
        from unittest.mock import patch, MagicMock
        from coding_library.level_architecture_experts import LevelArchitectureExpertTeam
        
        team = LevelArchitectureExpertTeam()
        
        # 1. Test Vertical Scaling Expert routing
        with patch.object(team.experts["vertical"].llm, "_call_model") as mock_call:
            mock_res = MagicMock()
            mock_res.success = True
            mock_res.content = "Level 11 is PDM tuned resonance."
            mock_call.return_value = mock_res
            
            ans = team.ask_expert("vertical", "What is Level 11?")
            self.assertEqual(ans, "Level 11 is PDM tuned resonance.")
            mock_call.assert_called_once()
            self.assertIn("Vertical Scaling Expert", mock_call.call_args[1]["messages"][0]["content"])

        # 2. Test Horizontal Routing Expert routing
        with patch.object(team.experts["horizontal"].llm, "_call_model") as mock_call:
            mock_res = MagicMock()
            mock_res.success = True
            mock_res.content = "Phase-Division Multiplexing splits lanes."
            mock_call.return_value = mock_res
            
            ans = team.ask_expert("horizontal", "How does phase routing work?")
            self.assertEqual(ans, "Phase-Division Multiplexing splits lanes.")
            mock_call.assert_called_once()
            self.assertIn("Horizontal Routing Expert", mock_call.call_args[1]["messages"][0]["content"])

    def test_library_unified_routing(self):
        """Test that LuminaLibraryAgent.ask_expert can route to all 7 experts."""
        from unittest.mock import patch
        from coding_library.library_agent import LuminaLibraryAgent
        
        manager = LuminaLibraryAgent()
        
        # Route to Exciton-MoA giants
        with patch("coding_library.exciton_moa_experts.ExcitonMoaExpertTeam.ask_expert", return_value="Giants called") as mock_moa:
            ans = manager.ask_expert("giants", "Hi Giants")
            self.assertEqual(ans, "Giants called")
            mock_moa.assert_called_once_with("giants", "Hi Giants", None)
            
        # Route to Level Architecture vertical
        with patch("coding_library.level_architecture_experts.LevelArchitectureExpertTeam.ask_expert", return_value="Vertical called") as mock_level:
            ans = manager.ask_expert("vertical", "Hi Vertical")
            self.assertEqual(ans, "Vertical called")
            mock_level.assert_called_once_with("vertical", "Hi Vertical", None)

        # Route to main compiler
        with patch("coding_library.experts.LuminaExpertTeam.ask_expert", return_value="Compiler called") as mock_main:
            ans = manager.ask_expert("compiler", "Hi Compiler")
            self.assertEqual(ans, "Compiler called")
            mock_main.assert_called_once_with("compiler", "Hi Compiler", None)

        # Route to Discovery
        with patch("coding_library.discovery_experts.DiscoveryExpertTeam.ask_expert", return_value="Discovery called") as mock_disc:
            ans = manager.ask_expert("discovery", "Hi Discovery")
            self.assertEqual(ans, "Discovery called")
            mock_disc.assert_called_once_with("discovery", "Hi Discovery", None)

        # Route to Experiment planner
        with patch("coding_library.experiment_experts.ExperimentExpertTeam.ask_expert", return_value="Planner called") as mock_plan:
            ans = manager.ask_expert("planner", "Hi Planner")
            self.assertEqual(ans, "Planner called")
            mock_plan.assert_called_once_with("planner", "Hi Planner", None)

        # Route to Wave Synthesis
        with patch("coding_library.advanced_experts.AdvancedExpertTeam.ask_expert", return_value="Wave called") as mock_wave:
            ans = manager.ask_expert("wave_synthesis", "Hi Wave")
            self.assertEqual(ans, "Wave called")
            mock_wave.assert_called_once_with("wave_synthesis", "Hi Wave", None)

        # Route to Compiler Optimizer
        with patch("coding_library.advanced_experts.AdvancedExpertTeam.ask_expert", return_value="Opt called") as mock_opt:
            ans = manager.ask_expert("compiler_optimizer", "Hi Opt")
            self.assertEqual(ans, "Opt called")
            mock_opt.assert_called_once_with("compiler_optimizer", "Hi Opt", None)

        # Route to Evolve Cortex
        with patch("coding_library.advanced_experts.AdvancedExpertTeam.ask_expert", return_value="Evolve called") as mock_evol:
            ans = manager.ask_expert("evolve_cortex", "Hi Evolve")
            self.assertEqual(ans, "Evolve called")
            mock_evol.assert_called_once_with("evolve_cortex", "Hi Evolve", None)

        # Route to Phase Calibration
        with patch("coding_library.calibration_experts.CalibrationExpertTeam.ask_expert", return_value="Phase called") as mock_phase:
            ans = manager.ask_expert("phase_calibration", "Hi Phase")
            self.assertEqual(ans, "Phase called")
            mock_phase.assert_called_once_with("phase_calibration", "Hi Phase", None)

        # Route to Acoustic Impedance
        with patch("coding_library.calibration_experts.CalibrationExpertTeam.ask_expert", return_value="Impedance called") as mock_imp:
            ans = manager.ask_expert("acoustic_impedance", "Hi Impedance")
            self.assertEqual(ans, "Impedance called")
            mock_imp.assert_called_once_with("acoustic_impedance", "Hi Impedance", None)

        # Route to Collision Arbitrator
        with patch("coding_library.network_experts.NetworkExpertTeam.ask_expert", return_value="Arbitrator called") as mock_arb:
            ans = manager.ask_expert("collision_arbitrator", "Hi Arbitrator")
            self.assertEqual(ans, "Arbitrator called")
            mock_arb.assert_called_once_with("collision_arbitrator", "Hi Arbitrator", None)

        # Route to Soliton Waveform
        with patch("coding_library.network_experts.NetworkExpertTeam.ask_expert", return_value="Soliton called") as mock_sol:
            ans = manager.ask_expert("soliton_waveform", "Hi Soliton")
            self.assertEqual(ans, "Soliton called")
            mock_sol.assert_called_once_with("soliton_waveform", "Hi Soliton", None)

        # Route to Mass Sentinel
        with patch("coding_library.verification_experts.VerificationExpertTeam.ask_expert", return_value="Sentinel called") as mock_sent:
            ans = manager.ask_expert("mass_sentinel", "Hi Sentinel")
            self.assertEqual(ans, "Sentinel called")
            mock_sent.assert_called_once_with("mass_sentinel", "Hi Sentinel", None)

        # Route to Circuit Proofer
        with patch("coding_library.verification_experts.VerificationExpertTeam.ask_expert", return_value="Proofer called") as mock_proof:
            ans = manager.ask_expert("circuit_proofer", "Hi Proofer")
            self.assertEqual(ans, "Proofer called")
            mock_proof.assert_called_once_with("circuit_proofer", "Hi Proofer", None)

        # Route to Resonant Attention
        with patch("coding_library.cognitive_experts.CognitiveExpertTeam.ask_expert", return_value="Attention called") as mock_att:
            ans = manager.ask_expert("resonant_attention", "Hi Attention")
            self.assertEqual(ans, "Attention called")
            mock_att.assert_called_once_with("resonant_attention", "Hi Attention", None)

        # Route to H-CAM Recall
        with patch("coding_library.cognitive_experts.CognitiveExpertTeam.ask_expert", return_value="Hcam called") as mock_hcam:
            ans = manager.ask_expert("hcam_recall", "Hi Hcam")
            self.assertEqual(ans, "Hcam called")
            mock_hcam.assert_called_once_with("hcam_recall", "Hi Hcam", None)

        # Route to Level Agent
        with patch("coding_library.level_agents.LevelOrchestrator.ask_level_agent", return_value="Level called") as mock_level_agent:
            ans = manager.ask_expert("level_agent", "Hi Level", {"level": 3})
            self.assertEqual(ans, "Level called")
            mock_level_agent.assert_called_once_with(3, "Hi Level", {"level": 3})

        # Route to Level 3 Agent directly by name
        with patch("coding_library.level_agents.LevelOrchestrator.ask_level_agent", return_value="Level 3 called") as mock_level_agent_3:
            ans = manager.ask_expert("level3", "Hi Level 3")
            self.assertEqual(ans, "Level 3 called")
            mock_level_agent_3.assert_called_once_with(3, "Hi Level 3", None)

        # Route to Level 12 Agent directly by name with underscore
        with patch("coding_library.level_agents.LevelOrchestrator.ask_level_agent", return_value="Level 12 called") as mock_level_agent_12:
            ans = manager.ask_expert("level_12", "Hi Level 12")
            self.assertEqual(ans, "Level 12 called")
            mock_level_agent_12.assert_called_once_with(12, "Hi Level 12", None)

    def test_discovery_expert_routing_and_queries(self):
        """Test that the Discovery expert team can route queries and load documents."""
        from unittest.mock import patch, MagicMock
        from coding_library.discovery_experts import DiscoveryExpertTeam
        
        team = DiscoveryExpertTeam()
        
        # 1. Test Discovery Expert routing
        with patch.object(team.experts["discovery"].llm, "_call_model") as mock_call:
            mock_res = MagicMock()
            mock_res.success = True
            mock_res.content = "Holographic Bus operates via wave interference."
            mock_call.return_value = mock_res
            
            ans = team.ask_expert("discovery", "Explain Holographic Bus.")
            self.assertEqual(ans, "Holographic Bus operates via wave interference.")
            mock_call.assert_called_once()
            self.assertIn("SOL Discovery Expert", mock_call.call_args[1]["messages"][0]["content"])

        # 2. Test Recommendation Expert routing
        with patch.object(team.experts["recommendation"].llm, "_call_model") as mock_call:
            mock_res = MagicMock()
            mock_res.success = True
            mock_res.content = "Recommend damping of 0.002."
            mock_call.return_value = mock_res
            
            ans = team.ask_expert("recommendation", "Suggest overrides.")
            self.assertEqual(ans, "Recommend damping of 0.002.")
            mock_call.assert_called_once()
            self.assertIn("SOL Recommendation Expert", mock_call.call_args[1]["messages"][0]["content"])

    def test_experiment_expert_routing_and_queries(self):
        """Test that the Experiment expert team can route queries."""
        from unittest.mock import patch, MagicMock
        from coding_library.experiment_experts import ExperimentExpertTeam
        
        team = ExperimentExpertTeam()
        
        # 1. Test Planner Expert routing
        with patch.object(team.experts["planner"].llm, "_call_model") as mock_call:
            mock_res = MagicMock()
            mock_res.success = True
            mock_res.content = "Plan sweeps input combinations."
            mock_call.return_value = mock_res
            
            ans = team.ask_expert("planner", "Design a test sweep.")
            self.assertEqual(ans, "Plan sweeps input combinations.")
            mock_call.assert_called_once()
            self.assertIn("SOL Experiment Planner Expert", mock_call.call_args[1]["messages"][0]["content"])

        # 2. Test Controller Expert routing
        with patch.object(team.experts["controller"].llm, "_call_model") as mock_call:
            mock_res = MagicMock()
            mock_res.success = True
            mock_res.content = "Controller executes and checks mass >= 14.0."
            mock_call.return_value = mock_res
            
            ans = team.ask_expert("controller", "Run the experiment.")
            self.assertEqual(ans, "Controller executes and checks mass >= 14.0.")
            mock_call.assert_called_once()
            self.assertIn("SOL Experiment Controller Expert", mock_call.call_args[1]["messages"][0]["content"])

    def test_advanced_expert_routing_and_queries(self):
        """Test that the Advanced expert team can route queries to synthesizer, optimizer, and cortex experts."""
        from unittest.mock import patch, MagicMock
        from coding_library.advanced_experts import AdvancedExpertTeam
        
        team = AdvancedExpertTeam()
        
        # 1. Test Wave Logic Synthesizer Expert routing
        with patch.object(team.experts["wave_synthesis"].llm, "_call_model") as mock_call:
            mock_res = MagicMock()
            mock_res.success = True
            mock_res.content = "Modulate carriers at phase 0.75 * pi."
            mock_call.return_value = mock_res
            
            ans = team.ask_expert("wave_synthesis", "Explain carrier phase mapping.")
            self.assertEqual(ans, "Modulate carriers at phase 0.75 * pi.")
            mock_call.assert_called_once()
            self.assertIn("SOL Wave-Logic Synthesizer Expert", mock_call.call_args[1]["messages"][0]["content"])

        # 2. Test Compiler Optimizer Expert routing
        with patch.object(team.experts["compiler_optimizer"].llm, "_call_model") as mock_call:
            mock_res = MagicMock()
            mock_res.success = True
            mock_res.content = "Minimize register spills by reuse."
            mock_call.return_value = mock_res
            
            ans = team.ask_expert("compiler_optimizer", "How to minimize spills?")
            self.assertEqual(ans, "Minimize register spills by reuse.")
            mock_call.assert_called_once()
            self.assertIn("SOL Compiler Optimizer Expert", mock_call.call_args[1]["messages"][0]["content"])

        # 3. Test Evolve Cortex Expert routing
        with patch.object(team.experts["evolve_cortex"].llm, "_call_model") as mock_call:
            mock_res = MagicMock()
            mock_res.success = True
            mock_res.content = "Mutation suggestions extracted from ledger."
            mock_call.return_value = mock_res
            
            ans = team.ask_expert("evolve_cortex", "Suggest prompt mutations.")
            self.assertEqual(ans, "Mutation suggestions extracted from ledger.")
            mock_call.assert_called_once()
            self.assertIn("SOL Evolve/Cortex Expert", mock_call.call_args[1]["messages"][0]["content"])

    def test_calibration_expert_routing_and_queries(self):
        """Test that the Calibration expert team can route queries to phase calibration and acoustic impedance experts."""
        from unittest.mock import patch, MagicMock
        from coding_library.calibration_experts import CalibrationExpertTeam

        team = CalibrationExpertTeam()

        # 1. Test Phase Calibration Expert routing
        with patch.object(team.experts["phase_calibration"].llm, "_call_model") as mock_call:
            mock_res = MagicMock()
            mock_res.success = True
            mock_res.content = "Realign carrier phases by 0.75 * pi."
            mock_call.return_value = mock_res

            ans = team.ask_expert("phase_calibration", "How to fix phase drift?")
            self.assertEqual(ans, "Realign carrier phases by 0.75 * pi.")
            mock_call.assert_called_once()
            self.assertIn("SOL Phase Calibration Expert", mock_call.call_args[1]["messages"][0]["content"])

        # 2. Test Acoustic Impedance Expert routing
        with patch.object(team.experts["acoustic_impedance"].llm, "_call_model") as mock_call:
            mock_res = MagicMock()
            mock_res.success = True
            mock_res.content = "Configure PML width of 16 grid cells."
            mock_call.return_value = mock_res

            ans = team.ask_expert("acoustic_impedance", "How to set up PML boundary?")
            self.assertEqual(ans, "Configure PML width of 16 grid cells.")
            mock_call.assert_called_once()
            self.assertIn("SOL Acoustic Impedance Expert", mock_call.call_args[1]["messages"][0]["content"])

    def test_network_expert_routing_and_queries(self):
        """Test that the Network expert team can route queries to collision arbitrator and soliton waveform experts."""
        from unittest.mock import patch, MagicMock
        from coding_library.network_experts import NetworkExpertTeam

        team = NetworkExpertTeam()

        # 1. Test Collision Arbitrator Expert routing
        with patch.object(team.experts["collision_arbitrator"].llm, "_call_model") as mock_call:
            mock_res = MagicMock()
            mock_res.success = True
            mock_res.content = "Route packets dynamically using Basin_Sel."
            mock_call.return_value = mock_res

            ans = team.ask_expert("collision_arbitrator", "How to route packets?")
            self.assertEqual(ans, "Route packets dynamically using Basin_Sel.")
            mock_call.assert_called_once()
            self.assertIn("SOL Waveguide Collision Arbitrator Expert", mock_call.call_args[1]["messages"][0]["content"])

        # 2. Test Soliton Waveform Expert routing
        with patch.object(team.experts["soliton_waveform"].llm, "_call_model") as mock_call:
            mock_res = MagicMock()
            mock_res.success = True
            mock_res.content = "Modulate envelopes using hyperbolic secant functions."
            mock_call.return_value = mock_res

            ans = team.ask_expert("soliton_waveform", "Describe soliton shape.")
            self.assertEqual(ans, "Modulate envelopes using hyperbolic secant functions.")
            mock_call.assert_called_once()
            self.assertIn("SOL Soliton Waveform Expert", mock_call.call_args[1]["messages"][0]["content"])

    def test_verification_expert_routing_and_queries(self):
        """Test that the Verification expert team can route queries to mass sentinel and circuit proofer experts."""
        from unittest.mock import patch, MagicMock
        from coding_library.verification_experts import VerificationExpertTeam

        team = VerificationExpertTeam()

        # 1. Test Mass Sentinel Expert routing
        with patch.object(team.experts["mass_sentinel"].llm, "_call_model") as mock_call:
            mock_res = MagicMock()
            mock_res.success = True
            mock_res.content = "Statically check loops for SETTLE instructions."
            mock_call.return_value = mock_res

            ans = team.ask_expert("mass_sentinel", "How to verify loops?")
            self.assertEqual(ans, "Statically check loops for SETTLE instructions.")
            mock_call.assert_called_once()
            self.assertIn("SOL Liveness & Mass Sentinel Expert", mock_call.call_args[1]["messages"][0]["content"])

        # 2. Test Circuit Proofer Expert routing
        with patch.object(team.experts["circuit_proofer"].llm, "_call_model") as mock_call:
            mock_res = MagicMock()
            mock_res.success = True
            mock_res.content = "Generate correctness assertions for adder circuit."
            mock_call.return_value = mock_res

            ans = team.ask_expert("circuit_proofer", "How to prove adder?")
            self.assertEqual(ans, "Generate correctness assertions for adder circuit.")
            mock_call.assert_called_once()
            self.assertIn("SOL Circuit Proofer Expert", mock_call.call_args[1]["messages"][0]["content"])

    def test_cognitive_expert_routing_and_queries(self):
        """Test that the Cognitive expert team can route queries to resonant attention and H-CAM recall experts."""
        from unittest.mock import patch, MagicMock
        from coding_library.cognitive_experts import CognitiveExpertTeam

        team = CognitiveExpertTeam()

        # 1. Test Resonant Attention Expert routing
        with patch.object(team.experts["resonant_attention"].llm, "_call_model") as mock_call:
            mock_res = MagicMock()
            mock_res.success = True
            mock_res.content = "Configure w0 and w1 phase-coherently."
            mock_call.return_value = mock_res

            ans = team.ask_expert("resonant_attention", "How to set attention weights?")
            self.assertEqual(ans, "Configure w0 and w1 phase-coherently.")
            mock_call.assert_called_once()
            self.assertIn("SOL Resonant Attention Expert", mock_call.call_args[1]["messages"][0]["content"])

        # 2. Test H-CAM Recall Expert routing
        with patch.object(team.experts["hcam_recall"].llm, "_call_model") as mock_call:
            mock_res = MagicMock()
            mock_res.success = True
            mock_res.content = "Superimpose query phase signatures."
            mock_call.return_value = mock_res

            ans = team.ask_expert("hcam_recall", "How to query H-CAM?")
            self.assertEqual(ans, "Superimpose query phase signatures.")
            mock_call.assert_called_once()
            self.assertIn("SOL H-CAM Recall Expert", mock_call.call_args[1]["messages"][0]["content"])

    def test_level_agents_loading_and_routing(self):
        """Test that LevelOrchestrator can load level configurations and query active level agents."""
        import tempfile
        import shutil
        import json
        from pathlib import Path
        from unittest.mock import patch, MagicMock
        from coding_library.level_agents import LevelOrchestrator

        temp_dir = Path(tempfile.mkdtemp())
        try:
            # Create a mock level_registry.json
            registry_file = temp_dir / "level_registry.json"
            mock_data = [
                {
                    "level_number": 3,
                    "name": "Sub-manifolds",
                    "description": "Attractor basin memory layer.",
                    "key_operations": ["SETTLE_BASIN"]
                }
            ]
            with open(registry_file, "w", encoding="utf-8") as f:
                json.dump(mock_data, f)

            # Initialize orchestrator in temp directory
            orch = LevelOrchestrator(library_dir=temp_dir)
            self.assertEqual(len(orch.levels_db), 1)
            self.assertEqual(orch.levels_db[0]["name"], "Sub-manifolds")

            # Route query to Level 3 Agent
            agent = orch.get_level_agent(3)
            self.assertIsNotNone(agent)
            self.assertEqual(agent.level_name, "Sub-manifolds")

            with patch.object(agent.llm, "_call_model") as mock_call:
                mock_res = MagicMock()
                mock_res.success = True
                mock_res.content = "Attractor dynamics settled."
                mock_call.return_value = mock_res

                ans = orch.ask_level_agent(3, "Verify Basin_A")
                self.assertEqual(ans, "Attractor dynamics settled.")
                mock_call.assert_called_once()
                self.assertIn("Level 3 Agent", mock_call.call_args[1]["messages"][0]["content"])

        finally:
            shutil.rmtree(temp_dir)

    def test_level_invention_and_registration(self):
        """Test that LevelOrchestrator can dynamically invent, register, and assign new level agents."""
        import tempfile
        import shutil
        import json
        from pathlib import Path
        from unittest.mock import patch, MagicMock
        from coding_library.level_agents import LevelOrchestrator

        temp_dir = Path(tempfile.mkdtemp())
        try:
            registry_file = temp_dir / "level_registry.json"
            with open(registry_file, "w", encoding="utf-8") as f:
                json.dump([], f)

            orch = LevelOrchestrator(library_dir=temp_dir)
            self.assertEqual(len(orch.levels_db), 0)

            # Register/invent Level 12 agent dynamically
            success = orch.register_new_level(
                level_num=12,
                name="Hyper-manifolds",
                description="Hyper-dimensional attractor spaces.",
                key_operations=["TENSOR_FLATTEN", "HYPER_RECALL"]
            )
            self.assertTrue(success)
            self.assertEqual(len(orch.levels_db), 1)
            self.assertEqual(orch.levels_db[0]["level_number"], 12)

            # Route query to newly invented Level 12 agent
            agent = orch.get_level_agent(12)
            self.assertIsNotNone(agent)
            self.assertEqual(agent.level_name, "Hyper-manifolds")
            self.assertIn("Level 12 Agent", agent.system_prompt)
            self.assertIn("Hyper-manifolds", agent.system_prompt)

            with patch.object(agent.llm, "_call_model") as mock_call:
                mock_res = MagicMock()
                mock_res.success = True
                mock_res.content = "Hyper-dimensional operations initialized."
                mock_call.return_value = mock_res

                ans = orch.ask_level_agent(12, "Run HYPER_RECALL")
                self.assertEqual(ans, "Hyper-dimensional operations initialized.")
                mock_call.assert_called_once()

        finally:
            shutil.rmtree(temp_dir)

    def test_substrate_ranger_diagnostics(self):
        """Test that LuminaSubstrateRanger can travel to a running sequencer and run diagnostics."""
        from coding_library.roaming_agents import LuminaSubstrateRanger
        from unittest.mock import MagicMock
        
        ranger = LuminaSubstrateRanger()
        mock_sequencer = MagicMock()
        mock_group = MagicMock()
        mock_sequencer.group = mock_group
        
        # Setup mock nodes
        mock_bat = {"rho": 4.0} # critically low
        mock_host = {"rho": 10.0} # total 14.0 (< 14.5)
        mock_group.get_node.side_effect = lambda n: mock_bat if "_B" in n else mock_host
        
        ranger.travel(mock_sequencer)
        self.assertEqual(ranger.current_context, mock_sequencer)
        
        res = ranger.run_diagnostics()
        self.assertEqual(res["status"], "DANGER")
        self.assertTrue(len(res["warnings"]) > 0)
        self.assertIn("Register A mass is critically low", res["warnings"][0])
        
    def test_hotfix_dispatcher_injection(self):
        """Test that LuminaHotfixDispatcher can travel to a sequencer and inject hotfix instructions."""
        from coding_library.roaming_agents import LuminaHotfixDispatcher
        from unittest.mock import MagicMock
        
        dispatcher = LuminaHotfixDispatcher()
        mock_sequencer = MagicMock()
        mock_group = MagicMock()
        mock_sequencer.group = mock_group
        
        # Setup low mass node
        mock_bat = {"rho": 4.0}
        mock_host = {"rho": 10.0} # total 14.0 (< 14.2)
        mock_group.get_node.side_effect = lambda n: mock_bat if "_B" in n else mock_host
        
        patched = dispatcher.intercept_and_patch(mock_sequencer)
        self.assertTrue(patched)
        self.assertTrue(mock_sequencer.execute_instruction.call_count >= 2)
        # Check that the hotfix for Register A was logged in state history
        self.assertTrue(any("boosted Register A" in log for log in dispatcher.state_history))
        
    def test_ledger_archivist_doc_compilation(self):
        """Test that LuminaLedgerArchivist can read JSONL files and compile a markdown report."""
        import tempfile
        import shutil
        import json
        from pathlib import Path
        from coding_library.roaming_agents import LuminaLedgerArchivist
        
        temp_dir = Path(tempfile.mkdtemp())
        try:
            # Write mock cost ledger entries
            ledger_file = temp_dir / "llm_cost_ledger.jsonl"
            with open(ledger_file, "w", encoding="utf-8") as f:
                f.write(json.dumps({"cost": 0.05, "prompt_tokens": 100}) + "\n")
                f.write(json.dumps({"cost": 0.02, "prompt_tokens": 50}) + "\n")
                
            archivist = LuminaLedgerArchivist()
            report = archivist.synthesize_reports(temp_dir)
            
            self.assertIn("Lumina Archivist Synthesized Report", report)
            self.assertIn("**Cumulative USD Cost**: $0.07000", report)
            self.assertIn("**Total Cost Ledger Entries**: 2", report)
            
        finally:
            shutil.rmtree(temp_dir)
            
    def test_roaming_agents_routing(self):
        """Test that library agent can route expert queries to roaming agents."""
        from unittest.mock import patch, MagicMock
        from coding_library.library_agent import LuminaLibraryAgent
        
        lib = LuminaLibraryAgent()
        with patch("coding_library.roaming_agents.LuminaSubstrateRanger.query", return_value="Ranger query active") as mock_q:
            ans = lib.ask_expert("ranger", "What is status?")
            self.assertEqual(ans, "Ranger query active")
            mock_q.assert_called_once_with("What is status?", None)

    def test_lessons_ledger_archiving(self):
        """Test that LuminaLedgerArchivist compiles lessons and level agents load them in context."""
        import tempfile
        import shutil
        import json
        from pathlib import Path
        from coding_library.roaming_agents import LuminaLedgerArchivist
        from coding_library.level_agents import LuminaLevelAgent
        
        temp_dir = Path(tempfile.mkdtemp())
        try:
            # Create a mock error log
            error_log = temp_dir / "rsi_run_error.log"
            with open(error_log, "w", encoding="utf-8") as f:
                f.write("AssertionError: Mass preservation failure on Register A: expected >= 14.0, got 13.5\n")
                f.write("Error: PLL synchronization lost in crossbar\n")
                
            archivist = LuminaLedgerArchivist()
            # Set library dir of archivist to temp_dir so it writes level_lessons.json there
            archivist.lib_agent.lib_dir = temp_dir
            
            lessons = archivist.extract_level_lessons(temp_dir)
            self.assertIn("3", lessons)
            self.assertIn("11", lessons)
            self.assertIn("Mass preservation failure on Register A", lessons["3"][0]["error"])
            
            # Verify level agent context loads the lesson
            level_agent = LuminaLevelAgent(3, "Sub-manifolds", "Memory layer", ["SETTLE_BASIN"], lib_agent=archivist.lib_agent)
            ctx = level_agent._get_context()
            self.assertIn("Historical Failures & Lessons Learned for this Level", ctx)
            self.assertIn("Mass preservation failure on Register A", ctx)
            
        finally:
            shutil.rmtree(temp_dir)
            
    def test_level_11_agent_loads_real_lessons(self):
        """Test that the Level 11 Agent loads the permanent level_lessons.json and holographic_bus_reference.md content."""
        from coding_library.level_agents import LevelOrchestrator
        from coding_library.library_agent import LuminaLibraryAgent
        
        lib = LuminaLibraryAgent()
        orch = LevelOrchestrator()
        agent = orch.get_level_agent(11, lib_agent=lib)
        self.assertIsNotNone(agent)
        
        ctx = agent._get_context()
        self.assertIn("Historical Failures & Lessons Learned for this Level", ctx)
        self.assertIn("PDM phase calibration failure for period 18.0", ctx)
        self.assertIn("Holographic Bus Reference", ctx)
        self.assertIn("Level 11 PDM Calibration and Stabilization Guidelines", ctx)

    def test_compiler_static_safety_proofing(self):
        """Test that LuminaCompiler triggers StaticVerificationError when safety is breached."""
        from lumina_compiler import LuminaCompiler, LuminaAgent, StaticVerificationError
        
        # 1. Flow that decays Register A too much (settle 120 steps)
        class BadAgent(LuminaAgent):
            def configure(self):
                self.inputs = {"x": "Basin_A"}
                self.outputs = {"z": "Basin_SUM"}
            def flow(self):
                self.z = self.x
                self.settle(120)  # active register z will decay below 14.0
                
        with self.assertRaises(StaticVerificationError) as context:
            LuminaCompiler.compile_agent(BadAgent, verify_mass=True)
            
        self.assertIn("drains Register", str(context.exception))
        
        # 2. Flow that compiles successfully with compensatory nudge
        class GoodAgent(LuminaAgent):
            def configure(self):
                self.inputs = {"x": "Basin_A"}
                self.outputs = {"z": "Basin_SUM"}
            def flow(self):
                self.z = self.x
                self.nudge("Basin_SUM", 10.0) # boost mass to 25.0
                self.settle(50)  # decays to 20.0 (still >= 14.0)
                
        program = LuminaCompiler.compile_agent(GoodAgent, verify_mass=True)
        self.assertTrue(len(program) > 0)
        
    def test_level_simulation_chambers(self):
        """Test that Level 1, 3, and 11 simulation chambers run operations correctly."""
        from coding_library.level_chambers import Level1Chamber, Level3Chamber, Level11Chamber
        
        # Test Level 1
        c1 = Level1Chamber()
        res1 = c1.execute([
            {"op": "CHARGE", "args": ["Cell_A"]},
            {"op": "READ_CELL", "args": ["Cell_A"]}
        ])
        self.assertEqual(res1["final_cells"]["Cell_A"], 10.0)
        self.assertIn("Charged cell Cell_A", res1["results"][0])
        
        # Test Level 3
        c3 = Level3Chamber(damping=0.02)
        res3 = c3.execute([
            {"op": "SETTLE_BASIN", "args": [10]},
            {"op": "MEASURE_RHO", "args": ["A"]}
        ])
        # Register A decays by 0.02 * 10 = 0.2 -> 14.8
        self.assertEqual(res3["final_registers"]["A"], 14.8)
        
        # Test Level 11
        c11 = Level11Chamber()
        res11 = c11.execute([
            {"op": "PDM_MODULATE", "args": [2, 0.75]},
            {"op": "PLL_SYNC", "args": []}
        ])
        self.assertEqual(res11["final_lanes"][2], [0.75])
        self.assertTrue(res11["pll_locked"])

if __name__ == "__main__":
    unittest.main()
