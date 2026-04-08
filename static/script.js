/**
 * ============================================================================
 * SIMULADOR DE PIPELINE RISC CON FORWARDING - JAVASCRIPT FRONTEND
 * ============================================================================
 * Autor: numbasan-san.
 * Fecha: 07/04/2026.
 * Descripción: Controlador principal de la interfaz web.
 * ============================================================================
 */

// ============================================================================
// VARIABLES GLOBALES
// ============================================================================

let simulationData = null;
let currentCycleIndex = 0;
let animationInterval = null;

// ============================================================================
// INICIALIZACIÓN
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    const simulateBtn = document.getElementById('simulateBtn');
    const loadExample1 = document.getElementById('loadExample1');
    const loadExample2 = document.getElementById('loadExample2');
    const loadExample3 = document.getElementById('loadExample3');
    const prevCycle = document.getElementById('prevCycle');
    const nextCycle = document.getElementById('nextCycle');
    const playAnimation = document.getElementById('playAnimation');
    const manualBtn = document.getElementById('manualBtn');
    const modal = document.getElementById('manualModal');
    const closeBtn = document.querySelector('.close');
    const closeModalBtn = document.getElementById('closeModalBtn');
    
    if (simulateBtn) simulateBtn.addEventListener('click', runSimulation);
    if (loadExample1) loadExample1.addEventListener('click', () => loadExample(1));
    if (loadExample2) loadExample2.addEventListener('click', () => loadExample(2));
    if (loadExample3) loadExample3.addEventListener('click', () => loadExample(3));
    if (prevCycle) prevCycle.addEventListener('click', () => navigateCycle(-1));
    if (nextCycle) nextCycle.addEventListener('click', () => navigateCycle(1));
    if (playAnimation) playAnimation.addEventListener('click', toggleAnimation);
    
    if (manualBtn) {
        manualBtn.addEventListener('click', () => {
            if (modal) {
                modal.style.display = 'block';
                document.body.style.overflow = 'hidden';
            }
        });
    }
    
    if (closeBtn) closeBtn.addEventListener('click', () => {
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
    });
    
    if (closeModalBtn) closeModalBtn.addEventListener('click', () => {
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
    });
    
    window.addEventListener('click', (event) => {
        if (event.target === modal) {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
    });
});

// ============================================================================
// CARGA DE EJEMPLOS
// ============================================================================

function loadExample(exampleNum) {
    const instructionsTextarea = document.getElementById('instructions');
    const registersInput = document.getElementById('registers');
    
    if (!instructionsTextarea || !registersInput) return;
    
    if (exampleNum === 1) {
        instructionsTextarea.value = `ADD R1, R2, R3
SUB R4, R1, R5`;
        registersInput.value = 'R2=10, R3=5, R5=2';
    } else if (exampleNum === 2) {
        instructionsTextarea.value = `LW R1, 0(R2)
ADD R3, R1, R4`;
        registersInput.value = 'R2=100, R4=50';
    } else if (exampleNum === 3) {
        instructionsTextarea.value = `ADD R1, R2, R3
SUB R4, R1, R5
ADD R6, R1, R4`;
        registersInput.value = 'R2=10, R3=5, R5=2';
    }
    
    // El checkbox NO se modifica al cargar ejemplos
    // (mantiene el estado que el usuario eligió)
    
    setTimeout(() => runSimulation(), 100);
}

// ============================================================================
// SIMULACIÓN PRINCIPAL
// ============================================================================

async function runSimulation() {
    if (animationInterval) {
        clearInterval(animationInterval);
        animationInterval = null;
        const playButton = document.getElementById('playAnimation');
        if (playButton) playButton.textContent = '▶ Reproducir';
    }
    
    const instructions = document.getElementById('instructions')?.value || '';
    const registers = document.getElementById('registers')?.value || '';
    const enableForwardingCheckbox = document.getElementById('enableForwarding');
    const enableForwarding = enableForwardingCheckbox ? enableForwardingCheckbox.checked : true;
    
    console.log("🔘 Checkbox marcado?:", enableForwarding);
    
    const resultsPanel = document.getElementById('resultsPanel');
    if (!resultsPanel) return;
    
    resultsPanel.style.display = 'block';
    resultsPanel.innerHTML = '<div style="text-align:center; padding:50px;"><div class="spinner"></div><p>🔄 Simulando pipeline...</p></div>';
    
    try {
        const response = await fetch('/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                instructions: instructions, 
                registers: registers, 
                enable_forwarding: enableForwarding
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            simulationData = data;
            // 🔑 Guardar el modo usado para el título
            simulationData.mode_forwarding = enableForwarding;
            currentCycleIndex = 0;
            rebuildResultsPanel();
            displayCycle(0);
            resultsPanel.scrollIntoView({ behavior: 'smooth' });
        } else {
            resultsPanel.innerHTML = `<div style="text-align:center; padding:50px; color:red;">❌ Error: ${data.error}</div>`;
        }
    } catch (error) {
        resultsPanel.innerHTML = `<div style="text-align:center; padding:50px; color:red;">❌ Error de conexión: ${error.message}</div>`;
    }
}

// ============================================================================
// CONSTRUCCIÓN DEL PANEL DE RESULTADOS
// ============================================================================

function rebuildResultsPanel() {
    const panel = document.getElementById('resultsPanel');
    if (!panel || !simulationData) return;
    
    const instructionsCount = simulationData.instructions_count || 0;
    const idealCycles = simulationData.ideal_cycles || (instructionsCount + 4);
    const efficiency = simulationData.efficiency || ((idealCycles / simulationData.total_cycles) * 100);
    const penalty = simulationData.total_cycles - idealCycles;
    const usedRegisters = simulationData.used_registers || {};
    const usedRegistersList = simulationData.used_registers_list || [];
    
    // 🔑 DETECTAR SI HAY FORWARDING (basado en eventos de forwarding)
    // Si hay eventos de forwarding (>0) o si se recibió el estado desde el backend
    const hasForwarding = simulationData.forwarding_events > 0;
    const forwardingText = hasForwarding ? "✅ Con Forwarding" : "❌ Sin Forwarding";
    
    panel.innerHTML = `
        <h2>📊 Resultados de la Simulación - ${forwardingText}</h2>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">${simulationData.total_cycles}</div>
                <div class="stat-label">Ciclos Totales</div>
                <div class="stat-hint">Ideal: ${idealCycles}</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${simulationData.stalls || 0}</div>
                <div class="stat-label">Stalls / Burbujas</div>
                <div class="stat-hint">Penalización: +${penalty}</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${simulationData.forwarding_events || 0}</div>
                <div class="stat-label">Eventos de Forwarding</div>
                <div class="stat-hint">Stalls evitados: ${simulationData.forwarding_events || 0}</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${efficiency.toFixed(1)}%</div>
                <div class="stat-label">Eficiencia del Pipeline</div>
                <div class="stat-hint">${instructionsCount} instrucciones</div>
            </div>
        </div>

        <div class="performance-note">
            <strong>📈 Nota de rendimiento:</strong>
            Un pipeline ideal ejecutaría ${instructionsCount} instrucciones en 
            ${idealCycles} ciclos (${instructionsCount} + 4 para llenado).
            ${simulationData.forwarding_events > 0 ? 
                'El forwarding evitó ' + simulationData.forwarding_events + ' stall(s) y mejoró la eficiencia.' : 
                (simulationData.stalls > 0 ? 'Hay stalls que podrían evitarse con forwarding.' : 'Pipeline funcionando de manera óptima.')}
        </div>

        <div class="registers-view">
            <h3>💾 Registros Utilizados (${usedRegistersList.length} registros)</h3>
            <div id="registersGrid" class="registers-grid"></div>
        </div>

        <div class="pipeline-view">
            <div class="pipeline-header">
                <h3>🔄 Evolución del Pipeline por Ciclo</h3>
                <div class="pipeline-buttons">
                    <button id="toggleHistoryBtn" class="btn-history">📊 Historial</button>
                    <button id="exportHistoryBtn" class="btn-history">💾 Exportar</button>
                </div>
            </div>
            <div class="timeline-controls">
                <button id="prevCycle" class="btn-small">◀ Anterior</button>
                <span id="currentCycleLabel">Ciclo 1 de ${simulationData.total_cycles}</span>
                <button id="nextCycle" class="btn-small">Siguiente ▶</button>
                <button id="playAnimation" class="btn-small">▶ Reproducir</button>
                <button id="resetView" class="btn-small">🔄 Reiniciar</button>
            </div>
            <div id="pipelineDiagram" class="pipeline-diagram"></div>
            <div id="cycleInfo" class="cycle-info"></div>
        </div>
        
        <div id="historyView" class="history-view" style="display: none;">
            <h3>📜 Historial del Pipeline</h3>
            <div class="history-table-container">
                <div class="table-wrapper">
                    <table id="pipelineHistoryTable" class="history-table">
                        <thead><tr><th>Ciclo</th><th>FI</th><th>DI</th><th>EX</th><th>MEM</th><th>WB</th><th>Evento</th></tr></thead>
                        <tbody id="historyTableBody"></tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
    
    // Eventos
    document.getElementById('prevCycle')?.addEventListener('click', () => navigateCycle(-1));
    document.getElementById('nextCycle')?.addEventListener('click', () => navigateCycle(1));
    document.getElementById('playAnimation')?.addEventListener('click', toggleAnimation);
    document.getElementById('resetView')?.addEventListener('click', () => displayCycle(0));
    
    document.getElementById('toggleHistoryBtn')?.addEventListener('click', () => {
        const historyView = document.getElementById('historyView');
        if (historyView) {
            const isHidden = historyView.style.display === 'none';
            historyView.style.display = isHidden ? 'block' : 'none';
            document.getElementById('toggleHistoryBtn').textContent = isHidden ? '📊 Ocultar' : '📊 Historial';
            if (isHidden) buildHistoryTable();
        }
    });
    
    document.getElementById('exportHistoryBtn')?.addEventListener('click', exportHistoryToCSV);
    
    displayRegisters(simulationData.final_registers || [], usedRegisters, usedRegistersList);
}

// ============================================================================
// VISUALIZACIÓN DE REGISTROS
// ============================================================================

function displayRegisters(registers, usedRegistersDict, usedRegistersList) {
    const container = document.getElementById('registersGrid');
    if (!container) return;
    container.innerHTML = '';
    
    if (usedRegistersList && usedRegistersList.length > 0) {
        // Mostrar solo los registros que fueron usados (SIN tarjeta de contador al final)
        for (const regNum of usedRegistersList) {
            const regValue = usedRegistersDict[regNum] || 0;
            const regDiv = document.createElement('div');
            regDiv.className = 'register-card';
            regDiv.innerHTML = `
                <div class="register-name">R${regNum}</div>
                <div class="register-value">${regValue}</div>
            `;
            container.appendChild(regDiv);
        }
        // NOTA: Ya NO se agrega la tarjeta "📊 Total" al final
        
    } else {
        // Fallback: mostrar registros que tienen valor != 0 (hasta R15)
        const maxReg = Math.min(registers.length, 16);
        for (let i = 0; i < maxReg; i++) {
            const val = registers[i] !== undefined ? registers[i] : 0;
            if (val !== 0 || i === 0) {
                const regDiv = document.createElement('div');
                regDiv.className = 'register-card';
                if (val === 0 && i !== 0) {
                    regDiv.style.opacity = '0.5';
                }
                regDiv.innerHTML = `
                    <div class="register-name">R${i}</div>
                    <div class="register-value">${val}</div>
                `;
                container.appendChild(regDiv);
            }
        }
    }
}

// ============================================================================
// VISUALIZACIÓN DEL PIPELINE
// ============================================================================

function displayCycle(index) {
    if (!simulationData?.cycles || index >= simulationData.cycles.length) return;
    
    const cycle = simulationData.cycles[index];
    currentCycleIndex = index;
    
    const cycleLabel = document.getElementById('currentCycleLabel');
    if (cycleLabel) cycleLabel.textContent = `Ciclo ${cycle.cycle} de ${simulationData.total_cycles}`;
    
    const diagramContainer = document.getElementById('pipelineDiagram');
    if (!diagramContainer) return;
    
    const stages = ['IF', 'ID', 'EX', 'MEM', 'WB'];
    const stageNames = { 'IF': '🔍 FI', 'ID': '📖 DI', 'EX': '⚙️ EX', 'MEM': '💾 MEM', 'WB': '✍️ WB' };
    
    let html = '<div class="pipeline-stage">';
    for (const stage of stages) {
        const inst = cycle.post?.[stage];
        const isBubble = !inst;
        const isForwarding = cycle.forwarding && cycle.forwarding.includes(stage);
        
        let instructionHtml = '---';
        let resultHtml = '';
        
        if (inst) {
            instructionHtml = `${inst.op} R${inst.rd}`;
            if (inst.result && inst.result !== 0) resultHtml = `<div class="stage-result">→ ${inst.result}</div>`;
        }
        
        html += `<div class="stage ${isBubble ? 'bubble' : ''} ${isForwarding ? 'forwarding' : ''}">
                    <div class="stage-name">${stageNames[stage]}</div>
                    <div class="stage-instruction">${instructionHtml}</div>${resultHtml}
                </div>`;
    }
    html += '</div>';
    diagramContainer.innerHTML = html;
    
    const infoContainer = document.getElementById('cycleInfo');
    if (infoContainer) {
        if (cycle.stall) {
            infoContainer.innerHTML = `<div class="cycle-info stall"><strong>⚠️ STALL:</strong> ${cycle.stall_reason}<br>Se inserta una burbuja en DI.</div>`;
        } else if (cycle.forwarding) {
            infoContainer.innerHTML = `<div class="cycle-info forwarding"><strong>🔄 FORWARDING:</strong> ${cycle.forwarding}<br>Dato pasado desde etapa posterior.</div>`;
        } else {
            infoContainer.innerHTML = `<div class="cycle-info"><strong>✅ Normal:</strong> No hay riesgos de datos.</div>`;
        }
    }
}

// ============================================================================
// NAVEGACIÓN Y ANIMACIÓN
// ============================================================================

function navigateCycle(delta) {
    if (!simulationData?.cycles) return;
    const newIndex = currentCycleIndex + delta;
    if (newIndex >= 0 && newIndex < simulationData.cycles.length) displayCycle(newIndex);
}

function toggleAnimation() {
    if (!simulationData?.cycles) return;
    if (animationInterval) {
        clearInterval(animationInterval);
        animationInterval = null;
        const playButton = document.getElementById('playAnimation');
        if (playButton) playButton.textContent = '▶ Reproducir';
    } else {
        startAnimation();
    }
}

function startAnimation() {
    let index = currentCycleIndex;
    const playButton = document.getElementById('playAnimation');
    if (playButton) playButton.textContent = '⏸ Pausar';
    
    animationInterval = setInterval(() => {
        if (index >= simulationData.cycles.length - 1) {
            clearInterval(animationInterval);
            animationInterval = null;
            if (playButton) playButton.textContent = '▶ Reproducir';
        } else {
            index++;
            displayCycle(index);
        }
    }, 800);
}

// ============================================================================
// TABLA HISTÓRICA
// ============================================================================

function buildHistoryTable() {
    if (!simulationData?.cycles) return;
    const tbody = document.getElementById('historyTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';
    
    for (const cycle of simulationData.cycles) {
        const row = document.createElement('tr');
        row.appendChild(createCell(cycle.cycle, true));
        
        for (const stage of ['IF', 'ID', 'EX', 'MEM', 'WB']) {
            const inst = cycle.post?.[stage];
            const cell = document.createElement('td');
            if (!inst) {
                cell.innerHTML = '<span class="bubble">💨 ---</span>';
                cell.classList.add('stall-cell');
            } else {
                let resultText = (inst.result && inst.result !== 0) ? `<small> → ${inst.result}</small>` : '';
                cell.innerHTML = `<span class="instruction">${inst.op} R${inst.rd}</span>${resultText}`;
                if (cycle.forwarding?.includes(stage)) cell.classList.add('forwarding-cell');
                else cell.classList.add('normal-cell');
            }
            row.appendChild(cell);
        }
        
        const eventCell = document.createElement('td');
        if (cycle.stall) {
            eventCell.innerHTML = '⚠️ STALL';
            eventCell.classList.add('stall-cell');
        } else if (cycle.forwarding) {
            eventCell.innerHTML = '🔄 FORWARDING';
            eventCell.classList.add('forwarding-cell');
        } else {
            eventCell.innerHTML = '✅ Normal';
            eventCell.classList.add('normal-cell');
        }
        row.appendChild(eventCell);
        tbody.appendChild(row);
    }
}

function createCell(content, isBold = false) {
    const cell = document.createElement('td');
    cell.textContent = content;
    if (isBold) cell.style.fontWeight = 'bold';
    return cell;
}

// ============================================================================
// EXPORTAR CSV
// ============================================================================

function exportHistoryToCSV() {
    if (!simulationData?.cycles) {
        alert('No hay datos para exportar');
        return;
    }
    
    const headers = ['Ciclo', 'FI', 'DI', 'EX', 'MEM', 'WB', 'Evento'];
    const rows = [];
    
    for (const cycle of simulationData.cycles) {
        const row = [cycle.cycle];
        for (const stage of ['IF', 'ID', 'EX', 'MEM', 'WB']) {
            const inst = cycle.post?.[stage];
            if (!inst) {
                row.push('--- (Burbuja)');
            } else {
                let text = `${inst.op} R${inst.rd}`;
                if (inst.result && inst.result !== 0) text += ` = ${inst.result}`;
                row.push(text);
            }
        }
        if (cycle.stall) row.push('STALL');
        else if (cycle.forwarding) row.push('FORWARDING');
        else row.push('NORMAL');
        rows.push(row);
    }
    
    const csvContent = [headers, ...rows].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.href = url;
    link.setAttribute('download', `pipeline_history_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}
