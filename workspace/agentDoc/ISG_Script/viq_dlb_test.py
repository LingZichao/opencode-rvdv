from riscv.EnvRISCV import EnvRISCV
from riscv.GenThreadRISCV import GenThreadRISCV
from base.Sequence import Sequence


class MainSequence(Sequence):
    def generate(self, **kargs):
        # Phase 1: Generate 2000-3000 continuous floating-point instructions (FMUL.S and FDIV.S)
        # Create load imbalance between VIQ0 and VIQ1 using f0-f31 registers
        self.notice('Phase 1: Generating 2500 continuous FP instructions for VIQ load imbalance')
        for i in range(2500):
            # Use different float register combinations to avoid dependency conflicts
            # f0-f31 registers, cycle through different combinations
            reg_idx = i % 32
            reg1 = reg_idx
            reg2 = (reg_idx + 5) % 32
            reg3 = (reg_idx + 10) % 32
            
            # Alternate between FMUL.S and FDIV.S
            if i % 2 == 0:
                # FMUL.S f0, f1, f2
                self.genInstruction(f'FMUL.S##RISCV', {'rd': reg1, 'rs1': reg2, 'rs2': reg3})
            else:
                # FDIV.S f0, f1, f2
                self.genInstruction(f'FDIV.S##RISCV', {'rd': reg1, 'rs1': reg2, 'rs2': reg3})
        
        # Phase 2: Generate 1000-1500 mixed floating-point instructions
        # Verify DLB mechanism redirects instructions to VIQ1
        self.notice('Phase 2: Generating 1200 mixed FP instructions for DLB verification')
        for i in range(1200):
            reg_idx = i % 32
            reg1 = reg_idx
            reg2 = (reg_idx + 7) % 32
            reg3 = (reg_idx + 14) % 32
            
            # Cycle through FADD.S, FMUL.S, FSUB.S
            op_type = i % 3
            if op_type == 0:
                self.genInstruction(f'FADD.S##RISCV', {'rd': reg1, 'rs1': reg2, 'rs2': reg3})
            elif op_type == 1:
                self.genInstruction(f'FMUL.S##RISCV', {'rd': reg1, 'rs1': reg2, 'rs2': reg3})
            else:
                self.genInstruction(f'FSUB.S##RISCV', {'rd': reg1, 'rs1': reg2, 'rs2': reg3})
        
        # Phase 3: Generate 3000-5000 high-density floating-point instructions
        # Continuous stress testing of DLB mechanism
        self.notice('Phase 3: Generating 4000 high-density FP instructions for DLB stress test')
        for i in range(4000):
            reg_idx = i % 32
            reg1 = reg_idx
            reg2 = (reg_idx + 3) % 32
            reg3 = (reg_idx + 9) % 32
            
            # Use all available FP instructions for maximum density
            op_type = i % 4
            if op_type == 0:
                self.genInstruction(f'FMUL.S##RISCV', {'rd': reg1, 'rs1': reg2, 'rs2': reg3})
            elif op_type == 1:
                self.genInstruction(f'FDIV.S##RISCV', {'rd': reg1, 'rs1': reg2, 'rs2': reg3})
            elif op_type == 2:
                self.genInstruction(f'FADD.S##RISCV', {'rd': reg1, 'rs1': reg2, 'rs2': reg3})
            else:
                self.genInstruction(f'FSUB.S##RISCV', {'rd': reg1, 'rs1': reg2, 'rs2': reg3})

MainSequenceClass = MainSequence
GenThreadClass = GenThreadRISCV
EnvClass = EnvRISCV