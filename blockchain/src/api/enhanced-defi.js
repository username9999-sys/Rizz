/**
 * Rizz Blockchain - Enhanced DeFi & NFT Marketplace
 * Features: DEX, Staking, Yield Farming, NFT Marketplace, DAO
 */

const express = require('express');
const mongoose = require('mongoose');
const crypto = require('crypto');

const app = express();
app.use(express.json());

// ===== ENHANCED MODELS =====

// DEX - Decentralized Exchange
const LiquidityPoolSchema = new mongoose.Schema({
  name: String,
  token0: { address: String, symbol: String, reserve: Number },
  token1: { address: String, symbol: String, reserve: Number },
  totalLiquidity: Number,
  fee: { type: Number, default: 0.003 }, // 0.3%
  apr: Number,
  volume24h: Number,
  fees24h: Number
});

const SwapSchema = new mongoose.Schema({
  user: String,
  tokenIn: String,
  tokenOut: String,
  amountIn: Number,
  amountOut: Number,
  priceImpact: Number,
  fee: Number,
  timestamp: { type: Date, default: Date.now },
  txHash: String
});

// Yield Farming
const FarmSchema = new mongoose.Schema({
  name: String,
  stakingToken: String,
  rewardToken: String,
  apr: Number,
  totalStaked: Number,
  rewardPerBlock: Number,
  startBlock: Number,
  endBlock: Number
});

const StakeSchema = new mongoose.Schema({
  user: String,
  farm: mongoose.Schema.Types.ObjectId,
  amount: Number,
  stakedAt: { type: Date, default: Date.now },
  pendingRewards: Number,
  lastRewardBlock: Number
});

// NFT Marketplace Enhanced
const NFTSaleSchema = new mongoose.Schema({
  nft: mongoose.Schema.Types.ObjectId,
  seller: String,
  price: Number,
  currency: String,
  type: { type: String, enum: ['fixed', 'auction'], default: 'fixed' },
  auction: {
    startTime: Date,
    endTime: Date,
    reservePrice: Number,
    bids: [{
      bidder: String,
      amount: Number,
      timestamp: Date
    }]
  },
  status: { type: String, enum: ['active', 'sold', 'cancelled'], default: 'active' }
});

// DAO Governance
const ProposalSchema = new mongoose.Schema({
  title: String,
  description: String,
  proposer: String,
  votes: {
    for: Number,
    against: Number,
    abstain: Number
  },
  voters: [{
    user: String,
    vote: { type: String, enum: ['for', 'against', 'abstain'] },
    power: Number
  }],
  startTime: Date,
  endTime: Date,
  status: { type: String, enum: ['active', 'passed', 'rejected', 'executed'], default: 'active' },
  executionData: mongoose.Schema.Types.Mixed
});

const LiquidityPool = mongoose.model('LiquidityPool', LiquidityPoolSchema);
const Swap = mongoose.model('Swap', SwapSchema);
const Farm = mongoose.model('Farm', FarmSchema);
const Stake = mongoose.model('Stake', StakeSchema);
const NFTSale = mongoose.model('NFTSale', NFTSaleSchema);
const Proposal = mongoose.model('Proposal', ProposalSchema);

// ===== DEX FUNCTIONS =====

class DEX {
  // Calculate output amount with constant product formula
  calculateSwapOutput(amountIn, reserveIn, reserveOut) {
    const amountInWithFee = amountIn * (1 - 0.003); // 0.3% fee
    const numerator = amountInWithFee * reserveOut;
    const denominator = reserveIn + amountInWithFee;
    return numerator / denominator;
  }
  
  // Calculate price impact
  calculatePriceImpact(amountIn, reserveIn, reserveOut) {
    const spotPrice = reserveOut / reserveIn;
    const executionPrice = this.calculateSwapOutput(amountIn, reserveIn, reserveOut) / amountIn;
    return ((spotPrice - executionPrice) / spotPrice) * 100;
  }
  
  // Add liquidity
  async addLiquidity(poolId, token0Amount, token1Amount, user) {
    const pool = await LiquidityPool.findById(poolId);
    if (!pool) throw new Error('Pool not found');
    
    // Calculate LP tokens to mint
    const liquidity = Math.sqrt(token0Amount * token1Amount);
    
    pool.token0.reserve += token0Amount;
    pool.token1.reserve += token1Amount;
    pool.totalLiquidity += liquidity;
    
    await pool.save();
    
    return { liquidity, pool };
  }
  
  // Remove liquidity
  async removeLiquidity(poolId, lpTokens, user) {
    const pool = await LiquidityPool.findById(poolId);
    if (!pool) throw new Error('Pool not found');
    
    // Calculate share of reserves
    const share = lpTokens / pool.totalLiquidity;
    const token0Amount = pool.token0.reserve * share;
    const token1Amount = pool.token1.reserve * share;
    
    pool.token0.reserve -= token0Amount;
    pool.token1.reserve -= token1Amount;
    pool.totalLiquidity -= lpTokens;
    
    await pool.save();
    
    return { token0Amount, token1Amount, pool };
  }
  
  // Execute swap
  async executeSwap(poolId, tokenIn, amountIn, user) {
    const pool = await LiquidityPool.findById(poolId);
    if (!pool) throw new Error('Pool not found');
    
    const isToken0 = tokenIn === pool.token0.address;
    const reserveIn = isToken0 ? pool.token0.reserve : pool.token1.reserve;
    const reserveOut = isToken0 ? pool.token1.reserve : pool.token0.reserve;
    
    const amountOut = this.calculateSwapOutput(amountIn, reserveIn, reserveOut);
    const priceImpact = this.calculatePriceImpact(amountIn, reserveIn, reserveOut);
    const fee = amountIn * 0.003;
    
    // Update reserves
    if (isToken0) {
      pool.token0.reserve += amountIn;
      pool.token1.reserve -= amountOut;
    } else {
      pool.token1.reserve += amountIn;
      pool.token0.reserve -= amountOut;
    }
    
    await pool.save();
    
    // Record swap
    const swap = await Swap.create({
      user,
      tokenIn,
      tokenOut: isToken0 ? pool.token1.address : pool.token0.address,
      amountIn,
      amountOut,
      priceImpact,
      fee,
      txHash: crypto.randomBytes(32).toString('hex')
    });
    
    return { swap, pool };
  }
}

const dex = new DEX();

// ===== YIELD FARMING =====

class YieldFarming {
  async stake(farmId, amount, user) {
    const farm = await Farm.findById(farmId);
    if (!farm) throw new Error('Farm not found');
    
    // Check if user already has stake
    let stake = await Stake.findOne({ farm: farmId, user });
    
    if (stake) {
      // Claim pending rewards first
      await this.claimRewards(stake._id, user);
      stake.amount += amount;
    } else {
      stake = await Stake.create({
        user,
        farm: farmId,
        amount,
        pendingRewards: 0
      });
    }
    
    farm.totalStaked += amount;
    await farm.save();
    
    return stake;
  }
  
  async claimRewards(stakeId, user) {
    const stake = await Stake.findById(stakeId);
    if (!stake) throw new Error('Stake not found');
    
    const farm = await Farm.findById(stake.farm);
    const currentBlock = await this.getCurrentBlock();
    
    // Calculate pending rewards
    const blocksStaked = currentBlock - stake.lastRewardBlock;
    const rewardShare = (stake.amount / farm.totalStaked) * farm.rewardPerBlock * blocksStaked;
    
    stake.pendingRewards += rewardShare;
    stake.lastRewardBlock = currentBlock;
    
    // Transfer rewards and reset
    const rewards = stake.pendingRewards;
    stake.pendingRewards = 0;
    
    await stake.save();
    
    return { rewards, stake };
  }
  
  async getCurrentBlock() {
    // In production, get from blockchain
    return Math.floor(Date.now() / 1000);
  }
}

const yieldFarming = new YieldFarming();

// ===== API ROUTES =====

// DEX Routes
app.get('/api/dex/pools', async (req, res) => {
  try {
    const pools = await LiquidityPool.find().sort('-totalLiquidity');
    res.json({ pools });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/dex/swap', async (req, res) => {
  try {
    const { poolId, tokenIn, amountIn, user, slippage } = req.body;
    
    const result = await dex.executeSwap(poolId, tokenIn, amountIn, user);
    
    // Check slippage
    if (result.swap.priceImpact > slippage) {
      return res.status(400).json({ error: 'Price impact exceeds slippage tolerance' });
    }
    
    res.json({ swap: result.swap, pool: result.pool });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/dex/liquidity/add', async (req, res) => {
  try {
    const { poolId, token0Amount, token1Amount, user } = req.body;
    const result = await dex.addLiquidity(poolId, token0Amount, token1Amount, user);
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/dex/liquidity/remove', async (req, res) => {
  try {
    const { poolId, lpTokens, user } = req.body;
    const result = await dex.removeLiquidity(poolId, lpTokens, user);
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Yield Farming Routes
app.get('/api/farms', async (req, res) => {
  try {
    const farms = await Farm.find().sort('-apr');
    res.json({ farms });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/farms/stake', async (req, res) => {
  try {
    const { farmId, amount, user } = req.body;
    const stake = await yieldFarming.stake(farmId, amount, user);
    res.json({ stake });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/farms/claim', async (req, res) => {
  try {
    const { stakeId, user } = req.body;
    const result = await yieldFarming.claimRewards(stakeId, user);
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// NFT Marketplace Routes
app.get('/api/nft/sales', async (req, res) => {
  try {
    const sales = await NFTSale.find({ status: 'active' }).populate('nft');
    res.json({ sales });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/nft/sales/:id/bid', async (req, res) => {
  try {
    const { amount, bidder } = req.body;
    const sale = await NFTSale.findById(req.params.id);
    
    if (sale.type !== 'auction') {
      return res.status(400).json({ error: 'Not an auction' });
    }
    
    if (sale.auction.endTime < new Date()) {
      return res.status(400).json({ error: 'Auction ended' });
    }
    
    const currentBid = sale.auction.bids.length > 0 
      ? Math.max(...sale.auction.bids.map(b => b.amount))
      : sale.auction.reservePrice;
    
    if (amount <= currentBid) {
      return res.status(400).json({ error: 'Bid too low' });
    }
    
    sale.auction.bids.push({ bidder, amount, timestamp: new Date() });
    await sale.save();
    
    res.json({ sale });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// DAO Routes
app.get('/api/dao/proposals', async (req, res) => {
  try {
    const proposals = await Proposal.find().sort('-startTime');
    res.json({ proposals });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/dao/proposals', async (req, res) => {
  try {
    const proposal = await Proposal.create(req.body);
    res.status(201).json({ proposal });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/dao/proposals/:id/vote', async (req, res) => {
  try {
    const { vote, user, power } = req.body;
    const proposal = await Proposal.findById(req.params.id);
    
    if (proposal.endTime < new Date()) {
      return res.status(400).json({ error: 'Voting ended' });
    }
    
    proposal.votes[vote] += power;
    proposal.voters.push({ user, vote, power });
    
    await proposal.save();
    
    res.json({ proposal });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Start server
const PORT = process.env.PORT || 5008;
app.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════╗
║   ⛓️ Rizz Blockchain - Enhanced DeFi       ║
║   Running on port ${PORT}                      ║
║                                            ║
║   Features:                                ║
║   - DEX (Decentralized Exchange)           ║
║   - Yield Farming & Staking                ║
║   - NFT Marketplace with Auctions          ║
║   - DAO Governance                         ║
╚════════════════════════════════════════════╝
  `);
});

module.exports = app;
