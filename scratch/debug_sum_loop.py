import sys
sys.path.append("tools/sol-core")
from sol_wideword_computation_validation import WideWordVirtualVM
from tests.test_wideword_waveguide_program_execution import make_sum_loop_program

vm = WideWordVirtualVM(width=32)
prog = make_sum_loop_program(10)
report = vm.run_program_with_backend(prog, backend="lane_fabric_vm")
print("success:", report.success)
print("oracle_match:", report.oracle_match)
print("cases_passed:", report.cases_passed)
print("cases_failed:", report.cases_failed)
if hasattr(vm, "trace_steps"):
    for step in vm.trace_steps:
        print(f"step {step.step_index}: PC={step.pc_before}->{step.pc_after} Inst={step.instruction} SOL={step.sol_result} ORACLE={step.oracle_result} match={step.match}")
        if step.sol_flags != step.oracle_flags:
            print("  SOL flags:", step.sol_flags)
            print("  ORACLE flags:", step.oracle_flags)

mismatches = vm.compare_program_trace_to_oracle()
for m in mismatches:
    print(f"Mismatch: step={m.step_index} pc={m.pc} reason={m.failure_reason}")
    if "details" in m.__dict__ or hasattr(m, "details"):
        print("  details:", m.details)
