// script.js
let simulationData = null;
let currentCycleIndex = 0;
let animationInterval = null;

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
    
    // Manual modal handlers
    if (manualBtn) {
        manualBtn.addEventListener('click', () => {
            if (modal) {
                modal.style.display = 'block';
                document.body.style.overflow = 'hidden';
            }
        });
    }
    
    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    if (closeModalBtn) closeModalBtn.addEventListener('click', closeModal);
    
    window.addEventListener('click', (event) => {
        if (event.target === modal) closeModal();
    });
    
    function closeModal() {
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
    }
});

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
    
    // Auto-ejecutar después de cargar el ejemplo
    setTimeout(() => runSimulation(), 100);
}

async function runSimulation() {
    // Detener animación si está corriendo
    if (animationInterval) {
        clearInterval(animationInterval);
        animationInterval = null;
        const playButton = document.getElementById('playAnimation');
        if (playButton) playButton.textContent = '▶ Reproducir';
    }
    
    const instructions = document.getElementById('instructions')?.value || '';
    const registers = document.getElementById('registers')?.value || '';
    const enableForwarding = document.getElementById('enableForwarding')?.checked || true;
    
    // Mostrar loading
    const resultsPanel = document.getElementById('resultsPanel');
    if (!resultsPanel) return;
    
    resultsPanel.style.display = 'block';
    resultsPanel.innerHTML = '<div style="text-align:center; padding:50px;"><div class="spinner"></div><p>🔄 Simulando pipeline...</p></div>';
    
    try {
        const response = await fetch('/simulate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                instructions: instructions,
                registers: registers,
                enable_forwarding: enableForwarding
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            simulationData = data;
            currentCycleIndex = 0;
            
            // Reconstruir el panel de resultados con todas las estadísticas
            rebuildResultsPanel();
            
            // Mostrar primer ciclo
            displayCycle(0);
            
            // Scroll al panel de resultados
            resultsPanel.scrollIntoView({ behavior: 'smooth' });
        } else {
            resultsPanel.innerHTML = `<div style="text-align:center; padding:50px; color:red;">❌ Error: ${data.error}</div>`;
        }
    } catch (error) {
        resultsPanel.innerHTML = `<div style="text-align:center; padding:50px; color:red;">❌ Error de conexión: ${error.message}</div>`;
    }
}

function rebuildResultsPanel() {
    const panel = document.getElementById('resultsPanel');
    if (!panel || !simulationData) return;
    
    // Calcular métricas adicionales
    const instructionsCount = simulationData.instructions_count || simulationData.cycles?.length || 0;
    const idealCycles = simulationData.ideal_cycles || (instructionsCount + 4);
    const efficiency = simulationData.efficiency || ((idealCycles / simulationData.total_cycles) * 100);
    const penalty = simulationData.total_cycles - idealCycles;
    
    panel.innerHTML = `
        <h2>📊 Resultados de la Simulación</h2>
        
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
            <h3>💾 Registros Finales (R0-R15)</h3>
            <div id="registersGrid" class="registers-grid"></div>
        </div>

        <div class="pipeline-view">
            <h3>🔄 Evolución del Pipeline por Ciclo</h3>
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
    `;
    
    // Reasignar eventos
    const prevBtn = document.getElementById('prevCycle');
    const nextBtn = document.getElementById('nextCycle');
    const playBtn = document.getElementById('playAnimation');
    const resetBtn = document.getElementById('resetView');
    
    if (prevBtn) prevBtn.addEventListener('click', () => navigateCycle(-1));
    if (nextBtn) nextBtn.addEventListener('click', () => navigateCycle(1));
    if (playBtn) playBtn.addEventListener('click', toggleAnimation);
    if (resetBtn) resetBtn.addEventListener('click', () => displayCycle(0));
    
    // Mostrar registros finales
    displayRegisters(simulationData.final_registers || []);
}

function displayRegisters(registers) {
    const container = document.getElementById('registersGrid');
    if (!container) return;
    container.innerHTML = '';
    
    const numRegisters = Math.min(registers.length, 16);
    for (let i = 0; i < numRegisters; i++) {
        const regDiv = document.createElement('div');
        regDiv.className = 'register-card';
        regDiv.innerHTML = `
            <div class="register-name">R${i}</div>
            <div class="register-value">${registers[i] !== undefined ? registers[i] : 0}</div>
        `;
        container.appendChild(regDiv);
    }
}

function displayCycle(index) {
    if (!simulationData || !simulationData.cycles || index >= simulationData.cycles.length) return;
    
    const cycle = simulationData.cycles[index];
    currentCycleIndex = index;
    
    const cycleLabel = document.getElementById('currentCycleLabel');
    if (cycleLabel) cycleLabel.textContent = `Ciclo ${cycle.cycle} de ${simulationData.total_cycles}`;
    
    // Mostrar diagrama del pipeline (usar estado POST)
    const diagramContainer = document.getElementById('pipelineDiagram');
    if (!diagramContainer) return;
    
    const stages = ['IF', 'ID', 'EX', 'MEM', 'WB'];
    const stageNames = {'IF': '🔍 FI', 'ID': '📖 DI', 'EX': '⚙️ EX', 'MEM': '💾 MEM', 'WB': '✍️ WB'};
    
    let html = '<div class="pipeline-stage">';
    for (const stage of stages) {
        const inst = cycle.post ? cycle.post[stage] : null;
        const isBubble = !inst;
        const isForwarding = cycle.forwarding && cycle.forwarding.includes(stage);
        
        let instructionHtml = '---';
        let resultHtml = '';
        
        if (inst) {
            instructionHtml = `${inst.op} R${inst.rd}`;
            if (inst.result !== undefined && inst.result !== null && inst.result !== 0) {
                resultHtml = `<div class="stage-result">→ ${inst.result}</div>`;
            }
        }
        
        let bubbleClass = isBubble ? 'bubble' : '';
        let forwardingClass = isForwarding ? 'forwarding' : '';
        
        html += `
            <div class="stage ${bubbleClass} ${forwardingClass}">
                <div class="stage-name">${stageNames[stage]}</div>
                <div class="stage-instruction">${instructionHtml}</div>
                ${resultHtml}
            </div>
        `;
    }
    html += '</div>';
    diagramContainer.innerHTML = html;
    
    // Mostrar información del ciclo
    const infoContainer = document.getElementById('cycleInfo');
    if (!infoContainer) return;
    
    let infoHtml = '';
    
    if (cycle.stall) {
        infoHtml = `
            <div class="cycle-info stall">
                <strong>⚠️ STALL DETECTADO:</strong> ${cycle.stall_reason || 'Dependencia de datos'}
                <br>Se inserta una burbuja en la etapa DI. El pipeline se detiene 1 ciclo.
            </div>
        `;
    } else if (cycle.forwarding) {
        infoHtml = `
            <div class="cycle-info forwarding">
                <strong>🔄 FORWARDING ACTIVADO:</strong> ${cycle.forwarding}
                <br>El dato se pasa directamente desde una etapa posterior, evitando el stall.
            </div>
        `;
    } else {
        infoHtml = `
            <div class="cycle-info">
                <strong>✅ Pipeline normal:</strong> No hay riesgos de datos detectados.
                <br>Todas las etapas avanzan normalmente.
            </div>
        `;
    }
    
    infoContainer.innerHTML = infoHtml;
}

function navigateCycle(delta) {
    if (!simulationData || !simulationData.cycles) return;
    
    const newIndex = currentCycleIndex + delta;
    if (newIndex >= 0 && newIndex < simulationData.cycles.length) {
        displayCycle(newIndex);
    }
}

function toggleAnimation() {
    if (!simulationData || !simulationData.cycles) return;
    
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