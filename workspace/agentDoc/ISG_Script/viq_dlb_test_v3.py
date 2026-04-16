from riscv.EnvRISCV import EnvRISCV
from riscv.GenThreadRISCV import GenThreadRISCV
from base.Sequence import Sequence


class MainSequence(Sequence):
    def generate(self, **kargs):
        # Stage 0: Initialization (10 instructions)
        # Purpose: Set initial state with simple floating-point load instructions
        for i in range(10):
            # Use f0-f3 registers
            reg_idx = i % 4  # f0-f3
            reg1 = reg_idx
            reg2 = (reg_idx + 1) % 4
            reg3 = (reg_idx + 2) % 4
            
            # Use FADD.S for initialization
            self.genInstruction('FADD.S##RISCV', {'rd': reg1, 'rs1': reg2, 'rs2': reg3})
        
        # Stage 1: Force fill VIQ0 (2000 FDIV.S instructions)
        # Purpose: Fill VIQ0 to capacity (8 entries), VIQ1 remains empty
        # FDIV.S can only go to VIQ0
        for i in range(2000):
            # Cycle through f0-f15 registers
            reg_idx = i % 16  # f0-f15
            reg1 = reg_idx
            reg2 = (reg_idx + 5) % 16
            reg3 = (reg_idx + 10) % 16
            
            # 100% FDIV.S to force all instructions to VIQ0
            self.genInstruction('FDIV.S##RISCV', {'rd': reg1, 'rs1': reg2, 'rs2': reg3})
        
        # Stage 2: Maintain state (500 integer instructions)
        # Purpose: Keep VIQ0 full and VIQ1 empty while allowing consumption
        for i in range(500):
            # Cycle through x1-x15 registers
            rd = (i % 15) + 1  # x1-x15
            rs1 = ((i + 1) % 15) + 1
            rs2 = ((i + 2) % 15) + 1
            
            if i % 5 == 0:
                self.genInstruction('ADD##RISCV', {'rd': rd, 'rs1': rs1, 'rs2': rs2})
            elif i % 5 == 1:
                self.genInstruction('SUB##RISCV', {'rd': rd, 'rs1': rs1, 'rs2': rs2})
            elif i % 5 == 2:
                self.genInstruction('AND##RISCV', {'rd': rd, 'rs1': rs1, 'rs2': rs2})
            elif i % 5 == 3:
                self.genInstruction('OR##RISCV', {'rd': rd, 'rs1': rs1, 'rs2': rs2})
            else:
                self.genInstruction('XOR##RISCV', {'rd': rd, 'rs1': rs1, 'rs2': rs2})
        
        # Stage 3: Trigger VIQ1 update (1500 instructions without division)
        # Purpose: Send instructions to VIQ1 to trigger viq1_ctrl_entry_cnt_updt_vld=1
        # Use FADD.S and FMUL.S (no FDIV.S) which can go to VIQ1
        for i in range(1500):
            # Cycle through f16-f31 registers
            reg_idx = (i % 16) + 16  # f16-f31
            reg1 = reg_idx
            reg2 = (reg_idx + 3) % 32
            reg3 = (reg_idx + 7) % 32
            
            # Alternate between FADD.S and FMUL.S
            if i % 2 == 0:
                self.genInstruction('FADD.S##RISCV', {'rd': reg1, 'rs1': reg2, 'rs2': reg3})
            else:
                self.genInstruction('FMUL.S##RISCV', {'rd': reg1, 'rs1': reg2, 'rs2': reg3})
        
        # Stage 4: Trigger flush operations (500 instructions)
        # Purpose: Trigger rtu_idu_flush_is and rtu_yy_xx_flush
        # First 300: conditional branch instructions
        for i in range(300):
            # Use x1-x15 for branch operands
            rs1 = (i % 15) + 1
            rs2 = ((i + 1) % 15) + 1
            
            # Alternate between different branch types
            if i % 4 == 0:
                self.genInstruction('BEQ##RISCV', {'rs1': rs1, 'rs2': rs2, 'simm12': 4})
            elif i % 4 == 1:
                self.genInstruction('BNE##RISCV', {'rs1': rs1, 'rs2': rs2, 'simm12': 4})
            elif i % 4 == 2:
                self.genInstruction('BLT##RISCV', {'rs1': rs1, 'rs2': rs2, 'simm12': 4})
            else:
                self.genInstruction('BGE##RISCV', {'rs1': rs1, 'rs2': rs2, 'simm12': 4})
        
        # Last 200: mixed floating-point and integer instructions
        for i in range(200):
            if i % 2 == 0:
                # Floating-point instruction
                reg_idx = i % 32  # f0-f31
                self.genInstruction('FADD.S##RISCV', {'rd': reg_idx, 'rs1': reg_idx, 'rs2': (reg_idx + 1) % 32})
            else:
                # Integer instruction
                rd = (i % 15) + 1
                rs1 = ((i + 1) % 15) + 1
                rs2 = ((i + 2) % 15) + 1
                self.genInstruction('ADD##RISCV', {'rd': rd, 'rs1': rs1, 'rs2': rs2})

MainSequenceClass = MainSequence
GenThreadClass = GenThreadRISCV
EnvClass = EnvRISCV
