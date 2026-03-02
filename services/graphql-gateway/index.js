/**
 * GraphQL Gateway - Apollo Federation
 * Unified GraphQL API layer over all microservices
 */

const { ApolloServer } = require('@apollo/server');
const { expressMiddleware } = require('@apollo/server/express4');
const { ApolloGateway } = require('@apollo/gateway');
const express = require('express');
const cors = require('cors');
const { createServer } = require('http');
const { makeExecutableSchema } = require('@graphql-tools/schema');
const { GraphQLScalarType, Kind } = require('graphql');
const Redis = require('ioredis');
const client = require('prom-client');

// Prometheus metrics
const register = new client.Registry();
const gqlRequests = new client.Counter({
  name: 'graphql_requests_total',
  help: 'Total GraphQL requests',
  labelNames: ['operation', 'status'],
  registers: [register]
});

const gqlLatency = new client.Histogram({
  name: 'graphql_request_duration_seconds',
  help: 'GraphQL request latency',
  labelNames: ['operation'],
  buckets: [0.01, 0.05, 0.1, 0.5, 1, 2, 5],
  registers: [register]
});

// Redis for caching
const redis = new Redis(process.env.REDIS_URL || 'redis://redis:6379/6');

// Custom scalars
const DateTime = new GraphQLScalarType({
  name: 'DateTime',
  description: 'DateTime custom scalar',
  serialize(value) {
    return value.getTime();
  },
  parseValue(value) {
    return new Date(value);
  },
  parseLiteral(ast) {
    if (ast.kind === Kind.INT) {
      return new Date(parseInt(ast.value, 10));
    }
    return null;
  }
});

// Gateway configuration
const gateway = new ApolloGateway({
  supergraphSdl: new IntrospectAndCompose({
    subgraphs: [
      { name: 'users', url: process.env.USERS_SERVICE_URL || 'http://api:5000/graphql' },
      { name: 'posts', url: process.env.POSTS_SERVICE_URL || 'http://api:5000/graphql' },
      { name: 'analytics', url: process.env.ANALYTICS_SERVICE_URL || 'http://analytics:8001/graphql' },
      { name: 'search', url: process.env.SEARCH_SERVICE_URL || 'http://search:8003/graphql' },
      { name: 'storage', url: process.env.STORAGE_SERVICE_URL || 'http://storage:8004/graphql' },
    ]
  }),
  buildService({ name, url }) {
    return {
      executor: async (requestContext) => {
        const { request, context } = requestContext;
        
        // Add tracing
        const endTimer = gqlLatency.startTimer({ operation: request.operationName });
        
        try {
          const response = await fetch(url, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': context?.token ? `Bearer ${context.token}` : '',
              'X-Request-ID': context?.requestId
            },
            body: JSON.stringify(request)
          });
          
          const result = await response.json();
          endTimer();
          
          // Count request
          gqlRequests.inc({ 
            operation: request.operationName || 'unknown',
            status: result.errors ? 'error' : 'success'
          });
          
          return result;
        } catch (error) {
          endTimer();
          throw error;
        }
      }
    };
  }
});

// Rate limiting
const rateLimitMap = new Map();
function rateLimit(userId, limit = 100, window = 60000) {
  const now = Date.now();
  const key = `rate:${userId}`;
  
  const userRequests = rateLimitMap.get(key) || [];
  const recentRequests = userRequests.filter(time => now - time < window);
  
  if (recentRequests.length >= limit) {
    return false;
  }
  
  recentRequests.push(now);
  rateLimitMap.set(key, recentRequests);
  return true;
}

// Apollo Server
const server = new ApolloServer({
  gateway,
  plugins: [
    {
      async requestDidStart() {
        return {
          async willSendResponse({ response }) {
            // Cache successful queries
            if (response.kind === 'single' && !response.singleResult.errors) {
              const cacheKey = `gql:cache:${JSON.stringify(response.singleResult.data)}`;
              await redis.setex(cacheKey, 300, JSON.stringify(response.singleResult.data));
            }
          }
        };
      }
    }
  ],
  introspection: true,
  formatError: (error) => ({
    message: error.message,
    path: error.path,
    extensions: error.extensions
  })
});

// Express app
const app = express();
app.use(cors());
app.use(express.json());

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'graphql-gateway',
    version: '1.0.0',
    timestamp: new Date().toISOString()
  });
});

// Metrics endpoint
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
});

// GraphQL endpoint
app.use('/graphql', expressMiddleware(server, {
  context: async ({ req }) => ({
    token: req.headers.authorization?.split(' ')[1],
    requestId: req.headers['x-request-id'],
    userId: req.headers['x-user-id'],
    rateLimit: (limit, window) => rateLimit(req.headers['x-user-id'], limit, window)
  })
}));

// GraphQL Playground
app.use('/playground', expressMiddleware(server));

// Start server
const PORT = process.env.PORT || 5001;
const httpServer = createServer(app);

httpServer.listen(PORT, () => {
  console.log(`🚀 GraphQL Gateway running at http://localhost:${PORT}/graphql`);
  console.log(`🎮 Playground at http://localhost:${PORT}/playground`);
  console.log(`📊 Metrics at http://localhost:${PORT}/metrics`);
});

module.exports = { app, server };
