/**
 * Snake Game - Enhanced Edition
 * Features: Power-ups, Multiple Game Modes, Leaderboard, Combo System
 */

// ===== Constants =====
const CANVAS_SIZE = 400;
const GRID_SIZE = 20;
const CELL_SIZE = CANVAS_SIZE / GRID_SIZE;

// ===== Power-up Definitions =====
const POWERUPS = {
    SPEED_BOOST: { color: '#f59e0b', duration: 5000, effect: 'speed', icon: '⚡' },
    SLOW_MOTION: { color: '#3b82f6', duration: 5000, effect: 'slow', icon: '❄️' },
    DOUBLE_POINTS: { color: '#8b5cf6', duration: 10000, effect: 'double', icon: '💎' },
    GHOST: { color: '#ec4899', duration: 7000, effect: 'ghost', icon: '👻' },
    SHRINK: { color: '#10b981', duration: 0, effect: 'shrink', icon: '📉' }
};

// ===== Game State =====
let canvas, ctx;
let snake = [];
let food = {};
let currentPowerup = null;
let direction = 'right';
let nextDirection = 'right';
let score = 0;
let highScore = 0;
let gameLoop = null;
let baseSpeed = 150;
let currentSpeed = 150;
let isGameRunning = false;
let isPaused = false;
let activePowerups = [];
let gameMode = 'classic';
let timeRemaining = 180;
let timerLoop = null;
let combo = 0;
let comboTimer = null;
let lastFoodTime = 0;

// ===== Leaderboard =====
const LEADERBOARD_KEY = 'snake_leaderboard';
const MAX_LEADERBOARD_ENTRIES = 10;

// ===== Initialize =====
document.addEventListener('DOMContentLoaded', () => {
    initElements();
    loadHighScore();
    setupEventListeners();
    drawInitialGrid();
});

function initElements() {
    canvas = document.getElementById('gameCanvas');
    ctx = canvas.getContext('2d');
    
    // Handle high DPI displays
    const dpr = window.devicePixelRatio || 1;
    canvas.width = CANVAS_SIZE * dpr;
    canvas.height = CANVAS_SIZE * dpr;
    ctx.scale(dpr, dpr);
    
    scoreEl = document.getElementById('score');
    highScoreEl = document.getElementById('highScore');
    finalScoreEl = document.getElementById('finalScore');
    timeEl = document.getElementById('time');
    comboEl = document.getElementById('combo');
    timeItem = document.getElementById('timeItem');
    comboItem = document.getElementById('comboItem');
    
    startScreen = document.getElementById('startScreen');
    gameOverScreen = document.getElementById('gameOverScreen');
    pauseScreen = document.getElementById('pauseScreen');
    leaderboardScreen = document.getElementById('leaderboardScreen');
    leaderboardContent = document.getElementById('leaderboardContent');
    powerupIndicators = document.getElementById('powerupIndicators');
    
    gameModeSelect = document.getElementById('gameMode');
    difficultySelect = document.getElementById('difficulty');
}

function setupEventListeners() {
    document.getElementById('startBtn').addEventListener('click', startGame);
    document.getElementById('restartBtn').addEventListener('click', startGame);
    document.getElementById('menuBtn').addEventListener('click', showMainMenu);
    document.getElementById('leaderboardBtn').addEventListener('click', showLeaderboard);
    document.getElementById('closeLeaderboardBtn').addEventListener('click', () => {
        leaderboardScreen.classList.add('hidden');
        startScreen.classList.remove('hidden');
    });
    
    document.addEventListener('keydown', handleKeyPress);
    setupMobileControls();
}

function setupMobileControls() {
    const btns = {
        upBtn: 'up', downBtn: 'down',
        leftBtn: 'left', rightBtn: 'right'
    };
    
    Object.entries(btns).forEach(([id, dir]) => {
        const btn = document.getElementById(id);
        btn?.addEventListener('touchstart', (e) => {
            e.preventDefault();
            changeDirection(dir);
        });
        btn?.addEventListener('click', () => changeDirection(dir));
    });
}

// ===== Game Logic =====

function startGame() {
    // Get settings
    gameMode = gameModeSelect.value;
    difficulty = parseInt(difficultySelect.value);
    
    // Adjust speed based on difficulty
    baseSpeed = 150 - (difficulty - 1) * 30;
    currentSpeed = baseSpeed;
    
    // Reset state
    snake = [{x: 5, y: 10}, {x: 4, y: 10}, {x: 3, y: 10}];
    direction = 'right';
    nextDirection = 'right';
    score = 0;
    combo = 0;
    activePowerups = [];
    currentPowerup = null;
    isGameRunning = true;
    isPaused = false;
    
    // Mode-specific setup
    if (gameMode === 'timed') {
        timeRemaining = 180;
        timeItem.style.display = 'block';
        comboItem.style.display = 'block';
    } else if (gameMode === 'survival') {
        timeItem.style.display = 'none';
        comboItem.style.display = 'block';
    } else {
        timeItem.style.display = 'none';
        comboItem.style.display = 'none';
    }
    
    updateScore();
    spawnFood();
    
    // Hide overlays
    startScreen.classList.add('hidden');
    gameOverScreen.classList.add('hidden');
    
    // Start game loop
    if (gameLoop) clearInterval(gameLoop);
    gameLoop = setInterval(update, currentSpeed);
    
    // Start timer for timed mode
    if (gameMode === 'timed' && timerLoop) {
        clearInterval(timerLoop);
        timerLoop = setInterval(() => {
            timeRemaining--;
            timeEl.textContent = timeRemaining;
            if (timeRemaining <= 0) gameOver();
        }, 1000);
    }
}

function update() {
    if (isPaused) return;
    
    direction = nextDirection;
    const head = {...snake[0]};
    
    switch(direction) {
        case 'up': head.y -= 1; break;
        case 'down': head.y += 1; break;
        case 'left': head.x -= 1; break;
        case 'right': head.x += 1; break;
    }
    
    // Check collisions
    if (checkCollision(head)) {
        // Ghost mode allows passing through walls
        if (!activePowerups.some(p => p.effect === 'ghost')) {
            gameOver();
            return;
        }
        // Wrap around
        if (head.x < 0) head.x = GRID_SIZE - 1;
        if (head.x >= GRID_SIZE) head.x = 0;
        if (head.y < 0) head.y = GRID_SIZE - 1;
        if (head.y >= GRID_SIZE) head.y = 0;
    }
    
    snake.unshift(head);
    
    // Check food collision
    if (head.x === food.x && head.y === food.y) {
        onFoodEaten();
    } else {
        snake.pop();
    }
    
    // Check powerup collision
    if (currentPowerup && head.x === currentPowerup.x && head.y === currentPowerup.y) {
        activatePowerup(currentPowerup);
        currentPowerup = null;
    }
    
    // Update combo
    updateCombo();
    
    draw();
}

function onFoodEaten() {
    const now = Date.now();
    const timeSinceLastFood = now - lastFoodTime;
    lastFoodTime = now;
    
    // Calculate points
    let points = 10;
    
    // Combo bonus
    if (combo >= 2) {
        points *= combo;
    }
    
    // Double points powerup
    if (activePowerups.some(p => p.effect === 'double')) {
        points *= 2;
    }
    
    score += points;
    updateScore();
    
    // Increase combo
    if (timeSinceLastFood < 5000) {
        combo++;
        comboEl.textContent = `x${combo}`;
        resetComboTimer();
    }
    
    // Speed up slightly
    if (currentSpeed > 50 && gameMode !== 'survival') {
        currentSpeed -= 1;
        clearInterval(gameLoop);
        gameLoop = setInterval(update, currentSpeed);
    }
    
    spawnFood();
    
    // Random powerup spawn (10% chance)
    if (Math.random() < 0.1 && !currentPowerup) {
        spawnPowerup();
    }
}

function updateCombo() {
    if (combo > 0) {
        comboEl.textContent = `x${combo}`;
    }
}

function resetComboTimer() {
    if (comboTimer) clearTimeout(comboTimer);
    comboTimer = setTimeout(() => {
        combo = 0;
        comboEl.textContent = 'x1';
    }, 5000);
}

function checkCollision(head) {
    // Wall collision
    if (head.x < 0 || head.x >= GRID_SIZE || head.y < 0 || head.y >= GRID_SIZE) {
        return true;
    }
    
    // Self collision (skip if ghost mode)
    if (!activePowerups.some(p => p.effect === 'ghost')) {
        for (let i = 0; i < snake.length; i++) {
            if (snake[i].x === head.x && snake[i].y === head.y) {
                return true;
            }
        }
    }
    
    return false;
}

function spawnFood() {
    food = getRandomPosition();
}

function spawnPowerup() {
    const types = Object.keys(POWERUPS);
    const type = types[Math.floor(Math.random() * types.length)];
    
    currentPowerup = {
        ...getRandomPosition(),
        type: type,
        ...POWERUPS[type]
    };
    
    // Powerup disappears after 10 seconds
    setTimeout(() => {
        if (currentPowerup) currentPowerup = null;
    }, 10000);
}

function activatePowerup(powerup) {
    const powerupDef = POWERUPS[powerup.type];
    
    switch(powerupDef.effect) {
        case 'speed':
            currentSpeed = Math.max(30, currentSpeed - 30);
            clearInterval(gameLoop);
            gameLoop = setInterval(update, currentSpeed);
            addActivePowerup(powerup.type, powerupDef.duration);
            break;
            
        case 'slow':
            currentSpeed = Math.min(250, currentSpeed + 50);
            clearInterval(gameLoop);
            gameLoop = setInterval(update, currentSpeed);
            addActivePowerup(powerup.type, powerupDef.duration);
            break;
            
        case 'double':
            addActivePowerup(powerup.type, powerupDef.duration);
            break;
            
        case 'ghost':
            addActivePowerup(powerup.type, powerupDef.duration);
            break;
            
        case 'shrink':
            // Remove last 3 segments
            const newLength = Math.max(3, snake.length - 3);
            snake = snake.slice(0, newLength);
            break;
    }
}

function addActivePowerup(type, duration) {
    activePowerups.push({type, duration, endTime: Date.now() + duration});
    updatePowerupIndicators();
    
    setTimeout(() => {
        deactivatePowerup(type);
    }, duration);
}

function deactivatePowerup(type) {
    activePowerups = activePowerups.filter(p => p.type !== type);
    updatePowerupIndicators();
    
    // Reset speed if needed
    if (type === 'speed' || type === 'slow') {
        currentSpeed = baseSpeed;
        clearInterval(gameLoop);
        gameLoop = setInterval(update, currentSpeed);
    }
}

function updatePowerupIndicators() {
    powerupIndicators.innerHTML = activePowerups.map(p => {
        const def = POWERUPS[p.type];
        return `<span class="powerup-active" style="background: ${def.color}">${def.icon}</span>`;
    }).join('');
}

function getRandomPosition() {
    let pos;
    do {
        pos = {
            x: Math.floor(Math.random() * GRID_SIZE),
            y: Math.floor(Math.random() * GRID_SIZE)
        };
    } while (snake.some(s => s.x === pos.x && s.y === pos.y));
    return pos;
}

function gameOver() {
    isGameRunning = false;
    clearInterval(gameLoop);
    if (timerLoop) clearInterval(timerLoop);
    
    // Check high score
    const isNewHighScore = score > highScore;
    if (isNewHighScore) {
        highScore = score;
        saveHighScore();
        document.getElementById('newHighScore').style.display = 'block';
    } else {
        document.getElementById('newHighScore').style.display = 'none';
    }
    
    // Save to leaderboard
    saveToLeaderboard(score);
    
    finalScoreEl.textContent = score;
    gameOverScreen.classList.remove('hidden');
}

function showMainMenu() {
    gameOverScreen.classList.add('hidden');
    leaderboardScreen.classList.add('hidden');
    startScreen.classList.remove('hidden');
    drawInitialGrid();
}

// ===== Drawing =====

function draw() {
    // Clear
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);
    
    drawGrid();
    drawFood();
    if (currentPowerup) drawPowerup();
    drawSnake();
}

function drawInitialGrid() {
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);
    drawGrid();
}

function drawGrid() {
    ctx.strokeStyle = 'rgba(51, 65, 85, 0.3)';
    ctx.lineWidth = 0.5;
    
    for (let i = 0; i <= GRID_SIZE; i++) {
        ctx.beginPath();
        ctx.moveTo(i * CELL_SIZE, 0);
        ctx.lineTo(i * CELL_SIZE, CANVAS_SIZE);
        ctx.stroke();
        
        ctx.beginPath();
        ctx.moveTo(0, i * CELL_SIZE);
        ctx.lineTo(CANVAS_SIZE, i * CELL_SIZE);
        ctx.stroke();
    }
}

function drawSnake() {
    snake.forEach((segment, index) => {
        const x = segment.x * CELL_SIZE;
        const y = segment.y * CELL_SIZE;
        
        // Check ghost mode
        const isGhost = activePowerups.some(p => p.effect === 'ghost');
        
        const gradient = ctx.createRadialGradient(
            x + CELL_SIZE/2, y + CELL_SIZE/2, 0,
            x + CELL_SIZE/2, y + CELL_SIZE/2, CELL_SIZE/2
        );
        
        if (index === 0) {
            gradient.addColorStop(0, isGhost ? '#f472b6' : '#34d399');
            gradient.addColorStop(1, isGhost ? '#ec4899' : '#10b981');
        } else {
            const intensity = 1 - (index / snake.length) * 0.5;
            gradient.addColorStop(0, isGhost ? `rgba(244, 114, 182, ${intensity})` : `rgba(16, 185, 129, ${intensity})`);
            gradient.addColorStop(1, isGhost ? `rgba(236, 72, 153, ${intensity})` : `rgba(5, 150, 105, ${intensity})`);
        }
        
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.roundRect(x + 1, y + 1, CELL_SIZE - 2, CELL_SIZE - 2, 6);
        ctx.fill();
        
        // Draw eyes on head
        if (index === 0) drawEyes(x, y);
    });
}

function drawEyes(x, y) {
    ctx.fillStyle = '#0f172a';
    const eyeSize = 4;
    const eyeOffset = 6;
    
    let positions = [];
    switch(direction) {
        case 'up': positions = [[x+eyeOffset, y+eyeOffset], [x+CELL_SIZE-eyeOffset-eyeSize, y+eyeOffset]]; break;
        case 'down': positions = [[x+eyeOffset, y+CELL_SIZE-eyeOffset-eyeSize], [x+CELL_SIZE-eyeOffset-eyeSize, y+CELL_SIZE-eyeOffset-eyeSize]]; break;
        case 'left': positions = [[x+eyeOffset, y+eyeOffset], [x+eyeOffset, y+CELL_SIZE-eyeOffset-eyeSize]]; break;
        case 'right': positions = [[x+CELL_SIZE-eyeOffset-eyeSize, y+eyeOffset], [x+CELL_SIZE-eyeOffset-eyeSize, y+CELL_SIZE-eyeOffset-eyeSize]]; break;
    }
    
    positions.forEach(([ex, ey]) => {
        ctx.beginPath();
        ctx.arc(ex + eyeSize/2, ey + eyeSize/2, eyeSize/2, 0, Math.PI * 2);
        ctx.fill();
    });
}

function drawFood() {
    const x = food.x * CELL_SIZE + CELL_SIZE/2;
    const y = food.y * CELL_SIZE + CELL_SIZE/2;
    const radius = CELL_SIZE/2 - 2;
    
    // Glow effect
    const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius + 8);
    gradient.addColorStop(0, 'rgba(239, 68, 68, 0.8)');
    gradient.addColorStop(0.5, 'rgba(239, 68, 68, 0.3)');
    gradient.addColorStop(1, 'rgba(239, 68, 68, 0)');
    
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(x, y, radius + 8, 0, Math.PI * 2);
    ctx.fill();
    
    // Apple
    const appleGradient = ctx.createRadialGradient(x-3, y-3, 0, x, y, radius);
    appleGradient.addColorStop(0, '#f87171');
    appleGradient.addColorStop(1, '#ef4444');
    
    ctx.fillStyle = appleGradient;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
}

function drawPowerup() {
    const x = currentPowerup.x * CELL_SIZE + CELL_SIZE/2;
    const y = currentPowerup.y * CELL_SIZE + CELL_SIZE/2;
    
    // Pulsing effect
    const pulse = Math.sin(Date.now() / 200) * 3;
    
    ctx.fillStyle = currentPowerup.color;
    ctx.beginPath();
    ctx.arc(x, y, CELL_SIZE/2 - 4 + pulse, 0, Math.PI * 2);
    ctx.fill();
    
    // Icon
    ctx.fillStyle = '#fff';
    ctx.font = '12px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(currentPowerup.icon, x, y);
}

// ===== Input Handling =====

function handleKeyPress(e) {
    if (['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Space','KeyW','KeyA','KeyS','KeyD','KeyP'].includes(e.code)) {
        e.preventDefault();
    }
    
    if (e.code === 'Space' || e.code === 'KeyP') {
        if (isGameRunning) togglePause();
        return;
    }
    
    if (!isGameRunning || isPaused) return;
    
    switch(e.code) {
        case 'ArrowUp': case 'KeyW': changeDirection('up'); break;
        case 'ArrowDown': case 'KeyS': changeDirection('down'); break;
        case 'ArrowLeft': case 'KeyA': changeDirection('left'); break;
        case 'ArrowRight': case 'KeyD': changeDirection('right'); break;
    }
}

function changeDirection(newDir) {
    if (!isGameRunning || isPaused) return;
    
    const opposites = {up: 'down', down: 'up', left: 'right', right: 'left'};
    if (opposites[newDir] !== direction) {
        nextDirection = newDir;
    }
}

function togglePause() {
    isPaused = !isPaused;
    pauseScreen.classList.toggle('hidden', !isPaused);
}

// ===== Score & Leaderboard =====

function updateScore() {
    scoreEl.textContent = score;
    highScoreEl.textContent = highScore;
}

function loadHighScore() {
    const saved = localStorage.getItem('snakeHighScore');
    if (saved) highScore = parseInt(saved);
}

function saveHighScore() {
    localStorage.setItem('snakeHighScore', highScore.toString());
}

function saveToLeaderboard(score) {
    let leaderboard = JSON.parse(localStorage.getItem(LEADERBOARD_KEY) || '[]');
    leaderboard.push({
        score,
        date: new Date().toISOString(),
        mode: gameMode
    });
    leaderboard.sort((a, b) => b.score - a.score);
    leaderboard = leaderboard.slice(0, MAX_LEADERBOARD_ENTRIES);
    localStorage.setItem(LEADERBOARD_KEY, JSON.stringify(leaderboard));
}

function showLeaderboard() {
    const leaderboard = JSON.parse(localStorage.getItem(LEADERBOARD_KEY) || '[]');
    
    if (leaderboard.length === 0) {
        leaderboardContent.innerHTML = '<p>No scores yet. Be the first!</p>';
    } else {
        leaderboardContent.innerHTML = leaderboard.map((entry, index) => `
            <div class="leaderboard-entry">
                <span class="leaderboard-rank">#${index + 1}</span>
                <span>${entry.mode}</span>
                <span class="leaderboard-score">${entry.score}</span>
                <span class="leaderboard-date">${new Date(entry.date).toLocaleDateString()}</span>
            </div>
        `).join('');
    }
    
    startScreen.classList.add('hidden');
    leaderboardScreen.classList.remove('hidden');
}

// ===== Polyfills =====
if (!ctx?.roundRect) {
    CanvasRenderingContext2D.prototype.roundRect = function(x, y, w, h, r) {
        if (w < 2*r) r = w/2;
        if (h < 2*r) r = h/2;
        this.moveTo(x+r, y);
        this.arcTo(x+w, y, x+w, y+h, r);
        this.arcTo(x+w, y+h, x, y+h, r);
        this.arcTo(x, y+h, x, y, r);
        this.arcTo(x, y, x+w, y, r);
        return this;
    };
}
