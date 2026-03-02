/**
 * Rizz Portfolio Web Application - Enhanced JavaScript
 * Features: Dark/Light Mode, Animations, API Integration, Form Validation
 * Author: username9999
 */

// ===== Configuration =====
const CONFIG = {
    apiBaseUrl: 'http://localhost:5000/api',
    typingSpeed: 100,
    typingDelay: 2000,
    scrollSmooth: true,
    intersectionThreshold: 0.1,
    cacheEnabled: true
};

// ===== State Management =====
const state = {
    darkMode: localStorage.getItem('darkMode') === 'true',
    currentSection: 'home',
    typingTexts: [
        'Full Stack Developer',
        'Python Expert',
        'API Architect',
        'Cloud Enthusiast',
        'Open Source Contributor'
    ],
    typingIndex: 0,
    charIndex: 0,
    isDeleting: false,
    projects: [],
    isLoading: false
};

// ===== DOM Elements =====
const elements = {};

// ===== Initialize Application =====
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Rizz Portfolio initialized');
    
    cacheElements();
    initializeTheme();
    initializeTyping();
    initializeScrollHandlers();
    initializeFormHandlers();
    initializeAnimations();
    initializeIntersectionObserver();
    loadProjects();
    initializeServiceWorker();
});

/**
 * Cache DOM elements for performance
 */
function cacheElements() {
    elements.typing = document.getElementById('typing');
    elements.themeToggle = document.getElementById('theme-toggle');
    elements.header = document.querySelector('header');
    elements.navLinks = document.querySelectorAll('.nav-link');
    elements.sections = document.querySelectorAll('section');
    elements.contactForm = document.getElementById('contact-form');
    elements.projectGrid = document.getElementById('project-grid');
    elements.skillBars = document.querySelectorAll('.skill-bar');
    elements.mobileMenu = document.querySelector('.mobile-menu');
    elements.mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
}

/**
 * Initialize theme (Dark/Light mode)
 */
function initializeTheme() {
    if (state.darkMode) {
        document.body.classList.add('dark-mode');
        if (elements.themeToggle) {
            elements.themeToggle.textContent = '☀️';
        }
    }
    
    if (elements.themeToggle) {
        elements.themeToggle.addEventListener('click', toggleTheme);
    }
}

/**
 * Toggle between dark and light mode
 */
function toggleTheme() {
    state.darkMode = !state.darkMode;
    document.body.classList.toggle('dark-mode', state.darkMode);
    
    if (elements.themeToggle) {
        elements.themeToggle.textContent = state.darkMode ? '☀️' : '🌙';
    }
    
    localStorage.setItem('darkMode', state.darkMode);
    
    // Animate theme change
    document.body.style.transition = 'background-color 0.3s ease, color 0.3s ease';
}

/**
 * Typing animation with multiple texts
 */
function initializeTyping() {
    if (!elements.typing) return;
    type();
}

function type() {
    const currentText = state.typingTexts[state.typingIndex];
    
    if (state.isDeleting) {
        elements.typing.textContent = currentText.substring(0, state.charIndex - 1);
        state.charIndex--;
    } else {
        elements.typing.textContent = currentText.substring(0, state.charIndex + 1);
        state.charIndex++;
    }
    
    let typeSpeed = CONFIG.typingSpeed;
    
    if (!state.isDeleting && state.charIndex === currentText.length) {
        // Finished typing, pause before deleting
        typeSpeed = CONFIG.typingDelay;
        state.isDeleting = true;
    } else if (state.isDeleting && state.charIndex === 0) {
        // Finished deleting, move to next text
        state.isDeleting = false;
        state.typingIndex = (state.typingIndex + 1) % state.typingTexts.length;
        typeSpeed = 500;
    }
    
    setTimeout(() => type(), typeSpeed);
}

/**
 * Scroll handlers for navigation and effects
 */
function initializeScrollHandlers() {
    // Smooth scrolling for navigation links
    elements.navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('href').substring(1);
            const targetSection = document.getElementById(targetId);
            
            if (targetSection && CONFIG.scrollSmooth) {
                targetSection.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Header background on scroll
    window.addEventListener('scroll', () => {
        if (window.scrollY > 100 && elements.header) {
            elements.header.classList.add('scrolled');
        } else if (elements.header) {
            elements.header.classList.remove('scrolled');
        }
        
        // Update current section
        updateCurrentSection();
    });
}

/**
 * Update current active section in navigation
 */
function updateCurrentSection() {
    const scrollPosition = window.scrollY + 200;
    
    elements.sections.forEach(section => {
        const sectionTop = section.offsetTop;
        const sectionHeight = section.offsetHeight;
        const sectionId = section.getAttribute('id');
        
        if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
            state.currentSection = sectionId;
            
            elements.navLinks.forEach(link => {
                link.classList.toggle('active', 
                    link.getAttribute('href') === `#${sectionId}`);
            });
        }
    });
}

/**
 * Form validation and submission
 */
function initializeFormHandlers() {
    if (!elements.contactForm) return;
    
    elements.contactForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = new FormData(elements.contactForm);
        const data = Object.fromEntries(formData.entries());
        
        // Validate form
        if (!validateForm(data)) return;
        
        // Show loading state
        setLoadingState(true);
        
        try {
            // Send to API
            const response = await fetch(`${CONFIG.apiBaseUrl}/contact`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            if (response.ok) {
                showNotification('Message sent successfully! 🎉', 'success');
                elements.contactForm.reset();
            } else {
                throw new Error('Failed to send message');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            showNotification('Failed to send message. Please try again.', 'error');
        } finally {
            setLoadingState(false);
        }
    });
}

/**
 * Validate contact form data
 */
function validateForm(data) {
    const errors = [];
    
    if (!data.name || data.name.trim().length < 2) {
        errors.push('Name must be at least 2 characters');
    }
    
    if (!data.email || !isValidEmail(data.email)) {
        errors.push('Please enter a valid email');
    }
    
    if (!data.message || data.message.trim().length < 10) {
        errors.push('Message must be at least 10 characters');
    }
    
    if (errors.length > 0) {
        showNotification(errors.join('<br>'), 'error');
        return false;
    }
    
    return true;
}

/**
 * Email validation regex
 */
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Set loading state for form
 */
function setLoadingState(loading) {
    const submitBtn = elements.contactForm.querySelector('button[type="submit"]');
    if (!submitBtn) return;
    
    if (loading) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span> Sending...';
        state.isLoading = true;
    } else {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Send Message';
        state.isLoading = false;
    }
}

/**
 * Show notification toast
 */
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = message;
    
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => notification.classList.add('show'), 10);
    
    // Remove after 5 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

/**
 * Initialize scroll animations
 */
function initializeAnimations() {
    // Fade in animations on scroll
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
            }
        });
    }, {
        threshold: CONFIG.intersectionThreshold
    });
    
    document.querySelectorAll('.animate-on-scroll').forEach(el => {
        observer.observe(el);
    });
    
    // Skill bars animation
    animateSkillBars();
}

/**
 * Animate skill bars when visible
 */
function animateSkillBars() {
    const skillObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const skillBar = entry.target;
                const width = skillBar.getAttribute('data-width');
                skillBar.style.width = width;
                skillObserver.unobserve(skillBar);
            }
        });
    }, { threshold: 0.5 });
    
    elements.skillBars.forEach(bar => skillObserver.observe(bar));
}

/**
 * Intersection Observer for lazy loading
 */
function initializeIntersectionObserver() {
    const lazyLoadObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.onload = () => img.classList.add('loaded');
                lazyLoadObserver.unobserve(img);
            }
        });
    });
    
    document.querySelectorAll('img[data-src]').forEach(img => {
        lazyLoadObserver.observe(img);
    });
}

/**
 * Load projects from API
 */
async function loadProjects() {
    if (!elements.projectGrid) return;
    
    try {
        const response = await fetch(`${CONFIG.apiBaseUrl}/posts?limit=6`);
        const data = await response.json();
        
        state.projects = data.posts || [];
        renderProjects();
    } catch (error) {
        console.error('Error loading projects:', error);
        // Fallback to static projects
        renderProjects();
    }
}

/**
 * Render projects to grid
 */
function renderProjects() {
    if (!elements.projectGrid) return;
    
    const projects = state.projects.length > 0 ? state.projects : getStaticProjects();
    
    elements.projectGrid.innerHTML = projects.map(project => `
        <div class="project-card animate-on-scroll">
            <div class="project-image">
                <img src="${project.image || 'https://via.placeholder.com/400x300'}" 
                     alt="${project.title}" 
                     loading="lazy">
            </div>
            <div class="project-content">
                <h3>${project.title}</h3>
                <p>${project.excerpt || project.description}</p>
                <div class="project-tags">
                    ${project.tags ? project.tags.map(tag => 
                        `<span class="tag">${tag}</span>`
                    ).join('') : ''}
                </div>
                <div class="project-links">
                    <a href="${project.link || '#'}" class="btn btn-primary" target="_blank">
                        View Project →
                    </a>
                    ${project.github ? `
                        <a href="${project.github}" class="btn btn-secondary" target="_blank">
                            GitHub
                        </a>
                    ` : ''}
                </div>
            </div>
        </div>
    `).join('');
}

/**
 * Get static projects as fallback
 */
function getStaticProjects() {
    return [
        {
            title: 'E-commerce Platform',
            description: 'Full-stack online shopping platform with payment integration',
            tags: ['React', 'Node.js', 'MongoDB'],
            image: 'https://via.placeholder.com/400x300',
            link: '#',
            github: '#'
        },
        {
            title: 'Chat Application',
            description: 'Real-time messaging app with WebSocket',
            tags: ['Socket.io', 'Express', 'Redis'],
            image: 'https://via.placeholder.com/400x300',
            link: '#',
            github: '#'
        },
        {
            title: 'Task Management API',
            description: 'RESTful API for task management with authentication',
            tags: ['Python', 'Flask', 'PostgreSQL'],
            image: 'https://via.placeholder.com/400x300',
            link: '#',
            github: '#'
        }
    ];
}

/**
 * Initialize Service Worker for PWA
 */
function initializeServiceWorker() {
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js')
            .then(registration => {
                console.log('ServiceWorker registered:', registration.scope);
            })
            .catch(error => {
                console.log('ServiceWorker registration failed:', error);
            });
    }
}

/**
 * Utility: Debounce function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Utility: Throttle function
 */
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        CONFIG,
        state,
        toggleTheme,
        showNotification,
        validateForm
    };
}
