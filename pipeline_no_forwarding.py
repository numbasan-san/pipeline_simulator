"""
PIPELINE SIN FORWARDING - VERSIÓN SIMPLE
================================================================================
Pipeline de 5 etapas SIN mecanismo de forwarding.
Todas las dependencias RAW causan stalls.
================================================================================
"""


class PipelineStage:
    def __init__(self):
        self.instruction = None
        self.bubble = True
        self.rd = None
        self.rs = None
        self.rt = None
        self.result = None
        self.reg_write = False
        self.val_rs = 0
        self.val_rt = 0


class PipelineNoForwarding:
    def __init__(self):
        self.IF = PipelineStage()
        self.ID = PipelineStage()
        self.EX = PipelineStage()
        self.MEM = PipelineStage()
        self.WB = PipelineStage()
        
        self.registers = [0] * 64
        
        self.cycle = 0
        self.stalls = 0
        self.bubbles_inserted = 0
        
        self.instructions = []
        self.pc = 0
        
        self.stall_pipeline = False
        self.stall_reason = ""
        
        self.cycle_history = []
        
        print(f"🔧 Pipeline SIN FORWARDING inicializado")
    
    def add_instruction(self, op, rd, rs, rt):
        self.instructions.append({
            'op': op.upper(),
            'rd': rd,
            'rs': rs,
            'rt': rt
        })
    
    def set_register(self, reg, value):
        if 0 <= reg < 64:
            self.registers[reg] = value
    
    def reset(self):
        self.IF = PipelineStage()
        self.ID = PipelineStage()
        self.EX = PipelineStage()
        self.MEM = PipelineStage()
        self.WB = PipelineStage()
        self.registers = [0] * 64
        self.cycle = 0
        self.stalls = 0
        self.bubbles_inserted = 0
        self.pc = 0
        self.stall_pipeline = False
        self.stall_reason = ""
        self.cycle_history = []
    
    def detect_hazard(self):
        """Detecta cualquier dependencia RAW (siempre causa stall)"""
        if not self.ID.bubble and self.ID.instruction:
            # Dependencia con instrucción en EX
            if (not self.EX.bubble and self.EX.reg_write and 
                self.EX.rd != 0 and 
                (self.EX.rd == self.ID.instruction['rs'] or 
                 self.EX.rd == self.ID.instruction['rt'])):
                self.stall_reason = f"RAW hazard (R{self.EX.rd})"
                return True
            # Dependencia con instrucción en MEM
            if (not self.MEM.bubble and self.MEM.reg_write and 
                self.MEM.rd != 0 and 
                (self.MEM.rd == self.ID.instruction['rs'] or 
                 self.MEM.rd == self.ID.instruction['rt'])):
                self.stall_reason = f"RAW hazard (R{self.MEM.rd})"
                return True
        return False
    
    def fetch(self):
        if self.stall_pipeline:
            return
        if self.pc < len(self.instructions):
            self.IF.instruction = self.instructions[self.pc]
            self.IF.bubble = False
            self.IF.rs = self.IF.instruction['rs']
            self.IF.rt = self.IF.instruction['rt']
            self.IF.rd = self.IF.instruction['rd']
            self.IF.reg_write = (self.IF.instruction['op'] != 'SW')
            self.pc += 1
        else:
            self.IF.bubble = True
            self.IF.instruction = None
    
    def decode(self):
        if self.stall_pipeline:
            self.ID.bubble = True
            self.ID.instruction = None
            self.bubbles_inserted += 1
            return
        if not self.IF.bubble:
            self.ID.instruction = self.IF.instruction
            self.ID.bubble = False
            self.ID.rs = self.IF.rs
            self.ID.rt = self.IF.rt
            self.ID.rd = self.IF.rd
            self.ID.reg_write = self.IF.reg_write
            self.ID.val_rs = 0
            self.ID.val_rt = 0
            if self.ID.rs != 0:
                self.ID.val_rs = self.registers[self.ID.rs]
            if self.ID.rt != 0 and self.ID.instruction['op'] in ['ADD', 'SUB']:
                self.ID.val_rt = self.registers[self.ID.rt]
        else:
            self.ID.bubble = True
            self.ID.instruction = None
    
    def execute(self):
        if not self.ID.bubble:
            self.EX.instruction = self.ID.instruction
            self.EX.bubble = False
            self.EX.rd = self.ID.rd
            self.EX.reg_write = self.ID.reg_write
            
            op1 = self.ID.val_rs
            op2 = self.ID.val_rt
            
            op = self.ID.instruction['op']
            if op == 'ADD':
                self.EX.result = op1 + op2
            elif op == 'SUB':
                self.EX.result = op1 - op2
            elif op == 'LW':
                self.EX.result = op1
            elif op == 'SW':
                self.EX.result = op1
        else:
            self.EX.bubble = True
            self.EX.result = None

    def memory(self):
        if not self.EX.bubble:
            self.MEM.instruction = self.EX.instruction
            self.MEM.bubble = False
            self.MEM.rd = self.EX.rd
            self.MEM.reg_write = self.EX.reg_write
            self.MEM.result = self.EX.result
            if self.MEM.instruction and self.MEM.instruction['op'] == 'LW':
                self.MEM.result = 200
        else:
            self.MEM.bubble = True
    
    def writeback(self):
        if not self.MEM.bubble and self.MEM.reg_write:
            if self.MEM.rd != 0:
                self.registers[self.MEM.rd] = self.MEM.result
                self.WB.instruction = self.MEM.instruction
                self.WB.bubble = False
                self.WB.rd = self.MEM.rd
                self.WB.result = self.MEM.result
            else:
                self.WB.bubble = True
        else:
            self.WB.bubble = True
    
    def get_stage_info(self, stage):
        if stage.bubble or stage.instruction is None:
            return None
        return {
            'op': stage.instruction['op'],
            'rd': stage.rd,
            'rs': stage.rs,
            'rt': stage.rt,
            'result': stage.result
        }
    
    def cycle_pipeline(self):
        self.cycle += 1
        
        # Detectar hazard (causa stall)
        need_stall = self.detect_hazard()
        
        self.stall_pipeline = need_stall
        if need_stall:
            self.stalls += 1
        
        pre_state = {
            'IF': self.get_stage_info(self.IF),
            'ID': self.get_stage_info(self.ID),
            'EX': self.get_stage_info(self.EX),
            'MEM': self.get_stage_info(self.MEM),
            'WB': self.get_stage_info(self.WB),
            'registers': self.registers.copy()
        }
        
        # Guardar MEM para WB
        mem_inst = self.MEM.instruction
        mem_rd = self.MEM.rd
        mem_write = self.MEM.reg_write
        mem_res = self.MEM.result
        
        # WB
        if not self.MEM.bubble and mem_write and mem_rd != 0:
            self.registers[mem_rd] = mem_res
            self.WB.instruction = mem_inst
            self.WB.bubble = False
            self.WB.rd = mem_rd
            self.WB.result = mem_res
        else:
            self.WB.bubble = True
        
        # MEM
        if not self.EX.bubble:
            self.MEM.instruction = self.EX.instruction
            self.MEM.bubble = False
            self.MEM.rd = self.EX.rd
            self.MEM.reg_write = self.EX.reg_write
            self.MEM.result = self.EX.result
            if self.MEM.instruction and self.MEM.instruction['op'] == 'LW':
                self.MEM.result = 200
        else:
            self.MEM.bubble = True
        
        # EX
        if not self.ID.bubble:
            self.EX.instruction = self.ID.instruction
            self.EX.bubble = False
            self.EX.rd = self.ID.rd
            self.EX.reg_write = self.ID.reg_write
            
            op1 = self.ID.val_rs
            op2 = self.ID.val_rt
            
            op = self.ID.instruction['op']
            if op == 'ADD':
                self.EX.result = op1 + op2
            elif op == 'SUB':
                self.EX.result = op1 - op2
            elif op == 'LW':
                self.EX.result = op1
            elif op == 'SW':
                self.EX.result = op1
        else:
            self.EX.bubble = True
            self.EX.result = None
        
        # ID
        if not self.stall_pipeline and not self.IF.bubble:
            self.ID.instruction = self.IF.instruction
            self.ID.bubble = False
            self.ID.rs = self.IF.rs
            self.ID.rt = self.IF.rt
            self.ID.rd = self.IF.rd
            self.ID.reg_write = self.IF.reg_write
            self.ID.val_rs = 0
            self.ID.val_rt = 0
            if self.ID.rs != 0:
                self.ID.val_rs = self.registers[self.ID.rs]
            if self.ID.rt != 0 and self.ID.instruction['op'] in ['ADD', 'SUB']:
                self.ID.val_rt = self.registers[self.ID.rt]
        else:
            self.ID.bubble = True
            self.ID.instruction = None
            if self.stall_pipeline:
                self.bubbles_inserted += 1
        
        # FI
        if not self.stall_pipeline and self.pc < len(self.instructions):
            self.IF.instruction = self.instructions[self.pc]
            self.IF.bubble = False
            self.IF.rs = self.IF.instruction['rs']
            self.IF.rt = self.IF.instruction['rt']
            self.IF.rd = self.IF.instruction['rd']
            self.IF.reg_write = (self.IF.instruction['op'] != 'SW')
            self.pc += 1
        else:
            self.IF.bubble = True
            self.IF.instruction = None
        
        post_state = {
            'IF': self.get_stage_info(self.IF),
            'ID': self.get_stage_info(self.ID),
            'EX': self.get_stage_info(self.EX),
            'MEM': self.get_stage_info(self.MEM),
            'WB': self.get_stage_info(self.WB),
            'registers': self.registers.copy()
        }
        
        self.cycle_history.append({
            'cycle': self.cycle,
            'pre_state': pre_state,
            'post_state': post_state,
            'stall': need_stall,
            'stall_reason': self.stall_reason if need_stall else None,
            'forwarding': None
        })
        
        self.stall_reason = ""

    def run(self):
        self.reset()
        
        used_registers = set()
        for inst in self.instructions:
            used_registers.add(inst.get('rd', 0))
            used_registers.add(inst.get('rs', 0))
            used_registers.add(inst.get('rt', 0))
        
        max_cycles = 500
        while (self.pc < len(self.instructions) or 
               not self.IF.bubble or 
               not self.ID.bubble or 
               not self.EX.bubble or 
               not self.MEM.bubble or
               not self.WB.bubble):
            self.cycle_pipeline()
            max_cycles -= 1
            if max_cycles <= 0:
                break
        
        for i, val in enumerate(self.registers):
            if val != 0:
                used_registers.add(i)
        
        used_registers_list = sorted([r for r in used_registers if r != 0 or self.registers[0] != 0])
        used_registers_dict = {r: self.registers[r] for r in used_registers_list}
        
        instructions_count = len(self.instructions)
        ideal_cycles = instructions_count + 4
        
        return {
            'total_cycles': self.cycle,
            'stalls': self.stalls,
            'bubbles': self.bubbles_inserted,
            'forwarding_events': 0,
            'instructions_count': instructions_count,
            'ideal_cycles': ideal_cycles,
            'efficiency': (ideal_cycles / self.cycle) * 100 if self.cycle > 0 else 0,
            'cycle_history': self.cycle_history,
            'final_registers': self.registers[:32],
            'used_registers': used_registers_dict,
            'used_registers_list': used_registers_list
        }