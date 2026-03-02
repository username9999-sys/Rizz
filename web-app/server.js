/**
 * Portfolio Backend Server
 * Express.js server with blog API and contact form handling
 */

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const nodemailer = require('nodemailer');
const path = require('path');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// ===== Middleware =====
app.use(cors());
app.use(helmet());
app.use(express.json());
app.use(express.static(path.join(__dirname, '../web-app')));

// Rate limiting
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 100
});
app.use('/api/', limiter);

// ===== MongoDB Connection =====
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/portfolio';
mongoose.connect(MONGODB_URI)
    .then(() => console.log('✅ MongoDB Connected'))
    .catch(err => console.error('❌ MongoDB Error:', err));

// ===== Models =====
const BlogPostSchema = new mongoose.Schema({
    title: { type: String, required: true },
    slug: { type: String, required: true, unique: true },
    content: { type: String, required: true },
    excerpt: String,
    coverImage: String,
    tags: [String],
    category: String,
    published: { type: Boolean, default: false },
    views: { type: Number, default: 0 },
    author: {
        name: { type: String, default: 'username9999' },
        avatar: String
    },
    createdAt: { type: Date, default: Date.now },
    updatedAt: Date
});

const ContactMessageSchema = new mongoose.Schema({
    name: { type: String, required: true },
    email: { type: String, required: true },
    message: { type: String, required: true },
    status: { type: String, enum: ['new', 'read', 'replied'], default: 'new' },
    createdAt: { type: Date, default: Date.now }
});

const VisitorSchema = new mongoose.Schema({
    ip: String,
    userAgent: String,
    page: String,
    visitedAt: { type: Date, default: Date.now }
});

const BlogPost = mongoose.model('BlogPost', BlogPostSchema);
const ContactMessage = mongoose.model('ContactMessage', ContactMessageSchema);
const Visitor = mongoose.model('Visitor', VisitorSchema);

// ===== Auth Middleware =====
const authMiddleware = (req, res, next) => {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) return res.status(401).json({ error: 'No token provided' });
    
    jwt.verify(token, process.env.JWT_SECRET || 'secret', (err, decoded) => {
        if (err) return res.status(401).json({ error: 'Invalid token' });
        req.user = decoded;
        next();
    });
};

// ===== Routes =====

// Blog Routes
app.get('/api/blog/posts', async (req, res) => {
    try {
        const { page = 1, limit = 10, category, tag } = req.query;
        const query = { published: true };
        
        if (category) query.category = category;
        if (tag) query.tags = tag;
        
        const posts = await BlogPost.find(query)
            .sort({ createdAt: -1 })
            .limit(limit * 1)
            .skip((page - 1) * limit);
        
        const count = await BlogPost.countDocuments(query);
        
        res.json({
            posts,
            totalPages: Math.ceil(count / limit),
            currentPage: page,
            total: count
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/blog/posts/:slug', async (req, res) => {
    try {
        const post = await BlogPost.findOneAndUpdate(
            { slug: req.params.slug },
            { $inc: { views: 1 } },
            { new: true }
        );
        
        if (!post) return res.status(404).json({ error: 'Post not found' });
        res.json(post);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/blog/posts', authMiddleware, async (req, res) => {
    try {
        const post = new BlogPost({
            ...req.body,
            slug: req.body.slug || req.body.title.toLowerCase().replace(/[^a-z0-9]+/g, '-')
        });
        await post.save();
        res.status(201).json(post);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.put('/api/blog/posts/:id', authMiddleware, async (req, res) => {
    try {
        const post = await BlogPost.findByIdAndUpdate(
            req.params.id,
            { ...req.body, updatedAt: Date.now() },
            { new: true }
        );
        if (!post) return res.status(404).json({ error: 'Post not found' });
        res.json(post);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.delete('/api/blog/posts/:id', authMiddleware, async (req, res) => {
    try {
        const post = await BlogPost.findByIdAndDelete(req.params.id);
        if (!post) return res.status(404).json({ error: 'Post not found' });
        res.json({ message: 'Post deleted' });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Contact Form Route
app.post('/api/contact', async (req, res) => {
    try {
        const { name, email, message } = req.body;
        
        if (!name || !email || !message) {
            return res.status(400).json({ error: 'All fields are required' });
        }
        
        // Save to database
        const contactMessage = new ContactMessage({ name, email, message });
        await contactMessage.save();
        
        // Send email notification (if configured)
        if (process.env.EMAIL_HOST && process.env.EMAIL_PASSWORD) {
            const transporter = nodemailer.createTransport({
                host: process.env.EMAIL_HOST,
                port: 587,
                secure: false,
                auth: {
                    user: process.env.EMAIL_USER,
                    pass: process.env.EMAIL_PASSWORD
                }
            });
            
            await transporter.sendMail({
                from: process.env.EMAIL_USER,
                to: process.env.CONTACT_EMAIL || 'contact@rizz.dev',
                subject: `New Contact Message from ${name}`,
                html: `
                    <h2>New Contact Message</h2>
                    <p><strong>Name:</strong> ${name}</p>
                    <p><strong>Email:</strong> ${email}</p>
                    <p><strong>Message:</strong></p>
                    <p>${message}</p>
                `
            });
        }
        
        res.json({ message: 'Message sent successfully!' });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Visitor Counter
app.post('/api/track-visit', async (req, res) => {
    try {
        const visitor = new Visitor({
            ip: req.ip,
            userAgent: req.get('user-agent'),
            page: req.body.page || '/'
        });
        await visitor.save();
        res.json({ message: 'Visit tracked' });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/stats', async (req, res) => {
    try {
        const totalVisitors = await Visitor.distinct('ip').count();
        const totalViews = await Visitor.countDocuments();
        const totalPosts = await BlogPost.countDocuments({ published: true });
        const totalMessages = await ContactMessage.countDocuments();
        
        // Get visits per day (last 7 days)
        const sevenDaysAgo = new Date();
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
        
        const dailyVisits = await Visitor.aggregate([
            { $match: { visitedAt: { $gte: sevenDaysAgo } } },
            {
                $group: {
                    _id: { $dateToString: { format: '%Y-%m-%d', date: '$visitedAt' } },
                    count: { $sum: 1 }
                }
            },
            { $sort: { _id: 1 } }
        ]);
        
        res.json({
            totalVisitors,
            totalViews,
            totalPosts,
            totalMessages,
            dailyVisits
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Auth Routes (for blog admin)
app.post('/api/auth/login', async (req, res) => {
    try {
        const { username, password } = req.body;
        
        // Simple auth (in production, use proper user model)
        if (username === process.env.ADMIN_USERNAME && password === process.env.ADMIN_PASSWORD) {
            const token = jwt.sign(
                { username, role: 'admin' },
                process.env.JWT_SECRET || 'secret',
                { expiresIn: '7d' }
            );
            res.json({ token });
        } else {
            res.status(401).json({ error: 'Invalid credentials' });
        }
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Serve index.html for all other routes (SPA)
app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, '../web-app/index.html'));
});

// ===== Error Handling =====
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({ error: 'Something went wrong!' });
});

// ===== Start Server =====
app.listen(PORT, () => {
    console.log(`
╔════════════════════════════════════════════╗
║   🚀 Portfolio Backend Server              ║
║   Running on http://localhost:${PORT}          ║
║                                            ║
║   Endpoints:                               ║
║   - /api/blog/posts     - Blog posts       ║
║   - /api/contact        - Contact form     ║
║   - /api/stats          - Statistics       ║
║   - /api/auth/login     - Admin login      ║
╚════════════════════════════════════════════╝
    `);
});
