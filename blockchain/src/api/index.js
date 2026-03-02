/**
 * Rizz Blockchain Platform - Enterprise Blockchain & Crypto
 * Features: Wallet, Token, NFT, DeFi, Smart Contracts
 */

const express = require('express');
const mongoose = require('mongoose');
const { createServer } = require('http');
const { Server } = require('socket.io');
const crypto = require('crypto');
const jwt = require('jsonwebtoken');
require('dotenv').config();

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, { cors: { origin: '*' } });

app.use(express.json());

// Database
mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/rizz_blockchain')
  .then(() => console.log('✅ MongoDB Connected'))
  .catch(err => console.error('❌ MongoDB Error:', err));

// Models
const WalletSchema = new mongoose.Schema({
  address: { type: String, unique: true, required: true },
  publicKey: String,
  encryptedPrivateKey: String,
  owner: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
  
  // Balances
  balances: [{
    token: String,
    balance: { type: Number, default: 0 },
    locked: { type: Number, default: 0 }
  }],
  
  // NFTs
  nfts: [{
    tokenId: String,
    contractAddress: String,
    name: String,
    description: String,
    image: String,
    metadata: mongoose.Schema.Types.Mixed
  }],
  
  // Transactions
  transactions: [{
    hash: String,
    from: String,
    to: String,
    value: Number,
    token: String,
    type: { type: String, enum: ['transfer', 'swap', 'stake', 'unstake', 'mint', 'burn'] },
    status: { type: String, enum: ['pending', 'confirmed', 'failed'] },
    timestamp: Date,
    blockNumber: Number,
    gasUsed: Number,
    gasPrice: Number
  }],
  
  // DeFi
  staking: [{
    pool: String,
    amount: Number,
    stakedAt: Date,
    rewards: Number,
    lockPeriod: Number
  }],
  
  // Security
  nonce: { type: Number, default: 0 },
  createdAt: { type: Date, default: Date.now }
});

const TokenSchema = new mongoose.Schema({
  name: { type: String, required: true },
  symbol: { type: String, required: true },
  address: { type: String, required: true },
  decimals: { type: Number, default: 18 },
  totalSupply: Number,
  circulatingSupply: Number,
  type: { type: String, enum: ['ERC20', 'BEP20', 'SPL'], default: 'ERC20' },
  
  // Market data
  price: Number,
  marketCap: Number,
  volume24h: Number,
  priceChange24h: Number,
  
  // Contract
  contractVerified: { type: Boolean, default: false },
  contractSource: String,
  
  createdAt: { type: Date, default: Date.now }
});

const NFTCollectionSchema = new mongoose.Schema({
  name: { type: String, required: true },
  symbol: String,
  contractAddress: { type: String, required: true },
  description: String,
  image: String,
  externalUrl: String,
  totalSupply: Number,
  floorPrice: Number,
  volumeTraded: Number,
  creator: mongoose.Schema.Types.ObjectId,
  royalty: { type: Number, default: 2.5 }, // percentage
  
  createdAt: { type: Date, default: Date.now }
});

const SmartContractSchema = new mongoose.Schema({
  name: String,
  address: { type: String, required: true },
  abi: [mongoose.Schema.Types.Mixed],
  bytecode: String,
  compilerVersion: String,
  optimization: Boolean,
  verified: { type: Boolean, default: false },
  sourceCode: String,
  functions: [{
    name: String,
    type: { type: String, enum: ['function', 'constructor', 'event'] },
    inputs: [mongoose.Schema.Types.Mixed],
    outputs: [mongoose.Schema.Types.Mixed],
    stateMutability: String
  }],
  
  createdAt: { type: Date, default: Date.now }
});

const TransactionSchema = new mongoose.Schema({
  hash: { type: String, unique: true, required: true },
  from: { type: String, required: true },
  to: String,
  value: String,
  gasLimit: Number,
  gasPrice: Number,
  gasUsed: Number,
  nonce: Number,
  data: String,
  blockNumber: Number,
  blockHash: String,
  transactionIndex: Number,
  status: { type: String, enum: ['pending', 'confirmed', 'failed'], default: 'pending' },
  timestamp: Date,
  confirmations: { type: Number, default: 0 }
});

const Wallet = mongoose.model('Wallet', WalletSchema);
const Token = mongoose.model('Token', TokenSchema);
const NFTCollection = mongoose.model('NFTCollection', NFTCollectionSchema);
const SmartContract = mongoose.model('SmartContract', SmartContractSchema);
const Transaction = mongoose.model('Transaction', TransactionSchema);

// Auth Middleware
const auth = async (req, res, next) => {
  try {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) return res.status(401).json({ error: 'No token' });
    
    const decoded = jwt.verify(token, process.env.JWT_SECRET || 'secret');
    req.user = await User.findById(decoded.userId);
    next();
  } catch (error) {
    res.status(401).json({ error: 'Invalid token' });
  }
};

// ===== API ROUTES =====

// Create Wallet
app.post('/api/wallet/create', auth, async (req, res) => {
  try {
    // Generate wallet address (in production, use proper crypto)
    const address = '0x' + crypto.randomBytes(20).toString('hex');
    const publicKey = crypto.randomBytes(64).toString('hex');
    
    const wallet = new Wallet({
      address,
      publicKey,
      owner: req.user._id,
      balances: [{ token: 'ETH', balance: 0 }]
    });
    
    await wallet.save();
    res.status(201).json({ wallet: { address, publicKey } });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get Wallet
app.get('/api/wallet/:address', async (req, res) => {
  try {
    const wallet = await Wallet.findOne({ address: req.params.address });
    if (!wallet) return res.status(404).json({ error: 'Wallet not found' });
    
    res.json({
      address: wallet.address,
      balances: wallet.balances,
      nfts: wallet.nfts,
      transactions: wallet.transactions.slice(-20)
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Transfer Token
app.post('/api/wallet/transfer', auth, async (req, res) => {
  try {
    const { fromAddress, toAddress, amount, token } = req.body;
    
    const wallet = await Wallet.findOne({ address: fromAddress, owner: req.user._id });
    if (!wallet) return res.status(404).json({ error: 'Wallet not found' });
    
    const balance = wallet.balances.find(b => b.token === token);
    if (!balance || balance.balance < amount) {
      return res.status(400).json({ error: 'Insufficient balance' });
    }
    
    // Create transaction
    const txHash = '0x' + crypto.randomBytes(32).toString('hex');
    
    balance.balance -= amount;
    wallet.transactions.push({
      hash: txHash,
      from: fromAddress,
      to: toAddress,
      value: amount,
      token,
      type: 'transfer',
      status: 'pending',
      timestamp: new Date()
    });
    
    await wallet.save();
    
    // Broadcast via socket
    io.emit('transaction', { hash: txHash, status: 'pending' });
    
    res.json({ hash: txHash, status: 'pending' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Create Token
app.post('/api/token/create', auth, async (req, res) => {
  try {
    const { name, symbol, totalSupply, decimals } = req.body;
    
    const token = new Token({
      name,
      symbol,
      address: '0x' + crypto.randomBytes(20).toString('hex'),
      decimals: decimals || 18,
      totalSupply,
      circulatingSupply: totalSupply
    });
    
    await token.save();
    res.status(201).json({ token });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// List Tokens
app.get('/api/tokens', async (req, res) => {
  try {
    const tokens = await Token.find().sort('-marketCap').limit(100);
    res.json(tokens);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Mint NFT
app.post('/api/nft/mint', auth, async (req, res) => {
  try {
    const { collectionAddress, name, description, image, metadata } = req.body;
    
    const collection = await NFTCollection.findOne({ contractAddress: collectionAddress });
    if (!collection) return res.status(404).json({ error: 'Collection not found' });
    
    const wallet = await Wallet.findOne({ owner: req.user._id });
    if (!wallet) return res.status(404).json({ error: 'Wallet not found' });
    
    const tokenId = crypto.randomBytes(16).toString('hex');
    
    wallet.nfts.push({
      tokenId,
      contractAddress: collectionAddress,
      name,
      description,
      image,
      metadata
    });
    
    await wallet.save();
    
    res.json({ tokenId, status: 'minted' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get NFTs
app.get('/api/nfts/:address', async (req, res) => {
  try {
    const wallet = await Wallet.findOne({ address: req.params.address });
    if (!wallet) return res.status(404).json({ error: 'Wallet not found' });
    
    res.json({ nfts: wallet.nfts });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Stake Tokens (DeFi)
app.post('/api/defi/stake', auth, async (req, res) => {
  try {
    const { walletAddress, pool, amount, lockPeriod } = req.body;
    
    const wallet = await Wallet.findOne({ address: walletAddress, owner: req.user._id });
    if (!wallet) return res.status(404).json({ error: 'Wallet not found' });
    
    const balance = wallet.balances.find(b => b.token === pool);
    if (!balance || balance.balance < amount) {
      return res.status(400).json({ error: 'Insufficient balance' });
    }
    
    balance.balance -= amount;
    balance.locked += amount;
    
    wallet.staking.push({
      pool,
      amount,
      stakedAt: new Date(),
      rewards: 0,
      lockPeriod
    });
    
    await wallet.save();
    
    res.json({ status: 'staked', amount, pool });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get Staking Info
app.get('/api/defi/staking/:address', async (req, res) => {
  try {
    const wallet = await Wallet.findOne({ address: req.params.address });
    if (!wallet) return res.status(404).json({ error: 'Wallet not found' });
    
    const stakingInfo = wallet.staking.map(s => ({
      pool: s.pool,
      amount: s.amount,
      stakedAt: s.stakedAt,
      rewards: s.rewards,
      lockPeriod: s.lockPeriod,
      canUnstake: new Date() > new Date(new Date(s.stakedAt).getTime() + s.lockPeriod)
    }));
    
    res.json({ staking: stakingInfo });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Deploy Smart Contract
app.post('/api/contract/deploy', auth, async (req, res) => {
  try {
    const { name, bytecode, abi, compilerVersion } = req.body;
    
    const contract = new SmartContract({
      name,
      address: '0x' + crypto.randomBytes(20).toString('hex'),
      abi,
      bytecode,
      compilerVersion,
      optimization: true
    });
    
    await contract.save();
    res.status(201).json({ contract });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get Transaction
app.get('/api/tx/:hash', async (req, res) => {
  try {
    const tx = await Transaction.findOne({ hash: req.params.hash });
    if (!tx) return res.status(404).json({ error: 'Transaction not found' });
    
    res.json(tx);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Market Data
app.get('/api/market/summary', async (req, res) => {
  try {
    const tokens = await Token.find();
    const totalMarketCap = tokens.reduce((sum, t) => sum + (t.marketCap || 0), 0);
    const totalVolume = tokens.reduce((sum, t) => sum + (t.volume24h || 0), 0);
    
    res.json({
      totalMarketCap,
      totalVolume,
      activeTokens: tokens.length,
      timestamp: new Date()
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ===== Socket.io Real-time =====
io.on('connection', (socket) => {
  console.log(`Client connected: ${socket.id}`);
  
  socket.on('subscribe_wallet', (address) => {
    socket.join(`wallet_${address}`);
  });
  
  socket.on('subscribe_tx', (hash) => {
    socket.join(`tx_${hash}`);
  });
  
  socket.on('disconnect', () => {
    console.log(`Client disconnected: ${socket.id}`);
  });
});

// Start Server
const PORT = process.env.PORT || 5005;
httpServer.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════╗
║   ⛓️ Rizz Blockchain Platform              ║
║   Running on port ${PORT}                      ║
║                                            ║
║   Features:                                ║
║   - Crypto Wallet                          ║
║   - Token Creation (ERC20)                 ║
║   - NFT Minting & Trading                  ║
║   - DeFi Staking                           ║
║   - Smart Contracts                        ║
║   - Real-time Transactions                 ║
╚════════════════════════════════════════════╝
  `);
});

module.exports = { app, io };
