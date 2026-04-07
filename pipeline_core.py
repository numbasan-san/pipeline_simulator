# pipeline_core.py
class PipelineStage:
    """Representa una etapa del pipeline"""
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

class Pipeline:
    def __init__(self, enable_forwarding=True):
        # Etapas del pipeline
        self.IF = PipelineStage()
        self.ID = PipelineStage()
        self.EX = PipelineStage()
        self.MEM = PipelineStage()
        self.WB = PipelineStage()
        
        # Banco de registros
        self.registers = [0] * 32
        
        # Contadores
        self.cycle = 0
        self.stalls = 0
        self.bubbles_inserted = 0
        self.forwarding_events = 0
        self.lw_stalls = 0
        
        # Instrucciones
        self.instructions = []
        self.pc = 0
        
        # Control de stalls
        self.stall_pipeline = False
        self.stall_reason = ""
        
        # Modo
        self.enable_forwarding = enable_forwarding
        
        # Historial para visualización - Guardar estado ANTES y DESPUÉS de cada ciclo
        self.cycle_history = []
        
    def add_instruction(self, op, rd, rs, rt):
        self.instructions.append({
            'op': op.upper(),
            'rd': rd,
            'rs': rs,
            'rt': rt
        })
    
    def set_register(self, reg, value):
        if 0 <= reg < 32:
            self.registers[reg] = value
    
    def reset(self):
        """Reinicia el pipeline para una nueva simulación"""
        self.IF = PipelineStage()
        self.ID = PipelineStage()
        self.EX = PipelineStage()
        self.MEM = PipelineStage()
        self.WB = PipelineStage()
        self.cycle = 0
        self.stalls = 0
        self.bubbles_inserted = 0
        self.forwarding_events = 0
        self.lw_stalls = 0
        self.pc = 0
        self.stall_pipeline = False
        self.stall_reason = ""
        self.cycle_history = []
    
    def detect_lw_stall(self):
        if (not self.EX.bubble and self.EX.instruction and 
            self.EX.instruction['op'] == 'LW' and
            not self.ID.bubble and self.ID.instruction):
            
            if (self.EX.rd != 0 and 
                (self.EX.rd == self.ID.instruction['rs'] or 
                 self.EX.rd == self.ID.instruction['rt'])):
                self.lw_stalls += 1
                self.stall_reason = f"LW hazard (R{self.EX.rd})"
                return True
        return False
    
    def detect_data_hazard_without_forwarding(self):
        if not self.ID.bubble and self.ID.instruction:
            if (not self.EX.bubble and self.EX.reg_write and 
                self.EX.rd != 0 and 
                (self.EX.rd == self.ID.instruction['rs'] or 
                 self.EX.rd == self.ID.instruction['rt'])):
                self.stall_reason = f"RAW hazard (R{self.EX.rd})"
                return True
            
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
        forwarding_info = None
        
        if not self.ID.bubble:
            self.EX.instruction = self.ID.instruction
            self.EX.bubble = False
            self.EX.rd = self.ID.rd
            self.EX.reg_write = self.ID.reg_write
            
            op1 = self.ID.val_rs
            op2 = self.ID.val_rt
            
            if self.enable_forwarding:
                # CORRECCIÓN: Forwarding desde EX/MEM - Usar la instrucción ANTERIOR que está en EX
                # Antes de sobrescribir EX, verificamos forwarding desde la instrucción que ya estaba en EX
                if (self.EX.instruction and self.EX.reg_write and 
                    self.EX.rd != 0 and self.EX.rd == self.ID.rs):
                    op1 = self.EX.result
                    self.forwarding_events += 1
                    forwarding_info = f"R{self.EX.rd} desde EX → RS"
                
                if (self.EX.instruction and self.EX.reg_write and 
                    self.EX.rd != 0 and self.EX.rd == self.ID.rt):
                    op2 = self.EX.result
                    self.forwarding_events += 1
                    forwarding_info = f"R{self.EX.rd} desde EX → RT"
                
                # Forwarding desde MEM/WB
                if (self.MEM.instruction and self.MEM.reg_write and 
                    self.MEM.rd != 0 and self.MEM.rd == self.ID.rs):
                    op1 = self.MEM.result
                    self.forwarding_events += 1
                    forwarding_info = f"R{self.MEM.rd} desde MEM → RS"
                
                if (self.MEM.instruction and self.MEM.reg_write and 
                    self.MEM.rd != 0 and self.MEM.rd == self.ID.rt):
                    op2 = self.MEM.result
                    self.forwarding_events += 1
                    forwarding_info = f"R{self.MEM.rd} desde MEM → RT"
            
            op = self.ID.instruction['op']
            if op == 'ADD':
                self.EX.result = op1 + op2
            elif op == 'SUB':
                self.EX.result = op1 - op2
            elif op == 'LW':
                self.EX.result = op1
            elif op == 'SW':
                self.EX.result = op1
            
            return forwarding_info
        else:
            self.EX.bubble = True
            self.EX.result = None
            return None

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
    
    def get_stage_info(self, stage):
        """Obtiene información formateada de una etapa"""
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
        """Ejecuta un ciclo completo del pipeline y guarda el estado"""
        # Guardar estado ANTES del ciclo
        pre_state = {
            'IF': self.get_stage_info(self.IF),
            'ID': self.get_stage_info(self.ID),
            'EX': self.get_stage_info(self.EX),
            'MEM': self.get_stage_info(self.MEM),
            'WB': self.get_stage_info(self.WB),
            'registers': self.registers.copy()
        }
        
        self.cycle += 1
        
        # Detectar stalls
        if self.enable_forwarding:
            need_stall = self.detect_lw_stall()
        else:
            need_stall = self.detect_data_hazard_without_forwarding()
        
        self.stall_pipeline = need_stall
        if need_stall:
            self.stalls += 1
        
        # Ejecutar etapas (orden inverso)
        self.writeback()
        self.memory()
        forwarding_info = self.execute()
        self.decode()
        self.fetch()
        
        # Guardar estado DESPUÉS del ciclo
        post_state = {
            'IF': self.get_stage_info(self.IF),
            'ID': self.get_stage_info(self.ID),
            'EX': self.get_stage_info(self.EX),
            'MEM': self.get_stage_info(self.MEM),
            'WB': self.get_stage_info(self.WB),
            'registers': self.registers.copy()
        }
        
        # Guardar en historial
        self.cycle_history.append({
            'cycle': self.cycle,
            'pre_state': pre_state,
            'post_state': post_state,
            'stall': need_stall,
            'stall_reason': self.stall_reason if need_stall else None,
            'forwarding': forwarding_info
        })
        
        # Resetear razón de stall
        self.stall_reason = ""
    
    def run(self):
        """Ejecuta el pipeline completo incluyendo vaciado"""
        self.reset()
        
        # Contador para evitar loops infinitos (seguridad)
        max_cycles = 100
        
        # Continuar mientras haya instrucciones por cargar O pipeline no esté vacío
        while (self.pc < len(self.instructions) or 
               not self.IF.bubble or 
               not self.ID.bubble or 
               not self.EX.bubble or 
               not self.MEM.bubble or
               not self.WB.bubble):  # ¡Importante! Incluir WB
            self.cycle_pipeline()
            max_cycles -= 1
            if max_cycles <= 0:
                print("Error: Límite de ciclos alcanzado")
                break
        
        # Calcular estadísticas adicionales
        instructions_count = len(self.instructions)
        ideal_cycles = instructions_count + 4  # Pipeline ideal: N + 4 ciclos
        
        return {
            'total_cycles': self.cycle,
            'stalls': self.stalls,
            'bubbles': self.bubbles_inserted,
            'forwarding_events': self.forwarding_events,
            'instructions_count': instructions_count,
            'ideal_cycles': ideal_cycles,
            'efficiency': (ideal_cycles / self.cycle) * 100 if self.cycle > 0 else 0,
            'cycle_history': self.cycle_history,
            'final_registers': self.registers[:16]
        }
