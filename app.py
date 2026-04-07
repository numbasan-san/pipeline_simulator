# app.py
from flask import Flask, render_template, request, jsonify
from pipeline_core import Pipeline
import re

app = Flask(__name__)

def parse_instruction(inst_str):
    """Parsea una instrucción en formato texto"""
    inst_str = inst_str.strip().upper()
    
    # Limpiar espacios en blanco alrededor de comas
    inst_str = re.sub(r'\s*,\s*', ',', inst_str)
    
    # Patrones para diferentes instrucciones
    patterns = {
        'ADD': r'ADD\s+R(\d+),R(\d+),R(\d+)',
        'SUB': r'SUB\s+R(\d+),R(\d+),R(\d+)',
        'LW': r'LW\s+R(\d+),(\d+)\(R(\d+)\)',
        'SW': r'SW\s+R(\d+),(\d+)\(R(\d+)\)'
    }
    
    for op, pattern in patterns.items():
        match = re.match(pattern, inst_str)
        if match:
            if op in ['ADD', 'SUB']:
                rd, rs, rt = map(int, match.groups())
                return {'op': op, 'rd': rd, 'rs': rs, 'rt': rt}
            elif op == 'LW':
                rd, offset, rs = map(int, match.groups())
                return {'op': op, 'rd': rd, 'rs': rs, 'rt': 0, 'offset': offset}
            elif op == 'SW':
                rt, offset, rs = map(int, match.groups())
                return {'op': op, 'rd': 0, 'rs': rs, 'rt': rt, 'offset': offset}
    
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/simulate', methods=['POST'])
def simulate():
    data = request.json
    
    instructions_text = data.get('instructions', '')
    registers_text = data.get('registers', '')
    enable_forwarding = data.get('enable_forwarding', True)
    
    # Parsear instrucciones
    instructions = []
    for line in instructions_text.strip().split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            inst = parse_instruction(line)
            if inst:
                instructions.append(inst)
            else:
                return jsonify({'error': f'Instrucción no válida: {line}'})
    
    if not instructions:
        return jsonify({'error': 'No se encontraron instrucciones válidas'})
    
    # Crear y configurar pipeline
    pipeline = Pipeline(enable_forwarding=enable_forwarding)
    
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
    
    # Formatear resultados para la respuesta
    formatted_cycles = []
    for cycle in result['cycle_history']:
        formatted_cycles.append({
            'cycle': cycle['cycle'],
            'stall': cycle['stall'],
            'stall_reason': cycle['stall_reason'],
            'forwarding': cycle['forwarding'],
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
    
    # Devolver todas las estadísticas
    return jsonify({
        'success': True,
        'total_cycles': result['total_cycles'],
        'stalls': result['stalls'],
        'forwarding_events': result['forwarding_events'],
        'instructions_count': result.get('instructions_count', len(instructions)),
        'ideal_cycles': result.get('ideal_cycles', len(instructions) + 4),
        'efficiency': result.get('efficiency', 0),
        'cycles': formatted_cycles,
        'final_registers': result['final_registers']
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
