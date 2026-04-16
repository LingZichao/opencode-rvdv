from riscv.EnvRISCV import EnvRISCV
from riscv.GenThreadRISCV import GenThreadRISCV
from base.Sequence import Sequence


class MainSequence(Sequence):
    def generate(self, **kargs):
        # Phase 1: 纯分支预测错误（约800条指令）
        for i in range(800):
            if i % 6 == 0:
                self.genInstruction("BEQ##RISCV")
            elif i % 6 == 1:
                self.genInstruction("BNE##RISCV")
            elif i % 6 == 2:
                self.genInstruction("BLT##RISCV")
            elif i % 6 == 3:
                self.genInstruction("BGE##RISCV")
            elif i % 6 == 4:
                self.genInstruction("BLTU##RISCV")
            else:
                self.genInstruction("BGEU##RISCV")
        
        # Phase 2: 超长依赖链队列填满（约800条指令）
        for i in range(800):
            if i % 7 == 0:
                self.genInstruction("DIV##RISCV")
            elif i % 7 == 1:
                self.genInstruction("DIVU##RISCV")
            elif i % 7 == 2:
                self.genInstruction("REM##RISCV")
            elif i % 7 == 3:
                self.genInstruction("REMU##RISCV")
            elif i % 7 == 4:
                self.genInstruction("MULH##RISCV")
            elif i % 7 == 5:
                self.genInstruction("MULHU##RISCV")
            else:
                self.genInstruction("MULHSU##RISCV")
        
        # Phase 3: 精确控制条件组合（约800条指令）
        # Stage 1: 6 long instructions to reach queue count = 6
        for i in range(6):
            self.genInstruction("DIV##RISCV")
        
        # Stage 2: 2 new instructions (create 2)
        self.genInstruction("MULH##RISCV")
        self.genInstruction("MULHU##RISCV")
        
        # Stage 3: FENCE to pause pop
        self.genInstruction("FENCE##RISCV")
        
        # Stage 4: Continue with instructions to maintain state
        for i in range(780):
            if i % 5 == 0:
                self.genInstruction("ADD##RISCV")
            elif i % 5 == 1:
                self.genInstruction("SUB##RISCV")
            elif i % 5 == 2:
                self.genInstruction("AND##RISCV")
            elif i % 5 == 3:
                self.genInstruction("OR##RISCV")
            else:
                self.genInstruction("XOR##RISCV")
        
        # Phase 4: 边界条件全覆盖（约800条指令）
        # Queue count 0: after flush
        self.genInstruction("BEQ##RISCV")
        self.genInstruction("BNE##RISCV")
        
        # Queue count 1-5: gradual fill
        for i in range(5):
            self.genInstruction("ADD##RISCV")
        
        # Queue count 6-8: long dependency chain
        for i in range(10):
            if i % 3 == 0:
                self.genInstruction("DIV##RISCV")
            elif i % 3 == 1:
                self.genInstruction("REM##RISCV")
            else:
                self.genInstruction("MULH##RISCV")
        
        # Additional boundary conditions
        for i in range(750):
            if i % 8 == 0:
                self.genInstruction("ADD##RISCV")
            elif i % 8 == 1:
                self.genInstruction("SUB##RISCV")
            elif i % 8 == 2:
                self.genInstruction("AND##RISCV")
            elif i % 8 == 3:
                self.genInstruction("OR##RISCV")
            elif i % 8 == 4:
                self.genInstruction("XOR##RISCV")
            elif i % 8 == 5:
                self.genInstruction("SLL##RISCV")
            elif i % 8 == 6:
                self.genInstruction("SRL##RISCV")
            else:
                self.genInstruction("SRA##RISCV")

MainSequenceClass = MainSequence
GenThreadClass = GenThreadRISCV
EnvClass = EnvRISCV