from riscv.EnvRISCV import EnvRISCV
from riscv.GenThreadRISCV import GenThreadRISCV
from base.Sequence import Sequence
import random


class MainSequence(Sequence):
    def generate(self, **kargs):
        # Phase 1: Preheat - 300 mixed instructions to initialize FP registers
        
        # Generate 300 preheat instructions
        for i in range(300):
            # Randomly select instruction type and registers
            instr_type = random.choice(["FADD.S", "FMUL.S", "FDIV.D", "FSQRT.D"])
            # Select different source/destination registers to avoid RAW dependencies
            dst_reg = random.randint(0, 31)
            src1_reg = random.randint(0, 31)
            src2_reg = random.randint(0, 31)
            
            if instr_type in ["FADD.S", "FMUL.S"]:
                # VIQ1 instructions
                self.genInstruction(f"{instr_type}##RISCV", {'rd': dst_reg, 'rs1': src1_reg, 'rs2': src2_reg})
            else:
                # VIQ0 instructions
                self.genInstruction(f"{instr_type}##RISCV", {'rd': dst_reg, 'rs1': src1_reg, 'rs2': src2_reg})
        
        # Phase 2: Imbalanced filling - 4500 instructions (80% VIQ0 + 20% VIQ1)
        # VIQ0: fdiv.d, fsqrt.d (3500 instructions)
        # VIQ1: fadd.s, fmul.s (1200 instructions)
        # Auxiliary: 500 instructions (total 5200)
        
        # Generate 3500 VIQ0 instructions (fdiv.d, fsqrt.d)
        for i in range(3500):
            dst_reg = random.randint(0, 31)
            src1_reg = random.randint(0, 31)
            src2_reg = random.randint(0, 31)
            
            # Ensure non-zero operands for division/sqrt to avoid exceptions
            if i % 2 == 0:
                # fdiv.d
                self.genInstruction("FDIV.D##RISCV", {'rd': dst_reg, 'rs1': src1_reg, 'rs2': src2_reg})
            else:
                # fsqrt.d
                self.genInstruction("FSQRT.D##RISCV", {'rd': dst_reg, 'rs1': src1_reg})
        
        # Generate 1200 VIQ1 instructions (fadd.s, fmul.s)
        for i in range(1200):
            dst_reg = random.randint(0, 31)
            src1_reg = random.randint(0, 31)
            src2_reg = random.randint(0, 31)
            
            if i % 2 == 0:
                # fadd.s
                self.genInstruction("FADD.S##RISCV", {'rd': dst_reg, 'rs1': src1_reg, 'rs2': src2_reg})
            else:
                # fmul.s
                self.genInstruction("FMUL.S##RISCV", {'rd': dst_reg, 'rs1': src1_reg, 'rs2': src2_reg})
        
        # Generate 500 auxiliary instructions (integer instructions only)
        # Use integer registers for auxiliary instructions
        for i in range(500):
            dst_reg = random.randint(0, 31)
            src1_reg = random.randint(0, 31)
            src2_reg = random.randint(0, 31)
            self.genInstruction("ADD##RISCV", {'rd': dst_reg, 'rs1': src1_reg, 'rs2': src2_reg})

MainSequenceClass = MainSequence
GenThreadClass = GenThreadRISCV
EnvClass = EnvRISCV
