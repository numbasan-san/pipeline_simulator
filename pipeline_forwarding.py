"""
PIPELINE CON FORWARDING - PIPELINE RISC DE 5 ETAPAS CON FORWARDING
================================================================================
Descripción: Implementación del pipeline de 5 etapas (FI, DI, EX, MEM, WB)
             con mecanismo de forwarding para resolver riesgos de datos (RAW).
             Soporta instrucciones: ADD, SUB, LW, SW.
================================================================================
"""


class PipelineStage:
    """
    Representa una etapa del pipeline.
    
    Cada etapa contiene:
        - instruction: La instrucción actual en la etapa (diccionario)
        - bubble: Indica si la etapa tiene una burbuja (stall)
        - rd, rs, rt: Números de registros destino/fuente
        - result: Resultado calculado en la etapa (para EX y MEM)
        - reg_write: Indica si la instrucción escribe un registro
        - val_rs, val_rt: Valores leídos de registros (solo para ID)
    """
    def __init__(self):
        self.instruction = None      # Instrucción actual
        self.bubble = True           # True = burbuja, False = instrucción válida
        self.rd = None               # Registro destino
        self.rs = None               # Registro fuente 1
        self.rt = None               # Registro fuente 2
        self.result = None           # Resultado de la etapa
        self.reg_write = False       # ¿Escribe en registro?
        self.val_rs = 0              # Valor leído de Rs
        self.val_rt = 0              # Valor leído de Rt


class Pipeline:
    """
    Simulador de pipeline RISC de 5 etapas con forwarding.
    
    Etapas del pipeline:
        1. FI (Instruction Fetch)   - Búsqueda de instrucción
        2. DI (Instruction Decode)  - Decodificación y lectura de registros
        3. EX (Execute)             - Ejecución en ALU
        4. MEM (Memory)             - Acceso a memoria (para LW/SW)
        5. WB (Write Back)          - Escritura en banco de registros
    
    El forwarding permite resolver dependencias RAW sin necesidad de stalls,
    excepto para LW que requiere 1 ciclo de stall (dato disponible en MEM).
    """
    
    def __init__(self, enable_forwarding=True):
        """
        Inicializa el pipeline con todas sus etapas vacías.
        
        Args:
            enable_forwarding (bool): True = forwarding activado, False = desactivado
        """

        print(f"🔧 Pipeline inicializado con forwarding={'ACTIVADO' if enable_forwarding else 'DESACTIVADO'}")

        # ====================================================================
        # ETAPAS DEL PIPELINE
        # ====================================================================
        self.IF = PipelineStage()      # Instruction Fetch
        self.ID = PipelineStage()      # Instruction Decode
        self.EX = PipelineStage()      # Execute
        self.MEM = PipelineStage()     # Memory
        self.WB = PipelineStage()      # Write Back
        
        # ====================================================================
        # BANCO DE REGISTROS (64 registros, R0 siempre 0)
        # ====================================================================
        self.registers = [0] * 64      # R0 a R63, todos inicializados a 0
        
        # ====================================================================
        # CONTADORES Y ESTADÍSTICAS
        # ====================================================================
        self.cycle = 0                  # Ciclo actual
        self.stalls = 0                 # Total de ciclos de stall
        self.bubbles_inserted = 0       # Burbujas insertadas en DI
        self.forwarding_events = 0      # Eventos de forwarding realizados
        self.lw_stalls = 0              # Stalls específicos por LW
        
        # ====================================================================
        # PROGRAMA A EJECUTAR
        # ====================================================================
        self.instructions = []          # Lista de instrucciones
        self.pc = 0                     # Program Counter (índice de instrucción)
        
        # ====================================================================
        # CONTROL DE STALLS
        # ====================================================================
        self.stall_pipeline = False     # Indica si el pipeline está detenido
        self.stall_reason = ""          # Razón del stall (para depuración)
        
        # ====================================================================
        # CONFIGURACIÓN DEL MODO
        # ====================================================================
        self.enable_forwarding = enable_forwarding   # Modo forwarding on/off
        
        # ====================================================================
        # HISTORIAL PARA VISUALIZACIÓN
        # ====================================================================
        self.cycle_history = []         # Registro de estados ciclo a ciclo
    
    # =========================================================================
    # MÉTODOS DE CONFIGURACIÓN DEL PROGRAMA
    # =========================================================================
    
    def add_instruction(self, op, rd, rs, rt):
        """
        Agrega una instrucción al programa.
        
        Args:
            op (str): Operación (ADD, SUB, LW, SW)
            rd (int): Registro destino
            rs (int): Registro fuente 1
            rt (int): Registro fuente 2 (para LW/SW se ignora)
        """
        self.instructions.append({
            'op': op.upper(),
            'rd': rd,
            'rs': rs,
            'rt': rt
        })
    
    def set_register(self, reg, value):
        """
        Establece el valor inicial de un registro.
        
        Args:
            reg (int): Número de registro (0-63)
            value (int): Valor a asignar
        """
        if 0 <= reg < 64:
            self.registers[reg] = value
    
    def reset(self):
        """
        Reinicia el pipeline para una nueva simulación.
        Limpia todas las etapas y restablece los contadores.
        """
        self.IF = PipelineStage()
        self.ID = PipelineStage()
        self.EX = PipelineStage()
        self.MEM = PipelineStage()
        self.WB = PipelineStage()
        self.registers = [0] * 64
        self.cycle = 0
        self.stalls = 0
        self.bubbles_inserted = 0
        self.forwarding_events = 0
        self.lw_stalls = 0
        self.pc = 0
        self.stall_pipeline = False
        self.stall_reason = ""
        self.cycle_history = []
    
    # =========================================================================
    # DETECCIÓN DE RIESGOS (HAZARDS)
    # =========================================================================
    
    def detect_lw_stall(self):
        """
        Detecta si se necesita un stall por dependencia con LW.
        Esto aplica TANTO con forwarding como sin forwarding,
        porque LW siempre necesita 1 ciclo de stall.
        
        Returns:
            bool: True si se necesita stall, False en caso contrario
        """
        # Verificar si hay LW en EX y depende de él
        if (not self.EX.bubble and self.EX.instruction and 
            self.EX.instruction['op'] == 'LW' and
            not self.ID.bubble and self.ID.instruction):
            
            # La instrucción en DI necesita el resultado del LW?
            if (self.EX.rd != 0 and 
                (self.EX.rd == self.ID.instruction['rs'] or 
                 self.EX.rd == self.ID.instruction['rt'])):
                self.lw_stalls += 1
                self.stall_reason = f"LW hazard (R{self.EX.rd})"
                return True
        return False
    
    def detect_data_hazard_without_forwarding(self):
        """
        Detecta dependencias de datos RAW cuando el forwarding está desactivado.
        Sin forwarding, cualquier dependencia requiere un stall.
        
        Returns:
            bool: True si hay dependencia que requiere stall
        """
        if not self.ID.bubble and self.ID.instruction:
            # Verificar dependencia con instrucción en EX
            if (not self.EX.bubble and self.EX.reg_write and 
                self.EX.rd != 0 and 
                (self.EX.rd == self.ID.instruction['rs'] or 
                 self.EX.rd == self.ID.instruction['rt'])):
                self.stall_reason = f"RAW hazard (R{self.EX.rd})"
                return True
            
            # Verificar dependencia con instrucción en MEM
            if (not self.MEM.bubble and self.MEM.reg_write and 
                self.MEM.rd != 0 and 
                (self.MEM.rd == self.ID.instruction['rs'] or 
                 self.MEM.rd == self.ID.instruction['rt'])):
                self.stall_reason = f"RAW hazard (R{self.MEM.rd})"
                return True
        return False
    
    # =========================================================================
    # ETAPAS DEL PIPELINE
    # =========================================================================
    
    def fetch(self):
        """
        Etapa FI (Instruction Fetch).
        Trae la siguiente instrucción de memoria (simulado) y la coloca en IF.
        Si hay stall, no avanza.
        """
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
        """
        Etapa DI (Instruction Decode).
        Decodifica la instrucción y lee los valores de los registros.
        Si hay stall, inserta una burbuja.
        """
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
            
            # Leer valores de registros (siempre desde el banco de registros)
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
        """
        Etapa EX (Execute).
        Ejecuta la operación en ALU con o sin forwarding según la configuración.
        
        Returns:
            str or None: Información del forwarding realizado (para visualización)
        """
        forwarding_info = None
        
        if not self.ID.bubble:
            # Guardar la instrucción anterior de EX antes de sobrescribir
            prev_ex_instruction = self.EX.instruction
            prev_ex_result = self.EX.result
            prev_ex_reg_write = self.EX.reg_write
            prev_ex_rd = self.EX.rd
            
            # Actualizar EX con la nueva instrucción
            self.EX.instruction = self.ID.instruction
            self.EX.bubble = False
            self.EX.rd = self.ID.rd
            self.EX.reg_write = self.ID.reg_write
            
            # Obtener operandos (valores leídos en DI)
            op1 = self.ID.val_rs
            op2 = self.ID.val_rt
            
            # ================================================================
            # MECANISMO DE FORWARDING (SOLO SI ESTÁ HABILITADO)
            # ================================================================
            if self.enable_forwarding:
                print(f"🔄 FORWARDING ACTIVADO en ciclo {self.cycle}")
                # Forwarding desde EX (instrucción anterior que estaba en EX)
                if (prev_ex_instruction and prev_ex_reg_write and 
                    prev_ex_rd != 0 and prev_ex_rd == self.ID.rs):
                    op1 = prev_ex_result
                    self.forwarding_events += 1
                    forwarding_info = f"R{prev_ex_rd} desde EX → RS"
                
                if (prev_ex_instruction and prev_ex_reg_write and 
                    prev_ex_rd != 0 and prev_ex_rd == self.ID.rt):
                    op2 = prev_ex_result
                    self.forwarding_events += 1
                    forwarding_info = f"R{prev_ex_rd} desde EX → RT"
                
                # Forwarding desde MEM
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
                    
            else:
                # SIN FORWARDING: No se hace nada, los operandos ya son los
                # valores leídos del banco de registros (que pueden ser obsoletos)
                print(f"❌ FORWARDING DESACTIVADO en ciclo {self.cycle}")
                pass
            # ================================================================
            # EJECUCIÓN DE LA OPERACIÓN
            # ================================================================
            op = self.ID.instruction['op']
            if op == 'ADD':
                self.EX.result = op1 + op2
            elif op == 'SUB':
                self.EX.result = op1 - op2
            elif op == 'LW':
                self.EX.result = op1      # Dirección base (simplificado)
            elif op == 'SW':
                self.EX.result = op1      # Dirección base (simplificado)
            
            return forwarding_info
        else:
            self.EX.bubble = True
            self.EX.result = None
            return None

    def memory(self):
        """
        Etapa MEM (Memory Access).
        Accede a memoria para instrucciones LW y SW.
        Para LW, simula la carga de un valor (200) desde memoria.
        """
        if not self.EX.bubble:
            self.MEM.instruction = self.EX.instruction
            self.MEM.bubble = False
            self.MEM.rd = self.EX.rd
            self.MEM.reg_write = self.EX.reg_write
            self.MEM.result = self.EX.result
            
            # Simular carga desde memoria para LW
            if self.MEM.instruction and self.MEM.instruction['op'] == 'LW':
                self.MEM.result = 200     # Valor fijo para simplificar
        else:
            self.MEM.bubble = True
    
    def writeback(self):
        """
        Etapa WB (Write Back).
        Escribe el resultado en el banco de registros.
        Solo para instrucciones que escriben (ADD, SUB, LW).
        """
        if not self.MEM.bubble and self.MEM.reg_write:
            if self.MEM.rd != 0:          # R0 nunca se escribe
                self.registers[self.MEM.rd] = self.MEM.result
    
    # =========================================================================
    # MÉTODOS DE GESTIÓN DEL ESTADO
    # =========================================================================
    
    def get_stage_info(self, stage):
        """
        Obtiene información formateada de una etapa del pipeline.
        
        Args:
            stage (PipelineStage): La etapa a inspeccionar
            
        Returns:
            dict or None: Diccionario con información de la etapa o None si es burbuja
        """
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
        """
        Ejecuta un ciclo completo del pipeline.
        
        El orden de ejecución es IMPORTANTE:
            1. Detectar stalls
            2. Ejecutar etapas en orden: WB → MEM → EX → ID → FI
            3. Guardar estado antes y después para visualización
        
        Este orden asegura que los datos fluyan correctamente y que
        el forwarding funcione adecuadamente.
        """
        self.cycle += 1
        
        # ====================================================================
        # 1. DETECTAR STALLS (antes de ejecutar las etapas)
        # ====================================================================
        if self.enable_forwarding:
            # Con forwarding: solo stalls por LW
            need_stall = self.detect_lw_stall()
        else:
            # Sin forwarding: stalls por LW y por cualquier dependencia RAW
            need_stall = self.detect_lw_stall() or self.detect_data_hazard_without_forwarding()
        
        self.stall_pipeline = need_stall
        if need_stall:
            self.stalls += 1
        
        # ====================================================================
        # 2. GUARDAR ESTADO ANTES DEL CICLO (para visualización)
        # ====================================================================
        pre_state = {
            'IF': self.get_stage_info(self.IF),
            'ID': self.get_stage_info(self.ID),
            'EX': self.get_stage_info(self.EX),
            'MEM': self.get_stage_info(self.MEM),
            'WB': self.get_stage_info(self.WB),
            'registers': self.registers.copy()
        }
        
        # ====================================================================
        # 3. EJECUTAR ETAPAS (orden inverso para evitar conflictos)
        # ====================================================================
        
        # Guardar lo que hay en MEM antes de sobrescribirlo (para WB)
        mem_instruction = self.MEM.instruction
        mem_rd = self.MEM.rd
        mem_reg_write = self.MEM.reg_write
        mem_result = self.MEM.result
        
        # --- WB: Escribe desde MEM (usando el valor guardado) ---
        if not self.MEM.bubble and mem_reg_write and mem_rd != 0:
            self.registers[mem_rd] = mem_result
            self.WB.instruction = mem_instruction
            self.WB.bubble = False
            self.WB.rd = mem_rd
            self.WB.result = mem_result
            self.WB.reg_write = True
        else:
            self.WB.bubble = True
            self.WB.instruction = None
        
        # --- MEM: Recibe de EX ---
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
            self.MEM.instruction = None
        
        # --- EX: Recibe de ID (con o sin forwarding según configuración) ---
        forwarding_info = None
        if not self.ID.bubble:
            # Guardar EX anterior para forwarding
            prev_ex_result = self.EX.result
            prev_ex_rd = self.EX.rd
            prev_ex_reg_write = self.EX.reg_write
            
            self.EX.instruction = self.ID.instruction
            self.EX.bubble = False
            self.EX.rd = self.ID.rd
            self.EX.reg_write = self.ID.reg_write
            
            op1 = self.ID.val_rs
            op2 = self.ID.val_rt
            
            # ================================================================
            # FORWARDING (SOLO SI ESTÁ HABILITADO)
            # ================================================================
            if self.enable_forwarding:
                # Forwarding desde EX anterior
                if (prev_ex_reg_write and prev_ex_rd != 0 and prev_ex_rd == self.ID.rs):
                    op1 = prev_ex_result
                    self.forwarding_events += 1
                    forwarding_info = f"R{prev_ex_rd} desde EX → RS"
                
                if (prev_ex_reg_write and prev_ex_rd != 0 and prev_ex_rd == self.ID.rt):
                    op2 = prev_ex_result
                    self.forwarding_events += 1
                    forwarding_info = f"R{prev_ex_rd} desde EX → RT"
                
                # Forwarding desde MEM
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
            # Si forwarding está deshabilitado, op1 y op2 ya son los valores
            # leídos del banco de registros en decode()
            
            # Ejecutar operación
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
        
        # --- ID: Recibe de IF ---
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
        
        # --- FI: Carga nueva instrucción ---
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
        
        # ====================================================================
        # 4. GUARDAR ESTADO DESPUÉS DEL CICLO (para visualización)
        # ====================================================================
        post_state = {
            'IF': self.get_stage_info(self.IF),
            'ID': self.get_stage_info(self.ID),
            'EX': self.get_stage_info(self.EX),
            'MEM': self.get_stage_info(self.MEM),
            'WB': self.get_stage_info(self.WB),
            'registers': self.registers.copy()
        }
        
        # ====================================================================
        # 5. REGISTRAR EN HISTORIAL
        # ====================================================================
        self.cycle_history.append({
            'cycle': self.cycle,
            'pre_state': pre_state,
            'post_state': post_state,
            'stall': need_stall,
            'stall_reason': self.stall_reason if need_stall else None,
            'forwarding': forwarding_info
        })
        
        self.stall_reason = ""
    
    # =========================================================================
    # EJECUCIÓN PRINCIPAL
    # =========================================================================
    
    def run(self):
        """Ejecuta el pipeline completo incluyendo vaciado"""
        self.reset()
        
        max_cycles = 500
        
        # Registrar qué registros fueron usados durante la simulación
        used_registers = set()
        
        # Marcar registros que aparecen en las instrucciones
        for inst in self.instructions:
            used_registers.add(inst.get('rd', 0))
            used_registers.add(inst.get('rs', 0))
            used_registers.add(inst.get('rt', 0))
        
        # Marcar registros con valores iniciales no cero
        for i, val in enumerate(self.registers):
            if val != 0:
                used_registers.add(i)
        
        while (self.pc < len(self.instructions) or 
               not self.IF.bubble or 
               not self.ID.bubble or 
               not self.EX.bubble or 
               not self.MEM.bubble or
               not self.WB.bubble):
            self.cycle_pipeline()
            max_cycles -= 1
            if max_cycles <= 0:
                print("Error: Límite de ciclos alcanzado")
                break
        
        # Marcar registros que terminaron con valor no cero
        for i, val in enumerate(self.registers):
            if val != 0:
                used_registers.add(i)
        
        # Filtrar R0 (solo mostrarlo si tiene valor != 0)
        if self.registers[0] == 0 and 0 in used_registers:
            used_registers.discard(0)
        
        # Ordenar registros
        used_registers_list = sorted(used_registers)
        
        # Crear diccionario de registros usados con sus valores
        used_registers_dict = {r: self.registers[r] for r in used_registers_list}
        
        instructions_count = len(self.instructions)
        ideal_cycles = instructions_count + 4
        
        return {
            'total_cycles': self.cycle,
            'stalls': self.stalls,
            'bubbles': self.bubbles_inserted,
            'forwarding_events': self.forwarding_events,
            'instructions_count': instructions_count,
            'ideal_cycles': ideal_cycles,
            'efficiency': (ideal_cycles / self.cycle) * 100 if self.cycle > 0 else 0,
            'cycle_history': self.cycle_history,
            'final_registers': self.registers[:32],
            'used_registers': used_registers_dict,
            'used_registers_list': used_registers_list
        }