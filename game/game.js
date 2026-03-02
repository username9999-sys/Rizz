/**
 * Snake Game - Classic arcade game implementation
 * Built with HTML5 Canvas and JavaScript
 */

// ===== Game Constants =====
const CANVAS_SIZE = 400;
const GRID_SIZE = 20;
const CELL_SIZE = CANVAS_SIZE / GRID_SIZE;
const INITIAL_SPEED = 150;
const SPEED_INCREMENT = 5;
const MIN_SPEED = 50;

// ===== Game State =====
let canvas, ctx;
let snake = [];
let food = {};
let direction = 'right';
let nextDirection = 'right';
let score = 0;
let highScore = 0;
let gameLoop = null;
let gameSpeed = INITIAL_SPEED;
let isGameRunning = false;
let isPaused = false;

// ===== DOM Elements =====
let startScreen, gameOverScreen, pauseScreen;
let scoreEl, highScoreEl, finalScoreEl;
let startBtn, restartBtn;

// ===== Initialize Game =====
document.addEventListener('DOMContentLoaded', () => {
    initElements();
    loadHighScore();
    setupEventListeners();
    drawInitialGrid();
});

function initElements() {
    canvas = document.getElementById('gameCanvas');
    ctx = canvas.getContext('2d');
    
    startScreen = document.getElementById('startScreen');
    gameOverScreen = document.getElementById('gameOverScreen');
    pauseScreen = document.getElementById('pauseScreen');
    
    scoreEl = document.getElementById('score');
    highScoreEl = document.getElementById('highScore');
    finalScoreEl = document.getElementById('finalScore');
    
    startBtn = document.getElementById('startBtn');
    restartBtn = document.getElementById('restartBtn');
    
    // Set canvas size for high DPI displays
    const dpr = window.devicePixelRatio || 1;
    canvas.width = CANVAS_SIZE * dpr;
    canvas.height = CANVAS_SIZE * dpr;
    ctx.scale(dpr, dpr);
    canvas.style.width = `${CANVAS_SIZE}px`;
    canvas.style.height = `${CANVAS_SIZE}px`;
}

function setupEventListeners() {
    // Button listeners
    startBtn.addEventListener('click', startGame);
    restartBtn.addEventListener('click', startGame);
    
    // Keyboard listeners
    document.addEventListener('keydown', handleKeyPress);
    
    // Mobile controls
    setupMobileControls();
    
    // Prevent default touch behaviors
    canvas.addEventListener('touchstart', (e) => e.preventDefault(), { passive: false });
}

function setupMobileControls() {
    const upBtn = document.getElementById('upBtn');
    const downBtn = document.getElementById('downBtn');
    const leftBtn = document.getElementById('leftBtn');
    const rightBtn = document.getElementById('rightBtn');
    
    upBtn?.addEventListener('touchstart', (e) => {
        e.preventDefault();
        changeDirection('up');
    });
    downBtn?.addEventListener('touchstart', (e) => {
        e.preventDefault();
        changeDirection('down');
    });
    leftBtn?.addEventListener('touchstart', (e) => {
        e.preventDefault();
        changeDirection('left');
    });
    rightBtn?.addEventListener('touchstart', (e) => {
        e.preventDefault();
        changeDirection('right');
    });
    
    // Mouse support for testing
    upBtn?.addEventListener('click', () => changeDirection('up'));
    downBtn?.addEventListener('click', () => changeDirection('down'));
    leftBtn?.addEventListener('click', () => changeDirection('left'));
    rightBtn?.addEventListener('click', () => changeDirection('right'));
}

// ===== Game Logic =====

function startGame() {
    // Reset game state
    snake = [
        { x: 5, y: 10 },
        { x: 4, y: 10 },
        { x: 3, y: 10 }
    ];
    direction = 'right';
    nextDirection = 'right';
    score = 0;
    gameSpeed = INITIAL_SPEED;
    isGameRunning = true;
    isPaused = false;
    
    updateScore();
    spawnFood();
    
    // Hide overlays
    startScreen.classList.add('hidden');
    gameOverScreen.classList.add('hidden');
    pauseScreen.classList.add('hidden');
    
    // Start game loop
    if (gameLoop) clearInterval(gameLoop);
    gameLoop = setInterval(update, gameSpeed);
}

function update() {
    if (isPaused) return;
    
    // Update direction
    direction = nextDirection;
    
    // Calculate new head position
    const head = { ...snake[0] };
    
    switch (direction) {
        case 'up': head.y -= 1; break;
        case 'down': head.y += 1; break;
        case 'left': head.x -= 1; break;
        case 'right': head.x += 1; break;
    }
    
    // Check collisions
    if (checkCollision(head)) {
        gameOver();
        return;
    }
    
    // Add new head
    snake.unshift(head);
    
    // Check if food eaten
    if (head.x === food.x && head.y === food.y) {
        score += 10;
        updateScore();
        spawnFood();
        
        // Increase speed
        if (gameSpeed > MIN_SPEED) {
            gameSpeed -= SPEED_INCREMENT;
            clearInterval(gameLoop);
            gameLoop = setInterval(update, gameSpeed);
        }
    } else {
        // Remove tail
        snake.pop();
    }
    
    // Draw everything
    draw();
}

function checkCollision(head) {
    // Wall collision
    if (head.x < 0 || head.x >= GRID_SIZE || head.y < 0 || head.y >= GRID_SIZE) {
        return true;
    }
    
    // Self collision
    for (let i = 0; i < snake.length; i++) {
        if (snake[i].x === head.x && snake[i].y === head.y) {
            return true;
        }
    }
    
    return false;
}

function spawnFood() {
    let newFood;
    let isValid;
    
    do {
        isValid = true;
        newFood = {
            x: Math.floor(Math.random() * GRID_SIZE),
            y: Math.floor(Math.random() * GRID_SIZE)
        };
        
        // Make sure food doesn't spawn on snake
        for (let segment of snake) {
            if (segment.x === newFood.x && segment.y === newFood.y) {
                isValid = false;
                break;
            }
        }
    } while (!isValid);
    
    food = newFood;
}

function gameOver() {
    isGameRunning = false;
    clearInterval(gameLoop);
    
    // Update high score
    if (score > highScore) {
        highScore = score;
        saveHighScore();
    }
    
    // Show game over screen
    finalScoreEl.textContent = score;
    gameOverScreen.classList.remove('hidden');
}

function togglePause() {
    if (!isGameRunning) return;
    
    isPaused = !isPaused;
    
    if (isPaused) {
        pauseScreen.classList.remove('hidden');
    } else {
        pauseScreen.classList.add('hidden');
    }
}

// ===== Drawing =====

function draw() {
    // Clear canvas
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);
    
    // Draw grid
    drawGrid();
    
    // Draw food
    drawFood();
    
    // Draw snake
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
        // Vertical lines
        ctx.beginPath();
        ctx.moveTo(i * CELL_SIZE, 0);
        ctx.lineTo(i * CELL_SIZE, CANVAS_SIZE);
        ctx.stroke();
        
        // Horizontal lines
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
        
        // Gradient color from head to tail
        const gradient = ctx.createRadialGradient(
            x + CELL_SIZE / 2, y + CELL_SIZE / 2, 0,
            x + CELL_SIZE / 2, y + CELL_SIZE / 2, CELL_SIZE / 2
        );
        
        if (index === 0) {
            // Head
            gradient.addColorStop(0, '#34d399');
            gradient.addColorStop(1, '#10b981');
        } else {
            // Body - fade gradient
            const intensity = 1 - (index / snake.length) * 0.5;
            gradient.addColorStop(0, `rgba(16, 185, 129, ${intensity})`);
            gradient.addColorStop(1, `rgba(5, 150, 105, ${intensity})`);
        }
        
        ctx.fillStyle = gradient;
        
        // Rounded rectangle for segments
        const radius = index === 0 ? 8 : 6;
        const padding = 1;
        
        ctx.beginPath();
        ctx.roundRect(
            x + padding, y + padding,
            CELL_SIZE - padding * 2, CELL_SIZE - padding * 2,
            radius
        );
        ctx.fill();
        
        // Draw eyes on head
        if (index === 0) {
            drawEyes(x, y);
        }
    });
}

function drawEyes(x, y) {
    ctx.fillStyle = '#0f172a';
    
    const eyeSize = 4;
    const eyeOffset = 6;
    
    let eye1X, eye1Y, eye2X, eye2Y;
    
    switch (direction) {
        case 'up':
            eye1X = x + eyeOffset;
            eye1Y = y + eyeOffset;
            eye2X = x + CELL_SIZE - eyeOffset - eyeSize;
            eye2Y = y + eyeOffset;
            break;
        case 'down':
            eye1X = x + eyeOffset;
            eye1Y = y + CELL_SIZE - eyeOffset - eyeSize;
            eye2X = x + CELL_SIZE - eyeOffset - eyeSize;
            eye2Y = y + CELL_SIZE - eyeOffset - eyeSize;
            break;
        case 'left':
            eye1X = x + eyeOffset;
            eye1Y = y + eyeOffset;
            eye2X = x + eyeOffset;
            eye2Y = y + CELL_SIZE - eyeOffset - eyeSize;
            break;
        case 'right':
            eye1X = x + CELL_SIZE - eyeOffset - eyeSize;
            eye1Y = y + eyeOffset;
            eye2X = x + CELL_SIZE - eyeOffset - eyeSize;
            eye2Y = y + CELL_SIZE - eyeOffset - eyeSize;
            break;
    }
    
    ctx.beginPath();
    ctx.arc(eye1X + eyeSize / 2, eye1Y + eyeSize / 2, eyeSize / 2, 0, Math.PI * 2);
    ctx.arc(eye2X + eyeSize / 2, eye2Y + eyeSize / 2, eyeSize / 2, 0, Math.PI * 2);
    ctx.fill();
}

function drawFood() {
    const x = food.x * CELL_SIZE + CELL_SIZE / 2;
    const y = food.y * CELL_SIZE + CELL_SIZE / 2;
    const radius = CELL_SIZE / 2 - 2;
    
    // Glow effect
    const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius + 5);
    gradient.addColorStop(0, 'rgba(239, 68, 68, 0.8)');
    gradient.addColorStop(0.5, 'rgba(239, 68, 68, 0.3)');
    gradient.addColorStop(1, 'rgba(239, 68, 68, 0)');
    
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(x, y, radius + 5, 0, Math.PI * 2);
    ctx.fill();
    
    // Apple body
    const appleGradient = ctx.createRadialGradient(x - 3, y - 3, 0, x, y, radius);
    appleGradient.addColorStop(0, '#f87171');
    appleGradient.addColorStop(1, '#ef4444');
    
    ctx.fillStyle = appleGradient;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
    
    // Stem
    ctx.strokeStyle = '#854d0e';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x, y - radius + 2);
    ctx.lineTo(x + 2, y - radius - 3);
    ctx.stroke();
    
    // Leaf
    ctx.fillStyle = '#10b981';
    ctx.beginPath();
    ctx.ellipse(x + 5, y - radius - 1, 4, 2, Math.PI / 4, 0, Math.PI * 2);
    ctx.fill();
}

// ===== Input Handling =====

function handleKeyPress(e) {
    // Prevent default for game keys
    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space', 'KeyW', 'KeyA', 'KeyS', 'KeyD', 'KeyP'].includes(e.code)) {
        e.preventDefault();
    }
    
    // Pause toggle
    if (e.code === 'Space' || e.code === 'KeyP') {
        togglePause();
        return;
    }
    
    if (!isGameRunning || isPaused) return;
    
    // Direction controls
    switch (e.code) {
        case 'ArrowUp':
        case 'KeyW':
            changeDirection('up');
            break;
        case 'ArrowDown':
        case 'KeyS':
            changeDirection('down');
            break;
        case 'ArrowLeft':
        case 'KeyA':
            changeDirection('left');
            break;
        case 'ArrowRight':
        case 'KeyD':
            changeDirection('right');
            break;
    }
}

function changeDirection(newDirection) {
    if (!isGameRunning || isPaused) return;
    
    const opposites = {
        'up': 'down',
        'down': 'up',
        'left': 'right',
        'right': 'left'
    };
    
    // Prevent 180-degree turns
    if (opposites[newDirection] !== direction) {
        nextDirection = newDirection;
    }
}

// ===== Score Management =====

function updateScore() {
    scoreEl.textContent = score;
    highScoreEl.textContent = highScore;
}

function loadHighScore() {
    const saved = localStorage.getItem('snakeHighScore');
    if (saved) {
        highScore = parseInt(saved, 10);
        highScoreEl.textContent = highScore;
    }
}

function saveHighScore() {
    localStorage.setItem('snakeHighScore', highScore.toString());
}

// ===== Utility =====

// Polyfill for roundRect if not supported
if (!ctx?.roundRect) {
    CanvasRenderingContext2D.prototype.roundRect = function(x, y, w, h, r) {
        if (w < 2 * r) r = w / 2;
        if (h < 2 * r) r = h / 2;
        this.moveTo(x + r, y);
        this.arcTo(x + w, y, x + w, y + h, r);
        this.arcTo(x + w, y + h, x, y + h, r);
        this.arcTo(x, y + h, x, y, r);
        this.arcTo(x, y, x + w, y, r);
        return this;
    };
}

// Console easter egg
console.log('%c🐍 Snake Game', 'font-size: 20px; font-weight: bold; color: #10b981;');
console.log('%cBuilt with ❤️ by username9999', 'font-size: 12px; color: #94a3b8;');
console.log('%cTip: Use arrow keys or WASD to play!', 'font-size: 12px; color: #f59e0b;');
