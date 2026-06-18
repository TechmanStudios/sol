# SOL Micro-ISA v0 Specification

This document defines the official SOL Micro-ISA v0 instruction set, operand rules, and flags.

## Instruction Table

| Mnemonic | Category | Operands | Flags Read | Flags Written | Required | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `LOAD_IMM` | data_movement | register, immediate | None | None | Yes | Load immediate value into destination register |
| `LOAD` | memory | register, register | None | None | Yes | Load value from memory address stored in src1 into dst |
| `STORE` | memory | register, register | None | None | Yes | Store value from register dst into memory address stored in src1 |
| `MOV` | data_movement | register, register_or_immediate | None | None | Yes | Copy value from src1 to dst register |
| `ADD` | alu | register, register, register_or_immediate | None | zero, carry, overflow, sign | Yes | Add src1 and src2, store in dst, update flags |
| `SUB` | alu | register, register, register_or_immediate | None | zero, carry, overflow, sign, borrow | Yes | Subtract src2 from src1, store in dst, update flags |
| `AND` | bitwise | register, register, register_or_immediate | None | zero, sign, carry, overflow, borrow | Yes | Bitwise AND src1 and src2, store in dst, update flags |
| `OR` | bitwise | register, register, register_or_immediate | None | zero, sign, carry, overflow, borrow | Yes | Bitwise OR src1 and src2, store in dst, update flags |
| `XOR` | bitwise | register, register, register_or_immediate | None | zero, sign, carry, overflow, borrow | Yes | Bitwise XOR src1 and src2, store in dst, update flags |
| `NOT` | bitwise | register, register | None | zero, sign, carry, overflow, borrow | Yes | Bitwise NOT src1, store in dst, update flags |
| `SHL` | shift | register, register, register_or_immediate | None | zero, sign, carry, overflow, borrow | Yes | Logical shift left src1 by src2, store in dst, update flags |
| `SHR` | shift | register, register, register_or_immediate | None | zero, sign, carry, overflow, borrow | Yes | Logical shift right src1 by src2, store in dst, update flags |
| `CMP` | compare | register, register_or_immediate | None | zero, carry, overflow, sign, borrow | Yes | Compare dst and src1 by subtraction (dst - src1), discard result, update flags |
| `JMP` | branch | label | None | None | Yes | Unconditionally branch to target label |
| `JZ` | branch | label | zero | None | Yes | Branch to target label if zero flag is 1 |
| `JNZ` | branch | label | zero | None | Yes | Branch to target label if zero flag is 0 |
| `JC` | branch | label | carry | None | Yes | Branch to target label if carry flag is 1 |
| `JNC` | branch | label | carry | None | Yes | Branch to target label if carry flag is 0 |
| `JB` | branch | label | borrow | None | Yes | Branch to target label if borrow flag is 1 |
| `JNB` | branch | label | borrow | None | Yes | Branch to target label if borrow flag is 0 |
| `HALT` | control | None | None | None | Yes | Terminate program execution |

## Flags Definition

- **zero**: Set to 1 if result of ALU operation is 0, else 0.
- **carry**: Set if arithmetic operation generates a carry out.
- **overflow**: Set if signed arithmetic overflow occurs.
- **sign**: Set to MSB of result (1 for negative, 0 for positive).
- **borrow**: Set if subtraction requires a borrow (same as carry).

## Operand Constraints

1. **Registers**: Format `R0` to `R15` representing CPU register files.
2. **Immediates**: Integer values within 32-bit or 64-bit bounds.
3. **Labels**: String tokens indicating jump target labels or program PC addresses.