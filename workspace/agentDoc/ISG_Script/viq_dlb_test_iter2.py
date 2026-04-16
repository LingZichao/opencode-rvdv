from riscv.EnvRISCV import EnvRISCV
from riscv.GenThreadRISCV import GenThreadRISCV
from base.Sequence import Sequence


class MainSequence(Sequence):
    def generate(self, **kargs):
        # Basic initialization
        self.genInstruction("ADD##RISCV")
        self.genInstruction("SUB##RISCV")
        
        # Phase 1: Flush triggers
        for i in range(200):
            if i % 4 == 0:
                self.genInstruction("BEQ##RISCV")
            elif i % 4 == 1:
                self.genInstruction("BNE##RISCV")
            elif i % 4 == 2:
                self.genInstruction("ECALL##RISCV")
            else:
                self.genInstruction("EBREAK##RISCV")
        
        # Phase 2: Queue fill
        for i in range(150):
            if i % 3 == 0:
                self.genInstruction("MUL##RISCV")
            elif i % 3 == 1:
                self.genInstruction("DIV##RISCV")
            else:
                self.genInstruction("ADD##RISCV")
        
        # Phase 3: Complex conditions
        for i in range(150):
            if i % 3 == 0:
                self.genInstruction("MUL##RISCV")
            elif i % 3 == 1:
                self.genInstruction("ADD##RISCV")
            else:
                self.genInstruction("AND##RISCV")
        
        # Phase 4: Flush interaction
        for i in range(150):
            if i % 4 == 0:
                self.genInstruction("BEQ##RISCV")
            elif i % 4 == 1:
                self.genInstruction("ECALL##RISCV")
            elif i % 4 == 2:
                self.genInstruction("ADD##RISCV")
            else:
                self.genInstruction("MUL##RISCV")
        
        # Phase 5: Boundary conditions
        for i in range(150):
            if i % 3 == 0:
                self.genInstruction("ADD##RISCV")
            elif i % 3 == 1:
                self.genInstruction("LB##RISCV")
            else:
                self.genInstruction("SB##RISCV")

MainSequenceClass = MainSequence
GenThreadClass = GenThreadRISCV
EnvClass = EnvRISCV