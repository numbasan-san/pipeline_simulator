"""
APLICACIÓN WEB - SIMULADOR DE PIPELINE RISC CON FORWARDING
================================================================================
Autor: numbasan-san.
Fecha: 07/04/2026.
Descripción: Servidor Flask que recibe instrucciones assembly, ejecuta la 
             simulación del pipeline de 5 etapas y devuelve los resultados 
             en formato JSON para visualización en la interfaz web.
================================================================================
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from pipeline_forwarding import Pipeline
from pipeline_no_forwarding import PipelineNoForwarding
import re
import sys

# ============================================================================
# CONFIGURACIÓN DE LA APLICACIÓN FLASK
# ============================================================================

app = Flask(__name__)
CORS(app)

# Aumentar límite de tamaño de petición (soporta programas grandes de hasta 16MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


# ============================================================================
# FUNCIÓN PARA PASEAR INSTRUCCIONES ASSEMBLY
# ============================================================================

def parse_instruction(inst_str):
    """
    Parsea una instrucción en formato texto a un diccionario estructurado.
    
    Formatos soportados:
        ADD Rd, Rs, Rt    -> Ej: ADD R1, R2, R3
        SUB Rd, Rs, Rt    -> Ej: SUB R4, R1, R5
        LW Rd, offset(Rs) -> Ej: LW R1, 0(R2)
        SW Rt, offset(Rs) -> Ej: SW R3, 0(R4)
    
    Args:
        inst_str (str): Línea de texto con la instrucción assembly
        
    Returns:
        dict or None: Diccionario con la instrucción parseada o None si es inválida
    """
    # Ignorar líneas que son comentarios (empiezan con #)
    if inst_str.startswith('#'):
        return None
    inst_str = inst_str.strip().upper()
    inst_str = re.sub(r'\s*,\s*', ',', inst_str)
    patterns = {
        'ADD': r'ADD\s+R(\d+),R(\d+),R(\d+)',
        'SUB': r'SUB\s+R(\d+),R(\d+),R(\d+)',
        'LW': r'LW\s+R(\d+),(\d+)\(R(\d+)\)',
        'SW': r'SW\s+R(\d+),(\d+)\(R(\d+)\)'
    }
    for op, pattern in patterns.items():
        match = re.match(pattern, inst_str)
        if match:
            try:
                if op in ['ADD', 'SUB']:
                    rd, rs, rt = map(int, match.groups())
                    return {'op': op, 'rd': rd, 'rs': rs, 'rt': rt}
                elif op == 'LW':
                    rd, offset, rs = map(int, match.groups())
                    return {'op': op, 'rd': rd, 'rs': rs, 'rt': 0, 'offset': offset}
                elif op == 'SW':
                    rt, offset, rs = map(int, match.groups())
                    return {'op': op, 'rd': 0, 'rs': rs, 'rt': rt, 'offset': offset}
            except:
                return None
    return None


@app.route('/')
def index():
    """Ruta raíz que sirve la interfaz web del simulador."""
    return render_template('index.html')


@app.route('/simulate', methods=['POST'])
def simulate():
    """Endpoint que ejecuta la simulación y devuelve resultados en JSON."""
    try:
        data = request.json
        
        instructions_text = data.get('instructions', '')
        registers_text = data.get('registers', '')
        enable_forwarding = data.get('enable_forwarding', True)
        
        # Parsear instrucciones
        instructions = []
        lines = instructions_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                inst = parse_instruction(line)
                if inst:
                    instructions.append(inst)
                elif line:
                    return jsonify({'error': f'Instrucción no válida: {line[:50]}...'})
        
        if not instructions:
            return jsonify({'error': 'No se encontraron instrucciones válidas'})
        
        print(f"Ejecutando simulación con {len(instructions)} instrucciones...")
        print(f"📥 Modo: {'FORWARDING ACTIVADO' if enable_forwarding else 'SIN FORWARDING'}")
        
        # ================================================================
        # SELECCIONAR EL PIPELINE CORRECTO SEGÚN LA OPCIÓN
        # ================================================================
        if enable_forwarding:
            print("✅ Usando pipeline CON forwarding")
            pipeline = Pipeline(enable_forwarding=True)
        else:
            print("❌ Usando pipeline SIN forwarding (versión paralela)")
            pipeline = PipelineNoForwarding()
        
        for inst in instructions:
            pipeline.add_instruction(
                inst['op'], 
                inst.get('rd', 0), 
                inst.get('rs', 0), 
                inst.get('rt', 0)
            )
        
        # Configurar registros iniciales
        if registers_text:
            for reg_str in registers_text.strip().split(','):
                reg_str = reg_str.strip()
                if '=' in reg_str:
                    parts = reg_str.split('=')
                    reg_name = parts[0].strip().upper()
                    try:
                        reg_num = int(reg_name.replace('R', ''))
                        reg_val = int(parts[1].strip())
                        pipeline.set_register(reg_num, reg_val)
                    except:
                        pass
        
        # Ejecutar simulación
        result = pipeline.run()
        
        print(f"Simulación completada: {result['total_cycles']} ciclos, {result['stalls']} stalls")
        
        # Formatear resultados
        formatted_cycles = []
        max_cycles_to_show = 200
        
        for i, cycle in enumerate(result['cycle_history']):
            if i >= max_cycles_to_show:
                break
            formatted_cycles.append({
                'cycle': cycle['cycle'],
                'stall': cycle['stall'],
                'stall_reason': cycle['stall_reason'],
                'forwarding': cycle.get('forwarding'),
                'pre': {
                    'IF': cycle['pre_state']['IF'],
                    'ID': cycle['pre_state']['ID'],
                    'EX': cycle['pre_state']['EX'],
                    'MEM': cycle['pre_state']['MEM'],
                    'WB': cycle['pre_state']['WB']
                },
                'post': {
                    'IF': cycle['post_state']['IF'],
                    'ID': cycle['post_state']['ID'],
                    'EX': cycle['post_state']['EX'],
                    'MEM': cycle['post_state']['MEM'],
                    'WB': cycle['post_state']['WB']
                }
            })
        
        response_data = {
            'success': True,
            'total_cycles': result['total_cycles'],
            'stalls': result['stalls'],
            'forwarding_events': result['forwarding_events'],
            'instructions_count': result.get('instructions_count', len(instructions)),
            'ideal_cycles': result.get('ideal_cycles', len(instructions) + 4),
            'efficiency': result.get('efficiency', 0),
            'cycles': formatted_cycles,
            'final_registers': result['final_registers'],
            'used_registers': result.get('used_registers', {}),
            'used_registers_list': result.get('used_registers_list', [])
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error en simulación: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error interno: {str(e)}'})

if __name__ == '__main__':
    sys.setrecursionlimit(10000)
    app.run(debug=True, port=5000, threaded=True)
