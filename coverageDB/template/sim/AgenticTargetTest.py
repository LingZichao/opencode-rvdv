from riscv.EnvRISCV import EnvRISCV
from riscv.GenThreadRISCV import GenThreadRISCV
from base.Sequence import Sequence


class MainSequence(Sequence):
    def generate(self, **kargs):
        # ============================================
        # 场景 1：Create1 inst0 选择精准触发（约 4000 条）
        # 目标：触发 Inst0 进入 Create1 通道的特定条件
        # 条件：Inst0=ALU, Inst1/2/3 中有 AIQ0 和 AIQ1 混合，且 AIQ0 不超过 1 个
        # ============================================
        
        # 子场景 1.1：Inst0=ALU, Inst1=MUL(AIQ0), Inst2=DIV(AIQ1), Inst3=LD/SD（约 1500 条）
        # 连续 4 条指令为一组，确保无依赖
        for group in range(375):  # 375 组 × 4 条 = 1500 条
            base_int = (group % 27) + 5
            base_offset = (group * 8) % 2048
            
            # Inst0: ALU 指令（ADD/AND/OR/XOR）- 可分配到 AIQ0 或 AIQ1
            alu_choice = group % 4
            if alu_choice == 0:
                self.genInstruction('ADD##RISCV', {'rd': base_int, 'rs1': ((base_int + 2) % 27) + 5, 'rs2': ((base_int + 4) % 27) + 5})
            elif alu_choice == 1:
                self.genInstruction('AND##RISCV', {'rd': base_int, 'rs1': ((base_int + 2) % 27) + 5, 'rs2': ((base_int + 4) % 27) + 5})
            elif alu_choice == 2:
                self.genInstruction('OR##RISCV', {'rd': base_int, 'rs1': ((base_int + 2) % 27) + 5, 'rs2': ((base_int + 4) % 27) + 5})
            else:
                self.genInstruction('XOR##RISCV', {'rd': base_int, 'rs1': ((base_int + 2) % 27) + 5, 'rs2': ((base_int + 4) % 27) + 5})
            
            # Inst1: MUL 指令（分配到 AIQ0）
            self.genInstruction('MUL##RISCV', {'rd': (base_int + 1) % 27 + 5, 'rs1': ((base_int + 6) % 27) + 5, 'rs2': ((base_int + 8) % 27) + 5})
            
            # Inst2: DIV 指令（分配到 AIQ1）- 使用固定非零除数
            self.genInstruction('DIV##RISCV', {'rd': (base_int + 2) % 27 + 5, 'rs1': ((base_int + 10) % 27) + 5, 'rs2': 5})
            
            # Inst3: LD 指令（分配到 LSIQ，不占用 AIQ）
            self.genInstruction('LD##RISCV', {'rd': (base_int + 3) % 27 + 5, 'rs1': 2, 'simm12': base_offset})
        
        # 子场景 1.2：Inst0=ALU, Inst1=DIV(AIQ1), Inst2=MUL(AIQ0), Inst3=BEQ/BNE（约 1500 条）
        for group in range(375):  # 375 组 × 4 条 = 1500 条
            base_int = (group % 27) + 5
            
            # Inst0: ALU 指令
            alu_choice = group % 4
            if alu_choice == 0:
                self.genInstruction('ADD##RISCV', {'rd': base_int, 'rs1': ((base_int + 2) % 27) + 5, 'rs2': ((base_int + 4) % 27) + 5})
            elif alu_choice == 1:
                self.genInstruction('AND##RISCV', {'rd': base_int, 'rs1': ((base_int + 2) % 27) + 5, 'rs2': ((base_int + 4) % 27) + 5})
            elif alu_choice == 2:
                self.genInstruction('OR##RISCV', {'rd': base_int, 'rs1': ((base_int + 2) % 27) + 5, 'rs2': ((base_int + 4) % 27) + 5})
            else:
                self.genInstruction('XOR##RISCV', {'rd': base_int, 'rs1': ((base_int + 2) % 27) + 5, 'rs2': ((base_int + 4) % 27) + 5})
            
            # Inst1: DIV 指令（分配到 AIQ1）
            self.genInstruction('DIV##RISCV', {'rd': (base_int + 1) % 27 + 5, 'rs1': ((base_int + 6) % 27) + 5, 'rs2': 5})
            
            # Inst2: MUL 指令（分配到 AIQ0）
            self.genInstruction('MUL##RISCV', {'rd': (base_int + 2) % 27 + 5, 'rs1': ((base_int + 8) % 27) + 5, 'rs2': ((base_int + 10) % 27) + 5})
            
            # Inst3: 分支指令（分配到 BIQ，不占用 AIQ）
            rs1 = ((base_int + 12) % 27) + 5
            rs2 = ((base_int + 14) % 27) + 5
            if group % 2 == 0:
                self.genInstruction('BEQ##RISCV', {'rs1': rs1, 'rs2': rs2, 'simm12': 8})
            else:
                self.genInstruction('BNE##RISCV', {'rs1': rs1, 'rs2': rs2, 'simm12': 8})
        
        # 子场景 1.3：Inst0=ALU, Inst1=MUL(AIQ0), Inst2=LD, Inst3=DIV(AIQ1)（约 1000 条）
        for group in range(250):  # 250 组 × 4 条 = 1000 条
            base_int = (group % 27) + 5
            base_offset = (group * 8) % 2048
            
            # Inst0: ALU 指令
            alu_choice = group % 4
            if alu_choice == 0:
                self.genInstruction('ADD##RISCV', {'rd': base_int, 'rs1': ((base_int + 2) % 27) + 5, 'rs2': ((base_int + 4) % 27) + 5})
            elif alu_choice == 1:
                self.genInstruction('SUB##RISCV', {'rd': base_int, 'rs1': ((base_int + 2) % 27) + 5, 'rs2': ((base_int + 4) % 27) + 5})
            elif alu_choice == 2:
                self.genInstruction('AND##RISCV', {'rd': base_int, 'rs1': ((base_int + 2) % 27) + 5, 'rs2': ((base_int + 4) % 27) + 5})
            else:
                self.genInstruction('OR##RISCV', {'rd': base_int, 'rs1': ((base_int + 2) % 27) + 5, 'rs2': ((base_int + 4) % 27) + 5})
            
            # Inst1: MUL 指令（分配到 AIQ0）
            self.genInstruction('MUL##RISCV', {'rd': (base_int + 1) % 27 + 5, 'rs1': ((base_int + 6) % 27) + 5, 'rs2': ((base_int + 8) % 27) + 5})
            
            # Inst2: LD 指令（分配到 LSIQ）
            self.genInstruction('LD##RISCV', {'rd': (base_int + 2) % 27 + 5, 'rs1': 2, 'simm12': base_offset})
            
            # Inst3: DIV 指令（分配到 AIQ1）
            self.genInstruction('DIV##RISCV', {'rd': (base_int + 3) % 27 + 5, 'rs1': ((base_int + 10) % 27) + 5, 'rs2': 5})
        
        # ============================================
        # 场景 2：Inst3 队列分配强化（约 3000 条）
        # 目标：确保 Inst3 被分配到各队列
        # 关键：连续 4 条指令同时有效，无 stall
        # ============================================
        
        # 子场景 2.1：Inst3 AIQ0 分配（约 1000 条）
        # 连续 4 条整数指令，最后一条是 MUL（分配到 AIQ0）
        for group in range(250):  # 250 组 × 4 条 = 1000 条
            base_int = (group % 27) + 5
            
            # Inst0-2: ADD 指令
            self.genInstruction('ADD##RISCV', {'rd': base_int, 'rs1': ((base_int + 2) % 27) + 5, 'rs2': ((base_int + 4) % 27) + 5})
            self.genInstruction('ADD##RISCV', {'rd': (base_int + 1) % 27 + 5, 'rs1': ((base_int + 6) % 27) + 5, 'rs2': ((base_int + 8) % 27) + 5})
            self.genInstruction('ADD##RISCV', {'rd': (base_int + 2) % 27 + 5, 'rs1': ((base_int + 10) % 27) + 5, 'rs2': ((base_int + 12) % 27) + 5})
            
            # Inst3: MUL 指令（分配到 AIQ0）
            self.genInstruction('MUL##RISCV', {'rd': (base_int + 3) % 27 + 5, 'rs1': ((base_int + 14) % 27) + 5, 'rs2': ((base_int + 16) % 27) + 5})
        
        # 子场景 2.2：Inst3 VIQ0 分配（约 1000 条）
        # 连续 4 条浮点指令，最后一条是 FDIV.S（分配到 VIQ0）
        for group in range(250):  # 250 组 × 4 条 = 1000 条
            base_fp = group % 32
            
            # Inst0-2: FADD.S 指令
            self.genInstruction('FADD.S##RISCV', {'rd': base_fp, 'rs1': (base_fp + 4) % 32, 'rs2': (base_fp + 8) % 32})
            self.genInstruction('FADD.S##RISCV', {'rd': (base_fp + 1) % 32, 'rs1': (base_fp + 12) % 32, 'rs2': (base_fp + 16) % 32})
            self.genInstruction('FADD.S##RISCV', {'rd': (base_fp + 2) % 32, 'rs1': (base_fp + 20) % 32, 'rs2': (base_fp + 24) % 32})
            
            # Inst3: FDIV.S 指令（分配到 VIQ0）
            self.genInstruction('FDIV.S##RISCV', {'rd': (base_fp + 3) % 32, 'rs1': (base_fp + 28) % 32, 'rs2': (base_fp + 5) % 32})
        
        # 子场景 2.3：Inst3 LSIQ 分配（约 1000 条）
        # 连续 4 条加载指令，全部分配到 LSIQ
        for group in range(250):  # 250 组 × 4 条 = 1000 条
            base_int = (group % 27) + 5
            base_offset = (group * 16) % 2048
            
            # Inst0-3: LD 指令（全部分配到 LSIQ）
            self.genInstruction('LD##RISCV', {'rd': base_int, 'rs1': 2, 'simm12': base_offset})
            self.genInstruction('LD##RISCV', {'rd': (base_int + 1) % 27 + 5, 'rs1': 2, 'simm12': (base_offset + 8) % 2048})
            self.genInstruction('LD##RISCV', {'rd': (base_int + 2) % 27 + 5, 'rs1': 2, 'simm12': (base_offset + 16) % 2048})
            self.genInstruction('LD##RISCV', {'rd': (base_int + 3) % 27 + 5, 'rs1': 2, 'simm12': (base_offset + 24) % 2048})
        
        # ============================================
        # 场景 3：AIQ1/VIQ1 Create1 inst1/inst2 回归测试（约 2000 条）
        # 目标：恢复第一轮已覆盖但第二轮丢失的场景
        # ============================================
        
        # 子场景 3.1：AIQ1 Create1 inst1/inst2 选择（约 1000 条）
        # 大量 DIV 指令填充 AIQ1，触发队列满条件
        for i in range(1000):
            rd = (i % 27) + 5
            # 无依赖，最大化并行
            self.genInstruction('DIV##RISCV', {'rd': rd, 'rs1': ((i + 5) % 27) + 5, 'rs2': 5})
        
        # 子场景 3.2：VIQ1 Create1 inst1/inst2 选择（约 1000 条）
        # 大量 FADD/FMUL 指令填充 VIQ1
        for i in range(500):
            rd = i % 32
            self.genInstruction('FADD.S##RISCV', {'rd': rd, 'rs1': (rd + 8) % 32, 'rs2': (rd + 16) % 32})
        
        for i in range(500):
            rd = i % 32
            self.genInstruction('FMUL.S##RISCV', {'rd': rd, 'rs1': (rd + 4) % 32, 'rs2': (rd + 12) % 32})
        
        # ============================================
        # 场景 4：三指令组合测试（约 1500 条）
        # 目标：触发三指令同时进入同一队列
        # ============================================
        
        # 子场景 4.1：三指令 AIQ0 组合（约 500 条）
        # 连续 3 条 MUL 指令
        for group in range(167):  # 167 组 × 3 条 ≈ 500 条
            base_int = (group % 27) + 5
            
            self.genInstruction('MUL##RISCV', {'rd': base_int, 'rs1': ((base_int + 2) % 27) + 5, 'rs2': ((base_int + 4) % 27) + 5})
            self.genInstruction('MUL##RISCV', {'rd': (base_int + 1) % 27 + 5, 'rs1': ((base_int + 6) % 27) + 5, 'rs2': ((base_int + 8) % 27) + 5})
            self.genInstruction('MUL##RISCV', {'rd': (base_int + 2) % 27 + 5, 'rs1': ((base_int + 10) % 27) + 5, 'rs2': ((base_int + 12) % 27) + 5})
        
        # 子场景 4.2：三指令 AIQ1 组合（约 500 条）
        # 连续 3 条 DIV 指令
        for group in range(167):  # 167 组 × 3 条 ≈ 500 条
            base_int = (group % 27) + 5
            
            self.genInstruction('DIV##RISCV', {'rd': base_int, 'rs1': ((base_int + 2) % 27) + 5, 'rs2': 5})
            self.genInstruction('DIV##RISCV', {'rd': (base_int + 1) % 27 + 5, 'rs1': ((base_int + 4) % 27) + 5, 'rs2': 5})
            self.genInstruction('DIV##RISCV', {'rd': (base_int + 2) % 27 + 5, 'rs1': ((base_int + 6) % 27) + 5, 'rs2': 5})
        
        # 子场景 4.3：三指令 VIQ 组合（约 500 条）
        # 连续 3 条 FADD.S 指令
        for group in range(167):  # 167 组 × 3 条 ≈ 500 条
            base_fp = group % 32
            
            self.genInstruction('FADD.S##RISCV', {'rd': base_fp, 'rs1': (base_fp + 8) % 32, 'rs2': (base_fp + 16) % 32})
            self.genInstruction('FADD.S##RISCV', {'rd': (base_fp + 1) % 32, 'rs1': (base_fp + 24) % 32, 'rs2': (base_fp + 5) % 32})
            self.genInstruction('FADD.S##RISCV', {'rd': (base_fp + 2) % 32, 'rs1': (base_fp + 12) % 32, 'rs2': (base_fp + 20) % 32})
        
        # ============================================
        # 场景 5：Stall 保持状态测试（约 500 条）
        # 目标：触发 IR 阶段 stall，让指令保持状态
        # ============================================
        
        # 子场景 5.1：寄存器依赖 Stall（约 250 条）
        # 100% RAW 依赖链，触发寄存器分配失败
        last_rd = 5
        for i in range(250):
            rd = (i % 27) + 5
            # 每条指令都依赖前一条的结果
            self.genInstruction('ADD##RISCV', {'rd': rd, 'rs1': last_rd, 'rs2': ((i + 7) % 27) + 5})
            last_rd = rd
        
        # 子场景 5.2：队列满 Stall（约 250 条）
        # 长延迟指令填充队列
        for i in range(125):
            rd = (i % 27) + 5
            self.genInstruction('DIV##RISCV', {'rd': rd, 'rs1': ((i + 5) % 27) + 5, 'rs2': 5})
        
        for i in range(125):
            rd = i % 32
            self.genInstruction('FDIV.S##RISCV', {'rd': rd, 'rs1': (rd + 4) % 32, 'rs2': (rd + 8) % 32})


MainSequenceClass = MainSequence
GenThreadClass = GenThreadRISCV
EnvClass = EnvRISCV
